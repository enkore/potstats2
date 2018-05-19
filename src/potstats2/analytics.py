from urllib.parse import urlparse
from time import perf_counter

import click
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from .db import get_session, Post, PostLinks, QuoteRelation, LinkRelation, LinkType
from .util import ElapsedProgressBar, chunk_query


@click.command()
def main():
    session = get_session()
    session.query(QuoteRelation).delete()
    session.query(PostLinks).delete()

    edge_insert_stmt = insert(QuoteRelation.__table__)
    edge_insert_stmt = edge_insert_stmt.on_conflict_do_update(
        index_elements=QuoteRelation.__table__.primary_key.columns,
        set_=dict(count=edge_insert_stmt.excluded.count + QuoteRelation.__table__.c.count)
    )

    url_insert_stmt = insert(PostLinks.__table__)
    url_insert_stmt = url_insert_stmt.on_conflict_do_update(
        index_elements=PostLinks.__table__.primary_key.columns,
        set_=dict(count=url_insert_stmt.excluded.count + PostLinks.__table__.c.count)
    )

    num_posts = session.query(Post).count()
    with ElapsedProgressBar(length=num_posts, label='Analyzing posts') as bar:
        pid_to_poster_uid = dict(session.query(Post.pid, Post.poster_uid))
        edges = []
        urls = []
        n = 0

        for post in chunk_query(session.query(Post), Post.pid, chunk_size=10000):
            analyze_post(post, pid_to_poster_uid, edges, urls)
            n += 1

            if n > 2000:
                bar.update(n)
                n = 0

            if len(edges) > 1000:
                session.execute(edge_insert_stmt, edges)
                edges.clear()
            if len(urls) > 1000:
                session.execute(url_insert_stmt, urls)
                urls.clear()

        session.execute(edge_insert_stmt, edges)
        session.execute(url_insert_stmt, urls)
        edges.clear()
        urls.clear()

    print('Analyzed {} posts in {:.1f} s ({:.0f} posts/s),\n'
          'discovering {} quote relationships and {} quotes.'
          .format(num_posts, bar.elapsed, num_posts / bar.elapsed,
                  session.query(QuoteRelation).count(), session.query(func.sum(QuoteRelation.count)).one()))

    analyze_post_links(session)

    session.commit()
    from .backend import cache
    cache.invalidate()


def analyze_post_links(session):
    t0 = perf_counter()
    LinkRelation.refresh(session)
    elapsed = perf_counter() - t0
    print('Aggregated {} links into {} link relationships in {:.1f} s.'
          .format(session.query(PostLinks).count(), session.query(LinkRelation).count(), elapsed))


def analyze_post(post, pid_to_poster_uid, edges, urls):
    in_tag = False
    capture_contents = False
    current_tag = ''
    tag_contents = ''
    quote_level = 0

    def update_edge(quote_tag, poster_uid):
        try:
            # quote=tid,pid,"user"
            _, _, params = quote_tag.partition('=')
            # tid,pid,"user"
            tid, pid, user_name = params.split(',', maxsplit=3)
            pid = int(pid)
        except ValueError as ve:
            print('PID %d: Malformed quote= tag: %r (%s)' % (post.pid, quote_tag, ve))
            return

        try:
            quotee_uid = pid_to_poster_uid[pid]
        except KeyError:
            print('PID %d: Quoted PID not on record: %d' % (post.pid, pid))
            return

        edges.append(dict(quoter_uid=poster_uid, quotee_uid=quotee_uid, count=1))

    def update_url(url, link_type, post):
        if url:
            if url[0] == url[-1] and url[0] in ("'", '"'):
                url = url[1:-1]
            if url[0] == '/':
                url = 'http://forum.mods.de' + url
            if url.startswith('./'):
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
                update_edge(current_tag, post.poster_uid)

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
