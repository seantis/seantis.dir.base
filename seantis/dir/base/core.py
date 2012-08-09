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
from plone.registry.interfaces import IRegistry

from collective.geo.settings.interfaces import IGeoSettings
from collective.geo.mapwidget.browser.widget import MapWidget
from collective.geo.mapwidget.maplayers import MapLayer
from collective.geo.kml.browser.maplayers import KMLMapLayer
from collective.geo.kml.browser import kmldocument

from seantis.dir.base import session
from seantis.dir.base import utils
from seantis.dir.base.utils import get_current_language
from seantis.dir.base.utils import remove_count

class DirectoryMapLayer(MapLayer):
    """ Defines the map layer for markers shown in the directory view. Pretty
    much equal to the KMLMapLayer, but with optional zooming and letter
    setting by query.

    """

    letter = None
    zoom = False

    @memoizedproperty
    def jsfactory(self):
        title = self.context.Title().replace("'", "\\'")
        if isinstance(title, str):
            title = title.decode('utf-8')
        
        context_url = self.context.absolute_url()
        if not context_url.endswith('/'):
            context_url += '/'
        
        zoom = ""
        if self.zoom:
            zoom = """
            layer.events.on({"loadend":function(){
                layer.map.zoomToExtent(layer.getDataExtent());
                if(layer.features.length>1){
                    layer.map.zoomTo(layer.map.getZoom()-1)
                } else {
                    layer.map.zoomTo(layer.map.getZoom()-4)
                }
            }});
            """

        js = """
            function() {
                var layer=new OpenLayers.Layer.GML('%s','%s'+'@@kml-document?letter=%s',{
                    format:OpenLayers.Format.KML,
                    projection:cgmap.createDefaultOptions().displayProjection,
                    formatOptions:{
                        extractStyles:true,
                        extractAttributes:true
                    }
                });
                
                %s

                return layer
            }"""
        return js % (title, context_url, self.letter or u'', zoom)

letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

class KMLDocument(kmldocument.KMLDocument):
    
    @property
    def marker_url(self):
        letter = self.request.get('letter', None) or None
        return u'string:' + utils.get_marker_url(self.context, letter)

    @property
    def features(self):
        features = super(KMLDocument, self).features
        if features:
            features[0].styles['marker_image'] = self.marker_url

        return features

class View(grok.View):
    grok.baseclass()

    def update(self, **kwargs):
        try:
            self.lettermap = dict()
            self.mapfields
        except AttributeError:
            pass

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
                layer = DirectoryMapLayer(context=self.context)
                layer.zoom = True
                layer.letter = None
                mapwidget._layers = [layer]
        else:

            # in a directory view we can expect a batch
            # (only items in the shown batch are painted on the map as performance
            # is going to be a problem otherwise)
            assert hasattr(self, 'batch')

            index = 0
            maxindex = len(letters) - 1

            self.lettermap.clear()
            mapwidget._layers = list()

            for item in sorted(self.batch, key=lambda i: i.title):
                if item.has_mapdata():

                    layer = DirectoryMapLayer(context=item)

                    if index <= maxindex:
                        layer.letter = self.lettermap[item] = letters[index]
                        index += 1

                    mapwidget._layers.append(layer)

        return (mapwidget, )

    def marker_image(self, item):
        return utils.get_marker_url(item, self.lettermap.get(item, None))

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