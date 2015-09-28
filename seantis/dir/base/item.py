import json

from five import grok
from zope.interface import implements

from plone.dexterity.content import Container
from collective.geo.contentlocations.geostylemanager import GeoStyleManager

from zope.annotation.interfaces import IAttributeAnnotatable
from collective.geo.geographer.interfaces import IGeoreferenceable
from collective.geo.geographer.geo import GeoreferencingAnnotator
from collective.geo.settings.interfaces import IGeoCustomFeatureStyle
from collective.geo.contentlocations.geomanager import GeoManager

from seantis.dir.base.interfaces import IDirectoryItemBase


class DirectoryItem(Container):
    """Represents objects created using IDirectoryItem."""

    implements(IAttributeAnnotatable, IGeoreferenceable)

    def get_description(self):
        # ensure that the description is never None (which is handled by the
        # interface definition really, but older items were created without
        # the missing_value option and might be different)
        # => yes a migration would be much better, but I lack the nerve
        # of dealing with GenericSetup right now.
        return self.__dict__['description'] or u''

    def set_description(self, value):
        self.__dict__['description'] = value

    description = property(get_description, set_description)

    def html_description(self):
        """Returns the description with newlines replaced by <br/> tags"""
        if self.description:
            return self.description.replace('\n', '<br />')
        else:
            return ''

    @property
    def longitude(self):
        geo = GeoreferencingAnnotator(self).geo
        if geo['type'] and geo['type'].lower() == 'point':
            return geo['coordinates'][0]

    @property
    def latitude(self):
        geo = GeoreferencingAnnotator(self).geo
        if geo['type'] and geo['type'].lower() == 'point':
            return geo['coordinates'][1]

    def get_coordinates(self):
        return GeoManager(self).getCoordinates()

    def set_coordinates(self, type, coords):
        geo = GeoreferencingAnnotator(self).geo
        geo['type'] = type
        geo['coordinates'] = coords
        geo['crs'] = None

    def remove_coordinates(self):
        geo = GeoreferencingAnnotator(self).geo
        geo['type'] = None
        geo['coordinates'] = None

    # coordiantes_json is used for import / export of coordinates
    def get_coordinates_json(self):
        if all(self.get_coordinates()):
            return json.dumps(self.get_coordinates())
        else:
            return ""

    def set_coordinates_json(self, json_string):
        if json_string is None or not json_string.strip():
            return self.remove_coordinates()

        self.set_coordinates(*json.loads(json_string))

    coordinates_json = property(get_coordinates_json, set_coordinates_json)


class DirectoryItemGeoStyleAdapter(GeoStyleManager, grok.Adapter):

    grok.context(IDirectoryItemBase)
    grok.provides(IGeoCustomFeatureStyle)

    def __init__(self, context):
        super(DirectoryItemGeoStyleAdapter, self).__init__(context)

    def get(self, key, default=False):

        # permanently override certain style settings
        self.ensure_geostyle('map_viewlet_position', u'fake-manager')
        self.ensure_geostyle('marker_image_size', 0.71875)
        self.ensure_geostyle('use_custom_styles', True)
        self.ensure_geostyle('display_properties', [
            'title', 'description', 'cat1', 'cat2', 'cat3', 'cat4'
        ])

        return self.geostyles.get(key, default)

    def ensure_geostyle(self, key, value):
        if self.geostyles[key] != value:
            self.geostyles[key] = value
