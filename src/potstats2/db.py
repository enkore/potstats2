import enum
import sys

from sqlalchemy import create_engine, Column, ForeignKey, Integer, Unicode, UnicodeText, Boolean, TIMESTAMP, \
    CheckConstraint, func, Enum, Index
from sqlalchemy.orm import sessionmaker, relationship, Query, Session, query_expression, aliased
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import insert, JSONB

import click

from . import config


def get_engine():
    db_url = config.get('DB')
    print('Database URL:', db_url, file=sys.stderr)
    return create_engine(db_url, use_batch_mode=True)


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
def shell():
    import code
    locals = dict(session=get_session())
    locals.update(globals())
    code.interact(local=locals, banner='>>> session=get_session()\n'
                                       '>>> from potstats2.db import *', exitmsg='')


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
    __table_args__ = (
        CheckConstraint('(is_closed and not is_sticky and not is_global) or not is_complete', name='complete_requires_closed'),
    )

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

    tags = Column(JSONB)

    is_complete = Column(Boolean)

    @property
    def can_be_complete(self):
        return self.is_closed and not self.is_sticky and not self.is_global


class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (
        CheckConstraint('last_edit_uid is null or edit_count > 0', name='last_edit_uid_check'),
        CheckConstraint('last_edit_timestamp is null or edit_count > 0', name='last_edit_timestamp_check'),
        # This index is mostly for speeding up queries of the "find the first/last post in thread X";
        # it is used by the query populating Thread.first_post. Actually no query would be necessary for that,
        # but oh well I'm lazy.
        Index('tid_pid', 'tid', 'pid'),
    )

    pid = bb_id_column()
    poster_uid = Column(Integer, ForeignKey('users.uid'))
    tid = Column(Integer, ForeignKey('threads.tid'))

    timestamp = Column(TIMESTAMP, index=True)
    edit_count = Column(Integer)
    # NULL iff edit_count=0
    last_edit_uid = Column(Integer, ForeignKey('users.uid'), nullable=True)
    last_edit_timestamp = Column(TIMESTAMP, nullable=True)

    is_hidden = Column(Boolean)

    content_length = Column(Integer)

    poster = relationship('User', foreign_keys=poster_uid)
    last_edit_user = relationship('User', foreign_keys=last_edit_uid)
    thread = relationship('Thread', foreign_keys=tid, backref='posts')


class PostContent(Base):
    __tablename__ = 'post_contents'

    pid = Column(Integer, ForeignKey('posts.pid'), primary_key=True)
    title = Column(Unicode)
    content = Column(UnicodeText)

    post = relationship('Post', backref='content')


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
    def refresh(cls, session: Session, query: Query = None):
        session.flush()
        session.query(cls).delete()
        if not query:
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


class WorldeaterThreadsNeedingUpdate(Base):
    __tablename__ = 'worldeater_tnu'

    tid = Column(Integer, ForeignKey('threads.tid'), primary_key=True)
    start_page = Column(Integer)
    est_number_of_posts = Column(Integer)

    thread = relationship('Thread')


class PostQuotes(Base):
    __tablename__ = 'post_quotes'

    pid = Column(Integer, ForeignKey('posts.pid'), primary_key=True)
    quoted_pid = Column(Integer, ForeignKey('posts.pid'), primary_key=True)
    count = Column(Integer, default=0)

    post = relationship('Post', foreign_keys=pid)
    quoted_post = relationship('Post', foreign_keys=quoted_pid)


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
        .having(func.sum(PostLinks.count) >= 10)
    )

    uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    domain = Column(Unicode, primary_key=True)
    year = Column(Integer, primary_key=True)
    type = Column(Enum(LinkType), primary_key=True)

    count = Column(Integer, default=0)

    user = relationship('User')


class QuoteRelation(PseudoMaterializedView):
    __tablename__ = 'baked_quote_stats'

    year = Column(Integer, primary_key=True)
    bid = Column(Integer, primary_key=True)
    quoter_uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    quoted_uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    count = Column(Integer, default=0)
    intensity = query_expression()

    quoter = relationship('User', foreign_keys=quoter_uid)
    quoted = relationship('User', foreign_keys=quoted_uid)


class PosterStats(PseudoMaterializedView):
    __tablename__ = 'baked_poster_stats'

    year = Column(Integer, primary_key=True)
    bid = Column(Integer, ForeignKey('boards.bid'), primary_key=True)
    uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)

    post_count = Column(Integer)
    edit_count = Column(Integer)
    avg_post_length = Column(Integer)
    threads_created = Column(Integer)
    quoted_count = Column(Integer)
    quotes_count = Column(Integer)

    board = relationship('Board')
    user = relationship('User')


class DailyStats(PseudoMaterializedView):
    __tablename__ = 'baked_daily_stats'

    year = Column(Integer, primary_key=True)
    day_of_year = Column(Integer, primary_key=True)
    bid = Column(Integer, ForeignKey('boards.bid'), primary_key=True)

    post_count = Column(Integer)
    edit_count = Column(Integer)
    posts_length = Column(Integer)
    threads_created = Column(Integer)
    active_users = Column(Integer)
    active_threads = Column(JSONB)

    board = relationship('Board')
