from time import perf_counter
from datetime import datetime, timezone

import click
from sqlalchemy import func, desc, event
from sqlalchemy.orm.attributes import set_attribute

from .api import XmlApiConnector
from ..config import setup_debugger
from ..db import get_session, Category, Board, Thread, Post, PostContent, User, WorldeaterState, WorldeaterThreadsNeedingUpdate
from ..util import ElapsedProgressBar
from ..backend import cache


def i2b(boolean_xml_tag):
    return boolean_xml_tag.attrib['value'] == '1'


def sync_categories(api, session):
    categories = api.boards()
    with ElapsedProgressBar(categories, label='Syncing categories') as bar:
        for category in bar:
            cid = int(category.attrib['id'])
            dbcat = session.query(Category).get(cid) or Category(cid=cid)
            dbcat.name = category.find('./name').text
            dbcat.description = category.find('./description').text
            session.add(dbcat)
        session.commit()
    return categories


def sync_boards(session, categories):
    num_boards = len(categories.findall('.//boards/board'))
    with ElapsedProgressBar(length=num_boards, label='Syncing boards') as bar:
        for board in categories.findall('./category/boards/board'):
            bid = int(board.attrib['id'])
            dbboard = session.query(Board).get(bid) or Board(bid=bid)
            dbboard.name = board.find('./name').text
            dbboard.description = board.find('./description').text
            dbboard.category = session.query(Category).get(int(board.find('./in-category').attrib['id']))
            session.add(dbboard)
            bar.update(1)
        session.commit()


def datetime_from_xml(date_tag):
    """Convert XML `<date timestamp=...>ISO-8601 date</date>` structure to datetime object."""
    return datetime.fromtimestamp(int(date_tag.attrib['timestamp']), timezone.utc)


def merge_posts(session, dbthread, posts):
    """
    Merge *posts* in thread *dbthread* into the database. Return number of posts processed.

    Update dbthread.last_post as required.
    """
    i, post = -1, None
    for i, post in enumerate(posts):
        pid = int(post.attrib['id'])
        # We roundtrip to the DB for each post here, but that's most likely not a problem
        # because we get at most 30 posts per 0.2 s (API rate limiting and network speed).
        dbpost = session.query(Post).get(pid) or Post(pid=pid, thread=dbthread)
        dbpost.poster = User.from_xml(session, post.find('./user'))
        dbpost.timestamp = datetime_from_xml(post.find('./date'))
        edited = post.find('./message/edited')
        dbpost.edit_count = int(edited.attrib['count'])
        if dbpost.edit_count:
            dbpost.last_edit_user = User.from_xml(session, edited.find('./lastedit/user'))
            dbpost.last_edit_timestamp = datetime_from_xml(edited.find('./lastedit/date'))

        post_content = session.query(PostContent).get(pid) or PostContent(pid=pid)
        post_content.content = post.find('./message/content').text
        post_content.title = post.find('./message/title').text
        post.content = post_content
        post.content_length = len(post_content.content)

        is_hidden = post.attrib.get('is-hidden', '')
        if is_hidden:
            dbpost.is_hidden = True
            if is_hidden != 'texthidden':
                print('PID %d: Unknown value %r for attribute is-hidden.' % (pid, is_hidden))

        session.add(dbpost)
    if post and dbpost.pid > (dbthread.last_pid or 0):
        dbthread.last_post = dbpost
    return i + 1


def merge_pages(api, session, dbthread, start_page=None):
    """
    Merge all posts in thread *dbthread* starting from and including *start_page*.
    Return number of posts processed.
    """
    return merge_posts(session, dbthread, api.iter_thread(dbthread.tid, start_page))


def thread_from_xml(session, thread):
    """
    Create Thread object from board-level <thread> tag.

    Precondition: Board object must exist to satisfy foreign key constraint on Thread.bid.
    """
    tid = int(thread.attrib['id'])
    dbthread = session.query(Thread).get(tid) or Thread(tid=tid)
    dbthread.board = session.query(Board).get(int(thread.find('./in-board').attrib['id']))
    dbthread.title = thread.find('./title').text
    dbthread.subtitle = thread.find('./subtitle').text
    dbthread.is_closed = i2b(thread.find('./flags/is-closed'))
    dbthread.is_sticky = i2b(thread.find('./flags/is-sticky'))
    dbthread.is_important = i2b(thread.find('./flags/is-important'))
    dbthread.is_announcement = i2b(thread.find('./flags/is-announcement'))
    dbthread.is_global = i2b(thread.find('./flags/is-global'))
    dbthread.hit_count = int(thread.find('./number-of-hits').attrib['value'])
    dbthread.est_number_of_replies = int(thread.find('./number-of-replies').attrib['value'])
    return dbthread


def process_threads_needing_update(api, session):
    count, = session.query(func.count(WorldeaterThreadsNeedingUpdate.tid)).one()
    if not count:
        return
    est_post_count, = session.query(func.sum(WorldeaterThreadsNeedingUpdate.est_number_of_posts)).one()
    print('%d threads need an update with up to %d new posts.' % (count, est_post_count))
    with ElapsedProgressBar(length=est_post_count, show_pos=True, label='Merging updated posts') as bar:
        for tnu in session.query(WorldeaterThreadsNeedingUpdate).order_by('tid').all():
            dbthread = session.query(Thread).get(tnu.tid)
            num_merged_posts = merge_pages(api, session, dbthread, tnu.start_page)
            if num_merged_posts:  # ProgressBar.update doesn't like zero.
                bar.update(num_merged_posts)
            dbthread.first_post = session.query(Post).filter(Post.tid == dbthread.tid).order_by(Post.pid).first()
            if dbthread.can_be_complete:
                dbthread.is_complete = True
            session.delete(tnu)
            session.commit()


