import configparser
import datetime
import json

from flask import Flask, request, Response, url_for, g
from sqlalchemy import func, desc, tuple_, column

from ..db import Post, User, LinkType
from .. import db, dal, config
from .cache import cache_api_view, get_stats

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


@app.route('/api/backend-stats')
def backend_stats():
    return json_response(get_stats())


@app.route('/api/boards')
@cache_api_view
def boards():
    session = get_session()
    year = request_arg('year', int, default=None)
    rows = []
    for row in dal.boards(session, year).all():
        rows.append({
            'bid': row.Board.bid,
            'name': row.Board.name,
            'description': row.Board.description,
            'thread_count': row.thread_count,
            'post_count': int(row.post_count),
        })
    return json_response({'rows': rows})


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
    - order: asc/desc, default desc, set sort direction
    - order_by: default 'post_count', one of ('post_count', 'edit_count', 'avg_post_length', 'threads_created', 'quoted_count', 'quotes_count')

    Parameters for pagination:
    - limit: optional int, default 1000, restrict number of rows
    - following_uid: the UID of the last row currently held by the client
    - following_ob: the value of the order_by column of the last row currently held by the client
    """
    session = get_session()

    year = request_arg('year', int, default=None)
    bid = request_arg('bid', int, default=None)
    limit = request_arg('limit', int, default=1000)
    following_uid = request_arg('following_uid', int, default=None)
    following_ob = request_arg('following_ob', float, default=None)
    order = request_arg('order', str, default='desc')
    order_by_column = request_arg('order_by', str, default='post_count')

    if order_by_column not in ('post_count', 'edit_count', 'avg_post_length', 'threads_created', 'quoted_count', 'quotes_count'):
        raise APIError('Invalid order_by_column: %s' % order_by_column)

    try:
        order_by = {
            'asc': order_by_column,
            'desc': desc(order_by_column),
        }[order]
    except KeyError:
        raise APIError('Invalid order_by: %s' % order)

    query = dal.poster_stats(session, year, bid).order_by(order_by, User.uid)

    if following_ob is not None and following_uid is not None:
        if order == 'asc':
            query = query.filter(tuple_(column(order_by_column), User.uid) > tuple_(following_ob, following_uid))
        else:
            query = query.filter(tuple_(column(order_by_column), User.uid) < tuple_(following_ob, following_uid))
    elif (following_ob is None or following_uid is None) and (following_ob is not None or following_uid is not None):
        raise APIError('Need to specify either both or none of following_uid, following_ob.')

    query = query.limit(limit + 1)

    rows = []
    for r in query.all():
        rows.append(r._asdict())

    response = dict(rows=rows)
    if len(rows) == limit + 1:
        rows.pop()
        # we are on a full "page" with at least one row after that page
        response['next'] = url_for('poster_stats', year=year, bid=bid,
                                   order=order, order_by=order_by_column, limit=limit,
                                   following_uid=rows[-1]['User'].uid, following_ob=rows[-1][order_by_column])

    return json_response(response)


def time_segregated_stats(time_column, time_column_name):
    def view():
        session = get_session()
        year = request_arg('year', int, default=None)
        bid = request_arg('bid', int, default=None)

        query = dal.aggregate_stats_segregated_by_time(session, time_column, year, bid)

        rows = []
        for row in query.all():
            row = row._asdict()
            row[time_column_name] = row.pop('time')
            rows.append(row)

        return json_response({'rows': rows})
    view.__name__ = 'view_' + time_column_name
    return cache_api_view(view)


app.route('/api/weekday-stats')(
    time_segregated_stats(func.to_char(Post.timestamp, 'ID'), 'weekday')
)

app.route('/api/hourly-stats')(
    time_segregated_stats(func.to_char(Post.timestamp, 'WW:ID:HH24'), 'weekday_hour')
)

app.route('/api/year-over-year-stats')(
    time_segregated_stats(func.extract('year', Post.timestamp), 'year')
)


@app.route('/api/daily-stats')
@cache_api_view
def daily_stats():
    """
    Return daily stats for a given year, organized as time-series as required by ngx-charts
    for e.g. a heat map (compare GitHub profiles).
    """
    session = get_session()

    year = request_arg('year', int)
    bid = request_arg('bid', int, default=None)
    statistic = request_arg('statistic', str)

    cte = dal.aggregate_stats_segregated_by_time(session, func.extract('doy', Post.timestamp), year, bid).cte()
    legal_statistics = list(cte.c.keys())
    legal_statistics.remove('time')
    if statistic not in legal_statistics:
        raise APIError('Invalid statistic %r, choose from: %s' % (statistic, legal_statistics))
    query = session.query(cte.c.time, cte.c[statistic].label('statistic'))
    rows = query.all()

    start_date = datetime.date(year, 1, 1)
    day = datetime.timedelta(days=1)

    weekdays = ('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag')
    series = [
        dict(week=0, name='KW0', series=[])
    ]

    for row in rows:
        day_of_year = row.time - 1  # Postgres doy is 1-365/366 (leap years have 366 days)
        date = start_date + day_of_year * day
        week_of_the_year = int(date.strftime('%W'))
        if week_of_the_year == series[-1]['week'] + 1:
            series.append(dict(week=week_of_the_year, name='KW%d' % week_of_the_year, series=[]))
        else:
            assert week_of_the_year == series[-1]['week'], \
                'date %s week %d, last week is %d' % (date, week_of_the_year, series[-1]['week'])

        series[-1]['series'].append(dict(name=weekdays[date.weekday()], value=row.statistic))

    for s in series:
        s.pop('week')

    return json_response({'series': series})


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
