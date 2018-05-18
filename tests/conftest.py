import os

from sqlalchemy import create_engine

from potstats2 import db, config

import pytest
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope='session')
def test_db_name():
    return 'test_%d' % os.getpid()


@pytest.yield_fixture(scope='session')
def db_engine(test_db_name):
    def execute_db_level(stmt):
        engine = db.get_engine()
        conn = engine.connect()
        conn.execution_options(autocommit=False)
        conn.execute('ROLLBACK')
        try:
            conn.execute(stmt)
        finally:
            conn.close()
            engine.dispose()

    try:
        execute_db_level('DROP DATABASE ' + test_db_name)
    except ProgrammingError:
        pass
    execute_db_level('CREATE DATABASE ' + test_db_name)

    test_url = make_url(config.get('DB'))
    test_url.database = test_db_name

    engine = create_engine(test_url)
    yield engine

    engine.dispose()
    execute_db_level('DROP DATABASE ' + test_db_name)


@pytest.fixture(scope='session')
def schema(db_engine):
    db.Base.metadata.create_all(db_engine)


@pytest.yield_fixture
def session(db_engine, schema):
    sm = sessionmaker(bind=db_engine)
    session = sm()
    session.begin_nested()
    yield session
    session.rollback()
    sm.close_all()


@pytest.fixture
def data(session):
    session.add(db.User(uid=1, gid=2, name='foobar'))
    session.add(db.User(uid=2891831, gid=6, name='schneemann'))
    session.add(db.Category(cid=5, name='Fake Kategorie'))
    session.add(db.Board(bid=7, cid=5, name='Fake Forum für 1 fake Kategorie'))
    session.add(db.Thread(tid=123123, bid=7, title='Thread1'))
