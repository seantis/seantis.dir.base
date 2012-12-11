import logging
logger = logging.getLogger('seantis.dir.base')

from five import grok

from zope.interface import Interface, implements
from zope.component import getUtility

from plone.dexterity.schema import SCHEMA_CACHE
from plone.memoize.instance import memoizedproperty
from plone.memoize import view
from plone.z3cform.fieldsets.utils import move
from plone.registry.interfaces import IRegistry

from z3c.form.interfaces import IFieldsForm, IFormLayer, IAddForm
from z3c.form.field import FieldWidgets

from collective.geo.settings.interfaces import IGeoSettings
from collective.geo.mapwidget.browser.widget import MapWidget
from collective.geo.mapwidget.maplayers import MapLayer
from collective.geo.kml.browser import kmldocument

from seantis.dir.base import utils
from seantis.dir.base import session
from seantis.dir.base.utils import get_current_language
from seantis.dir.base.utils import remove_count
from seantis.dir.base.interfaces import (
    IDirectoryPage, IDirectoryRoot, IDirectoryItemBase, IMapMarker
)


class DirectoryMapLayer(MapLayer):
    """ Defines the map layer for markers shown in the directory view. Pretty
    much equal to the KMLMapLayer, but with optional zooming and letter
    setting by query.

    """

    # A letter of A-Z used for the markers in the klm-document
    letter = None

    # True if the map should be zoomed to the marker on load
    zoom = False

    @memoizedproperty
    def jsfactory(self):
        title = self.context.Title().replace("'", "\\'")
        if isinstance(title, str):
            title = title.decode('utf-8')

        context_url = self.context.absolute_url()
        if not context_url.endswith('/'):
            context_url += '/'

        js = """
        function() {return seantis.maplayer('%(id)s', '%(url)s', '%(title)s', '%(letter)s', %(zoom)s);}
        """

        return js % dict(
            id=self.context.id,
            url=context_url,
            title=title,
            letter=self.letter or u'',
            zoom=self.zoom and 'true' or 'false')

letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class LetterMapMarker(grok.Adapter):

    grok.context(IDirectoryItemBase)
    grok.implements(IMapMarker)

    def url(self, letter):
        """
        Returns URL to a marker image with the letter given as argument.
        """
        return utils.get_marker_url(self.context, letter)


class KMLDocument(kmldocument.KMLDocument):

    @property
    def marker_url(self):
        letter = self.request.get('letter', None) or None
        marker = IMapMarker(self.context)
        return u'string:' + marker.url(letter)

    @property
    def features(self):
        """ Manipulates the features of the klm-document to include the marker
        defined by the query (e.g. @@kml-document?letter=A). """
        features = super(KMLDocument, self).features
        if features:
            features[0].styles['marker_image'] = self.marker_url

        return features


