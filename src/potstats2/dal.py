from datetime import datetime
from functools import partial
from sqlalchemy import func, cast, Float, desc, column, tuple_, Integer, and_, Date, text, Interval
from sqlalchemy.orm import aliased

from .db import User, Board, Thread, Post
from .db import PostQuotes
from .db import LinkRelation
from .db import PosterStats, DailyStats, QuoteRelation


class DalParameterError(RuntimeError):
    pass


json_thread_columns = (Thread.tid, Thread.title, Thread.subtitle)


def apply_year_filter(query, year=None):
    if year:
        # [lower, upper)
        lower_timestamp_bound = datetime(year, 1, 1, 0, 0, 0)
        upper_timestamp_bound = lower_timestamp_bound.replace(year=year + 1)
        query = (
            query
            .filter(lower_timestamp_bound <= Post.timestamp)
            .filter(Post.timestamp < upper_timestamp_bound)
        )
    return query


def apply_board_filter(query, bid=None):

    if bid:
        query = query.filter(Post.thread.has(Thread.bid == bid))
    return query


def apply_standard_filters(query, year, bid):
    """
    Filter query related to Post according to year/bid.
    """
    return apply_board_filter(apply_year_filter(query, year), bid)


def poster_stats_agg(session, post_count_cutoff=25):
    """
    Statistics on posts and threads for each user.

    Result columns:
    user => User
    post_count, edit_count, avg_post_length, threads_created

    Note: total length of all posts is post_count * avg_post_length.
    """
    year = func.extract('year', Post.timestamp).label('year')
    threads_opened = (
        session
        .query(
            Post.poster_uid,
            Thread.bid,
            year,
            func.count(Thread.tid).label('threads_created'),
        )
        .join(Thread, Thread.first_pid == Post.pid)
    ).group_by(year, Thread.bid, Post.poster_uid).subquery('threads_opened')

    post_stats = (
        session
        .query(
            Thread.bid,
            year,
            Post.poster_uid,
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            cast(func.avg(Post.content_length), Integer).label('avg_post_length'),
        )
        .join(Post.thread)
    ).group_by(year, Thread.bid, Post.poster_uid).subquery('post_stats')

    quoted_stats = (
        session
        .query(
            Thread.bid,
            year,
            Post.poster_uid,
            func.count(PostQuotes.count).label('quoted_count'),
        )
        .join(Post.thread)
        .join(PostQuotes, PostQuotes.quoted_pid == Post.pid)
    ).group_by(year, Thread.bid, Post.poster_uid).subquery('quoted_stats')

    quotes_stats = (
        session
        .query(
            Thread.bid,
            year,
            Post.poster_uid,
            func.count(PostQuotes.count).label('quotes_count'),
        )
        .join(Post.thread)
        .join(PostQuotes, PostQuotes.pid == Post.pid)
    ).group_by(year, Thread.bid, Post.poster_uid).subquery('quotes_stats')

    query = (
        session
        .query(
            post_stats.c.bid,
            post_stats.c.year,
            post_stats.c.poster_uid.label('uid'),
            post_stats.c.post_count,
            post_stats.c.edit_count,
            post_stats.c.avg_post_length,
            func.coalesce(threads_opened.c.threads_created, 0).label('threads_created'),
            func.coalesce(quoted_stats.c.quoted_count, 0).label('quoted_count'),
            func.coalesce(quotes_stats.c.quotes_count, 0).label('quotes_count'),
        )
        .select_from(post_stats)
        .outerjoin(threads_opened,
                   and_(threads_opened.c.year == post_stats.c.year,
                   threads_opened.c.bid == post_stats.c.bid,
                   threads_opened.c.poster_uid == post_stats.c.poster_uid))
        .outerjoin(quoted_stats,
                   and_(quoted_stats.c.year == post_stats.c.year,
                   quoted_stats.c.bid == post_stats.c.bid,
                   quoted_stats.c.poster_uid == post_stats.c.poster_uid))
        .outerjoin(quotes_stats,
                   and_(quotes_stats.c.year == post_stats.c.year,
                   quotes_stats.c.bid == post_stats.c.bid,
                   quotes_stats.c.poster_uid == post_stats.c.poster_uid))
        .filter(post_stats.c.post_count >= post_count_cutoff)
    )

    return query


