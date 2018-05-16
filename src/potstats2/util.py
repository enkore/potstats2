from time import perf_counter
from click._termui_impl import ProgressBar


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
