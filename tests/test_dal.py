
from potstats2 import db, dal


def test_simple(session, data):
    assert session.query(db.User).count() == 3
