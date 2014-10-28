import string

from functools import partial
from collections import defaultdict
from itertools import groupby

from five import grok
from Products.CMFCore.utils import getToolByName

from seantis.dir.base.interfaces import (
    IDirectoryItemLike,
    IDirectoryBase,
    IDirectoryCatalog
)
from seantis.dir.base import utils


def is_exact_match(item, term):
    """Returns true if a given item is an exact match of term. Term is the same
    as in category_search.

    """

    categories = defaultdict(list)

    if callable(item.categories):
        item_categories = item.categories()
    else:
        item_categories = item.categories

    for category, label, value in item_categories:
        # category values should be lists
        if isinstance(value, basestring):
            categories[category].append((value.strip(), ))
        else:
            categories[category].append(map(string.strip, value))

    for key, term_values in term.items():

        # empty keys are like missing keys -> ignore
        if term_values == '!empty':
            continue

        if isinstance(term_values, basestring):
            term_values = (term_values, )

        if not categories[key]:
            if ''.join(term_values) != '':
                return False

        for t in term_values:
            for category_values in categories[key]:
                if not t in category_values:
                    return False  # any non-matching => not exact match

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
            object_provides=IDirectoryItemLike.__identifier__,
            **kwargs
        )
        return results

    def sortkey(self):
        """Returns the default sortkey."""
        uca_sortkey = utils.unicode_collate_sortkey()
        return lambda b: uca_sortkey(b.Title.decode('utf-8'))

    def items(self):
        return sorted(self.query(), key=self.sortkey())

    def filter(self, term):
        results = self.query(
            categories={'query': term.values(), 'operator': 'and'}
        )
        filter_key = partial(is_exact_match, term=term)

        return sorted(filter(filter_key, results), key=self.sortkey())

    def search(self, text):

        # remove the fuzzy-search first
        text = text.replace('*', '')

        # wrap the text in quotes so the query parser ignores the content
        # (the user should not be able to get his text inspected by the
        # query parser, because it's a hidden feature at best and a security
        # problem at worst)
        #
        # add a wildcard at the end for fuzzyness
        text = '"{}*"'.format(text)

        return sorted(self.query(SearchableText=text), key=self.sortkey())

    def possible_values(self, items=None, categories=None):
        """Returns a dictionary with the keys being the categories of the
        directory, filled with a list of all possible values for each category.
        If an item contains a list of values (as opposed to a single string)
        those values flattened. In other words, there is no hierarchy in the
        resulting list.

        """
        items = items or self.query()
        categories = categories or self.directory.all_categories()

        values = dict([(c, list()) for c in categories])
        for item in items:
            for key, label, value in item.categories:
                if not key in categories:
                    continue

                if not value:
                    continue

                if isinstance(value, basestring):
                    values[key].append(value)
                else:
                    map(values[key].append, utils.flatten(value))

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
