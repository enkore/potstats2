import configparser
import json
from datetime import datetime
from itertools import zip_longest
from collections import defaultdict

from flask import Flask, request, Response, url_for
from sqlalchemy import and_, func, desc, cast, Float

from ..db import get_session, Post, User, Thread, Board
from .. import config

app = Flask(__name__)
no_default = object()

cfg = configparser.ConfigParser()
try:
    with open(config.INI_PATH, 'r') as fd:
        cfg.read_file(fd)
except FileNotFoundError:
    pass
try:
    app.config.from_mapping({k.upper(): v for k, v in cfg['flask'].items()})
except KeyError:
    pass


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


def apply_board_filter(query, bid=no_default):
    if bid is no_default:
        bid = request_arg('bid', int, default=None)
    if bid:
        query = query.filter(Post.thread.has(Thread.bid == bid))
    return query


def apply_standard_filters(query):
    return apply_board_filter(apply_year_filter(query))


@app.route('/api/boards')
def boards():
    session = get_session()
    rows = {}
    for board in session.query(Board).all():
        rows[board.bid] = {
            'name': board.name,
            'description': board.description,
        }
    return json_response(rows)


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

    threads_opened = apply_standard_filters(
        session
        .query(
            User.uid,
            func.count(Thread.tid).label('threads_created'),
        )
        .join(Post.poster)
        .join(Thread, Thread.first_pid == Post.pid)
    ).group_by(User.uid).subquery()

    post_stats = apply_standard_filters(
        session
        .query(
            User.uid,
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            cast(func.avg(func.length(Post.content)), Float).label('avg_post_length'),
        )
        .join(Post.poster)
    ).group_by(User.uid).subquery()

    query = (
        session
        .query(
            User,
            post_stats,
            func.coalesce(threads_opened.c.threads_created, 0).label('threads_created'),
        )
        .outerjoin(threads_opened, threads_opened.c.uid == User.uid)
        .join(post_stats, post_stats.c.uid == User.uid)
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


def time_segregated_stats(time_column, time_column_name):
    def view():
        session = get_session()
        rows = defaultdict(lambda: {'post_count': 0, 'edit_count': 0, 'avg_post_length': 0, 'threads_created': 0})
        post_query = apply_standard_filters(
            session
            .query(
                func.count(Post.pid).label('post_count'),
                func.sum(Post.edit_count).label('edit_count'),
                cast(func.avg(func.length(Post.content)), Float).label('avg_post_length'),
                time_column.label(time_column_name)
            )
            .group_by(time_column_name)
            .order_by(time_column_name)
        )
        threads_query = apply_standard_filters(
            session
            .query(
                func.count(Thread.tid).label('threads_created'),
                time_column.label(time_column_name)
            )
            .join(Thread.first_post)
            .group_by(time_column_name)
            .order_by(time_column_name)
        )

        for q in (post_query, threads_query):
            for row in q.all():
                row = row._asdict()
                rows[row.pop(time_column_name)].update(row)

        return json_response({'rows': rows})
    view.__name__ = 'view_' + time_column_name
    return view


app.route('/api/weekday-stats')(
    time_segregated_stats(func.to_char(Post.timestamp, 'ID'), 'weekday')
)

app.route('/api/hourly-stats')(
    time_segregated_stats(func.to_char(Post.timestamp, 'WW:ID:HH24'), 'weekday_hour')
)

app.route('/api/year-over-year-stats')(
    time_segregated_stats(func.extract('year', Post.timestamp), 'year')
)


@app.route('/api')
def api():
    apis = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api') and rule.endpoint != 'api':
            apis.append(url_for(rule.endpoint, _external=True))
    return json_response({'apis': apis})


def main():
    print('Only for development!')
    app.run()