def process_board(api, session, bid, force_initial_pass):
    board = api.board(bid)

    initial_pass = not session.query(func.count(Thread.tid)).join(Thread.board).filter(Board.bid == bid)[0][0] \
                   or force_initial_pass

    newest_complete_tid = None
    if initial_pass:
        print('Initial pass on this board.')
    else:
        newest_complete_thread = session.query(Thread).filter_by(is_complete=True, bid=bid).join(
            Thread.last_post).order_by(desc(Post.pid)).first()
        if newest_complete_thread:
            # This is an easy shortcut that mostly works because Sammelthreads.
            newest_complete_tid = newest_complete_thread.tid
            print('Update pass on this board. Fixpoint thread is TID %d (%s).' % (
            newest_complete_tid, newest_complete_thread.title))

    thread_set = set()

    with ElapsedProgressBar(length=int(board.find('./number-of-threads').attrib['value']),
                            show_pos=True, label='Syncing threads') as bar:
        for thread in api.iter_board(bid, oldest_tid=newest_complete_tid, reverse=initial_pass):
            dbthread = thread_from_xml(session, thread)
            set_attribute(dbthread, 'tags', api.thread_tags(dbthread.tid))
            session.add(dbthread)
            thread_set.add(dbthread)
            bar.update(1)
        session.commit()

    with ElapsedProgressBar(thread_set,
                            show_pos=True, label='Finding updated threads') as bar:
        for dbthread in bar:
            tnu = WorldeaterThreadsNeedingUpdate(thread=dbthread)
            if dbthread.last_pid:
                thread = api.thread(dbthread.tid, pid=dbthread.last_post.pid)
                # Might advance dbthread.last_post to the last post on this page
                posts = thread.findall('./posts/post')
                merge_posts(session, dbthread, posts)
                pids = [int(post.attrib['id']) for post in posts]
                last_on_page = pids[-1] == dbthread.last_post.pid
                last_page = int(thread.find('./number-of-pages').attrib['value']) == int(
                    thread.find('./posts').attrib['page'])

                if last_on_page and (last_page or len(posts) < 30):
                    # Up to date on this thread if the last post we have is the last post on its page
                    # and we are on the last page. This method seems to be accurate, unlike
                    # XML:number-of-replies, which is not generally correct. (IIRC there are multiple corner cases
                    # involving hidden and deleted posts; some threads have XML:nor=500, but the last page
                    # has offset=500 and count=2, for example).
                    #
                    # Note that XML:number-of-pages is computed in bB based on XML:number-of-replies,
                    # so if a lot of replies are missing it will be wrong as well. We catch of most of these
                    # (~97 % in some theoretical sense) with the extra len(posts)<30 check, which will trigger
                    # if we are already on the last *real* page which is not full.
                    # If the stars align just right we'll always think a thread has some new posts and we will
                    # never be able to tell it doesn't.
                    if dbthread.can_be_complete:
                        dbthread.is_complete = True
                    continue

                index_in_page = pids.index(dbthread.last_post.pid)
                index_in_thread = int(thread.find('./posts').attrib['offset']) + index_in_page
                num_replies = int(thread.find('./number-of-replies').attrib['value'])
                # Due to XML:number-of-replies inaccuracy this might become negative
                estimated_number_of_posts = max(0, num_replies - index_in_thread)

                tnu.start_page = int(thread.find('./posts').attrib['page']) + 1
                tnu.est_number_of_posts = estimated_number_of_posts
            else:
                tnu.start_page = 0
                tnu.est_number_of_posts = dbthread.est_number_of_replies
            session.add(tnu)

    session.commit()


class StateTracker:
    def __init__(self, api, session):
        self.api = api
        self.session = session
        self.ws = WorldeaterState.get(session)
        self.t0 = perf_counter()
        self.num_api_requests0 = 0
        self.nomnom_time = 0

    def update(self):
        self.ws.num_api_requests += (self.api.num_requests - self.num_api_requests0)
        self.num_api_requests0 = self.api.num_requests
        t1 = perf_counter()
        self.ws.nomnom_time += int(t1 - self.t0)
        self.nomnom_time += t1 - self.t0
        self.t0 = t1


@click.command()
@click.option('--board-id', default=53)
@click.option('--only-tnu', default=False, is_flag=True)
@click.option('--force-initial-pass', default=False, is_flag=True)
def main(board_id, only_tnu, force_initial_pass):
    setup_debugger()
    print('nomnomnom')
    api = XmlApiConnector()
    session = get_session()
    st = StateTracker(api, session)
    event.listen(session, 'before_commit', lambda s: st.update())

    initial_post_count, = session.query(func.count(Post.pid)).one()
    initial_thread_count, = session.query(func.count(Thread.tid)).one()

    process_threads_needing_update(api, session)
    if not only_tnu:
        categories = sync_categories(api, session)
        sync_boards(session, categories)

        process_board(api, session, board_id, force_initial_pass=force_initial_pass)

        process_threads_needing_update(api, session)

    st.update()

    added_posts, = session.query(func.count(Post.pid) - initial_post_count).one()
    added_threads, = session.query(func.count(Thread.tid) - initial_thread_count).one()

    print('Statistics')
    print('----------------------> this session <--------------> total <---')
    print('API requests            {:12d}           {:12d}'.format(api.num_requests, st.ws.num_api_requests))
    print('Nomnom time             {:12.0f}           {:12d}'.format(st.nomnom_time, st.ws.nomnom_time))
    print('Added posts             {:12d}           {:12d}'.format(added_posts, initial_post_count + added_posts))
    print('Added threads           {:12d}           {:12d}'.format(added_threads, initial_thread_count + added_threads))

    session.commit()
    cache.invalidate()
