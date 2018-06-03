from datetime import datetime
from functools import partial
from sqlalchemy import func, cast, Float, desc, column
from sqlalchemy.orm import aliased

from .db import User, Board, Thread, Post
from .db import PostQuotes
from .db import LinkRelation


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


def poster_stats(session, year, bid):
    """
    Statistics on posts and threads for each user.

    Result columns:
    user => User
    post_count, edit_count, avg_post_length, threads_created

    Note: total length of all posts is post_count * avg_post_length.
    """
    asf = partial(apply_standard_filters, year=year, bid=bid)
    threads_opened = asf(
        session
        .query(
            User.uid,
            func.count(Thread.tid).label('threads_created'),
        )
        .join(Post.poster)
        .join(Thread, Thread.first_pid == Post.pid)
    ).group_by(User.uid).subquery()

    post_stats = asf(
        session
        .query(
            User.uid,
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            cast(func.avg(func.length(Post.content)), Float).label('avg_post_length'),
        )
        .join(Post.poster)
    ).group_by(User.uid).subquery()

    quoted_stats = asf(
        session
        .query(
            User.uid,
            func.count(PostQuotes.count).label('quoted_count'),
        )
        .join(Post.poster)
        .join(PostQuotes, PostQuotes.quoted_pid == Post.pid)
    ).group_by(User.uid).subquery()

    quotes_stats = asf(
        session
        .query(
            User.uid,
            func.count(PostQuotes.count).label('quotes_count'),
        )
        .join(Post.poster)
        .join(PostQuotes, PostQuotes.pid == Post.pid)
    ).group_by(User.uid).subquery()

    query = (
        session
        .query(
            User,
            post_stats,
            func.coalesce(threads_opened.c.threads_created, 0).label('threads_created'),
            func.coalesce(quoted_stats.c.quoted_count, 0).label('quoted_count'),
            func.coalesce(quotes_stats.c.quotes_count, 0).label('quotes_count'),
        )
        .outerjoin(threads_opened, threads_opened.c.uid == User.uid)
        .outerjoin(quoted_stats, quoted_stats.c.uid == User.uid)
        .outerjoin(quotes_stats, quotes_stats.c.uid == User.uid)
        .join(post_stats, post_stats.c.uid == User.uid)
    )

    return query


def aggregate_stats_segregated_by_time(session, time_column_expression, year, bid):
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
    asf = partial(apply_standard_filters, year=year, bid=bid)
    post_query = asf(
        session
        .query(
            func.count(Post.pid).label('post_count'),
            func.sum(Post.edit_count).label('edit_count'),
            cast(func.avg(func.length(Post.content)), Float).label('avg_post_length'),
            time_column_expression.label('time')
        )
        .group_by('time')
    ).subquery()
    threads_query = asf(
        session
        .query(
            func.count(Thread.tid).label('threads_created'),
            time_column_expression.label('time')
        )
        .join(Thread.first_post)
        .group_by('time')
    ).subquery()
    user_sq = asf(
        session
        .query(
            User.uid,
            time_column_expression.label('time'),
        )
        .join(Post.poster)
        .group_by('time', User.uid)
    ).subquery()
    active_users_query = (
        session.query(
            func.count(user_sq.c.uid).label('active_users'),
            user_sq.c.time
        )
        .select_from(user_sq)
        .group_by(user_sq.c.time)
    ).subquery()

    query = (
        session
        .query('post_count', 'edit_count', 'avg_post_length',
               # We don't need to COALESCE the post stats,
               # because a created thread implies at least one post.
               func.coalesce(threads_query.c.threads_created, 0).label('threads_created'),
               'active_users',
               post_query.c.time)
        .select_from(post_query)
        .outerjoin(threads_query, post_query.c.time == threads_query.c.time, full=True)
        .outerjoin(active_users_query, post_query.c.time == active_users_query.c.time, full=True)
        .order_by(post_query.c.time)
    )
    return query


def daily_aggregate_statistic(session, statistic, year, bid=None):
    """
    Aggregate a specific statistic for each day in a given year.

    Result columns:
    - time (day of year)
    - statistic
    - active_threads: list of dicts of the most active threads (w.r.t. post count) of the day.
      Each dict consists of json_thread_columns (tid, [sub]title) plus "thread_post_count".
    """
    cte = aggregate_stats_segregated_by_time(session, func.extract('doy', Post.timestamp), year, bid).cte('agg_stats')
    legal_statistics = list(cte.c.keys())
    legal_statistics.remove('time')
    if statistic not in legal_statistics:
        raise DalParameterError('Invalid statistic %r, choose from: %s' % (statistic, legal_statistics))

    json_thread_columns = (Thread.tid, Thread.title, Thread.subtitle)

    threads_active_during_time = apply_standard_filters(
        session
            .query(*json_thread_columns, func.count(Post.pid).label('thread_post_count'))
            .join(Post.thread)
            .filter(func.extract('doy', Post.timestamp) == cte.c.time)
            .group_by(*json_thread_columns)
            .order_by(desc('thread_post_count'))
            .correlate(cte)
        , year, bid).limit(5).subquery('tadt')

    threads_column = session.query(func.json_agg(column('tadt'))).select_from(threads_active_during_time).label('active_threads')

    return session.query(cte.c.time.label('day_of_year'), cte.c[statistic].label('statistic'), threads_column)


def boards(session, year=None):
    """
    Retrieve boards and aggregate statistics.

    Result columns:
    Board, thread_count, post_count
    """
    sq = session.query(Thread.bid, Thread.tid, func.count(Post.pid).label('post_count')).join(Thread.posts).group_by(Thread.tid)
    if year:
        sq = apply_year_filter(sq, year)
    sq = sq.subquery()
    query = (
        session
        .query(Board, func.count(sq.c.tid).label('thread_count'), func.sum(sq.c.post_count).label('post_count'))
        .join(sq, sq.c.bid == Board.bid).group_by(Board)
    )
    return query


def social_graph(session, year=None):
    """
    Retrieve social graph (based on how users quote each other).

    Result columns:
    User: quoter, User: quotee, count, intensity

    intensity is count relative to the maximum count in the current result
    (thus, intensity is between zero and one).
    """

    quoter = aliased(User, name='quoter')
    quotee = aliased(User, name='quotee')
    quoted_post = aliased(Post, name='quoted_post')

    count = func.sum(PostQuotes.count).label('count')

    query = apply_year_filter(
        session
        .query(quoter, quotee, count)
        .join(Post, PostQuotes.post)
        .join(quoted_post, PostQuotes.quoted_post)
        .join(quoter, Post.poster)
        .join(quotee, quoted_post.poster)
        .group_by(quoter.uid, quotee.uid)
        .order_by(desc(count))
        , year
    )

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
