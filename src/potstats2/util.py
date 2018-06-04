from time import perf_counter

from click._termui_impl import ProgressBar
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Executable, ClauseElement, _literal_as_text


class ElapsedProgressBar(ProgressBar):
    def __init__(self, iterable=None, length=None, label=None, show_eta=True,
                show_percent=None, show_pos=False,
                item_show_func=None, fill_char='#', empty_char='-',
                bar_template='%(label)s  [%(bar)s]  %(info)s',
                info_sep='  ', width=36, file=None, color=None):
        super().__init__(iterable=iterable, length=length, show_eta=show_eta,
                       show_percent=show_percent, show_pos=show_pos,
                       item_show_func=item_show_func, fill_char=fill_char,
                       empty_char=empty_char, bar_template=bar_template,
                       info_sep=info_sep, file=file, label=label,
                       width=width, color=color)

    def __enter__(self):
        self.t0 = perf_counter()
        return super().__enter__()

    def render_finish(self):
        self.elapsed = perf_counter() - self.t0
        self.show_eta = False
        self._last_line = ""
        self.render_progress()
        self.file.write(' ... elapsed %.1f s' % self.elapsed)
        super().render_finish()


def chunk_query(query, primary_key, chunk_size=1000):
    """
    Split a query into smaller ones along the given primary key.
    """
    last_id = None
    while True:
        q = query
        if last_id is not None:
            q = query.filter(primary_key > last_id)
        row = None
        for row in q.order_by(primary_key).limit(chunk_size):
            yield row
        if row is None:
            break
        last_id = getattr(row, primary_key.name) if row else None


class explain(Executable, ClauseElement):
    def __init__(self, stmt, analyze=False):
        self.statement = _literal_as_text(stmt)
        self.analyze = analyze
        # helps with INSERT statements
        self.inline = getattr(stmt, 'inline', None)


@compiles(explain, 'postgresql')
def pg_explain(element, compiler, **kw):
    text = "EXPLAIN "
    if element.analyze:
        text += "ANALYZE "
    text += compiler.process(element.statement, **kw)
    return text


def explain_query(session, query):
    return '\n'.join(s for s, in session.execute(explain(query, analyze=True)).fetchall())
