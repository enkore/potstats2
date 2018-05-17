import marshal
import functools
import hashlib

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from flask import Request, Response, request

from .. import config

redis_url = config.get('REDIS_URL')
if redis_url:
    print('Using redis cache at', redis_url)
    region = make_region().configure(
        'dogpile.cache.redis',
        arguments={
            'url': redis_url,
            'distributed_lock': True
        }
    )
else:
    print('API request caching disabled.')
    region = None


def cache_key(view, view_args, view_kwargs, request: Request):
    return hashlib.sha256(marshal.dumps({
        'view': view.__name__,
        'view_args': view_args,
        'view_kwargs': view_kwargs,
        'request_url': request.full_path,  # order controlled by UA, so possibly doubled cache entries
    })).hexdigest()


def cache_api_view(view):
    if not region:
        return view

    @functools.wraps(view)
    def cache_frontend(*args, **kwargs):
        key = cache_key(view, args, kwargs, request)
        cached = region.get(key)
        if cached is NO_VALUE:
            response = view(*args, **kwargs)
            if response.status_code == 200 and response.mimetype == 'application/json':
                region.set(key, response.get_data(as_text=False))
            return response
        else:
            return Response(cached, status=200, mimetype='application/json')
    return cache_frontend


def invalidate():
    if region:
        region.invalidate()
