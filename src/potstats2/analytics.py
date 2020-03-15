import datetime
import json
import os
import signal
import select
import sys
import threading
from urllib.parse import urlparse
from queue import Queue
from time import perf_counter

import click
from sqlalchemy import bindparam, and_, func
from sqlalchemy.dialects.postgresql import insert
from pyroaring import BitMap
from lxml import html

try:
    import elasticsearch.helpers
except ImportError:
    pass

from . import dal, config
from .db import get_session, TierType, Thread
from .db import Post, PostContent
from .db import PostLinks, PostQuotes, LinkRelation, LinkType
from .db import PosterStats, DailyStats, QuoteRelation
from .db import MyModsUserStaging, UserTier, AccountState
from .util import ElapsedProgressBar


@click.command()
@click.option('--skip-posts', is_flag=True, default=False)
@click.option('--state-file', type=click.Path(dir_okay=False))
def main(skip_posts, state_file):
    config.setup_debugger()
    session = get_session()

    if not skip_posts:
        analyze_posts(session, state_file)

    index_threads(session)
    parse_user_profiles(session)
    aggregate_post_links(session)
    bake_poster_stats(session)
    bake_daily_stats(session)
    bake_quote_relation(session)

    session.commit()
    from .backend import cache
    cache.invalidate()


