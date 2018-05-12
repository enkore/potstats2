from flask import Flask, request, jsonify

from ..db import get_session, Post

app = Flask(__name__)


@app.route('/api/poster-stats')
def hello():
    session = get_session()
    return jsonify({'rows': []})


def main():
    print('Only for development!')
    app.run()
