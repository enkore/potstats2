import marshal
import functools
import hashlib

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
        cached = cache_db.get(key)
        if not cached:
            response = view(*args, **kwargs)
            if response.status_code == 200 and response.mimetype == 'application/json':
                # It's only an actual miss if we are able to cache the response
                stats_db.incr(view.__name__ + '_cache_miss')
                cache_db.set(key, response.get_data(as_text=False))
            return response
        else:
            stats_db.incr(view.__name__ + '_cache_hits')
            return Response(cached, status=200, mimetype='application/json')
    return cache_frontend


def observe_request_started(sender, **extra):
    try:
        view = current_app.view_functions[request.endpoint]
    except KeyError:
        stats_db.incr('404_hits')
        return
    stats_db.incr(view.__name__ + '_hits')


def observe_request_finished(sender, response, **extra):
    try:
        view = current_app.view_functions[request.endpoint]
    except KeyError:
        return
    stats_db.incr('%s_responses_%d' % (view.__name__, response.status_code))


if stats_db:
    from flask import request_started, request_finished
    request_started.connect(observe_request_started)
    request_finished.connect(observe_request_finished)


def invalidate():
    if cache_db:
        cache_db.flushdb()