def iter_posts(session, nchild, pids, chunk_size=10000):
    pivots = (pids[len(pids) // 4], pids[len(pids) // 2], pids[len(pids) // 4 * 3])
    if nchild == 0:
        ec = and_(PostContent.pid >= pids[0], PostContent.pid < pivots[0])
        ep = and_(Post.pid >= pids[0], Post.pid < pivots[0])
    elif nchild == 1:
        ec = and_(PostContent.pid >= pivots[0], PostContent.pid < pivots[1])
        ep = and_(Post.pid >= pivots[0], Post.pid < pivots[1])
    elif nchild == 2:
        ec = and_(PostContent.pid >= pivots[1], PostContent.pid < pivots[2])
        ep = and_(Post.pid >= pivots[1], Post.pid < pivots[2])
    elif nchild == 3:
        ec = PostContent.pid >= pivots[2]
        ep = Post.pid >= pivots[2]

    start_pid = bindparam('start_pid')
    contents = (
        session
        .query(PostContent)
        .filter(PostContent.pid > start_pid)
        .filter(ec)
        .order_by(PostContent.pid)
        .limit(chunk_size)
        .subquery()
    )
    query = (
        session
        .query(Post.pid, Post.poster_uid, contents.c.content, contents.c.title)
        .join(contents, contents.c.pid == Post.pid)
        .filter(Post.pid > start_pid)
        .filter(ep)
        .order_by(Post.pid)
        .limit(chunk_size)
    )

    last_pid = 0
    while True:
        posts = query.params(start_pid=last_pid).all()
        yield from posts
        if not posts:
            break
        last_pid = posts[-1].pid


ESP_POISON = object()


def elasticsearch_pusher(queue):
    es = config.elasticsearch_client()
    if not es:
        return
    while True:
        bodies = queue.get()
        if bodies is ESP_POISON:
            break
        actions = [dict(_index='post', _type='post', _id=body['pid'], _source=body) for body in bodies]
        elasticsearch.helpers.bulk(es, actions, chunk_size=10000, max_chunk_bytes=100 * 1024 * 1024)


def analyze_posts_process(nchild, progress_fd, pids, pids_to_process):
    quote_insert_stmt = insert(PostQuotes.__table__)
    quote_insert_stmt = quote_insert_stmt.on_conflict_do_update(
        index_elements=PostQuotes.__table__.primary_key.columns,
        set_=dict(count=quote_insert_stmt.excluded.count + PostQuotes.__table__.c.count)
    )

    url_insert_stmt = insert(PostLinks.__table__)
    url_insert_stmt = url_insert_stmt.on_conflict_do_update(
        index_elements=PostLinks.__table__.primary_key.columns,
        set_=dict(count=url_insert_stmt.excluded.count + PostLinks.__table__.c.count)
    )

    session = get_session()

    quotes = []
    urls = []
    search_contents = []
    elasticsearch_queue = Queue(maxsize=10)  # maximum of ~10×10000 = 100k pending ES index updates
    elasticsearch_thread = threading.Thread(target=elasticsearch_pusher, args=(elasticsearch_queue,))
    elasticsearch_thread.start()
    n = 0

    for post in iter_posts(session, nchild, pids_to_process):
        analyze_post(post, pids, quotes, urls, search_contents)
        n += 1

        if n > 2000:
            os.write(progress_fd, n.to_bytes(4, byteorder='little'))
            n = 0

        if len(quotes) > 1000:
            session.execute(quote_insert_stmt, quotes)
            quotes.clear()
        if len(urls) > 1000:
            session.execute(url_insert_stmt, urls)
            urls.clear()
        if len(search_contents) > 10000:
            elasticsearch_queue.put(search_contents)
            search_contents = []

    if quotes:
        session.execute(quote_insert_stmt, quotes)
    if urls:
        session.execute(url_insert_stmt, urls)
    if search_contents:
        elasticsearch_queue.put(search_contents)
    quotes.clear()
    urls.clear()
    session.commit()
    elasticsearch_queue.put(ESP_POISON)
    elasticsearch_thread.join()

    os.write(progress_fd, n.to_bytes(4, byteorder='little'))
    os.write(progress_fd, b'\xff' * 4)


def read_state_file(state_file):
    try:
        with open(state_file, 'r') as fd:
            return json.load(fd)
    except (FileNotFoundError, TypeError):
        print('State file %s does not exist, starting from scratch' % state_file)
        return {
            'last_pid': 0,
        }


def write_state_file(state_file, last_pid):
    if not state_file:
        return
    with open(state_file, 'w') as fd:
        json.dump({
            'last_pid': last_pid,
        }, fd)


def analyze_posts(session, state_file):
    pids = BitMap()
    last_pid = None
    while True:
        query = session.query(Post.pid)
        if last_pid:
            query = query.filter(Post.pid > last_pid)
        chunk = query.order_by(Post.pid).limit(100000).from_self(func.array_agg(Post.pid)).all()[0][0]
        if not chunk:
            break
        last_pid = chunk[-1]
        pids.update(chunk)

    bitmap_size = len(pids.serialize())
    print('PID bitmap size %d bytes, %d entries, %.2f bits per entry' % (bitmap_size, len(pids), bitmap_size / len(pids) * 8))

    state = read_state_file(state_file)
    pids_to_process = pids.to_array()
    try:
        slice_index = pids_to_process.index(state['last_pid'])
    except ValueError:
        slice_index = 0
    pids_to_process = pids_to_process[slice_index:]
    pids_to_process = BitMap(pids_to_process)

    num_posts = len(pids_to_process)
    continuing = bool(slice_index)
    es = config.elasticsearch_client()
    if not continuing:
        session.query(PostQuotes).delete()
        session.query(PostLinks).delete()
        session.commit()
        if es:
            es.indices.delete('post', ignore=[404])
            es.indices.create('post', body={
                'settings': {
                    'refresh_interval': '300s',
                    'number_of_shards': 1,
                },
                'mappings': {
                    'post': {
                        'properties': {
                            'content': {
                                'type': 'text',
                                'analyzer': 'german',
                            },
                            'title': {
                                'type': 'text',
                                'analyzer': 'german',
                            },
                            'poster_uid': {
                                'type': 'integer',
                            },
                            'pid': {
                                'type': 'integer',
                            }
                        }
                    }
                }
            })
    if es:
        es.indices.put_settings({
            'index': {
                'refresh_interval': -1,
            }
        }, 'post')

    children = {}
    for nchild in range(4):
        p, c = os.pipe()
        child_pid = os.fork()
        if not child_pid:
            progress_fd = c
            session.invalidate()
            session.bind.dispose()
            analyze_posts_process(nchild, progress_fd, pids, pids_to_process)
            sys.exit(0)
        children[p] = child_pid

    with ElapsedProgressBar(length=num_posts, label='Analyzing posts') as bar:
        while children:
            r, w, x = select.select(list(children), [], [])
            for fd in r:
                v = os.read(fd, 4)
                if v == b'\xff' * 4:
                    pid = children.pop(fd)
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                else:
                    bar.update(int.from_bytes(v, byteorder='little'))

    if es:
        es.indices.refresh('post')
        es.indices.put_settings({
            'index': {
                'refresh_interval': '300s',
            }
        }, 'post')

    print('Analyzed {} posts in {:.1f} s ({:.0f} posts/s).'.format(bar.pos, bar.elapsed, num_posts / bar.elapsed))

    write_state_file(state_file, pids_to_process.max())


def index_threads(session):
    es = config.elasticsearch_client()
    if not es:
        return

    es.indices.delete('thread', ignore=[404])
    es.indices.create('thread', body={
        'settings': {
            'refresh_interval': '300s',
            'number_of_shards': 1,
        },
        'mappings': {
            'thread': {
                'properties': {
                    'title': {
                        'type': 'text',
                        'analyzer': 'german',
                    },
                    'subtitle': {
                        'type': 'text',
                        'analyzer': 'german',
                    },
                    'tid': {
                        'type': 'integer',
                    }
                }
            }
        }
    })

    t0 = perf_counter()
    threads = session.query(Thread.tid, Thread.title, Thread.subtitle).all()
    actions = [dict(_index='thread', _type='thread', _id=thread.tid, _source=thread._asdict()) for thread in threads]
    elasticsearch.helpers.bulk(es, actions, chunk_size=200000, max_chunk_bytes=100 * 1024 * 1024)
    es.indices.refresh('thread')
    elapsed = perf_counter() - t0
    print('Indexed {} threads in {:.1f} s.'.format(len(threads), elapsed))


def aggregate_post_links(session):
    t0 = perf_counter()
    LinkRelation.refresh(session)
    elapsed = perf_counter() - t0
    print('Aggregated {} links into {} link relationships in {:.1f} s.'
          .format(session.query(PostLinks).count(), session.query(LinkRelation).count(), elapsed))


def bake_poster_stats(session):
    t0 = perf_counter()
    PosterStats.refresh(session, dal.poster_stats_agg(session))
    elapsed = perf_counter() - t0
    print('Baked poster stats ({} rows) in {:.1f} s.'.format(session.query(PosterStats).count(), elapsed))


def bake_daily_stats(session):
    t0 = perf_counter()
    session.query(DailyStats).delete()
    for day in dal.daily_statistics_agg(session).all():
        day = day._asdict()
        day['active_users'] = BitMap(day['active_users']).serialize()
        day.pop('active_threads')
        session.add(DailyStats(**day))
    elapsed = perf_counter() - t0
    print('Baked daily stats ({} rows) in {:.1f} s.'.format(session.query(DailyStats).count(), elapsed))


def bake_quote_relation(session):
    t0 = perf_counter()
    QuoteRelation.refresh(session, dal.social_graph_agg(session))
    elapsed = perf_counter() - t0
    print('Baked quote relation ({} rows) in {:.1f} s.'.format(session.query(QuoteRelation).count(), elapsed))


def analyze_post(post, pids, quotes, urls, search_contents=None):
    in_tag = False
    in_quoted_string = False
    capture_contents = False
    current_tag = ''
    tag_contents = ''
    quote_level = 0

    def update_edge(quote_tag, post):
        try:
            # quote=tid,pid,"user"
            _, _, params = quote_tag.partition('=')
            # tid,pid,"user"
            tid, pid, user_name = params.split(',', maxsplit=2)
            pid = int(pid)
            if pid not in pids:  # may raise OverflowError
                print('PID %d: Quoted PID not on record: %d' % (post.pid, pid))
                return
        except ValueError as ve:
            print('PID %d: Malformed quote= tag: %r (%s)' % (post.pid, quote_tag, ve))
            return
        except OverflowError:
            print('PID %d: Invalid quoted PID %d' % (post.pid, pid))
            return

        quotes.append(dict(pid=post.pid, quoted_pid=pid, count=1))

    def update_url(url, link_type, post):
        if url:
            if url.startswith('data:'):
                print('PID %d: Skipping data: URL' % post.pid)
                return
            if len(url) > 300:
                url = url[:300]
            if url[0] == url[-1] and url[0] in ("'", '"'):
                url = url[1:-1]
            if url.startswith('/'):
                url = 'http://forum.mods.de' + url
            elif url.startswith('./'):
                url = 'http://forum.mods.de/bb/' + url[2:]
            if '://' not in url:
                url = 'http://' + url
        try:
            domain = urlparse(url).netloc
        except ValueError:
            print('PID %d: Could not parse URL: %r' % (post.pid, url))
            return

        urls.append(dict(pid=post.pid, url=url, domain=domain, count=1, type=link_type))

    def index_for_search(post, original_content):
        if search_contents is not None:
            search_contents.append(dict(
                pid=post.pid,
                poster_uid=post.poster_uid,
                content=original_content,
                title=post.title,
            ))

    if not post.content:
        return

    original_content = ''

    for char in post.content:
        if not in_quoted_string and char == '[':
            in_tag = True
            current_tag = ''
        elif not in_quoted_string and char == ']':
            in_tag = False

            if current_tag.startswith('quote'):
                quote_level += 1
            elif current_tag == '/quote':
                quote_level -= 1

            if quote_level == 1 and current_tag.startswith('quote='):
                update_edge(current_tag, post)

            if quote_level == 0:
                if current_tag.startswith('url='):
                    update_url(current_tag[4:], LinkType.link, post)
                elif current_tag == 'url':
                    capture_contents = True
                elif current_tag == '/url' and capture_contents:
                    update_url(tag_contents, LinkType.link, post)
                    capture_contents = False
                    tag_contents = ''
                elif current_tag == 'img':
                    capture_contents = True
                elif current_tag == '/img' and capture_contents:
                    update_url(tag_contents, LinkType.image, post)
                    capture_contents = False
                    tag_contents = ''
                elif current_tag in ('video', 'video play', 'video autoplay'):
                    capture_contents = True
                elif current_tag == '/video' and capture_contents:
                    update_url(tag_contents, LinkType.video, post)
                    capture_contents = False
                    tag_contents = ''
        elif in_tag:
            current_tag += char
            if char == '"':
                in_quoted_string = not in_quoted_string
        elif capture_contents:
            tag_contents += char
        if quote_level == 0 and not in_tag and char not in ('[', ']'):
            original_content += char

    if original_content:
        index_for_search(post, original_content)


def parse_user_profiles(session):
    with ElapsedProgressBar(session.query(MyModsUserStaging).all(), label='Parsing user profiles', show_pos=True) as bar:
        for mmu in bar:
            page = html.fromstring(mmu.html)
            parse_user_profile(session, mmu.user, page)


def get_user_tier(session, user, page):
    def strip_extra_url_stuff(src):
        prefix = 'http://forum.mods.de/bb/img/rank/'
        assert src.startswith(prefix)
        assert src.endswith('.gif')
        return src[len(prefix):-len('.gif')]

    bars_img = page.cssselect('td.vam.avatar img[alt="*"]')
    tier_name = page.cssselect('span.rang')[0].text
    if user.uid == 28377:
        assert not tier_name
        tier_name = 'enos'
    else:
        if not tier_name and not bars_img:
            return None
        assert tier_name

    bar_map = {
        'links': None,
        'rechts': None,
        'orange': 'o',
        'gruen': 'g',
        'schwarz': 's',
        'empty': 'e',
        'rot': 'r',
        'blau': 'b',
        'hellblau': 'h',
    }

    if len(bars_img) in (9, 11):
        # Usually 11, but some ranks miss links|rechts, making it 9. E.g. UID#12216.
        bars = []

        for bar_img in bars_img:
            src = strip_extra_url_stuff(bar_img.attrib['src'])
            mapped = bar_map[src]
            if mapped:
                bars.append(mapped)

        tier_bar = ''.join(bars)
        tier_type = TierType.standard
    elif len(bars_img) == 1:
        src = strip_extra_url_stuff(bars_img[0].attrib['src'])
        tier_bar = src
        tier_type = TierType.special
    elif len(bars_img) == 0:
        tier_bar = ''
        tier_type = TierType.special
    elif len(bars_img) == 7:
        srcs = [strip_extra_url_stuff(img.attrib['src']) for img in bars_img]
        if set(srcs) == {'herz1'}:
            tier_bar = 'herz1'
            tier_type = TierType.special
        else:
            # UID#143
            bars = []
            for src in srcs:
                mapped = bar_map[src]
                if mapped:
                    bars.append(mapped)
            tier_bar = ''.join(bars)
            tier_type = TierType.special

    return session.query(UserTier).filter_by(name=tier_name, bars=tier_bar, type=tier_type).one_or_none() \
           or UserTier(name=tier_name, bars=tier_bar, type=tier_type)


def parse_user_profile(session, user, page):
    user.tier = get_user_tier(session, user, page)

    kv_trs = page.cssselect('#content tr:not(.bar)')[:5]
    for key_value_tr in kv_trs:
        key = key_value_tr.cssselect('.attrn')[0].text
        value = key_value_tr.cssselect('.attrv')[0].text

        if user.uid == 1 and key in ('Dabei seit:', 'Zuletzt im Board:'):
            # <!-- seit grauer Vorzeit. -->
            # <!-- genau jetzt. -->
            user.registered = None
            user.last_seen = None
            continue

        if key == 'Benutzername:':
            value = key_value_tr.cssselect('.attrv div')[0].tail.strip()
            if value != user.name:
                assert value
                user.name = value
        elif key == 'Dabei seit:':
            date = ' '.join(value.split(' ')[:2])
            user.registered = datetime.datetime.strptime(date, FORUM_DATETIME_FORMAT_NO_SECONDS)
        elif key == 'Zuletzt im Board:':
            maybe_private = key_value_tr.cssselect('.attrv em')
            if maybe_private:
                assert maybe_private[0].text == 'privat'
                user.last_seen = None
            else:
                user.last_seen = datetime.datetime.strptime(value, FORUM_DATETIME_FORMAT_NO_SECONDS)
        elif key == 'Status:':
            user.online_status = value
        elif key == 'Accountstatus:':
            if value.startswith('gesperrt bis'):
                value = value[len('gesperrt bis '):]
                user.account_state = AccountState.locked_temp
                user.locked_until = datetime.datetime.strptime(value, FORUM_DATE_FORMAT)
            else:
                user.account_state = {
                    'aktiv': AccountState.active,
                    'gesperrt': AccountState.locked,
                    'noch nicht freigeschaltet': AccountState.not_unlocked,
                }[value]
                user.locked_until = None

    user.user_profile_exists = True

FORUM_DATETIME_FORMAT_NO_SECONDS = '%d.%m.%Y %H:%M'
FORUM_DATE_FORMAT = '%d.%m.%Y'
