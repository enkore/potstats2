import enum
import sys
from urllib.parse import urlparse
from time import perf_counter

from sqlalchemy import create_engine, Column, ForeignKey, Integer, Unicode, UnicodeText, Boolean, TIMESTAMP, \
    CheckConstraint, func, Enum
from sqlalchemy.orm import sessionmaker, relationship, Query, Session, query_expression
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import insert

import click

from . import config
from .util import ElapsedProgressBar, chunk_query


def get_engine():
    db_url = config.get('DB')
    print('Database URL:', db_url, file=sys.stderr)
    return create_engine(db_url)


_global_session = None


def get_session():
    # not thread safe but if you do that you're an idiot anyway ¯\_(ツ)_/¯
    global _global_session
    if not _global_session:
        _global_session = sessionmaker(bind=get_engine())
    return _global_session()


@click.group()
def main():
    pass


@main.command()
def create_schema():
    engine = get_engine()
    Base.metadata.create_all(engine)


@main.command()
def analytics():
    session = get_session()
    session.query(QuoteRelation).delete()
    session.query(PostLinks).delete()

    num_posts = session.query(Post).count()
    with ElapsedProgressBar(length=num_posts, label='Analyzing posts') as bar:
        for post in chunk_query(session.query(Post), Post.pid, chunk_size=10000):
            analyze_post(session, post)
            bar.update(1)
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


def analyze_post(session, post):
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
            quotee_uid = session.query(Post).get(pid).poster_uid
        except AttributeError:
            print('PID %d: Quoted PID not on record: %d' % (post.pid, pid))
            return

        stmt = insert(QuoteRelation.__table__).values(quoter_uid=poster_uid, quotee_uid=quotee_uid, count=1)
        stmt = stmt.on_conflict_do_update(
            index_elements=QuoteRelation.__table__.primary_key.columns,
            set_=dict(count=stmt.excluded.count + QuoteRelation.__table__.c.count)
        )
        session.execute(stmt)

    def update_url(url, link_type, post):
        if url:
            if url[0] == url[-1] and url[0] in ("'", '"'):
                url = url[1:-1]
            if '://' not in url:
                url = 'http://' + url
        try:
            domain = urlparse(url).netloc
        except ValueError:
            print('PID %d: Could not parse URL: %r' % (post.pid, url))
            return

        stmt = insert(PostLinks.__table__).values(pid=post.pid, url=url, domain=domain, count=1, type=link_type)
        stmt = stmt.on_conflict_do_update(
            index_elements=PostLinks.__table__.primary_key.columns,
            set_=dict(count=stmt.excluded.count + PostLinks.__table__.c.count)
        )
        session.execute(stmt)

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


Base = declarative_base()


def bb_id_column():
    """ID column populated by bB (integer primary_key, no autoincrement)."""
    return Column(Integer, primary_key=True, autoincrement=False)


class User(Base):
    __tablename__ = 'users'

    uid = bb_id_column()
    # group-id, Nutzergruppe, nicht Nutzerrank,
    # z.B. group-id=3 sind Plebs, group-id=6 sind Mods, group-id=1 sind Admins.
    gid = Column(Integer)
    # Keine Konsistenz garantiert, insbesondere keine Einmaligkeit (zumindest theoretisch)
    name = Column(Unicode)

    @classmethod
    def from_xml(cls, session, user_tag):
        uid = int(user_tag.attrib['id'])
        try:
            gid = int(user_tag.attrib['group-id'])
        except KeyError:
            gid = None  # not all <user> tags have this
        user = session.query(cls).get(uid) or cls(
            uid=uid, gid=gid, name=user_tag.text,
        )
        session.add(user)
        return user


class Category(Base):
    __tablename__ = 'categories'

    cid = bb_id_column()
    name = Column(Unicode)
    description = Column(Unicode)


class Board(Base):
    __tablename__ = 'boards'

    bid = bb_id_column()
    cid = Column(Integer, ForeignKey('categories.cid'))
    name = Column(Unicode)
    description = Column(Unicode)

    category = relationship('Category')

    # XML:number-of-threads
    # XML:number-of-replies


