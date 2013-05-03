from five import grok

from plone.indexer.interfaces import IIndexer
from Products.ZCatalog.interfaces import IZCatalog

from seantis.dir.base.interfaces import IDirectoryItemLike
from seantis.dir.base import utils


class DirectoryItemBehavior(object):

    def __init__(self, context):
        self.context = context

    @property
    def directory(self):
        return self.context.aq_inner.aq_parent

    def categories(self):
        """Returns a list of tuples with each tuple containing three values:
        [0] = attribute name
        [1] = category label (from parent)
        [2] = category value (from self)

        Only returns actually used categories

        """
        items = []
        labels = self.directory.labels()
        for cat in labels.keys():
            value = hasattr(self, cat) and getattr(self, cat) or u''
            items.append((cat, labels[cat], value))

        return items

    def keywords(self, categories=None):
        """Returns a flat list of all categories, wheter they are actually
        visible in the directory or not, unless a list of categories is
        specifically passed.

        """
        categories = categories or self.directory.all_categories()
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

    def html_description(self):
        """Returns the description with newlines replaced by <br/> tags"""
        if self.description:
            return self.description.replace('\n', '<br />')
        else:
            return ''

    # I strongly dislike this cat1-4 setup here, but I failed so far in
    # creating those properties dynamically. Will try again => TODO
    def get_cat1(self):
        return self.context.cat1

    def set_cat1(self, value):
        self.context.cat1 = value

    cat1 = property(get_cat1, set_cat1)

    def get_cat2(self):
        return self.context.cat2

    def set_cat2(self, value):
        self.context.cat2 = value

    cat2 = property(get_cat2, set_cat2)

    def get_cat3(self):
        return self.context.cat3

    def set_cat3(self, value):
        self.context.cat3 = value

    cat3 = property(get_cat3, set_cat3)

    def get_cat4(self):
        return self.context.cat4

    def set_cat4(self, value):
        self.context.cat4 = value

    cat4 = property(get_cat4, set_cat4)

    @property
    def cat1_value(self):
        return self.category_values_string('cat1')

    @property
    def cat2_value(self):
        return self.category_values_string('cat2')

    @property
    def cat3_value(self):
        return self.category_values_string('cat3')

    @property
    def cat4_value(self):
        return self.category_values_string('cat4')


class DirectoryItemBehaviorIndexer(grok.MultiAdapter):

    grok.implements(IIndexer)
    grok.adapts(IDirectoryItemLike, IZCatalog)
    grok.name('categories')

    def __init__(self, context, catalog):
        self.behavior = DirectoryItemBehavior(context)

    def __call__(self):
        return self.behavior.categories()
