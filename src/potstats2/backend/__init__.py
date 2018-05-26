import configparser
import json

from flask import Flask, request, Response, url_for, g
from sqlalchemy import func, desc

from ..db import Post, User, LinkType
from .. import db, dal, config
from .cache import cache_api_view

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


def get_session():
    try:
        return g.session
    except AttributeError:
        g.session = db.get_session()
        return g.session


@app.teardown_request
def close_db_session(exc):
    if hasattr(g, 'session'):
        g.session.close()


class DatabaseAwareJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, User):
            return {
                'name': o.name,
                'uid': o.uid,
            }
        if callable(getattr(o, 'to_json', None)):
            return o.to_json()
        return super().default(o)


def json_response(data, status_code=200):
    return Response(json.dumps(data, cls=DatabaseAwareJsonEncoder), status=status_code, mimetype='application/json')


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


@app.route('/api/boards')
@cache_api_view
def boards():
    session = get_session()
    rows = {}
    for row in dal.boards(session).all():
        rows[row.Board.bid] = {
            'name': row.Board.name,
            'description': row.Board.description,
            'thread_count': row.thread_count,
            'post_count': int(row.post_count),
        }
    return json_response(rows)


@app.route('/api/social-graph')
@cache_api_view
def social_graph():
    session = get_session()
    limit = request_arg('limit', int, default=1000)
    year = request_arg('year', int, default=None)
    rows = []
    query = dal.social_graph(session, year).limit(limit)
    for relation in query.all():
        rows.append({
            'from': relation.quoter,
            'to': relation.quotee,
            'count': relation.count,
            'intensity': relation.intensity,
        })
    return json_response({'rows': rows})


def request_link_type():
    name = request_arg('type', str, default=None)
    if not name:
        return None
    try:
        return LinkType[name]
    except KeyError:
        raise APIError('Invalid link type %r (choose from %s)' % (name, list(LinkType.__members__)))


@app.route('/api/user-domains')
@cache_api_view
def user_domains():
    session = get_session()
    limit = request_arg('limit', int, default=1000)
    year = request_arg('year', int, default=None)
    link_type = request_link_type()
    rows = []
    for row in dal.user_domains(session, year, link_type).limit(limit).all():
        rows.append(row._asdict())
    return json_response({'rows': rows})


@app.route('/api/domains')
@cache_api_view
def domains():
    session = get_session()
    limit = request_arg('limit', int, default=1000)
    year = request_arg('year', int, default=None)
    link_type = request_link_type()
    rows = []
    for row in dal.domains(session, year, link_type).limit(limit).all():
        rows.append(row._asdict())
    return json_response({'rows': rows})


@app.route('/api/poster-stats')
@cache_api_view
def poster_stats():
    """
    Basic posting statistics on users

    Query parameters:
    - year: optional int, restrict to certain year
    - limit: optional int, default 1000, restrict number of rows
    - offset: optional int, default 0, set offset
    - order_by: asc/desc, default desc, set sort direction
    - order_by_column: default post_count, one of ('post_count', 'edit_count', 'avg_post_length', 'threads_created')
    """
    session = get_session()

    year = request_arg('year', int, default=None)
    bid = request_arg('bid', int, default=None)
    limit = request_arg('limit', int, default=1000)
    offset = request_arg('offset', int, default=0)
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

    # Have to use offset, because we don't order by any unique, orderable column.
    # {Finding a way to adapt the pk-index method to pagination to our situation would be great,
    #  since most queries do not satisfy the simple criterion above.}
    query = dal.poster_stats(session, year, bid).order_by(order_by).limit(limit).offset(offset)

    rows = []
    for r in query.all():
        rows.append(r._asdict())

    return json_response({'rows': rows})


def time_segregated_stats(time_column, time_column_name):
    @cache_api_view
    def view():
        session = get_session()
        year = request_arg('year', int, default=None)
        bid = request_arg('bid', int, default=None)

        query = dal.aggregate_stats_segregated_by_time(session, time_column, year, bid)

        rows = {}
        for row in query.all():
            row = row._asdict()
            rows[row.pop('time')] = row

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


@app.route('/api/')
def api():
    apis = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api') and rule.endpoint != 'api':
            apis.append(url_for(rule.endpoint, _external=True))
    return json_response({'apis': apis})


def main():
    print('Only for development!')
    app.run()
