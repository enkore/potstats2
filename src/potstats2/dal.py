from datetime import datetime
from functools import partial

from sqlalchemy import func, cast, Float

from .db import User, Post, Thread


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
    return apply_board_filter(apply_year_filter(query, year), bid)


def poster_stats(session, year, bid):
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

    query = (
        session
            .query(
            User,
            post_stats,
            func.coalesce(threads_opened.c.threads_created, 0).label('threads_created'),
        )
        .outerjoin(threads_opened, threads_opened.c.uid == User.uid)
        .join(post_stats, post_stats.c.uid == User.uid)
    )

    return query
