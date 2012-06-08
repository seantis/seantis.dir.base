from five import grok

from zope.component import adapts
from plone.dexterity.interfaces import IDexterityContent

from plone.app.dexterity.behaviors.metadata import DCFieldProperty
from collective.geo.mapwidget.browser.widget import MapWidget
from collective.geo.mapwidget.maplayers import MapLayer
from collective.geo.kml.browser.maplayers import KMLMapLayer
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate

from seantis.dir.base.utils import get_current_language
from seantis.dir.base.utils import remove_count
from plone.memoize.instance import memoizedproperty
from ZPublisher.interfaces import UseTraversalDefault

from five.customerize import zpt

class DirectoryMapLayer(MapLayer):
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

class View(grok.View):
    grok.baseclass()

    @property
    def current_language(self):
        return get_current_language(self.context, self.request)

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
    def mapfields(self):
        mapwidget = MapWidget(self, self.request, self.context)
        if not hasattr(self, 'items'):
            if self.context.has_mapdata():
                mapwidget._layers = [KMLMapLayer(context=self.context)]
        else:
            assert hasattr(self, 'batch')
            
            mapwidget._layers = list()
            for item in self.batch:
                if item.has_mapdata():
                    mapwidget._layers.append(DirectoryMapLayer(context=item))

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