class DirectoryFieldWidgets(FieldWidgets, grok.MultiAdapter):
    """ Adapter that hooks into the widget manager of z3c.forms to
    adjust categories to match the parents of items in add and edit forms.

    """

    grok.adapts(IFieldsForm, IFormLayer, IDirectoryRoot)

    def __init__(self, form, request, context):
        self.form = form
        self.context = context
        self.request = request

        # if this is a seantis dir type this widget manager adapter acts
        # like a poor mans version of plone.autoform (though it's actually more
        # advanced when it comes to the field ordering)
        # => see field_order, omitted_fields, reorder_widgets and update
        if hasattr(form, 'portal_type') and 'seantis.dir' in form.portal_type:
            self.hook_form = True
            self.reorder_widgets()
        else:
            self.hook_form = False

        super(DirectoryFieldWidgets, self).__init__(form, request, context)

    @property
    def update_category_widgets(self):
        """ Return true if the category widgets need to be removed / renamed. """

        return '.item' in self.form.portal_type

    @property
    def omitted_fields(self):
        """ Gets the omitted fields from the schema. May be specified like this:

        ISchema.setTaggedValue('seantis.dir.base.omitted', ['field1', 'field2'])
        """
        iface = SCHEMA_CACHE.get(self.form.portal_type)
        return iface.queryTaggedValue('seantis.dir.base.omitted', [])

    @property
    def field_order(self):
        """ See reorder_widgets. """
        iface = SCHEMA_CACHE.get(self.form.portal_type)
        return iface.queryTaggedValue('seantis.dir.base.order', ['*'])

    @property
    def custom_labels(self):
        """ See label_widgets. """
        iface = SCHEMA_CACHE.get(self.form.portal_type)
        return iface.queryTaggedValue('seantis.dir.base.labels', {})

    @property
    def omitted_categories(self):
        return self.directory.unused_categories()

    @property
    def directory(self):
        if IDirectoryItemBase.providedBy(self.content):
            return self.content.get_parent()
        else:
            return self.content

    def update(self):
        super(DirectoryFieldWidgets, self).update()

        # some forms are adapted which we don't care about, since the
        # add forms can't be adapted by the schema interface (they
        # implement the folder interface, not the type interface)
        # -> skip those
        if not self.hook_form:
            return

        # remove / rename category fields
        if self.update_category_widgets:
            self.label_widgets()
            map(self.remove_widget, self.omitted_categories)

        # remove omitted fields
        map(self.remove_widget, self.omitted_fields)

        # apply custom labels
        self.custom_label_widgets()

    def remove_widget(self, key):
        # the second way is probably the right one, but the first way
        # worked in older plone versions before, so i'll leave it
        if key in self.__dict__:
            del self[key]

        if key in self.form.widgets:
            del self.form.widgets[key]

    def reorder_widgets(self):
        """ Reorders the widgets of the form. Must be called before the parent's
        __init__ method. The field order is a list of fields. Fields present
        in the list are put in the order of the list. Fields not present in the
        list are put at the location of the asterisk (*) which must be present
        in the list.

        Example:
        class ISchema(Interface):
            field1 = Field()
            field2 = Field()
            field3 = Field()
            field4 = Field()
            field5 = Field()

        ISchema.setTaggedValue('seantis.dir.base.order',
            ["field5", "field4", "*", "field1"]

        Will produce this order:
        Field5, Field4, Field2, Field3, Field1

        """
        order = self.field_order
        default = order.index('*')

        # move fields before the star
        for prev, curr, next in utils.previous_and_next(reversed(order[:default])):
            move(self.form, curr, before=prev or '*')

        # move fields after the star
        for prev, curr, next in utils.previous_and_next(order[default + 1:]):
            move(self.form, curr, after=prev or '*')

    def label_widgets(self):
        """Takes a list of widgets and substitutes the labels of those
        representing category values with the labels from the Directory.

        """
        # Set correct label depending on the DirectoryItem value
        labels = self.directory.labels()
        for field, widget in self.items():
            if field in labels:
                widget.label = labels[field]

    def custom_label_widgets(self):
        """Goes throught he custom labels and applies them. """

        for field, label in self.custom_labels.items():
            if field in self.form.widgets:
                self.form.widgets[field].label = utils.translate(
                    self.context, self.request, label
                )


class DirectoryFieldWidgetsAddForm(DirectoryFieldWidgets):
    """ The DirectoryFieldWidgets form adapter doesn't adapt Directory creation
    forms, as their context is the folder not the item to be. IDirectoryRoot
    does therefore not adapt to the context.

    This subclass adapts to all add forms on the plone site. If this is indeed
    a good idea remains to be seen. It probably isn't, but it's what I got
    so far.

    """

    grok.adapts(IAddForm, IFormLayer, Interface)


class View(grok.View):

    implements(IDirectoryPage)

    grok.baseclass()

    def update(self, **kwargs):
        try:
            # load the mapfields on update ensuring that they are available
            # from the beginning
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
    def filtered(self):
        if self.is_itemview:
            directory = self.context.get_parent()
            return any((
                session.get_last_search(directory),
                session.get_last_filter(directory)
            ))
        else:
            if 'search' in self.request.keys():
                return True
            if 'filter' in self.request.keys():
                return True
            return len(self.items) != self.unfiltered_count

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

                if not item.id in self.lettermap and item.has_mapdata():

                    layer = DirectoryMapLayer(context=item)

                    if index <= maxindex:
                        layer.letter = self.lettermap[item.id] = letters[index]
                        index += 1

                    mapwidget._layers.append(layer)

        return (mapwidget, )

    def marker_image(self, item):
        """ Returns the marker image used in the mapfields. """
        marker = IMapMarker(item)
        return marker.url(self.lettermap.get(item.id, None))