class Thread(Base):
    __tablename__ = 'threads'

    tid = bb_id_column()
    bid = Column(Integer, ForeignKey('boards.bid'))

    title = Column(Unicode)
    subtitle = Column(Unicode)

    # Thread flags
    is_closed = Column(Boolean)
    is_sticky = Column(Boolean)
    is_important = Column(Boolean)
    is_announcement = Column(Boolean)
    is_global = Column(Boolean)

    # XML:number-of-hits
    hit_count = Column(Integer)
    # XML:number-of-replies, but this is not always correct iirc
    est_number_of_replies = Column(Integer)

    first_pid= Column(ForeignKey('posts.pid'))
    # Our last processed post, that is.
    last_pid = Column(ForeignKey('posts.pid'))

    board = relationship('Board', backref='threads')
    first_post = relationship('Post', foreign_keys=first_pid, post_update=True)
    last_post = relationship('Post', foreign_keys=last_pid, post_update=True)


class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (
        CheckConstraint('last_edit_uid is null or edit_count > 0', name='last_edit_uid_check'),
        CheckConstraint('last_edit_timestamp is null or edit_count > 0', name='last_edit_timestamp_check'),
    )

    pid = bb_id_column()
    poster_uid = Column(Integer, ForeignKey('users.uid'))
    tid = Column(Integer, ForeignKey('threads.tid'))

    timestamp = Column(TIMESTAMP, index=True)
    edit_count = Column(Integer)
    # NULL iff edit_count=0
    last_edit_uid = Column(Integer, ForeignKey('users.uid'), nullable=True)
    last_edit_timestamp = Column(TIMESTAMP, nullable=True)

    title = Column(Unicode)
    content = Column(UnicodeText)

    poster = relationship('User', foreign_keys=poster_uid)
    last_edit_user = relationship('User', foreign_keys=last_edit_uid)
    thread = relationship('Thread', foreign_keys=tid, backref='posts')


class PseudoMaterializedView(Base):
    """
    Helper class for building "poor man's" materialized views,
    i.e. regular tables that are populated by a query.

    The query attribute should be something Selectable (e.g. a Query()),
    whose columns match up with the (non-nullable, non-autoincrement) columns
    of the relation. Otherwise you will get errors on .refresh().
    """
    __abstract__ = True

    query: Query = None

    @classmethod
    def refresh(cls, session: Session):
        session.flush()
        session.query(cls).delete()
        query = cls.query.with_session(session)
        query_columns = [c['name'] for c in query.column_descriptions]
        stmt = insert(cls.__table__).from_select(query_columns, query)
        session.execute(stmt)


class WorldeaterState(Base):
    __tablename__ = 'worldeater_state'
    __table_args__ = (
        CheckConstraint('singleton = 0', name='ensure_single_state'),
    )

    singleton = Column(Integer, primary_key=True)

    nomnom_time = Column(Integer)
    num_api_requests = Column(Integer)
    rx_bytes = Column(Integer)
    tx_bytes = Column(Integer)

    def __init__(self):
        self.singleton = 0
        self.num_api_requests = 0
        self.nomnom_time = 0
        self.rx_bytes = 0
        self.tx_bytes = 0

    @staticmethod
    def get(session):
        state = session.query(WorldeaterState).first()
        if not state:
            state = WorldeaterState()
            session.add(state)
        return state


class QuoteRelation(Base):
    __tablename__ = 'quote_relation'

    quoter_uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    quotee_uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)

    quoter = relationship('User', foreign_keys=quoter_uid)
    quotee = relationship('User', foreign_keys=quotee_uid)

    count = Column(Integer, default=0)
    # A number between 0...1 where 1 is the most intense relation.
    intensity = query_expression()


class LinkType(enum.Enum):
    link = 1
    image = 2
    video = 3


class PostLinks(Base):
    __tablename__ = 'post_links'

    pid = Column(Integer, ForeignKey('posts.pid'), primary_key=True)
    url = Column(Unicode, primary_key=True)
    type = Column(Enum(LinkType), primary_key=True)
    domain = Column(Unicode)
    count = Column(Integer, default=0)

    post = relationship('Post')


class LinkRelation(PseudoMaterializedView):
    __tablename__ = 'link_relation'

    query = (
        Query((PostLinks.domain, User.uid, PostLinks.type,
               func.sum(PostLinks.count).label('count'),
               func.extract('year', Post.timestamp).label('year')))
        .join('post', 'poster')
        .group_by(PostLinks.domain, User.uid, PostLinks.type, 'year')
    )

    uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    domain = Column(Unicode, primary_key=True)
    year = Column(Integer, primary_key=True)
    type = Column(Enum(LinkType), primary_key=True)

    count = Column(Integer, default=0)

    user = relationship('User')


