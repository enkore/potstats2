import configparser
import csv
import datetime
import io
import json
import os.path
import time

from flask import Flask, request, Response, url_for, g, send_file
from sqlalchemy import func, desc, tuple_, column
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import joinedload
from sqlalchemy.util import KeyedTuple

from ..db import Post, User, LinkType, Thread
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
                'aliases': o.aliases,
            }
        if isinstance(o, Thread):
            return {
                'tid': o.tid,
                'title': o.title,
                'subtitle': o.subtitle,
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
            'to': relation.quoted,
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


@app.route('/api/poster-development')
@cache_api_view
def poster_developmental_issues():
    session = get_session()

    bid = request_arg('bid', int, default=None)
    uid = request_arg('uid', int, default=None)
    if uid is None:
        username = request_arg('user', str)
        user = session.query(User).filter(func.lower(User.name) == func.lower(username)).order_by(desc(User.uid)).first()
        if not user:
            raise APIError('User not found: %s' % username)
    else:
        user = session.query(User).get(uid)
        if not user:
            raise APIError('User ID not found: %s' % uid)

    columns = ['year', 'post_count', 'edit_count', 'threads_created', 'quoted_count', 'quotes_count', 'avg_post_length']
    rows = dal.poster_developmental_issues(session, user.uid, bid).all()
    years = {r.year: r for r in rows}
    for year in range(min(years), max(years)):
        if year not in years:
            years[year] = KeyedTuple([year, 0, 0, 0, 0, 0, 0],labels=columns)
    rows = sorted(years.values(), key=lambda r: r.year)

    if 'csv' in request.args:
        fd = io.StringIO()
        writer = csv.writer(fd)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)

        response = Response(fd.getvalue(), mimetype='text/csv')
        response.headers["Content-Disposition"] = "attachment; filename=user-development-%d.csv" % user.uid
        return response
    else:
        return json_response({
            'user': user,
            'years': {r.year: r._asdict() for r in rows},
        })


@app.route('/api/weekday-stats')
@cache_api_view
def weekday_stats():
    session = get_session()
    year = request_arg('year', int, default=None)
    bid = request_arg('bid', int, default=None)

    query = dal.weekday_stats(session, year, bid)

    rows = []
    for row in query.all():
        result = row.stats
        result['weekday'] = row.weekday
        rows.append(result)

    return json_response({'rows': rows})


@app.route('/api/year-over-year-stats')
@cache_api_view
def year_over_year_stats():
    session = get_session()
    year = request_arg('year', int, default=None)
    bid = request_arg('bid', int, default=None)

    query = dal.yearly_stats(session, year, bid)

    rows = []
    for row in query.all():
        result = row.stats
        result['year'] = row.year
        rows.append(result)

    return json_response({'rows': rows})


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

    try:
        query = dal.daily_statistic(session, statistic, year, bid)
    except dal.DalParameterError as dpe:
        raise APIError(str(dpe))

    rows = query.all()

    start_date = datetime.date(year, 1, 1)
    actual_start_date = None
    day = datetime.timedelta(days=1)

    def week():
        weekdays = ('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag')
        return [dict(name=weekdays[dow], value=0.0) for dow in range(7)]

    series = [
    ]

    for row in rows:
        day_of_year = row.day_of_year - 1  # Postgres doy is 1-365/366 (leap years have 366 days)
        date = start_date + day_of_year * day
        if not actual_start_date:
            actual_start_date = date
        week_of_the_year = int(date.strftime('%W'))
        if not series or week_of_the_year != series[-1]['name']:
            series.append(dict(name=week_of_the_year, series=week()))

        series[-1]['series'][date.weekday()]['value'] = row.stats[statistic]

    if rows:
        # Trim first week to actual week length
        first_weekday = actual_start_date.weekday()
        series[0]['series'] = series[0]['series'][first_weekday:]

        # Trim last week to actual week length
        last_weekday = date.weekday()
        series[-1]['series'] = series[-1]['series'][:last_weekday + 1]

    for s in series:
        s['series'].reverse()

    return json_response({'series': series})


def tokenize_query(textual_query):
    if textual_query.count('"') % 2:
        # If the number of " is odd, append a " to make it even.
        # This implicitly closes " left open.
        textual_query += '"'

    accumulator = ''
    quoted = False
    for char in textual_query:
        if char == '"' and quoted:
            yield accumulator
            accumulator = ''
            quoted = False
        elif char == '"' and not quoted:
            accumulator = '"'
            quoted = True
        elif char == ' ' and not quoted:
            if accumulator:
                yield accumulator
            accumulator = ''
        else:
            accumulator += char
    if accumulator:
        yield accumulator


