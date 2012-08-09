import logging
logger = logging.getLogger('seantis.dir.base')

from Acquisition import aq_inner, aq_parent

from uuid import uuid4 as uuid
from five import grok

from zope.interface import Interface
from zope.component import getUtility
from zope.schema import getFieldsInOrder

from Products.CMFCore.utils import getToolByName
from plone.dexterity.utils import createContent
from plone.dexterity.interfaces import IDexterityFTI
from plone.memoize.instance import memoizedproperty
from plone.memoize import view

from collective.geo.settings.interfaces import IGeoSettings
from collective.geo.mapwidget.browser.widget import MapWidget
from collective.geo.mapwidget.maplayers import MapLayer
from collective.geo.kml.browser.maplayers import KMLMapLayer

from seantis.dir.base import session
from seantis.dir.base.utils import get_current_language
from seantis.dir.base.utils import remove_count

class DirectoryMapLayer(MapLayer):
    """ Defines the map layer for markers shown in the directory view. Pretty
    much equal to the KMLMapLayer, but without any zooming function (i.e the
    center and zoom of collective.geo.settings is used).

    """

    @memoizedproperty
    def jsfactory(self):
        title = self.context.Title().replace("'", "\\'")
        if isinstance(title, str):
            title = title.decode('utf-8')
        
        context_url = self.context.absolute_url()
        if not context_url.endswith('/'):
            context_url += '/'
        
        js = """
            function() {
                var layer=new OpenLayers.Layer.GML('%s','%s'+'@@kml-document',{
                    format:OpenLayers.Format.KML,
                    projection:cgmap.createDefaultOptions().displayProjection,
                    formatOptions:{
                        extractStyles:true,
                        extractAttributes:true
                    }
                });
                
                return layer
            }"""
        return js % (title, context_url)

letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

class View(grok.View):
    grok.baseclass()

    @property
    def current_language(self):
        return get_current_language(self.context, self.request)

    @property
    @view.memoize
    def show_map(self):
        """ The map is shown if the interface is defined in the 
        collective.geo.settings. Said module usually sets or removes the
        interfaces. But since we define our own adapter which is always
        present we simply hide the mapwidget if the seantis.dir.base types
        are not in the content_types list. """

        try:
            settings = getUtility(IRegistry).forInterface(IGeoSettings)            
            return self.context.portal_type in settings.geo_content_types
        except:
            logger.warn('collective.geo could not be loaded', exc_info=True)
            return False

    def get_filter_terms(self):
        """Unpacks the filter terms from a request."""
        terms = {}
        request = self.request

        filterable = lambda k: k.startswith('cat') and request[k] != ''
        category_keys = (k for k in request.keys() if filterable(k))

        for key in category_keys:
            text = request[key].decode('utf-8')
            terms[key] = remove_count(text)

        return terms

    @property
    def is_itemview(self):
        # if no items are found it must be a single item view
        return not hasattr(self, 'items')

    @property
    @view.memoize
    def mapfields(self):
        """ Returns the mapwidgets to be shown on in the directory and item view."""
        
        if not self.show_map:
            return tuple()

        mapwidget = MapWidget(self, self.request, self.context)

        
        if self.is_itemview:
            if self.context.has_mapdata():
                mapwidget._layers = [KMLMapLayer(context=self.context)]

            # clear the possibly existing lettermap
            session.set_lettermap(self.context, dict())

        else:

            # in a directory view we can expect a batch
            # (only items in the shown batch are painted on the map as performance
            # is going to be a problem otherwise)
            assert hasattr(self, 'batch')

            index = 0
            maxindex = len(letters) - 1

            lettermap = dict()
            mapwidget._layers = list()

            for item in sorted(self.batch, key=lambda i: i.title):
                if item.has_mapdata():

                    # create a lettermap and store it in the session
                    # the current request won't suffice as the map layers are
                    # later loaded using ajax
                    if index <= maxindex:
                        lettermap[item.id] = letters[index]
                        index += 1

                    mapwidget._layers.append(DirectoryMapLayer(context=item))

            session.set_lettermap(self.context, lettermap)

        return (mapwidget, )

migration_token = None
def generate_token():
    global migration_token
    migration_token = uuid().hex[:8]

generate_token()

class TypeMigrationView(grok.View):
    grok.context(Interface)
    grok.require('cmf.ManagePortal')
    grok.name('typemigration')

    def __init__(self, *args, **kwargs):
        logger = logging.getLogger() # root
        logger.info("Token for type migration: %s" % migration_token)

        super(TypeMigrationView, self).__init__(*args, **kwargs)

    @property
    def valid_token(self):
        return self.request.get('token', None) == migration_token

    @property
    def directory(self):
        return getUtility(IDexterityFTI, name=self.request.get('directory', None))

    @property
    def item(self):
        return getUtility(IDexterityFTI, name=self.request.get('item', None))

    def render(self):

        if not self.valid_token:
            return "Invalid Token"

        self.catalog = getToolByName(self.context, 'portal_catalog')

        context_path = '/'.join(self.context.getPhysicalPath())
        directories = self.catalog(
            path={'query': context_path, 'depth': 1},
            portal_type='seantis.dir.base.directory'
        )
        
        if not directories:
            return "No directories found"

        for directory in directories:
            self.upgrade_directory(directory)

        self.catalog.clearFindAndRebuild()
        generate_token()

    def clone(self, original, type):
        cloned = createContent(type.factory, title=original.title)
        for key, type in getFieldsInOrder(type.lookupSchema()):
            if not hasattr(original, key):
                continue

            setattr(cloned, key, getattr(original, key))

        cloned._setId(original.id)

        return cloned

    def can_copy(self, obj):
        return 'seantis' in obj.portal_type

    def upgrade_directory(self, directory):

        directory = aq_inner(directory.getObject())
        parent = aq_parent(directory)

        directory_path = '/'.join(directory.getPhysicalPath())
        items = self.catalog(
            path={'query': directory_path, 'depth': 1}
        )

        new_directory = self.clone(directory, self.directory)

        for item in (aq_inner(i.getObject()) for i in items):
            if not self.can_copy(item):
                continue

            if item.portal_type == 'seantis.dir.base.item':
                item_path = '/'.join(item.getPhysicalPath())
                subitems = self.catalog(
                    path={'query': item_path, 'depth': 1}
                )

                new_item = self.clone(item, self.item)

                for subitem in (aq_inner(i.getObject()) for i in subitems):

                    if not self.can_copy(subitem):
                        continue

                    if 'dir.base' in subitem.portal_type:
                        continue

                    new_subitem = self.clone(subitem, getUtility(IDexterityFTI, subitem.portal_type))
                    new_item._setObject(new_subitem.id, new_subitem, suppress_events=True)

                new_directory._setObject(new_item.id, new_item, suppress_events=True)
            else:
                new_directory._setObject(item.id, item, suppress_events=True)

        parent._delObject(directory.id, suppress_events=True)
        parent._setObject(new_directory.id, new_directory, suppress_events=True)