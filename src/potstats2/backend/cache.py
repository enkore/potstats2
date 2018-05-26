import collections
import marshal
import functools
import hashlib
import gzip

try:
    import redis
    import blinker
except ImportError:
    redis = None

from flask import Request, Response, request, current_app

import potstats2
from .. import config

redis_url = config.get('REDIS_URL')
if redis_url and redis:
    print('Using redis cache at', redis_url)
    cache_db = redis.StrictRedis.from_url(redis_url, db=0)
    stats_db = redis.StrictRedis.from_url(redis_url, db=1)
elif redis_url:
    print('redis-py or blinker (pip install redis blinker) not installed - can\'t use caching.')
    cache_db = stats_db = None
else:
    print('API request caching disabled.')
    cache_db = stats_db = None


def cache_key(view, view_args, view_kwargs, request: Request):
    return hashlib.sha256(marshal.dumps({
        'version': potstats2.__version__,
        'view': view.__name__,
        'view_args': view_args,
        'view_kwargs': view_kwargs,
        'request_url': request.full_path,  # order controlled by UA, so possibly doubled cache entries
    })).hexdigest()


def cache_api_view(view):
    if not cache_db:
        return view

    @functools.wraps(view)
    def cache_frontend(*args, **kwargs):
        key = cache_key(view, args, kwargs, request)
        etag = key[:32]
        cached = cache_db.get(key)
        ua_does_gzip = 'gzip' in request.headers.get('Accept-Encoding', '').lower()
        if not cached:
            response = view(*args, **kwargs)
            if response.status_code == 200 and response.mimetype == 'application/json':
                data = response.get_data(as_text=False)
                compressed_data = gzip.compress(data, 5)

                cache_db.set(key, compressed_data)
                # It's only an actual miss if we are able to cache the response
                stats_db.incr(view.__name__ + '/cache_miss')
                stats_db.incr(view.__name__ + '/cache_size', len(data))
                stats_db.incr(view.__name__ + '/cache_size_gzipped', len(compressed_data))

                if ua_does_gzip:
                    response.set_data(compressed_data)
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = response.content_length
                    response.headers['Vary'] = 'Accept-Encoding'
                response.headers['ETag'] = etag
            return response
        else:
            if etag in request.headers.get('If-None-Match', ''):
                return Response(status=304)
            stats_db.incr(view.__name__ + '/cache_hits')
            response = Response(status=200, mimetype='application/json')
            if ua_does_gzip:
                response.set_data(cached)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = response.content_length
                response.headers['Vary'] = 'Accept-Encoding'
            else:
                response.set_data(gzip.decompress(cached))
                response.headers['Content-Length'] = response.content_length
            response.headers['ETag'] = etag
            return response
    return cache_frontend


def observe_request_started(sender, **extra):
    try:
        view = current_app.view_functions[request.endpoint]
    except KeyError:
        stats_db.incr('404_hits')
        return
    stats_db.incr(view.__name__ + '/hits')


def observe_request_finished(sender, response, **extra):
    try:
        view = current_app.view_functions[request.endpoint]
    except KeyError:
        return
    stats_db.incr('%s/responses/%d' % (view.__name__, response.status_code))
    stats_db.incr('%s/responses_size' % view.__name__, len(response.get_data()))


if stats_db:
    from flask import request_started, request_finished
    request_started.connect(observe_request_started)
    request_finished.connect(observe_request_finished)


def invalidate():
    if cache_db:
        cache_db.flushdb()


def get_stats():
    nested_dict = lambda: collections.defaultdict(nested_dict)

    stats = nested_dict()
    stats['version'] = potstats2.__version__
    if stats_db:
        for key in stats_db.keys('*'):
            key = key.decode()
            parts = key.split('/')
            insert_into = stats
            for part in parts[:-1]:
                insert_into = insert_into[part]

            v = stats_db.get(key).decode()
            try:
                v = int(v)
            except ValueError:
                pass
            insert_into[parts[-1]] = v
    return stats