def poster_stats(session, year=None, bid=None):
    """
    Statistics on posts and threads for each user.

    Result columns:
    user => User
    post_count, edit_count, avg_post_length, threads_created

    Note: total length of all posts is post_count * avg_post_length.
    """
    agg = lambda f, c: f(c).label(c.name)

    query = (
        session
        .query(
            User,
            agg(func.sum, PosterStats.post_count),
            agg(func.sum, PosterStats.edit_count),
            agg(func.sum, PosterStats.threads_created),
            agg(func.sum, PosterStats.quoted_count),
            agg(func.sum, PosterStats.quotes_count),
            cast(func.avg(PosterStats.avg_post_length), Integer).label('avg_post_length'),
        )
        .join(PosterStats.user)
        .group_by(PosterStats.uid, User)
    )
    if year:
        query = query.filter(PosterStats.year == year)
    if bid:
        query = query.filter(PosterStats.bid == bid)
    return query.from_self()


def aggregate_stats_segregated_by_time(session, time_column_expression, time_column_name):
    """
    Aggregate (across all users) statistics on posts and threads, grouped by time_column_expression.

    Result columns:
    time (=time_column_expression),
    post_count, edit_count, avg_post_length, threads_created

    time_column_expression is suggested to be something like ``func.to_char(Post.timestamp, 'ID')``
    or ``func.extract('year', Post.timestamp)`` but could in fact be pretty much any column expression.

    Note that time_column_expression is used in two slightly different contexts:
    For post statistics it applies to each post individually, while for thread statistics
    it applies to the first post (the start post) of the thread.

    See also:
    - https://www.postgresql.org/docs/current/static/functions-formatting.html
    - https://www.postgresql.org/docs/10/static/functions-datetime.html
    """
    year = func.extract('year', Post.timestamp).label('year')
    post_query = (
        session
        .query(
            year,
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            func.sum(Post.content_length).label('posts_length'),
            time_column_expression.label('time'),
            Board.bid
        )
        .join('thread', 'board')
        .group_by('time', 'year', Board.bid)
    ).subquery()
    threads_query = (
        session
        .query(
            Thread.bid,
            year,
            func.count(Thread.tid).label('threads_created'),
            time_column_expression.label('time')
        )
        .join(Thread.first_post)
        .group_by('time', 'year', Thread.bid)
    ).subquery()
    user_sq = (
        session
        .query(
            Thread.bid,
            year,
            User.uid,
            time_column_expression.label('time'),
        )
        .join(Post.poster)
        .join(Post.thread)
        .group_by('time', 'year', Thread.bid, User.uid)
    ).subquery()
    active_users_query = (
        session.query(
            func.array_agg(user_sq.c.uid).label('active_users'),
            user_sq.c.time,
            user_sq.c.year,
            user_sq.c.bid
        )
        .select_from(user_sq)
        .group_by(user_sq.c.time, user_sq.c.year, user_sq.c.bid)
    ).subquery()

    query = (
        session
        .query('post_count', 'edit_count', 'posts_length',
               # We don't need to COALESCE the post stats,
               # because a created thread implies at least one post.
               func.coalesce(threads_query.c.threads_created, 0).label('threads_created'),
               'active_users',
               post_query.c.time.label(time_column_name), post_query.c.year, post_query.c.bid)
        .select_from(post_query)
        .outerjoin(threads_query,
                   and_(post_query.c.time == threads_query.c.time,
                   post_query.c.year == threads_query.c.year,
                   post_query.c.bid == threads_query.c.bid), full=True)
        .outerjoin(active_users_query,
                   and_(post_query.c.time == active_users_query.c.time,
                   post_query.c.year == active_users_query.c.year,
                   post_query.c.bid == active_users_query.c.bid), full=True)
        .order_by(post_query.c.time)
    )
    return query


