import json

from five import grok
from zope.schema import Text
from zope.schema import TextLine
from zope.schema import Datetime
from zope.schema import Bool
from zope.interface import invariant
from zope.interface import Interface
from zope.interface import Invalid
from plone.directives import form
from plone.dexterity.content import Container
from Products.CMFPlone.PloneBatch import Batch
from plone.app.layout.viewlets.interfaces import IBelowContentTitle

from seantis.dir.base import _
from seantis.dir.base import core
from seantis.dir.base import catalog
from seantis.dir.base import utils
from seantis.dir.base import session
from seantis.dir.base.const import CATEGORIES, ITEMSPERPAGE

from seantis.dir.base.item import IDirectoryItemBase


class NoCategoriesDefined(Invalid):
    __doc__ = _(u"No categories were defined. Define at least one category")


class IDirectoryBase(form.Schema):
    """Container for all directory items."""

    title = TextLine(
            title=_(u'Name'),
        )

    subtitle = TextLine(
            title=_(u'Subtitle'),
            required=False
        )
    
    description = Text(
            title=_(u'Description'),
            required=False,
            default=u''
        )
    
    cat1 = TextLine(
            title=_(u'1st Category Name'),
            required=False,
            default=u''
        )

    cat2 = TextLine(
            title=_(u'2nd Category Name'),
            required=False,
            default=u''
        )

    cat3 = TextLine(
            title=_(u'3rd Category Name'),
            required=False,
            default=u''
        )

    cat4 = TextLine(
            title=_(u'4th Category Name'),
            required=False,
            default=u''
        )

    child_modified = Datetime(
            title=_(u'Last time a DirectoryItem was modified'),
            required=False,
            readonly=True
        )

    enable_filter = Bool(
            title=_(u'Enable filtering'),
            required=True,
            default=True
        )

    enable_search = Bool(
            title=_(u'Enable searching'),
            required=True,
            default=True
        )

    @invariant
    def validateCategories(data):
        if not any((data.cat1, data.cat2, data.cat3, data.cat4)):
            raise NoCategoriesDefined(
                _(u"No categories were defined. Define at least one category")
            )


class IDirectory(IDirectoryBase):
    pass


class Directory(Container):
    """Represents objects created using IDirectory."""

    def all_categories(self):
        """Return a list with the names of all category attributes."""
        return CATEGORIES

    def used_categories(self):
        """Return names of all used (non-empty) category attributes."""
        return [c for c in self.all_categories() if getattr(self, c)]
    
    def unused_categories(self):
        """Return names of all unused (empty) category attributes."""
        return [c for c in self.all_categories() if not getattr(self, c)]

    def labels(self):
        """Return a dictionary with they key being the category attribute
        name and the value being the label defined by the attribute value.
        Returns only used categories, as unused ones don't have labels.

        """
        categories = self.used_categories()
        titles = [getattr(self, c) for c in categories]

        return dict(zip(categories, titles))

    def html_description(self):
        """Returns the description with newlines replaced by <br/> tags"""
        return self.description and self.description.replace('\n', '<br />') or ''

class DirectorySearchViewlet(grok.Viewlet):

    grok.name('seantis.dir.base.DirectorySearchViewlet')
    grok.context(form.Schema)
    grok.require('zope2.View')
    grok.viewletmanager(IBelowContentTitle)

    _template = grok.PageTemplateFile('templates/search.pt')

    def get_context(self, context):
        if IDirectoryBase.providedBy(self.context):
            return IDirectoryBase(self.context)
        elif IDirectoryItemBase.providedBy(self.context):
            return IDirectoryItemBase(self.context).parent()
        else:
            return None

    @property
    def url(self):
        return self.context.absolute_url()

    def remove_count(self, text):
        return utils.remove_count(text);

    @property
    def widths(self):
        if self.context.enable_search and self.context.enable_filter:
            return (40, 60)
        elif self.context.enable_search:
            return (100, 0)
        elif self.context.enable_filter:
            return (0, 100)
        else:
            return (0, 0)

    @property
    def searchstyle(self):
        return 'width: %s%%' % self.widths[0]

    @property
    def filterstyle(self):
        return 'width: %s%%' % self.widths[1]

    def update(self, **kwargs):
        self.context = self.get_context(self.context)
        
        if self.context: 
            self.items = catalog.items(self.context)

            self.values = catalog.grouped_possible_values_counted(
                          self.context, self.items)
            self.labels = self.context.labels()
            self.select = session.get_last_filter(self.context)
            self.searchtext = session.get_last_search(self.context)

    def render(self, **kwargs):
        if self.context != None:
            return self._template.render(self)
        else:
            return u''

    def available(self):
        # grok.Viewlet does provide a way to indicate if the viewlet should be 
        # rendered or not (called between update and render). Unfortunately it is 
        # not used in versions prior to 1.9 which is quite new. 
        # For this reason the render method above is used instead of just 
        # specifying self.template. Once 1.9+ of grokcore.viewlet is widely used
        # self._template can be renamed to self.template and the render method 
        # can be removed.
        return self.get_context(self.context) != None


