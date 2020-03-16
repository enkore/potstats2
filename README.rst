potstats2
=========

A classic multi-zoo enterprise architecture:

- Backoffice: The crawler populates the database via the forum's XML API
- Backend: An JSON-API-to-RDBMS connector
- Frontend: Displays backend data as tables, graphs etc. and allows user interaction
- High Performance Offline Transactional Analytics: potstats2-analytics

Le Stack

- Database: PostgreSQL (10+)
- Database connector: sqlalchemy/psycopg2
- HTTP adapter: flask
- Frontend: Angular
- Search server: ElasticSearch (7+)

Setup
-----

1. Set up postgres

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

Worldeater
----------

Instead of complex error handling (beyond e.g. retries within the API abstraction) we can use checkpointing,
since all data is stored in a SQL database. The design itself already implies checkpoints,
some extra commits are already in place.
Phases which will take a lot of time in practice (thread, update and post discovery)
probably should get some time-based checkpoints.

Backend
-------

Run ``potstats2-backend-dev`` for the usual Flask dev server.

Try http://127.0.0.1:5000/api/poster-stats?year=2003

Optional API caching and statistics
+++++++++++++++++++++++++++++++++++

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
for lazy folks, ``potstats2-cache invalidate``.

The Redis DB used for caching is ``0``; DB ``1`` contains some basic statistics.

Statistics can be accessed through the ``/api/backend-stats`` endpoint, especially if you are using
a recent Firefox version, which formats JSON quite nicely by itself. Alternatively ``potstats2-cache stats``
does pretty much the same thing sans HTTP.

Frontend
--------

Go to the ``src/potstats2-frontend`` directory and ``npm install`` it. The ``pack-dist.sh`` script
creates a tarball for deployment at ``dist/potstats2-frontend.tar.gz``. The tarball includes
pre-compressed files compatible with nginx's ``gzip_static`` module.

Search frontend
---------------

This is plain JavaScript in a HTML file. No build tools/steps are required.
