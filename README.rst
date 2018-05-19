postats2
========

A classic four-zoo enterprise architecture:

- Backoffice: The worldeater populates the database via the XML API
- Backend: A JSON-API-to-RDBMS connector
- Frontend: Need that one too :D
- Business Intelligence: potstats2-analytics compiles secondary intelligence files from the primary database

Le Stack

- Database: PostgreSQL
- Database connector: sqlalchemy/psycopg2
- HTTP adapter: flask

Public instance lives at http://potstats2.enkore.de/api/ (no TLS yet, because that would show up in public CT logs).
That instance has GET-CORS enabled (for now) and thus the API can be used from other origins.

Setup
-----

1. Set up postgres or use postgres instance at potstats2.enkore.de via SSH port forwarding (see ticket #1).

   For Arch Linux:

   - Install postgres package.
   - ``su -l postgres``
   - ``[postgres]$ initdb --locale $LANG -E UTF8 -D '/var/lib/postgres/data' --data-checksums``
   - ``# systemctl enable postgresql; systemctl start postgresql``
   - ``[postgres]$ createuser --superuser $YOUR_LOGIN``
   - ``[$YOUR_LOGIN]$ createdb potstats2``

   This should work with the default database URL (``postgresql://localhost/potstats2``).
2. Create Python environment (possibly not conforming to recent-est PyPA guidelines)::

    virtualenv --python=python3 _venv
    . _venv/bin/activate
    pip install [-e,--editable] .

3. Create DB schema (probably use alembic later)::

    potstats2-db create_schema

4. Load database dump or run crawler (currently runs against some random subforum no one ever cared about, so this should take all but a minute)::

-  Database dump: Fetch https://pstore.enkore.de/dump-2018-05-16-200%7E54159332c65cf2b3728775b9601580fa65fa9b41a2c5e5bcd85a5936552fadbe%7E.sql.gz
   and run ``gunzip dump...sql.gz | psql potstats2``.
-  Crawler: potstats2-worldeater

Configuration (src/potstats2/config.py)
+++++++++++++++++++++++++++++++++++++++

- Optional config file (``~/.config/potstats2.ini``)::

   [potstats2]
   # See https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
   db = postgresql://scott:tiger@localhost/mydatabase

   [flask]
   some_flask_setting = 1234

- Environment variables override config file::

   # No post-mortem debugger
   export POTSTATS2_DEBUG=0

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

Optional API caching
++++++++++++++++++++

Redis can be used to cache API requests. Since there is no time-based expiry, setting
a memory limit and an eviction policy as per https://redis.io/topics/lru-cache is recommended.
The ``redis`` and ``blinker`` packages are required to use that functionality (``pip install redis blinker``
or ``pip install <this package>[cache]``, i.e. ``pip install .[cache]``).

After setting redis up, simply set REDIS_URL (for a local installation this would usually be ``redis://127.0.0.1:6379``).
The cache is automatically invalidated by

- running database analytics,
- running worldeater,
- changing software version.

Manual invalidation is provided by simply flushing the redis database, or alternatively
for lazy folks, ``potstats2-invalidate-cache``.

The Redis DB used for caching is ``0``; DB ``1`` contains some basic statistics.

About SQLAlchemy
----------------

The ORM is fairly similar to Django (well, it's a Python ORM based on the ActiveRecord pattern...),
but with less magic and no global state. E.g. instead of ``User.objects.get(...)`` (where does the
database connection even come from?) you would write ``session.query(User).get(...)`` (ahh,
a database session!).

``potstats2.db.get_session()`` gives you an ORM session. If needed (unlikely), the engine object
can be accessed through ``session.bind`` or ``potstats2.db.get_engine()``.

- https://docs.sqlalchemy.org/en/latest/orm/tutorial.html#querying

Ideas corner
------------

    Auf jeden Fall muss ein "Verfasser-Guess" auf Basis eines deep learning frameworks rein. 
    
    -- Oli

"Personal statistics", so filtering stats by a user to see things like when a specific user posts. I wouldn't feel comfortable to make this public (even though it technically kinda already is), so this should probably be private to users. This could be done by having a Bot-account PM a login link on request. Or something like that.

Thread tags aren't captured
