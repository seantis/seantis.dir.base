import json

from five import grok
from zope.interface import Interface
from zope.interface import implements
from zope.deprecation import deprecate

from plone.dexterity.content import Container
from collective.geo.contentlocations.geostylemanager import GeoStyleManager

from zope.annotation.interfaces import IAttributeAnnotatable
from collective.geo.geographer.interfaces import (
    IGeoreferenceable,
    IGeoreferenced
)
from collective.geo.geographer.geo import GeoreferencingAnnotator
from collective.geo.settings.interfaces import IGeoCustomFeatureStyle
from collective.geo.contentlocations.geomanager import GeoManager

from seantis.dir.base import const
from seantis.dir.base.behavior import DirectoryItemBehavior
from seantis.dir.base.interfaces import IDirectoryItemBase


deprecation_message = """
    Using this method or property on the directory item is deprecated,
    use DirectoryItemBehavior instead
"""


class DirectoryItem(Container):
    """Represents objects created using IDirectoryItem."""

    implements(IAttributeAnnotatable, IGeoreferenceable)

    def __init__(self, *args, **kwargs):
        super(DirectoryItem, self).__init__(*args, **kwargs)

    @deprecate(deprecation_message)
    def get_parent(self):
        return DirectoryItemBehavior(self).get_parent()

    @deprecate(deprecation_message)
    def categories(self):
        return DirectoryItemBehavior(self).categories()

    @deprecate(deprecation_message)
    def keywords(self, categories=None):
        return DirectoryItemBehavior(self).keywords(categories)

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

    def has_mapdata(self):
        return IGeoreferenced(self).type is not None

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

        # permanently override certain style settings
        self.geostyles['map_viewlet_position'] = u'fake-manager'
        self.geostyles['marker_image_size'] = 0.71875
        self.geostyles['display_properties'] = []
        self.geostyles['use_custom_styles'] = True
        self.geostyles['display_properties'] = [
            'title',
            'description'
        ] + ['{}_value'.format(cat) for cat in const.CATEGORIES]


class DirectoryItemViewletManager(grok.ViewletManager):
    """ Shown by default on the item list in the directory view. The viewlet
    have a local variable named context which is actually just a catalog brain.

    If an object is needed the viewlet itself has to take care of getting it.
    Though preferrably it won't because the directory might show a lot of
    items and getObject will therefore slow the site down.

    So it is better to define metadata if they are not too large.
    """
    grok.context(Interface)
    grok.name('seantis.dir.base.item.viewletmanager')


class DirectoryItemViewlet(grok.Viewlet):
    grok.context(Interface)
    grok.name('seantis.dir.base.item.detail')
    grok.require('zope2.View')
    grok.viewletmanager(DirectoryItemViewletManager)

    template = grok.PageTemplate(u"""
        <a tal:attributes="href context/getURL">
            <div class="result-title" tal:content="context/Title"/>
            <div class="result-description" tal:content="context/Description"/>
        </a>
    """)
