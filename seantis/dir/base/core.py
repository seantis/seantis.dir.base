import logging
logger = logging.getLogger('seantis.dir.base')

from five import grok

from zope.component import adapts, getUtility

from plone.registry.interfaces import IRegistry
from plone.dexterity.interfaces import IDexterityContent
from plone.app.dexterity.behaviors.metadata import DCFieldProperty
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
            if self.is_itemview:
                return 'seantis.dir.base.item'  in settings.geo_content_types
            else:
                return 'seantis.dir.base.directory' in settings.geo_content_types
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


def ExtendedDirectory(directory):
    interface = directory.interface
    fields = [(f, interface[f]) for f in interface]
    for name, field in fields:
        if not hasattr(directory, name):
            setattr(directory, name, DCFieldProperty(field))

    return directory

class DirectoryMetadataBase(object):

    adapts(IDexterityContent)
    
    def __init__(self, context):
        self.context = context

        for fieldname in self.interface:
            if not hasattr(self.context, fieldname):
                setattr(self.context, fieldname, None)
