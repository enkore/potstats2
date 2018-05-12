import json
from datetime import datetime

from flask import Flask, request, Response
from sqlalchemy import and_, func

from ..db import get_session, Post, User

app = Flask(__name__)


def json_response(data, status_code=200):
    return Response(json.dumps(data), status=status_code, mimetype='application/json')


@app.route('/api/poster-stats')
def poster_stats():
    session = get_session()

    try:
        year = int(request.args['year'])
    except (ValueError, KeyError) as exc:
        return json_response({'error': str(exc)}, status_code=400)

    # [lower, upper)
    lower_timestamp_bound = datetime(year, 1, 1, 0, 0, 0)
    upper_timestamp_bound = lower_timestamp_bound.replace(year=year + 1)

    rows = []
    for user, post_count in (
        session.query(User, func.count(Post.pid))
        .filter(Post.poster_uid == User.uid)
        .filter(and_(lower_timestamp_bound <= Post.timestamp, Post.timestamp < upper_timestamp_bound))
        .group_by(User)
    ).all():
        rows.append({
            'user': {'name': user.name, 'uid': user.uid},
            'post_count': post_count
        })

    return json_response({'rows': rows})


def main():
    print('Only for development!')
    app.run()
