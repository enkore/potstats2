import functools
from time import perf_counter
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import click
from click._termui_impl import ProgressBar

from .api import XmlApiConnector
from ..config import setup_debugger
from ..db import get_session, Category, Board, Thread, Post, User, WorldeaterState


def i2b(boolean_xml_tag):
    return boolean_xml_tag.attrib['value'] == '1'


class ElapsedProgressBar(ProgressBar):
    def __init__(self, iterable=None, length=None, label=None, show_eta=True,
                show_percent=None, show_pos=False,
                item_show_func=None, fill_char='#', empty_char='-',
                bar_template='%(label)s  [%(bar)s]  %(info)s',
                info_sep='  ', width=36, file=None, color=None):
        super().__init__(iterable=iterable, length=length, show_eta=show_eta,
                       show_percent=show_percent, show_pos=show_pos,
                       item_show_func=item_show_func, fill_char=fill_char,
                       empty_char=empty_char, bar_template=bar_template,
                       info_sep=info_sep, file=file, label=label,
                       width=width, color=color)

    def __enter__(self):
        self.t0 = perf_counter()
        return super().__enter__()

    def render_finish(self):
        td = perf_counter() - self.t0
        self.show_eta = False
        self._last_line = ""
        self.render_progress()
        self.file.write(' ... elapsed %.1f s' % td)
        super().render_finish()


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


def sync_boards(categories, session):
    num_boards = len(categories.findall('.//boards/board'))
    with ElapsedProgressBar(length=num_boards, label='Syncing boards') as bar:
        for board in categories.findall('./category/boards/board'):
            bid = int(board.attrib['id'])
            dbboard = session.query(Board).get(bid) or Board(bid=bid)
            dbboard.name = board.find('./name').text
            dbboard.description = board.find('./description').text
            dbboard.cid = int(board.find('./in-category').attrib['id'])
            session.add(dbboard)
            bar.update(1)
        session.commit()


def datetime_from_xml(date_tag):
    return datetime.fromtimestamp(int(date_tag.attrib['timestamp']), timezone.utc)


def merge_posts(session, dbthread, posts):
    i = 0
    for i, post in enumerate(posts):
        pid = int(post.attrib['id'])
        dbpost = session.query(Post).get(pid) or Post(pid=pid, tid=dbthread.tid)
        dbpost.poster_uid = User.from_xml(session, post.find('./user')).uid
        dbpost.timestamp = datetime_from_xml(post.find('./date'))
        edited = post.find('./message/edited')
        dbpost.edit_count = int(edited.attrib['count'])
        if dbpost.edit_count:
            dbpost.last_edit_uid = User.from_xml(session, edited.find('./lastedit/user')).uid
            dbpost.last_edit_timestamp = datetime_from_xml(edited.find('./lastedit/date'))
        dbpost.title = post.find('./message/title').text
        dbpost.content = post.find('./message/content').text
        session.add(dbpost)
    return i + 1


def merge_pages(api, session, dbthread, start_page=None):
    return merge_posts(session, dbthread, api.iter_thread(dbthread.tid, start_page))


def main():
    setup_debugger()
    print('nomnomnom')
    t0 = perf_counter()
    api = XmlApiConnector()
    session = get_session()

    categories = sync_categories(api, session)
    sync_boards(categories, session)

    # I'd be cool to just have the PID in the minified XML:post, but well.
    # _, latest_post_thread = max((int(post.find('date').attrib['timestamp']), post.find('in-thread'))
    #                            for post in categories.findall('.//post'))
    # print('Newest post in TID %s [%s]' % (latest_post_thread.attrib['id'], latest_post_thread.text))

    bid = 53  # pot 14 is love, pot is life
    board = api.board(bid)

    # This is incorrect, because we are working from newest to oldest
    newest_complete_thread = session.query(Thread).filter_by(is_closed=True).order_by(Thread.tid).first()
    if newest_complete_thread:
        # This is an easy shortcut that mostly works because Sammelthreads.
        newest_complete_tid = newest_complete_thread.tid
    else:
        ...
    newest_complete_tid = None

    with ElapsedProgressBar(length=int(board.find('./number-of-threads').attrib['value']),
                            show_pos=True, label='Syncing threads') as bar:
        for thread in api.iter_board(bid, oldest_tid=newest_complete_tid):
            tid = int(thread.attrib['id'])
            dbthread = session.query(Thread).get(tid) or Thread(tid=tid)
            dbthread.bid = bid
            dbthread.title = thread.find('./title').text
            dbthread.subtitle = thread.find('./subtitle').text
            dbthread.is_closed = i2b(thread.find('./flags/is-closed'))
            dbthread.is_sticky = i2b(thread.find('./flags/is-sticky'))
            dbthread.is_important = i2b(thread.find('./flags/is-important'))
            dbthread.is_announcement = i2b(thread.find('./flags/is-announcement'))
            dbthread.is_global = i2b(thread.find('./flags/is-global'))
            dbthread.hit_count = int(thread.find('./number-of-hits').attrib['value'])
            dbthread.est_number_of_replies = int(thread.find('./number-of-replies').attrib['value'])
            session.add(dbthread)
            bar.update(1)
        session.commit()

    # Possibly put this in the DB to checkpoint
    threads_needing_update = {}  # TID --> (start_page, number_of_posts_estimated)

    with ElapsedProgressBar(session.query(Thread).filter_by(bid=bid).all(),
                                     show_pos=True, label='Finding updated posts') as bar:
        for dbthread in bar:
            if dbthread.last_post:
                thread = api.thread(dbthread.tid, pid=dbthread.last_post)
                # Might advance dbthread.last_post to the last post on this page
                posts = thread.findall('./posts/post')
                merge_posts(api, session, dbthread, posts)
                pids = [int(post.attrib['id']) for post in posts]
                index_in_page = pids.index(dbthread.last_post)
                index_in_thread = int(thread.find('./posts').attrib['offset']) + index_in_page
                num_replies = int(thread.find('./number-of-replies').attrib['value'])
                if index_in_thread + 1 == num_replies:
                    continue
                threads_needing_update[dbthread.tid] = (int(thread.find('./posts').attrib['page']) + 1,
                                                        num_replies - index_in_thread)
            else:
                threads_needing_update[dbthread.tid] = (0,
                                                        dbthread.est_number_of_replies)

    total_posts = sum(nope for sp, nope in threads_needing_update.values())
    with ElapsedProgressBar(length=total_posts, show_pos=True, label='Merging updated posts') as bar:
        for tid, (start_page, estimated_number_of_posts) in threads_needing_update.items():
            dbthread = session.query(Thread).get(tid)
            num_merged_posts = merge_pages(api, session, dbthread, start_page)
            bar.update(num_merged_posts)
            session.commit()

    ws = WorldeaterState.get(session)
    ws.num_api_requests += api.num_requests
    nomnom_time = perf_counter() - t0
    ws.nomnom_time += int(nomnom_time)

    print('Statistics')
    print('----------------------> this session <-------> total <---')
    print('API requests            {:12d}           {:5d}'.format(api.num_requests, ws.num_api_requests))
    print('Nomnom time             {:12.0f}           {:5d}'.format(nomnom_time, ws.nomnom_time))

    session.commit()
