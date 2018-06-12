import pytest

from potstats2 import db, analytics


def test_quotes_with_square_brackets(session, data):
    class QuotePost:
        pid = 101
        content = '''[quote=1,100,"[Höhlenmensch]"]Foo[/quote]'''

    quotes, urls = [], []
    analytics.analyze_post(QuotePost, {100, 101}, quotes, urls)
    assert not urls
    assert len(quotes) == 1
    quote = quotes[0]
    assert quote['pid'] == 101
    assert quote['quoted_pid'] == 100
    assert quote['count'] == 1


@pytest.mark.parametrize('text,expect_quotes,expect_urls', (
    # URLs
    ('[url=google.de]foo[/url]',
      [],
      [dict(pid=101, url='http://google.de', domain='google.de', count=1, type=db.LinkType.link)]),
    ('[url=http://google.de]foo[/url]',
      [],
      [dict(pid=101, url='http://google.de', domain='google.de', count=1, type=db.LinkType.link)]),
    ('[url=https://google.de]foo[/url]',
     [],
     [dict(pid=101, url='https://google.de', domain='google.de', count=1, type=db.LinkType.link)]),
    ('[url]http://google.de[/url]',
     [],
     [dict(pid=101, url='http://google.de', domain='google.de', count=1, type=db.LinkType.link)]),
    ('[url="http://bracket.org/[foobar]"]link[/url]',
     [],
     [dict(pid=101, url='http://bracket.org/[foobar]', domain='bracket.org', count=1, type=db.LinkType.link)]),

    # Images
    ('[img][/img]',
     [],
     [dict(pid=101, url='', domain='', count=1, type=db.LinkType.image)]),
    ('[img]./img/icons/icon13.gif[/img]',
     [],
     [dict(pid=101, url='http://forum.mods.de/bb/img/icons/icon13.gif', domain='forum.mods.de', count=1, type=db.LinkType.image)]),
    ('[img]/bb/img/icons/icon13.gif[/img]',
     [],
     [dict(pid=101, url='http://forum.mods.de/bb/img/icons/icon13.gif', domain='forum.mods.de', count=1, type=db.LinkType.image)]),
    ('[img]google.de/something.gif[/img]',
     [],
     [dict(pid=101, url='http://google.de/something.gif', domain='google.de', count=1, type=db.LinkType.image)]),
    ('[img]data:base9001/image:jpg![/img]',
     [],
     []),

    # Videos
    ('[video]http://google.de/something.mp4[/video]',
     [],
    [dict(pid=101, url='http://google.de/something.mp4', domain='google.de', count=1, type=db.LinkType.video)]),

    # Quotes
    ('[quote]foo[/quote]', [], []),
    ('[quote=1,2]foo[/quote]', [], []),
    ('[quote=1,2,3]foo[/quote]', [], []),  # PID not on record
    ('[quote=1,1099511627776,3]foo[/quote]', [], []),  # PID overflow
    ('[quote=1,100,ignoriert]foo[/quote]', [dict(pid=101, quoted_pid=100, count=1)], []),
    ('[quote][quote=1,100,ignoriert]foo[/quote][/quote]', [], []),
))
def test_analyze_post(session, data, text, expect_quotes, expect_urls):
    class Post:
        pid = 101
        content = text

    quotes, urls = [], []
    analytics.analyze_post(Post, {100, 101}, quotes, urls)
    assert quotes == expect_quotes
    assert urls == expect_urls
