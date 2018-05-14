postats2
========

A classic three-zoo enterprise architecture:

- Backoffice: The worldeater populates the database via the XML API
- Backend: A JSON-API-to-RDBMS connector
- Frontend: Need that one too :D

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

Run crawler (currently runs against some random subforum no one ever cared about, so this should take all but a minute)::

    potstats2-worldeater

Error handling
++++++++++++++

Instead of complex error handling (beyond e.g. retries within the API abstraction) we can use checkpointing, since all data is stored in a SQL database. The design itself already implies checkpoints, some extra commits are already in place. Phases which will take a lot of time in practice (thread, update and post discovery) probably should get some time-based checkpoints.

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

---

Run ``potstats2-backend-dev`` for the usual Flask dev server.

Try http://127.0.0.1:5000/api/poster-stats?year=2003

About SQLAlchemy
----------------

The ORM is fairly similar to Django (well, it's a Python ORM based on the ActiveRecord pattern...),
but with less magic and no global state. E.g. instead of ``User.objects.get(...)`` (where does the
database connection even come from?) you would write ``session.query(User).get(...)`` (ahh,
a database session!).

``potstats2.db.get_session()`` gives you an ORM session. If needed (unlikely), the engine object
can be accessed through ``session.bind`` or ``potstats2.db.get_engine()``.

- https://docs.sqlalchemy.org/en/latest/orm/tutorial.html#querying
