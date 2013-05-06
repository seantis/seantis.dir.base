from five import grok

from plone.indexer.interfaces import IIndexer
from Products.ZCatalog.interfaces import IZCatalog

from seantis.dir.base.interfaces import IDirectoryItemLike
from seantis.dir.base import utils
from seantis.dir.base import const


class DirectoryItemBehavior(object):

    def __init__(self, context):
        self.context = context

    def get_parent(self):
        return self.context.aq_inner.aq_parent

    def categories(self):
        """Returns a list of tuples with each tuple containing three values:
        [0] = attribute name
        [1] = category label (from parent)
        [2] = category value (from self)

        Only returns actually used categories

        """
        items = []
        labels = self.get_parent().labels()
        for cat in labels.keys():
            value = hasattr(self, cat) and getattr(self, cat) or u''
            items.append((cat, labels[cat], value))

        return items

    def keywords(self, categories=None):
        """Returns a flat list of all categories, wheter they are actually
        visible in the directory or not, unless a list of categories is
        specifically passed.

        """
        categories = categories or self.get_parent().all_categories()
        values = []
        for cat in categories:
            values.append(getattr(self, cat))

        return list(utils.flatten(values))

    def category_values_string(self, category):
        """Returns the category values of the given category thusly:

        value;another value;a third value

        -> Required for collective.geo.kml's display_property
        """

        return ';'.join(k for k in self.keywords((category, )) if k)


# add cat1-4 accessors
def create_category_property(category):
    getter = lambda self: getattr(self.context, category)
    setter = lambda self, value: setattr(self.context, category, value)

    return getter, setter

for category in const.CATEGORIES:
    setattr(DirectoryItemBehavior, category, property(
        *create_category_property(category)
    ))


# add cat1-4_value properties
def create_category_value_property(category):
    return lambda self: self.category_values_string(category)

for category in const.CATEGORIES:
    setattr(DirectoryItemBehavior, '{}_value'.format(category), property(
        create_category_value_property(category)
    ))


class DirectoryItemBehaviorIndexer(grok.MultiAdapter):

    grok.implements(IIndexer)
    grok.adapts(IDirectoryItemLike, IZCatalog)
    grok.name('categories')

    def __init__(self, context, catalog):
        self.behavior = DirectoryItemBehavior(context)

    def __call__(self):
        return self.behavior.categories()
