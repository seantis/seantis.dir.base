from five import grok

from Acquisition import aq_base

from plone.indexer.interfaces import IIndexer
from Products.ZCatalog.interfaces import IZCatalog

from seantis.dir.base.interfaces import IDirectoryItemLike
from seantis.dir.base import utils
from seantis.dir.base import const


class DirectoryCategorized(object):

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


# add cat1-4 accessors
def create_category_property(category):
    def getter(self):
        if hasattr(aq_base(self.context), category):
            return getattr(aq_base(self.context), category)
        else:
            return None

    def setter(self, value):

        # if a set is given errors will happen in the keyword index
        if isinstance(value, set):
            value = list(value)

        value = utils.remove_empty(value)
        setattr(self.context, category, value)

    return getter, setter

for category in const.CATEGORIES:
    getter, setter = create_category_property(category)
    setattr(DirectoryCategorized, category, property(getter, setter))


class DirectoryCategorizedIndexer(grok.MultiAdapter):

    grok.implements(IIndexer)
    grok.adapts(IDirectoryItemLike, IZCatalog)
    grok.name('categories')

    def __init__(self, context, catalog):
        self.behavior = DirectoryCategorized(context)

    def __call__(self):
        return self.behavior.categories()
