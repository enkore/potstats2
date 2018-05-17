"""
Copyright (c) 2005-2018 the SQLAlchemy authors and contributors <see AUTHORS file>.
Copyright (c) 2018 Marian Beermann
SQLAlchemy is a trademark of Michael Bayer.

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

---

Represent functions and classes
which allow the usage of Dogpile caching with SQLAlchemy.
Introduces a query option called FromCache.

The three new concepts introduced here are:

 * CachingQuery - a Query subclass that caches and
   retrieves results in/from dogpile.cache.
 * FromCache - a query option that establishes caching
   parameters on a Query
 * RelationshipCache - a variant of FromCache which is specific
   to a query invoked during a lazy load.
 * _params_from_query - extracts value parameters from
   a Query.

The rest of what's here are standard SQLAlchemy and
dogpile.cache constructs.

"""
from hashlib import sha256

from dogpile.cache.region import make_region


dbfile = 'dogpile.dbm'


def mangle_key(key):
    return sha256(key.encode()).hexdigest()


regions = {
    'default': make_region(key_mangler=mangle_key).configure(
        'dogpile.cache.dbm',
        arguments={
            'filename': dbfile,
        }
    )
}


from sqlalchemy.orm.interfaces import MapperOption
from sqlalchemy.orm.query import Query
from dogpile.cache.api import NO_VALUE


class CachingQuery(Query):
    """
    A Query subclass which optionally loads full results from a dogpile
    cache region.

    The CachingQuery optionally stores additional state that allows it to consult
    a dogpile.cache cache before accessing the database, in the form
    of a FromCache or RelationshipCache object.   Each of these objects
    refer to the name of a :class:`dogpile.cache.Region` that's been configured
    and stored in a lookup dictionary.  When such an object has associated
    itself with the CachingQuery, the corresponding :class:`dogpile.cache.Region`
    is used to locate a cached result.  If none is present, then the
    Query is invoked normally, the results being cached.

    The FromCache and RelationshipCache mapper options below represent
    the "public" method of configuring this state upon the CachingQuery.

    """

    def __init__(self, regions, *args, **kw):
        self.cache_regions = regions
        Query.__init__(self, *args, **kw)

    def __iter__(self):
        """
        override __iter__ to pull results from dogpile
        if particular attributes have been configured.

        Note that this approach does *not* detach the loaded objects from
        the current session. If the cache backend is an in-process cache
        (like "memory") and lives beyond the scope of the current session's
        transaction, those objects may be expired. The method here can be
        modified to first expunge() each loaded item from the current
        session before returning the list of items, so that the items
        in the cache are not the same ones in the current Session.

        """
        super_ = super(CachingQuery, self)

        if hasattr(self, '_cache_region'):
            return self.get_value(createfunc=lambda: list(super_.__iter__()))
        else:
            return super_.__iter__()

    def _execute_and_instances(self, context):
        """
        override _execute_and_instances to pull results from dogpile
        if the query is invoked directly from an external context.

        This method is necessary in order to maintain compatibility
        with the "baked query" system now used by default in some
        relationship loader scenarios.   Note also the
        RelationshipCache._generate_cache_key method which enables
        the baked query to be used within lazy loads.
        """
        super_ = super(CachingQuery, self)

        if context.query is not self and hasattr(self, '_cache_region'):
            # special logic called when the Query._execute_and_instances()
            # method is called directly from the baked query
            return self.get_value(
                createfunc=lambda: list(
                    super_._execute_and_instances(context)
                )
            )
        else:
            return super_._execute_and_instances(context)

    def _get_cache_plus_key(self):
        """Return a cache region plus key."""

        dogpile_region = self.cache_regions[self._cache_region.region]
        if self._cache_region.cache_key:
            key = self._cache_region.cache_key
        else:
            key = _key_from_query(self)
        return dogpile_region, key

    def invalidate(self):
        """Invalidate the cache value represented by this Query."""

        dogpile_region, cache_key = self._get_cache_plus_key()
        dogpile_region.delete(cache_key)

    def get_value(self, merge=True, createfunc=None,
                  expiration_time=None, ignore_expiration=False):
        """
        Return the value from the cache for this query.

        Raise KeyError if no value present and no
        createfunc specified.
        """
        dogpile_region, cache_key = self._get_cache_plus_key()

        # ignore_expiration means, if the value is in the cache
        # but is expired, return it anyway.   This doesn't make sense
        # with createfunc, which says, if the value is expired, generate
        # a new value.
        assert not ignore_expiration or not createfunc, "Can't ignore expiration and also provide createfunc"

        if ignore_expiration or not createfunc:
            cached_value = dogpile_region.get(cache_key,
                                expiration_time=expiration_time,
                                ignore_expiration=ignore_expiration)
        else:
            cached_value = dogpile_region.get_or_create(
                                    cache_key,
                                    createfunc,
                                    expiration_time=expiration_time
                                )
        if cached_value is NO_VALUE:
            raise KeyError(cache_key)
        if merge:
            cached_value = self.merge_result(cached_value, load=False)
        return cached_value

    def set_value(self, value):
        """Set the value in the cache for this query."""

        dogpile_region, cache_key = self._get_cache_plus_key()
        dogpile_region.set(cache_key, value)


