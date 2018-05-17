"""
The MIT License (MIT)

Copyright (c) 2016 Jeff Widman
Copyright (c) 2018 Marian Beermann

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sqlalchemy
from sqlalchemy.schema import DDLElement, PrimaryKeyConstraint
from sqlalchemy.ext import compiler


class CreateMaterializedView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


@compiler.compiles(CreateMaterializedView)
def compile(element, compiler, **kw):
    # Could use "CREATE OR REPLACE MATERIALIZED VIEW..."
    # but I'd rather have noisy errors
    return "CREATE MATERIALIZED VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


def create_materialized_view(metadata, name, selectable):
    _mt = sqlalchemy.MetaData()  # temp metadata just for initial Table object creation
    t = sqlalchemy.Table(name, _mt)  # the actual mat view class is bound to db.metadata
    for c in selectable.c:
        t.append_column(sqlalchemy.Column(c.name, c.type, primary_key=c.primary_key))

    if not (any([c.primary_key for c in selectable.c])):
        t.append_constraint(PrimaryKeyConstraint(*[c.name for c in selectable.c]))

    sqlalchemy.event.listen(
        metadata, "after_create",
        CreateMaterializedView(name, selectable)
    )

    @sqlalchemy.event.listens_for(metadata, "after_create")
    def create_indexes(target, connection, **kw):
        for idx in t.indexes:
            idx.create(connection)

    sqlalchemy.event.listen(
        metadata, "before_drop",
        sqlalchemy.DDL('DROP MATERIALIZED VIEW IF EXISTS ' + name)
    )
    return t


def materialized_view_base(declarative_base):
    class MaterializedView(declarative_base):
        __abstract__ = True

        @classmethod
        def refresh(cls, session, concurrently=False):
            # since session.execute() bypasses autoflush, must manually flush in order
            # to include newly-created/modified objects in the refresh
            session.flush()
            table_name = cls.__table__.fullname
            session.execute('REFRESH MATERIALIZED VIEW '
                            + ('CONCURRENTLY ' if concurrently else '')
                            + table_name)

    return MaterializedView
