import json
from datetime import datetime

from five import grok
from zope.interface import Interface
from zope.interface import implements
from zope.app.container.interfaces import IObjectMovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from plone.dexterity.content import Container
from Products.CMFCore.interfaces import IActionSucceededEvent
from collective.geo.contentlocations.geostylemanager import GeoStyleManager

from zope.annotation.interfaces import IAttributeAnnotatable
from collective.geo.geographer.interfaces import (
    IGeoreferenceable,
    IGeoreferenced
)
from collective.geo.geographer.geo import GeoreferencingAnnotator
from collective.geo.settings.interfaces import IGeoCustomFeatureStyle
from collective.geo.contentlocations.geomanager import GeoManager

from seantis.dir.base import utils
from seantis.dir.base.interfaces import IDirectoryItemBase

# Subscribe to every event that potentially has an impact on the
# caching in order to trigger a cache invalidation.


@grok.subscribe(IDirectoryItemBase, IObjectMovedEvent)
def onMovedItem(item, event):
    # changed may not necesseraly be there (e.g. the object is
    # using IDirectoryItemBase as a dexterity behavior)
    if hasattr(item, 'changed'):
        item.changed(event.oldParent)
        item.changed(event.newParent)


@grok.subscribe(IDirectoryItemBase, IObjectModifiedEvent)
def onModifiedItem(item, event):
    if hasattr(item, 'changed'):
        item.changed(item.get_parent())


@grok.subscribe(IDirectoryItemBase, IActionSucceededEvent)
def onChangedWorkflowState(item, event):
    if hasattr(item, 'changed'):
        item.changed(item.get_parent())


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

    def get_parent(self):
        #I tried to use @property here, but this screws with the acquisition
        #context, which apparently is a known sideffect in this case
        return self.aq_inner.aq_parent

    def changed(self, parent):
        """Sets the time when a childitem was changed."""
        if parent:
            parent.child_modified = datetime.now()

    def categories(self):
        """Returns a list of tuples with each tuple containing three values:
        [0] = attribute name
        [1] = category label (from parent)
        [2] = category value (from self)

        Only returns actually used categories

        """
        items = []
        labels = self.get_parent().labels()
        for cat in labels.keys():
            value = hasattr(self, cat) and getattr(self, cat) or u''
            items.append((cat, labels[cat], value))

        return items

    def keywords(self, categories=None):
        """Returns a flat list of all categories, wheter they are actually
        visible in the directory or not, unless a list of categories is
        specifically passed.

        """
        categories = categories or self.get_parent().all_categories()
        values = []
        for cat in categories:
            values.append(getattr(self, cat))

        return list(utils.flatten(values))

    def html_description(self):
        """Returns the description with newlines replaced by <br/> tags"""
        return self.description and self.description.replace('\n', '<br />') or ''

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


class DirectoryItemViewletManager(grok.ViewletManager):
    grok.context(Interface)
    grok.name('seantis.dir.base.item.viewletmanager')


class DirectoryItemViewlet(grok.Viewlet):
    grok.context(IDirectoryItemBase)
    grok.name('seantis.dir.base.item.detail')
    grok.require('zope2.View')
    grok.viewletmanager(DirectoryItemViewletManager)

    template = grok.PageTemplate(u'<p tal:content="context/description" />')