def daily_statistics_agg(session):
    """
    Aggregate statistics for each day in each year.

    Result columns:
    - day_of_year, year
    - bid
    - post_count, edit_count, posts_length, threads_created, active_users
    - active_threads: list of dicts of the most active threads (w.r.t. post count) of the day.
      Each dict consists of json_thread_columns (tid, [sub]title) plus "thread_post_count".
    """
    year = func.extract('year', Post.timestamp).label('year')
    cte = aggregate_stats_segregated_by_time(session, func.extract('doy', Post.timestamp), 'day_of_year').subquery()

    json_thread_columns = (Thread.tid, Thread.title, Thread.subtitle)

    threads_active_during_time = (
        session
            .query(*json_thread_columns,
                   func.count(Post.pid).label('thread_post_count'),
                   func.extract('doy', Post.timestamp).label('doy'),
                   year,
                   Thread.bid,
                   func.row_number().over(
                       partition_by=tuple_(year, Thread.bid, func.extract('doy', Post.timestamp)),
                       order_by=tuple_(desc(func.count(Post.pid)), Thread.tid)
                   ).label('rank'))
            .join(Post.thread)
            .group_by(*json_thread_columns, 'doy', Thread.bid, year)
        ).subquery('tadt')

    active_threads = (
        session
        .query(threads_active_during_time.c.doy,
               threads_active_during_time.c.year,
               threads_active_during_time.c.bid,
               func.json_agg(column('tadt')).label('active_threads'))
        .select_from(threads_active_during_time)
        .filter(threads_active_during_time.c.rank <= 5)
        .group_by('doy', 'bid', 'year')
        .subquery()
    )

    return (
        session
        .query(
            *cte.c,
            active_threads.c.active_threads)
        .join(active_threads, and_(active_threads.c.doy == cte.c.day_of_year,
                                   active_threads.c.year == cte.c.year,
                                   active_threads.c.bid == cte.c.bid))
    )


def _daily_stats_agg_query(session):
    agg = lambda f, c: f(c).label(c.name)

    return (
        session
        .query(
            agg(func.sum, DailyStats.post_count),
            agg(func.sum, DailyStats.edit_count),
            agg(func.sum, DailyStats.threads_created),
            func.array_length(func.array_agg(func.distinct(column('users'))), 1).label('active_users'),
            cast(func.sum(DailyStats.posts_length) / func.sum(DailyStats.post_count), Integer).label('avg_post_length'),
        )
        .select_from(DailyStats, func.unnest(DailyStats.active_users).alias('users'))
    )


def yearly_stats(session, year=None, bid=None):
    """
    Aggregate (across all users) statistics on posts and threads

    Result columns:
    post_count, edit_count, avg_post_length, threads_created
    year if year filter is not specified.
    """
    query = _daily_stats_agg_query(session)
    if year:
        query = query.filter(DailyStats.year == year)
    else:
        query = query.add_column(DailyStats.year).group_by(DailyStats.year).order_by(DailyStats.year)

    if bid:
        query = query.filter(DailyStats.bid == bid)
    return query


def daily_stats(session, year, bid=None):
    """
    Aggregate (across all users) statistics on posts and threads

    Result columns:
    post_count, edit_count, avg_post_length, threads_created
    """
    query = (
        _daily_stats_agg_query(session)
        .add_columns(DailyStats.day_of_year, func.jsonb_agg(DailyStats.active_threads).label('active_threads'))
        .filter(DailyStats.year == year)
        .group_by(DailyStats.day_of_year)
        .order_by(DailyStats.day_of_year)
    )
    if bid:
        query = query.filter(DailyStats.bid == bid)
    return query


def daily_statistic(session, statistic, year, bid=None):
    """
    Aggregate (across all users) statistics on posts and threads

    Result columns:
    post_count, edit_count, avg_post_length, threads_created
    """
    sq = daily_stats(session, year, bid).subquery()
    legal_statistics = list(sq.c.keys())
    legal_statistics.remove('day_of_year')
    if statistic not in legal_statistics:
        raise DalParameterError('Invalid statistic %r, choose from: %s' % (statistic, legal_statistics))

    query = session.query(sq.c[statistic].label('statistic'), sq.c.day_of_year, sq.c.active_threads)
    return query