def parse_textual_query(textual_query: str, fields, default_slop=0):
    bool_query = {
        'must': [],
        'must_not': [],
    }

    stray_tokens = []
    for token in tokenize_query(textual_query):
        token_type = token[0]
        token_value = token[1:]
        if token_type == '"':
            bool_query['must'].append({
                'multi_match': {
                    'query': token_value,
                    'fields': fields,
                    'type': 'phrase',
                }
            })
        elif token_type == '+':
            bool_query['must'].append({
                'multi_match': {
                    'query': token_value,
                    'fields': fields,
                    'fuzziness': 0,
                }
            })
        elif token_type == '-':
            bool_query['must_not'].append({
                'multi_match': {
                    'query': token_value,
                    'fields': fields,
                    'fuzziness': 0,
                }
            })
        else:
            stray_tokens.append(token)

    stray = ' '.join(stray_tokens)
    if not stray and not bool_query['must'] and not bool_query['must_not']:
        # We need at least one clause, because elasticsearch ignores "highlight" clauses
        # when no "query" clause regarding its field exists.
        # This adds such a query clause, but since it queries for " " it will be an implicit
        # match-none clause.
        stray = ' '
    if stray:
        bool_query['must'].append({
            'multi_match': {
                'query': stray,
                'fields': fields,
                'slop': default_slop,
            }
        })

    return {'bool': bool_query}


@app.route('/api/search')
@cache_api_view
def search():
    content = request_arg('content', str)
    type = request_arg('type', str)
    sort = request_arg('sort', str, default='score')
    offset = request_arg('offset', int, default=0)
    if type not in ('post', 'thread'):
        raise APIError('Invalid value for type: %r' % type)

    oid = 'pid' if type == 'post' else 'tid'

    # sue me, mccabe

    if sort == 'score':
        sorting = ['_score']
    elif sort == 'date-asc':
        sorting = [
            {oid: {'order': 'asc'}},
            '_score',
        ]
    elif sort == 'date-desc':
        sorting = [
            {oid: {'order': 'desc'}},
            '_score',
        ]
    else:
        raise APIError('Invalid value for sort: %r' % sort)

    session = get_session()
    t0 = time.perf_counter()
    es = config.elasticsearch_client()

    if type == 'post':
        parser_kwargs = dict(
            fields=['content']
        )
    else:
        parser_kwargs = dict(
            fields=['title', 'subtitle'],
            default_slop=100,
        )

    query = parse_textual_query(content, **parser_kwargs)

    es_result = es.search(index=type, body={
        'from': offset,
        'size': 30,
        'query': query,
        'highlight': {
            'encoder': 'html',
            'fields': {
                'content': {
                    'pre_tags': ['<strong>'],
                    'post_tags': ['</strong>'],
                },
            },
        },
        'sort': sorting,
    })
    count = es_result['hits']['total']['value']

    if type == 'post':
        results = [dict(
            score=r['_score'],
            pid=int(r['_id']),  # elasticsearch stores _id always as a string
            poster_uid=r['_source']['poster_uid'],
            snippet=' … '.join(r['highlight']['content']),
        ) for r in es_result['hits']['hits']]

        posts = dict(
            session
            .query(db.Post.pid, db.Post)
            .options(joinedload('poster'), joinedload('thread'))
            .filter(db.Post.pid.in_([result['pid'] for result in results]))
            .all()
        )
        for result in results:
            post = posts[result['pid']]
            result['user'] = post.poster
            result['thread'] = post.thread
            result['timestamp'] = post.timestamp.timestamp()
    else:
        results = [dict(
            score=r['_score'],
            title=r['_source']['title'],
            subtitle=r['_source']['subtitle'],
            tid=int(r['_id']),
        ) for r in es_result['hits']['hits']]

    td = time.perf_counter() - t0
    return json_response({
        'count': count,
        'type': type,
        'results': results,
        'elapsed': td
    })


@app.route('/api/')
def api():
    apis = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api') and rule.endpoint != 'api':
            apis.append(url_for(rule.endpoint, _external=True))
    return json_response({'apis': apis})


def main():
    print('Only for development!')

    @app.route('/search/')
    def search_frontend():
        return send_file(os.path.join(os.path.dirname(__file__), '..', '..', 'search-frontend', 'index.html'))

    app.run(debug=True)
