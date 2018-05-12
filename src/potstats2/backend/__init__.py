import json
from datetime import datetime

from flask import Flask, request, Response
from sqlalchemy import and_, func, desc

from ..db import get_session, Post, User

app = Flask(__name__)
no_default = object()


def json_response(data, status_code=200):
    return Response(json.dumps(data), status=status_code, mimetype='application/json')


class APIError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__()
        self.message = str(message)
        self.status_code = status_code or type(self).status_code

    def get_response(self):
        return json_response({
            'error': self.message,
        }, status_code=self.status_code)


def request_arg(argument, type, default=no_default):
    try:
        return type(request.args[argument])
    except KeyError as exc:
        if default is not no_default:
            return default
        raise APIError('Missing request argument %s' % argument)
    except ValueError as exc:
        raise APIError('Malformed request argument %s: %s' % (argument, exc))


@app.errorhandler(APIError)
def handle_api_error(error: APIError):
    return error.get_response()


@app.route('/api/poster-stats')
def poster_stats():
    session = get_session()

    year = request_arg('year', int)
    limit = request_arg('limit', int, default=1000)
    order_by = request_arg('order_by', str, default='desc')
    try:
        order_by_column = {
            'asc': func.count(Post.pid),
            'desc': desc(func.count(Post.pid)),
        }[order_by]
    except KeyError:
        raise APIError('Invalid order_by: %s' % order_by)

    # [lower, upper)
    lower_timestamp_bound = datetime(year, 1, 1, 0, 0, 0)
    upper_timestamp_bound = lower_timestamp_bound.replace(year=year + 1)

    rows = []
    for user, post_count in (
        session.query(User, func.count(Post.pid))
        .filter(Post.poster_uid == User.uid)
        .filter(and_(lower_timestamp_bound <= Post.timestamp, Post.timestamp < upper_timestamp_bound))
        .group_by(User)
        .order_by(order_by_column)
        .limit(limit)
    ).all():
        rows.append({
            'user': {'name': user.name, 'uid': user.uid},
            'post_count': post_count
        })

    return json_response({'rows': rows})


def main():
    print('Only for development!')
    app.run()
