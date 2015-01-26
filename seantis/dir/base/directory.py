import json

from five import grok
from zope.interface import Interface
from zope.component import getAdapter
from zope.schema.interfaces import IContextSourceBinder
from plone.dexterity.content import Container
from Products.CMFPlone.PloneBatch import Batch
from plone.app.layout.viewlets.interfaces import IBelowContentTitle

from seantis.dir.base import core
from seantis.dir.base import utils
from seantis.dir.base import session
from seantis.dir.base import const
from seantis.dir.base.const import CATEGORIES, ITEMSPERPAGE

from seantis.dir.base.interfaces import (
    IDirectoryItemBase,
    IDirectoryBase,
    IDirectoryCatalog,
    IDirectoryRoot,
    IDirectoryPage,
    IDirectorySpecific
)

from zope.schema.vocabulary import SimpleVocabulary


def valid_category_name(category):
    category = category.replace('IDirectoryCategorized.', '')
    assert category in CATEGORIES
    return category


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

    def suggested_values(self, category):
        """Returns a list of suggested values defined on the directory.
        Will always return a list, thought the list may be empty.

        """
        category = valid_category_name(category)

        assert category in CATEGORIES
        attribute = '%s_suggestions' % category

        if not hasattr(self, attribute):
            return []

        return getattr(self, attribute) or []

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
        if self.description:
            return self.description.replace('\n', '<br />')
        else:
            return ''

    def source_provider(self, category):
        """Returns an IContextSourceBinder with the vocabulary of the
        suggestions for the given category.

        """

        category = valid_category_name(category)
        directory = self

        @grok.provider(IContextSourceBinder)
        def get_categories(ctx):
            terms = []

            for value in directory.suggested_values(category):
                terms.append(
                    SimpleVocabulary.createTerm(value, hash(value), value)
                )

            return SimpleVocabulary(terms)

        return get_categories


class DirectoryCatalogMixin(object):
    _catalog = None

    @property
    def catalog(self):
        if not self._catalog:
            self._catalog = getAdapter(self.directory, IDirectoryCatalog)
        return self._catalog

    @property
    def directory(self):
        if IDirectoryBase.providedBy(self.context):
            return self.context
        elif IDirectoryItemBase.providedBy(self.context):
            if hasattr(IDirectoryItemBase(self.context), 'get_parent'):
                return self.context.get_parent()

        return None


class DirectorySearchViewlet(grok.Viewlet, DirectoryCatalogMixin):

    grok.name('seantis.dir.base.DirectorySearchViewlet')
    grok.context(IDirectoryRoot)
    grok.require('zope2.View')
    grok.viewletmanager(IBelowContentTitle)
    grok.layer(IDirectorySpecific)

    _template = grok.PageTemplateFile('templates/search.pt')

    @property
    def search_url(self):
        return self.directory.absolute_url()

    @property
    def reset_url(self):
        return self.directory.absolute_url() + '?reset=true'

    def remove_count(self, text):
        return utils.remove_count(text)

    def update(self, **kwargs):
        if not self.available():
            return

        if hasattr(self.view, 'catalog'):
            catalog = self.view.catalog
            items = self.view.items
        else:
            catalog = self.catalog
            items = self.catalog.items

        self.items = items() if callable(items) else items

        # for the first category, count all items, for the others
        # count the ones in the current filter (might also be all)
        self.all_values = catalog.grouped_possible_values_counted()

        self.values = dict(cat1=self.all_values['cat1'])
        self.values.update(catalog.grouped_possible_values_counted(
            self.items, categories=['cat2', 'cat3', 'cat4']
        ))

        self.labels = self.directory.labels()
        self.select = session.get_last_filter(self.directory)
        self.searchtext = session.get_last_search(self.directory)

    def category_cache(self, cat):
        """Returns the given categories as json for the client side cache."""

        return json.dumps(self.all_values[cat])

    @property
    def show_filter_reset(self):
        show_reset = bool([v for v in self.select.values() if v != '!empty'])

        if not show_reset and not self.context.enable_search:
            show_reset = self.show_search_reset

        return show_reset

    @property
    def show_search_reset(self):
        show_reset = bool(self.searchtext)

        if not show_reset and not self.context.enable_filter:
            show_reset = self.show_filter_reset

        return show_reset

    def render(self, **kwargs):
        if self.available():
            return self._template.render(self)
        else:
            return u''

    def available(self):
        if not IDirectoryPage.providedBy(self.view):
            return False

        if hasattr(self.view, 'hide_search_viewlet'):
            if self.view.hide_search_viewlet:
                return False

        return self.directory is not None