class View(core.View):
    """Default view of Directory."""

    grok.context(IDirectoryBase)
    grok.require('zope2.View')
    
    template = grok.PageTemplateFile('templates/directory.pt')
    
    categories, items, values = None, None, None

    def filter(self, terms):
        if terms:
            self.items = catalog.category_filter(self.context, terms)
        session.set_last_filter(self.context, terms)

    def search(self, searchtext):
        if searchtext:
            self.items = catalog.fulltext_search(self.context, searchtext)
        session.set_last_search(self.context, searchtext)

    def reset(self, *args):
        session.reset_search_filter(self.context)

    def primary_action(self):
        action, param = None, None
        if 'reset' in self.request.keys():
            action = self.reset
            param = None
        elif 'search' in self.request.keys():
            action = self.search
            param = self.request.get('searchtext')
        elif 'filter' in self.request.keys():
            action = self.filter
            param = self.get_filter_terms()
        else:
            searchtext = session.get_last_search(self.context)
            terms = session.get_last_filter(self.context)
            if searchtext:
                action = self.search
                param = searchtext
            elif terms:
                action = self.filter
                param = terms
        
        if not action:
            action = lambda param: None
            
        return action, param

    @property
    def filtered(self):
        return len(self.items) != self.unfiltered_count

    def update(self, **kwargs):
        self.items = catalog.items(self.context)
        self.unfiltered_count = len(self.items)
        self.values = catalog.grouped_possible_values_counted(
                      self.context, self.items)
        self.labels = self.context.labels()

        action, param = self.primary_action()
        action(param)

        super(View, self).update(**kwargs)

    @property
    def batch(self):
        start = int(self.request.get('b_start') or 0)
        return Batch(self.items, ITEMSPERPAGE, start, orphan=1)

class JsonFilterView(core.View):
    """View to filter the catalog with ajax."""

    grok.context(IDirectoryBase)
    grok.require('zope2.View')
    grok.name('filter')

    def render(self, **kwargs):
        terms = self.get_filter_terms()

        if not len(terms.keys()):
            return json.dumps({})

        items = catalog.category_filter(self.context, terms)
        result = catalog.grouped_possible_values_counted(self.context, items)
        return json.dumps(result)


class JsonSearch(core.View):
    """View to search for a category using the jquery tokenizer plugin."""

    grok.context(IDirectoryBase)
    grok.require('zope2.View')
    grok.name('query')

    def render(self, **kwargs):
        category = 'cat%i' % int(self.request['cat'])

        if not category in CATEGORIES:
            return json.dumps([])

        directory = self.context
        possible = catalog.grouped_possible_values(directory, catalog.items(directory))
        possible = possible[category].keys()

        query = self.request['q']

        if not query:
            json.dumps([dict(id=val, name=val) for val in possible])

        searchtext = unicode(query.lower().decode('utf-8'))
        filterfn = lambda item: searchtext in item.lower()
        filtered = filter(filterfn, possible)
        
        return json.dumps([dict(id=val, name=val) for val in filtered])

class DirectoryViewletManager(grok.ViewletManager):
    grok.context(Interface)
    grok.name('seantis.dir.base.directory.viewletmanager')
