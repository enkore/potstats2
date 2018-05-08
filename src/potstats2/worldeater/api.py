import time
# WARNING: The xml.etree.ElementTree module is not secure
# against maliciously constructed data.
# ¯\_(ツ)_/¯
import xml.etree.ElementTree as ET

import requests

import potstats2
from .. import config

API_URL = 'http://forum.mods.de/bb/'
ENDPOINTS = (
    'boards', 'board', 'thread',
)


class InvalidBoardError(RuntimeError):
    def __str__(self):
        return 'Invalid board specified: bid=%d' % self.args


class InvalidThreadError(RuntimeError):
    def __str__(self):
        return 'Invalid thread specified: bid=%d' % self.args


def b2i(boolean):
    return '1' if boolean else '0'


class XmlApiConnector:
    def __init__(self, api_url=API_URL, requests_session=None):
        assert api_url.endswith('/')
        self.api_url = API_URL
        self.session = requests_session or requests.Session()
        self.session.headers['User-Agent'] = 'worldeater/' + potstats2.__version__
        self.request_delay = float(config.get('REQUEST_DELAY'))
        self.num_requests = 0

    def endpoint_url(self, ep):
        assert not ep.endswith('.php')
        assert ep in ENDPOINTS
        return self.api_url + 'xml/' + ep + '.php'

    def invoke(self, endpoint, query_params=None) -> ET.Element:
        response = self.session.get(self.endpoint_url(endpoint), params=query_params)
        self.num_requests += 1
        time.sleep(self.request_delay)
        # Note: response.encoding is, for some reason, ISO-8859-1; the XML is UTF-8
        # (Meanwhile, response.apparent_encoding is correct, but response.text is still broken)
        root_element = ET.fromstring(response.content.decode())
        return root_element

    def boards(self):
        return self.invoke('boards')

    def board(self, bid, page=0):
        board = self.invoke('board', query_params=dict(
            BID=str(bid), page=str(page)
        ))
        if board.tag == 'invalid-board':
            raise InvalidBoardError(bid)
        return board

    def thread(self, tid, page=None, pid=None):
        query_params=dict(TID=str(tid))
        if page is not None:
            query_params['page'] = str(page)
        if pid is not None:
            query_params['PID'] = str(pid)
        thread = self.invoke('thread', query_params=query_params)
        if thread.tag == 'invalid-thread':
            raise InvalidThreadError(tid)
        return thread

    # generators

    def iter_board(self, bid, oldest_tid=None):
        page = 0
        while True:
            board = self.board(bid, page)
            threads = board.findall('./threads/thread')
            yield from threads
            if len(threads) < 30 or (oldest_tid and board.find('./threads/thread[@id=\'%s\']' % oldest_tid)):
                # last page or oldest thread processed that we've wanted
                break
            page += 1

    def iter_thread(self, tid, start_page=0):
        page = start_page
        while True:
            thread = self.thread(tid, page)
            posts = thread.findall('./posts/post')
            yield from posts
            if len(posts) < 30:
                # last page
                break
            page += 1