class View(core.View, DirectoryCatalogMixin):
    """Default view of Directory."""

    grok.context(IDirectoryBase)
    grok.require('zope2.View')
    grok.layer(IDirectorySpecific)

    template = grok.PageTemplateFile('templates/directory.pt')

    categories, items = None, None
    filtered = False

    itemsperpage = ITEMSPERPAGE

    def filter(self, terms):
        if terms:
            self.items = self.catalog.filter(terms)
            self.filtered = True
            self._used_terms = terms
        session.set_last_filter(self.context, terms)

    def search(self, searchtext):
        if searchtext:
            self.items = self.catalog.search(searchtext)
            self.filtered = True
            self.used_searchtext = searchtext
        session.set_last_search(self.context, searchtext)

    def reset(self, *args):
        self.filtered = False
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
            elif terms and terms.values() != ['!empty'] * 4:
                action = self.filter
                param = terms

        if not action:
            action = lambda param: None

        return action, param

    def filter_url(self, category, value):
        base = self.context.absolute_url()
        base += '?filter=true&%s=%s' % (category, utils.remove_count(value))
        return base

    def items(self):
        return self.catalog.items()

    @property
    def labels(self):
        return self.context.labels()

    @property
    def used_terms(self):
        return dict(
            i for i in self._used_terms.items() if i[1] and i[1] != '!empty'
        )

    def update(self, **kwargs):
        self._used_terms = {}
        self.used_searchtext = ''

        action, param = self.primary_action()
        action(param)

        super(View, self).update(**kwargs)

    @property
    def batch(self):
        start = int(self.request.get('b_start') or 0)
        items = self.items() if callable(self.items) else self.items

        return Batch(items, self.itemsperpage, start)


class JsonFilterView(core.View, DirectoryCatalogMixin):
    """View to filter the catalog with ajax."""

    grok.context(IDirectoryBase)
    grok.require('zope2.View')
    grok.name('filter')
    grok.layer(IDirectorySpecific)

    mapfields = None
    json_view = True

    def render(self, **kwargs):
        terms = self.get_filter_terms()

        if not len(terms.keys()):
            return json.dumps({})

        if self.request.get('replay'):
            results = []

            for i in xrange(1, len(terms.keys()) + 1):
                cats = const.CATEGORIES[:i]
                term = dict([(k, v) for k, v in terms.items() if k in cats])

                items = self.catalog.filter(term)
                result = self.catalog.grouped_possible_values_counted(items)

                results.append(result)

            return json.dumps(results)

        items = self.catalog.filter(terms)
        result = self.catalog.grouped_possible_values_counted(items)

        return json.dumps(result)


class JsonSearch(core.View, DirectoryCatalogMixin):
    """View to search for a category using the jquery tokenizer plugin."""

    grok.context(IDirectoryBase)
    grok.require('zope2.View')
    grok.name('query')
    grok.layer(IDirectorySpecific)

    json_view = True

    def render(self, **kwargs):
        category = 'cat%i' % int(self.request['cat'])

        if not category in CATEGORIES:
            return json.dumps([])

        possible = self.catalog.grouped_possible_values(self.catalog.items())
        possible = set(possible[category].keys())
        possible = possible.union(self.context.suggested_values(category))

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
