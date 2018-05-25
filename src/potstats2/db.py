import enum
import sys

from sqlalchemy import create_engine, Column, ForeignKey, Integer, Unicode, UnicodeText, Boolean, TIMESTAMP, \
    CheckConstraint, func, Enum
from sqlalchemy.orm import sessionmaker, relationship, Query, Session, query_expression, aliased
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import insert

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


class PostQuotes(Base):
    __tablename__ = 'post_quotes'

    pid = Column(Integer, ForeignKey('posts.pid'), primary_key=True)
    quoted_pid = Column(Integer, ForeignKey('posts.pid'), primary_key=True)
    count = Column(Integer, default=0)

    post = relationship('Post', foreign_keys=pid)
    quoted_post = relationship('Post', foreign_keys=quoted_pid)


quoter = aliased(User, name='quoter')
quotee = aliased(User, name='quotee')
quoted_post = aliased(Post, name='quoted_post')
agg_count = func.sum(PostQuotes.count).label('count')

func.extract('year', Post.timestamp)


qrq = (
    Query((quoter.uid.label('quoter_uid'),
           quotee.uid.label('quotee_uid'),
           func.extract('year', Post.timestamp).label('year'), agg_count))
    .join(Post, PostQuotes.post)
    .join(quoted_post, PostQuotes.quoted_post)
    .join(quoter, Post.poster)
    .join(quotee, quoted_post.poster)
    .group_by(quoter.uid, quotee.uid, 'year')
)


class QuoteRelation(PseudoMaterializedView):
    __tablename__ = 'quote_relation'

    quoter_uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    quotee_uid = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    year = Column(Integer, primary_key=True)

    quoter = relationship('User', foreign_keys=quoter_uid)
    quotee = relationship('User', foreign_keys=quotee_uid)

    count = Column(Integer, default=0)
    # A number between 0...1 where 1 is the most intense relation.
    intensity = query_expression()

    query = qrq


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