def weekday_stats(session, year=None, bid=None):
    query = (
        _daily_stats_agg_query(session)
        .add_column(func.to_char(
            func.cast(func.concat(DailyStats.year, '-01-01'), Date)
            + func.cast(func.concat(DailyStats.day_of_year - 1, ' days'), Interval),
            'ID').label('weekday'))
        .group_by('weekday')
        .order_by('weekday')
    )
    if year:
        query = query.filter(DailyStats.year == year)
    if bid:
        query = query.filter(DailyStats.bid == bid)
    return query


def boards(session, year=None):
    """
    Retrieve boards and aggregate statistics.

    Result columns:
    Board, thread_count, post_count
    """
    query = (
        session
        .query(Board,
               func.sum(DailyStats.post_count).label('post_count'),
               func.sum(DailyStats.threads_created).label('thread_count'))
        .join(DailyStats.board)
        .group_by(Board)
        .order_by(Board.bid)
    )
    if year:
        query = query.filter(DailyStats.year == year)
    return query


def social_graph_agg(session, count_cutoff=10):
    """
    Retrieve social graph (based on how users quote each other).

    Result columns:

    User: quoter, User: quotee, count

    intensity is count relative to the maximum count in the current result
    (thus, intensity is between zero and one).
    """

    quoter = aliased(User, name='quoter')
    quoted = aliased(User, name='quoted')
    quoted_post = aliased(Post, name='quoted_post')

    count = func.sum(PostQuotes.count).label('count')

    return (
        session
        .query(
            func.extract('year', Post.timestamp).label('year'), Thread.bid,
            quoter.uid.label('quoter_uid'), quoted.uid.label('quoted_uid'), count)
        .join(Post, PostQuotes.post)
        .join(Post.thread)
        .join(quoted_post, PostQuotes.quoted_post)
        .join(quoter, Post.poster)
        .join(quoted, quoted_post.poster)
        .group_by('year', Thread.bid, quoter.uid, quoted.uid)
        .having(count > count_cutoff)
    )


def social_graph(session, year=None):
    """
    Retrieve social graph (based on how users quote each other).

    Result columns:
    User: quoter, User: quotee, count, intensity

    intensity is count relative to the maximum count in the current result
    (thus, intensity is between zero and one).
    """
    quoter = aliased(User, name='quoter')
    quoted = aliased(User, name='quoted')
    count = func.sum(QuoteRelation.count).label('count')
    query = (
        session
        .query(quoter, quoted, count)
        .join(quoter, QuoteRelation.quoter)
        .join(quoted, QuoteRelation.quoted)
        .group_by(quoter, quoted)
        .order_by(desc(count))
    )
    if year:
        query = query.filter(QuoteRelation.year == year)
    # maximum_count = 0 <=> main query has empty result set - no division by zero happens.
    maximum_count = query.from_self(func.max(count)).one()[0] or 0
    query = query.add_columns((count / float(maximum_count)).label('intensity'))
    return query


def user_domains(session, year=None, link_type=None):
    query = (
        session
        .query(User, LinkRelation.domain, func.sum(LinkRelation.count).label('count'))
        .join(LinkRelation.user)
        .group_by(User, LinkRelation.domain)
        .order_by(desc('count'))
    )
    if year:
        query = query.filter(LinkRelation.year == year)
    if link_type:
        query = query.filter(LinkRelation.type == link_type)
    return query


def domains(session, year=None, link_type=None):
    query = (
        session
        .query(func.sum(LinkRelation.count).label('count'), LinkRelation.domain)
        .group_by(LinkRelation.domain)
        .order_by(desc('count'))
    )
    if year:
        query = query.filter(LinkRelation.year == year)
    if link_type:
        query = query.filter(LinkRelation.type == link_type)
    return query
