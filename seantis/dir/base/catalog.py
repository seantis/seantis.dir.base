from five import grok

from itertools import groupby, imap, ifilter
from Products.CMFCore.utils import getToolByName

from zope.ramcache.ram import RAMCache

from seantis.dir.base.interfaces import (
    IDirectoryItemBase,
    IDirectoryBase,
    IDirectoryCatalog
)
from seantis.dir.base import utils

item_cache = RAMCache()
item_cache.update(maxAge=0, maxEntries=10000)

uncached = object()


def directory_cachekey(directory):
    return ''.join(map(str, (
        directory.id,
        directory.modified(),
        directory.child_modified
    )))


def directory_item_cachekey(directory, item):
    return directory_cachekey(directory) + str(item.getRID())


def get_object(directory, result):

    cachekey = directory_item_cachekey(directory, result)

    obj = item_cache.query(cachekey, default=uncached)

    if obj is uncached:
        obj = result.getObject()
        item_cache.set(obj, cachekey)

    return obj


def is_exact_match(item, term):
    """Returns true if a given item is an exact match of term. Term is the same
    as in category_search.

    """

    for key in term.keys():
        # empty keys are like missing keys
        if term[key] == '!empty':
            continue

        # categories can be lists or strings, but we want a list in any case
        attrlist = getattr(item, key) or (u'', )
        if not hasattr(attrlist, '__iter__'):
            attrlist = (attrlist, )

        # also use a stripped attribute list as some users will end up adding
        # unused spaces
        striplist = [attr.strip() for attr in attrlist]

        # same goes for terms
        termlist = term[key]
        if not hasattr(termlist, '__iter__'):
            termlist = (termlist, )

        # if there is any term which is not matching, it's not an exact match
        matching_term = lambda term: term in attrlist or term in striplist
        if any([True for t in termlist if not matching_term(t)]):
            return False

    return True


class DirectoryCatalog(grok.Adapter):

    grok.context(IDirectoryBase)
    grok.provides(IDirectoryCatalog)

    def __init__(self, context):
        self.directory = context
        self.catalog = getToolByName(context, 'portal_catalog')
        self.path = '/'.join(context.getPhysicalPath())

    def query(self, **kwargs):
        """Runs a query on the catalog with default parameters set.
        Not part of the official IDirectoryCatalog interface as this is
        highly storage_backend dependent. """
        results = self.catalog(
            path={'query': self.path, 'depth': 1},
            object_provides=IDirectoryItemBase.__identifier__,
            **kwargs
        )
        return results

    def sortkey(self):
        """Returns the default sortkey."""
        uca_sortkey = utils.unicode_collate_sortkey()
        return lambda i: uca_sortkey(i.title)

    def get_object(self, brain):
        obj = get_object(self.directory, brain)
        # Set directory as parent of directory item which comes from the RAM
        # cache (makes absolute_url() work correctly).
        obj.__parent__ = self.directory
        return obj

    def items(self):
        result = map(self.get_object, self.query())
        result.sort(key=self.sortkey())

        return result

    def filter(self, term):
        results = self.query(
            categories={'query': term.values(), 'operator': 'and'}
        )
        filter_key = lambda item: is_exact_match(item, term)

        return sorted(
            ifilter(filter_key, imap(self.get_object, results)),
            key=self.sortkey()
        )

    def search(self, text):

        # make the search fuzzyish (cannot do wildcard in front)
        if not text.endswith('*'):
            text += '*'

        return sorted(
            imap(self.get_object, self.query(SearchableText=text)),
            key=self.sortkey()
        )

    def possible_values(self, items=None, categories=None):
        """Returns a dictionary with the keys being the categories of the
        directory, filled with a list of all possible values for each category.
        If an item contains a list of values (as opposed to a single string)
        those values flattened. In other words, there is no hierarchy in the
        resulting list.

        """
        items = items or self.items()

        categories = categories or self.directory.all_categories()
        values = dict([(cat, list()) for cat in categories])

        for item in items:
            for cat in values.keys():
                for word in item.keywords(categories=(cat,)):
                    word and values[cat].append(word)

        return values

    def grouped_possible_values(self, items=None, categories=None):
        """Same as possible_values, but with the categories of the dictionary
        being unique and each value being wrapped in a tuple with the first
        element as the actual value and the second element as the count
        non-unique values.

        It's really the grouped result of possible_values.

        """

        possible = self.possible_values(items, categories)
        grouped = dict([(k, dict()) for k in possible.keys()])

        for category, items in possible.items():
            groups = groupby(sorted(items))
            for group, values in groups:
                grouped[category][group] = len(list(values))

        return grouped

    def grouped_possible_values_counted(self, items=None, categories=None):
        """Returns a dictionary of categories with a list of possible values
        including counts in brackets.

        """
        possible = self.grouped_possible_values(items, categories)
        result = dict((k, []) for k in possible.keys())

        for category, values in possible.items():
            counted = []
            for text, count in values.items():
                counted.append(utils.add_count(text, count))

            result[category] = sorted(counted,
                                      key=utils.unicode_collate_sortkey())

        return result


def children(folder, portal_type):
    """Returns the descendants of a folder that match the given portal type."""

    catalog = getToolByName(folder, 'portal_catalog')
    path = '/'.join(folder.getPhysicalPath())

    results = catalog(
        path={'query': path, 'depth': 1},
        portal_type=portal_type
    )

    return [r.getObject() for r in results]
