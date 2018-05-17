import marshal
import functools
import hashlib

try:
    import redis
except ImportError:
    redis = None

from flask import Request, Response, request

import potstats2
from .. import config

redis_url = config.get('REDIS_URL')
if redis_url and redis:
    print('Using redis cache at', redis_url)
    redis_client = redis.StrictRedis.from_url(redis_url)
elif redis_url:
    print('redis-py (pip install redis) not installed - can\'t use caching.')
    redis_client = None
else:
    print('API request caching disabled.')
    redis_client = None


def cache_key(view, view_args, view_kwargs, request: Request):
    return hashlib.sha256(marshal.dumps({
        'version': potstats2.__version__,
        'view': view.__name__,
        'view_args': view_args,
        'view_kwargs': view_kwargs,
        'request_url': request.full_path,  # order controlled by UA, so possibly doubled cache entries
    })).hexdigest()


def cache_api_view(view):
    if not redis_client:
        return view

    @functools.wraps(view)
    def cache_frontend(*args, **kwargs):
        key = cache_key(view, args, kwargs, request)
        cached = redis_client.get(key)
        if not cached:
            response = view(*args, **kwargs)
            if response.status_code == 200 and response.mimetype == 'application/json':
                redis_client.set(key, response.get_data(as_text=False))
            return response
        else:
            return Response(cached, status=200, mimetype='application/json')
    return cache_frontend


def invalidate():
    if redis_client:
        redis_client.flushdb()
