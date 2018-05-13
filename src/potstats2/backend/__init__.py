import json
from datetime import datetime

from flask import Flask, request, Response
from sqlalchemy import and_, func, desc

from ..db import get_session, Post, User, Thread

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


def apply_year_filter(query, year=no_default):
    if year is no_default:
        year = request_arg('year', int, default=None)
    if year:
        # [lower, upper)
        lower_timestamp_bound = datetime(year, 1, 1, 0, 0, 0)
        upper_timestamp_bound = lower_timestamp_bound.replace(year=year + 1)
        query = (
            query
            .filter(lower_timestamp_bound <= Post.timestamp)
            .filter(Post.timestamp < upper_timestamp_bound)
        )
    return query


@app.route('/api/poster-stats')
def poster_stats():
    """
    Basic posting statistics on users

    Query parameters:
    - year: optional int, restrict to certain year
    - limit: optional int, default 1000, restrict number of rows
    - order_by: asc/desc, default desc, set sort direction
    - order_by_column: default post_count, one of ('post_count', 'edit_count', 'avg_post_length', 'threads_created')
    """
    session = get_session()

    limit = request_arg('limit', int, default=1000)
    order_by_order = request_arg('order_by', str, default='desc')
    order_by_column = request_arg('order_by_column', str, default='post_count')

    if order_by_column not in ('post_count', 'edit_count', 'avg_post_length', 'threads_created'):
        raise APIError('Invalid order_by_column: %s' % order_by_column)

    try:
        order_by = {
            'asc': order_by_column,
            'desc': desc(order_by_column),
        }[order_by_order]
    except KeyError:
        raise APIError('Invalid order_by: %s' % order_by_order)

    threads_opened = (
        session
        .query(
            User.uid,
            func.count(Thread.tid).label('threads_created'),
        )
        .filter(Thread.first_post == Post.pid)
        .filter(Post.poster_uid == User.uid)
    )

    threads_opened = (
        apply_year_filter(threads_opened)
        .group_by(User.uid)
        .subquery('to')
    )

    query = (
        session
        .query(
            User,
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            func.avg(func.length(Post.content)).label('avg_post_length'),
            func.coalesce(threads_opened.c.threads_created, 0).label('threads_created'),
        )
        .filter(Post.poster_uid == User.uid)
        # The OUTER JOIN will create rows with NULL to.c.threads_created if the user created no threads
        # (because there is no row matching the WHERE clause the aggregation has no result so the outer join
        #  inserts NULLs into the resulting columns).
        # These are killed off by the COALESCE above.
        .outerjoin(threads_opened, threads_opened.c.uid == User.uid)
    )

    query = apply_year_filter(query)

    query = (
        query
        .group_by(User)
        .order_by(order_by)
        .limit(limit)
    )

    rows = []
    for r in query.all():
        rows.append({
            'user': {'name': r.User.name, 'uid': r.User.uid},
            'post_count': r.post_count,
            'edit_count': r.edit_count,
            'avg_post_length': r.avg_post_length,
            'threads_created': r.threads_created
        })

    return json_response({'rows': rows})


@app.route('/api/weekday-stats')
def weekday_stats():
    session = get_session()
    rows = []
    post_query = apply_year_filter(
        session
        .query(
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            func.avg(func.length(Post.content)).label('avg_post_length'),
        )
    )
    threads_query = apply_year_filter(
        session
        .query(func.count(Thread.tid).label('threads_created'))
        .filter(Thread.first_post == Post.pid)
    )

    for weekday in range(7):  # You could use a cartesian join against VALUES(0, ..., 6), but SQLite doesn't like that
        row = post_query.filter(func.strftime('%w', Post.timestamp) == str(weekday)).one()._asdict()
        row.update(threads_query.filter(func.strftime('%w', Post.timestamp) == str(weekday)).one()._asdict())
        rows.append(row)

    return json_response({'rows': rows})


def main():
    print('Only for development!')
    app.run()