def query(*arg, **kw):
    return CachingQuery(regions, *arg, **kw)


def _key_from_query(query):
    """Given a Query, create a cache key.

    There are many approaches to this; here we use the simplest,
    which is to create a hash of the text of the SQL statement,
    combined with stringified versions of all the bound parameters
    within it.

    There's a bit of a performance hit with
    compiling out "query.statement" here; other approaches include
    setting up an explicit cache key with a particular Query,
    then combining that with the bound parameter values.
    """

    stmt = query.with_labels().statement
    compiled = stmt.compile()
    params = compiled.params

    # here we return the key as a long string.  our "key mangler"
    # set up with the region will boil it down to an md5.

    parts = [str(compiled)] + [str(params[k]) for k in sorted(params)]
    h = sha256()
    for part in parts:
        encoded = part.encode()
        h.update(len(encoded).to_bytes(4, 'little'))
        h.update(encoded)
    return h.hexdigest()


class FromCache(MapperOption):
    """Specifies that a Query should load results from a cache."""

    propagate_to_loaders = False

    def __init__(self, region='default', cache_key=None):
        """
        Construct a new FromCache.

        :param region: the cache region.  Should be a
        region configured in the dictionary of dogpile
        regions.

        :param cache_key: optional.  A string cache key
        that will serve as the key to the query.   Use this
        if your query has a huge amount of parameters (such
        as when using in_()) which correspond more simply to
        some other identifier.
        """
        self.region = region
        self.cache_key = cache_key

    def process_query(self, query):
        """Process a Query during normal loading operation."""
        query._cache_region = self


class RelationshipCache(MapperOption):
    """Specifies that a Query as called within a "lazy load"
       should load results from a cache."""

    propagate_to_loaders = True

    def __init__(self, attribute, region="default", cache_key=None):
        """Construct a new RelationshipCache.

        :param attribute: A Class.attribute which
        indicates a particular class relationship() whose
        lazy loader should be pulled from the cache.

        :param region: name of the cache region.

        :param cache_key: optional.  A string cache key
        that will serve as the key to the query, bypassing
        the usual means of forming a key from the Query itself.

        """
        self.region = region
        self.cache_key = cache_key
        self._relationship_options = {
            (attribute.property.parent.class_, attribute.property.key): self
        }

    def process_query_conditionally(self, query):
        """
        Process a Query that is used within a lazy loader.

        (the process_query_conditionally() method is a SQLAlchemy
        hook invoked only within lazyload.)
        """
        if query._current_path:
            mapper, prop = query._current_path[-2:]
            key = prop.key

            for cls in mapper.class_.__mro__:
                if (cls, key) in self._relationship_options:
                    relationship_option = self._relationship_options[(cls, key)]
                    query._cache_region = relationship_option
                    break

    def and_(self, option):
        """
        Chain another RelationshipCache option to this one.

        While many RelationshipCache objects can be specified on a single
        Query separately, chaining them together allows for a more efficient
        lookup during load.
        """
        self._relationship_options.update(option._relationship_options)
        return self

    def _generate_cache_key(self, path):
        """
        Indicate to the lazy-loader strategy that a "baked" query
        may be used by returning ``None``.

        If this method is omitted, the default implementation of
        :class:`.MapperOption._generate_cache_key` takes place, which
        returns ``False`` to disable the "baked" query from being used.
        """
        return None
