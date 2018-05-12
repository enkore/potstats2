postats2
========

Backoffice
----------

Installation (possibly not conforming to recent-est PyPA guidelines)::

    virtualenv --python=python3 _venv
    . _venv/bin/activate
    pip install [-e,--editable] .

Configuration (src/potstats2/config.py):

- Optional config file (``~/.config/potstats2.ini``)::

    [potstats2]
    # See https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
    db = sqlite:////home/foo/somewhere/db.sqlite3

- Environment variables override config file::

    # Use in-memory DB
    export POTSTATS2_DB=sqlite://
    # No post-mortem debugger
    export POTSTATS2_DEBUG=0

Create DB schema (probably use alembic later)::

    potstats2-db create_schema

Run crawler::

    potstats2-worldeater

Backend
-------

You're not an alcoholic if you flask it™

Methinks: Anyone can serve a bit of JS for the frontend, not the problem.
Frontend wants to get at the data, so we probably need something like
/api/stats?year=2005&order_by=post_frequency&limit=1000 -> ::

  {'rows': [
    {'user': {'name': ..., 'id': ...},
     'posts': 123928392103,
     'threads': 1231,
     'posts_per_day': 213123,
     ...},
    ...
  ]}

Rinse and repeat for the other statistics. Once we figured that out we can
add additional indexes or views to the DB as needed for performance.
We could even use materialized views for aggregate statistics
that we simply refresh after the crawler ran.
