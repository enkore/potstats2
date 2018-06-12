
from potstats2 import db, analytics


def test_quotes_with_square_brackets(session, data):
    cave = session.query(db.User).get(5000)
    thread = session.query(db.Thread).get(1)

    cavepost = db.Post(pid=100, thread=thread, poster=cave)
    cavepost.content = db.PostContent(post=cavepost, content='Foo')

    class QuotePost:
        pid = 101
        content = '''[quote=1,100,"[Höhlenmensch]"]Foo[/quote]'''

    quotes, urls = [], []
    analytics.analyze_post(QuotePost, {100, 101}, quotes, urls)
    assert not urls
    assert len(quotes) == 1
    quote = quotes[0]

