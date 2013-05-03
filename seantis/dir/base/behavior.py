from five import grok

from plone.indexer.interfaces import IIndexer
from Products.ZCatalog.interfaces import IZCatalog

from seantis.dir.base.interfaces import (
    IDirectoryItemLike,
    IDirectoryItemBehavior,
    IDirectoryItemBase
)
from seantis.dir.base import utils


class DirectoryItemBehavior(grok.Adapter):
    """Grant local roles to reviewers when the behavior is used.
    """

    grok.implements(IDirectoryItemBase)
    grok.context(IDirectoryItemBehavior)

    grok.name('seantis.dir.base.item-behavior')

    def __init__(self, context):
        self.context = context

    def get_cat1(self):
        return self.context.cat1

    def set_cat1(self, value):
        self.context.cat1 = value

    cat1 = property(get_cat1, set_cat1)

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

    def html_description(self):
        """Returns the description with newlines replaced by <br/> tags"""
        if self.description:
            return self.description.replace('\n', '<br />')
        else:
            return ''


class DirectoryItemBehaviorIndexer(grok.MultiAdapter):
    """Catalog indexer for the 'reviewers' index.
    """

    grok.implements(IIndexer)
    grok.adapts(IDirectoryItemLike, IZCatalog)
    grok.name('categories')

    def __init__(self, context, catalog):
        self.behavior = DirectoryItemBehavior(context)

    def __call__(self):
        return self.behavior.categories()
