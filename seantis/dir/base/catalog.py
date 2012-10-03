from five import grok

from itertools import groupby
from Products.CMFCore.utils import getToolByName

from seantis.dir.base.interfaces import (
    IDirectoryItemBase, 
    IDirectoryBase,
    IDirectoryCatalog
)
from seantis.dir.base import utils

class WrappedDict(dict):
    """Wrapper around normal dictionary to allow the dynamic creation of
    attributes on the instance, which is not possible in a normal dict.

    """

class DirectoryCatalog(grok.Adapter):

    grok.context(IDirectoryBase)
    grok.provides(IDirectoryCatalog)

    def __init__(self, context):
        self.directory = context
        self.catalog = getToolByName(context, 'portal_catalog')
        self.path = '/'.join(context.getPhysicalPath())

    def sortkey(self):
        """Returns the default sortkey."""
        uca_sortkey = utils.unicode_collate_sortkey()
        return lambda i: uca_sortkey(i.title)

    def items(self):
        results = self.catalog(path={'query': self.path, 'depth': 1},
            object_provides=IDirectoryItemBase.__identifier__
        )

        return [r.getObject() for r in results]

    def filter(self, term):

        results = self.catalog(path={'query': self.path, 'depth':1}, 
            categories={'query': term.values(), 'operator':'and'},
            object_provides=IDirectoryItemBase.__identifier__
        )

        def filter_key(item):
            for category, value in term.items():
                if value == '!empty':
                    continue
                if not value in getattr(item, category):
                    return False
            return True

        return filter(filter_key, (r.getObject() for r in results))

    def search(self, text):
        results = self.catalog(path={'query': self.path, 'depth':1},
            SearchableText=text,
            object_provides=IDirectoryItemBase.__identifier__
        )

        return [r.getObject() for r in results]

    def possible_values(self, items, categories=None):
        """Returns a dictionary with the keys being the categories of the directory,
        filled with a list of all possible values for each category. If an item 
        contains a list of values (as opposed to a single string) those values 
        flattened. In other words, there is no hierarchy in the resulting list.

        """
        categories = categories or self.directory.all_categories()
        values = dict([(cat,list()) for cat in categories])
        
        for item in items:
            for cat in values.keys():
                for word in item.keywords(categories=(cat,)):
                    word and values[cat].append(word)

        return values

    def grouped_possible_values(self, items, categories=None):
        """Same as possible_values, but with the categories of the dictionary being
        unique and each value being wrapped in a tuple with the first element
        as the actual value and the second element as the count non-unique values.

        It's really the grouped result of possible_values.

        """

        possible = self.possible_values(items, categories)
        grouped = dict([(k, dict()) for k in possible.keys()])

        for category, items in possible.items():
            groups = groupby(sorted(items))
            for group, values in groups:
                grouped[category][group] = len(list(values))

        return grouped

    def grouped_possible_values_counted(self, items, categories=None):
        """Returns a dictionary of categories with a list of possible values
        including counts in brackets.

        """
        possible = self.grouped_possible_values(items, categories)
        result = dict((k, []) for k in possible.keys())

        for category, values in possible.items():
            counted = []
            for text, count in values.items():
                counted.append(utils.add_count(text, count))
            
            result[category] = sorted(counted, key=utils.unicode_collate_sortkey())

        return result

def children(folder, portal_type):
    """Returns the descendants of a folder that match the given portal type."""
    
    catalog = getToolByName(folder, 'portal_catalog')
    path = '/'.join(folder.getPhysicalPath())
    
    results = catalog(
        path={'query': path, 'depth':1}, 
        portal_type=portal_type
    )

    return [r.getObject() for r in results]