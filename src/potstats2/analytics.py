from urllib.parse import urlparse
from time import perf_counter

import click
from sqlalchemy import func, bindparam
from sqlalchemy.dialects.postgresql import insert

from . import dal, config
from .db import get_session
from .db import Post, PostContent
from .db import PostLinks, PostQuotes, LinkRelation, LinkType
from .db import PosterStats, DailyStats
from .util import ElapsedProgressBar, chunk_query


@click.command()
@click.option('--skip-posts', is_flag=True, default=False)
def main(skip_posts):
    config.setup_debugger()
    session = get_session()

    if not skip_posts:
        analyze_posts(session)

    aggregate_post_links(session)
    bake_poster_stats(session)
    bake_daily_stats(session)

    session.commit()
    from .backend import cache
    cache.invalidate()


def iter_posts(session, chunk_size=10000):
    start_pid = bindparam('start_pid')
    contents = session.query(PostContent).filter(PostContent.pid > start_pid).order_by(PostContent.pid).limit(chunk_size).subquery()
    query = (
        session
        .query(Post.pid, Post.poster_uid, contents.c.content, contents.c.title)
        .join(contents, contents.c.pid == Post.pid)
        .filter(Post.pid > start_pid)
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


def analyze_posts(session):
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

    session.query(PostQuotes).delete()
    session.query(PostLinks).delete()

    num_posts = session.query(Post).count()
    with ElapsedProgressBar(length=num_posts, label='Analyzing posts') as bar:
        pids = set([n for n, in session.query(Post.pid)])
        quotes = []
        urls = []
        n = 0

        for post in iter_posts(session):
            analyze_post(post, pids, quotes, urls)
            n += 1

            if n > 2000:
                bar.update(n)
                n = 0

            if len(quotes) > 1000:
                session.execute(quote_insert_stmt, quotes)
                quotes.clear()
            if len(urls) > 1000:
                session.execute(url_insert_stmt, urls)
                urls.clear()

        if quotes:
            session.execute(quote_insert_stmt, quotes)
        if urls:
            session.execute(url_insert_stmt, urls)
        quotes.clear()
        urls.clear()

    print('Analyzed {} posts in {:.1f} s ({:.0f} posts/s).'.format(num_posts, bar.elapsed, num_posts / bar.elapsed))


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
    DailyStats.refresh(session, dal.daily_statistics_agg(session))
    elapsed = perf_counter() - t0
    print('Baked daily stats ({} rows) in {:.1f} s.'.format(session.query(DailyStats).count(), elapsed))


def analyze_post(post, pids, quotes, urls):
    in_tag = False
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
        except ValueError as ve:
            print('PID %d: Malformed quote= tag: %r (%s)' % (post.pid, quote_tag, ve))
            return

        if pid not in pids:
            print('PID %d: Quoted PID not on record: %d' % (post.pid, pid))
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

    if not post.content:
        return

    for char in post.content:
        if char == '[':
            in_tag = True
            current_tag = ''
        elif char == ']':
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
        elif capture_contents:
            tag_contents += char
