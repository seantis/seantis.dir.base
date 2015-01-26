import logging
log = logging.getLogger('seantis.dir.base')

from copy import copy, deepcopy
from collections import namedtuple
from five import grok

from zope.interface import Interface, implements
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.schema import Choice

from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.schema import SCHEMA_CACHE
from plone.memoize.instance import memoizedproperty
from plone.memoize import view
from plone.z3cform.fieldsets.utils import move
from plone.app.layout.globals.layout import LayoutPolicy

from z3c.form.interfaces import IFieldsForm, IFormLayer, IAddForm, IGroup
from z3c.form.field import FieldWidgets
from z3c.form.browser.checkbox import CheckBoxFieldWidget

from collective.geo.mapwidget.browser.widget import MapWidget
from collective.geo.mapwidget.maplayers import MapLayer
from collective.geo.geographer.interfaces import IGeoreferenced

# support both fastkml and kml (to be merged in the future)
try:
    from collective.geo.fastkml.browser.kmldocument import (
        KMLDocument as BaseKMLDocument,
        KMLFolderDocument as BaseKMLFolderDocument
    )
    log.info('using fastkml for kml generation')
except ImportError:
    from collective.geo.kml.browser.kmldocument import (
        KMLDocument as BaseKMLDocument,
        KMLFolderDocument as BaseKMLFolderDocument
    )
    log.info('using default for kml generation')

# no fastkml variant for this one
from collective.geo.kml.browser.kmldocument import Placemark as BasePlacemark

from seantis.dir.base import utils
from seantis.dir.base import session
from seantis.dir.base import const
from seantis.dir.base import catalog
from seantis.dir.base.utils import get_current_language
from seantis.dir.base.interfaces import (
    IDirectoryPage,
    IDirectoryRoot,
    IDirectoryBase,
    IDirectoryItemBase,
    IDirectory,
    IDirectoryCategorized,
    IDirectorySpecific,
    IMapMarker
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
        function() {
            return seantis.maplayer(
                '%(id)s', '%(url)s', '%(title)s', '%(letter)s', %(zoom)s
            );
        }
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


class KMLDocument(BaseKMLDocument):
    pass


class KMLFolderDocument(BaseKMLFolderDocument):

    @property
    def features(self):
        terms = utils.get_filter_terms(self.context, self.request)

        for feature in super(KMLFolderDocument, self).features:
            if not terms:
                yield feature
            else:
                item = IDirectoryCategorized(feature.context)

                if catalog.is_exact_match(item, terms):
                    yield feature


class Placemark(BasePlacemark):

    def __init__(self, context, request):
        super(Placemark, self).__init__(context, request)

        # styles are stored as annotation!
        # see collective/geo/contentlocations/geostylemanager.py
        self.styles = deepcopy(self.styles)

        # Manipulates the marker image as defined by the query
        # e.g. @@kml-document?letter=A
        letter = self.request.get('letter', None) or None
        marker = IMapMarker(self.context)
        self.styles['marker_image'] = u'string:' + marker.url(letter)

    def getDisplayValue(self, prop):
        """ Categories need to be flattened and joined sanely. The default
        practice of joining by space is not useful if there are spaces in the
        categories.

        """
        if prop in const.CATEGORIES:
            values = IDirectoryCategorized(self.context).keywords((prop, ))
            return ';'.join(v for v in values if v)
        return super(Placemark, self).getDisplayValue(prop)

    @property
    def extended_data(self):
        Element = namedtuple('ExtendedDataElement', [
            'name', 'value', 'display_name'
        ])

        elements = []
        directory = self.context.aq_inner.aq_parent

        for category, display_name in directory.labels().items():
            elements.append(
                Element(
                    category, self.getDisplayValue(category), display_name
                )
            )
        return elements


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
        if self.hook_form:
            self.reorder_widgets()

        super(DirectoryFieldWidgets, self).__init__(form, request, context)

    @property
    def portal_type(self):
        return self.portal_type_of_form(self.form)

    @property
    def is_group_form(self):
        return IGroup.providedBy(self.form)

    @property
    def uninstantiated_groups(self):
        """ Returns the number of groups which have not been instantiated by
        z3c.form.group.Group.

        """
        if not hasattr(self.form, 'groups'):
            return 0

        if not self.form.groups:
            return 0

        return sum(
            1 for group in self.form.groups if not IGroup.providedBy(group)
        )

    def portal_type_of_form(self, form):
        if hasattr(form, 'portal_type'):
            return form.portal_type
        if hasattr(form, 'context'):
            return form.context.portal_type
        if hasattr(form, 'parentForm'):
            return self.portal_type_of_form(form.parentForm)

        return None

    @property
    def hook_form(self):
        """ Return True if the form should be hooked. """

        if not IDirectorySpecific.providedBy(self.request):
            return False

        if self.is_group_form:
            return False

        if not self.portal_type:
            return False

        if not self.is_directory and not self.inside_directory:
            return False

        try:
            fti = getUtility(IDexterityFTI, name=self.portal_type)
        except ComponentLookupError:
            return False

        if fti.lookupSchema().isOrExtends(IDirectoryRoot):
            return True

        item_behavior = 'seantis.dir.base.interfaces.IDirectoryCategorized'
        if item_behavior in fti.behaviors:
            return True

        return False

    @property
    def is_directory(self):
        """ Return True if this form is a directory. """

        return '.directory' in self.portal_type

    @property
    def omitted_fields(self):
        """ Gets the omitted fields from the schema. Specify as follows:

        ISchema.setTaggedValue(
            'seantis.dir.base.omitted', ['field1', 'field2']
        )
        """
        iface = SCHEMA_CACHE.get(self.portal_type)
        return iface.queryTaggedValue('seantis.dir.base.omitted', [])

    @property
    def field_order(self):
        """ See reorder_widgets. """
        iface = SCHEMA_CACHE.get(self.portal_type)
        return iface.queryTaggedValue('seantis.dir.base.order', ['*'])

    @property
    def custom_labels(self):
        """ See label_widgets. """
        iface = SCHEMA_CACHE.get(self.portal_type)
        return iface.queryTaggedValue('seantis.dir.base.labels', {})

    @property
    def omitted_categories(self):
        return self.directory.unused_categories()

    @property
    def directory(self):
        if IDirectoryItemBase.providedBy(self.context):
            return self.context.aq_inner.aq_parent
        else:
            return self.context

    @property
    def inside_directory(self):
        return IDirectory.providedBy(self.directory)

    def update(self):
        # lock widgets
        if self.hook_form and not self.is_directory:
            if not self.directory.allow_custom_categories:
                self.lock_categories()

        super(DirectoryFieldWidgets, self).update()

        # some forms are adapted which we don't care about, since the
        # add forms can't be adapted by the schema interface (they
        # implement the folder interface, not the type interface)
        # -> skip those
        if not self.hook_form:
            return

        # remove / rename category fields
        if not self.is_directory:
            self.apply_labels(self.directory.labels())
            map(self.remove_widget, self.omitted_categories)

        # remove omitted fields
        map(self.remove_widget, self.omitted_fields)

        # apply custom labels
        self.apply_labels(self.custom_labels)

    def remove_widget(self, fieldname):
        for key, widget in self.form.widgets.items():
            if widget.field.__name__ == fieldname:
                del self.form.widgets[key]

    def reorder_widgets(self):
        """ Reorders the widgets of the form. Must be called before the
        parent's __init__ method. The field order is a list of fields. Fields
        present in the list are put in the order of the list. Fields not
        present in the list are put at the location of the asterisk (*) which
        must be present in the list.

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

        # The order is defined on the schema, but the this widget manager
        # is instantiated on groupforms as well as normal forms. The moving
        # should only happen on the parentform, not the groupform, as
        # the move function will otherwise not find the fields.
        if self.is_group_form:
            return

        # The move function searches for fields in the groups which fails
        # hard if the groups have not been instantiated yet.
        if self.uninstantiated_groups > 0:
            return

        order = self.field_order
        default = order.index('*')

        previous_and_next = utils.previous_and_next

        # move fields before the star
        for prev, curr, next in previous_and_next(reversed(order[:default])):
            move(self.form, curr, before=prev or '*')

        # move fields after the star
        for prev, curr, next in previous_and_next(order[default + 1:]):
            move(self.form, curr, after=prev or '*')

    def lock_categories(self):
        """ Forces radio buttons for categories on items to prevent the user
        from entering his own. Executed if 'allow_custom_categories' is set
        to False on the directory.

        The changes are actually made on the field, which is not what I would
        prefer since they are persistent. But I have yet to find a way to do
        the same thing with pure widgets.
        """

        # shallow copy the fields to be changed so the change does not leak
        # through to other forms.
        self.form.fields = copy(self.form.fields)

        field_names = (
            ['IDirectoryCategorized.cat{}'.format(i) for i in range(1, 5)]
        )
        try:
            for field in field_names:
                # copy field.field manually as the parent is shallow copied
                self.form.fields[field].field = copy(
                    self.form.fields[field].field
                )
        except KeyError:
            return

        categories = [self.form.fields[f] for f in field_names]

        for category in categories:
            category.widgetFactory = CheckBoxFieldWidget
            category.field.description = u''
            category.field.value_type = Choice(
                source=self.directory.source_provider(category.__name__)
            )

    def apply_labels(self, labels):
        """ Applies the labels of the given dictionary built as follows:

            { fieldname => label }

        """
        for widget in self.form.widgets.values():
            if widget.field.__name__ in labels:
                widget.label = labels[widget.field.__name__]


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

    def safe_html(self, html):
        return utils.safe_html(html)

    @property
    @view.memoize
    def show_map(self):
        """ The map is shown if the item type uses the collective.geo
        behaviour. The directory itself does not have coordinates.

        Additionally, the map can be hidden on a per-directory basis, if
        enable_map is set to False.

        """

        if not self.context.enable_map:
            return False

        # blimey, those brits and their spelling
        behavior = 'collective.geo.behaviour.interfaces.ICoordinates'

        if self.is_itemview:
            item_type = self.context.portal_type
        else:
            item_type = self.context.portal_type.replace('.directory', '.item')

        try:
            fti = getUtility(IDexterityFTI, name=item_type)
        except ComponentLookupError:
            log.error("Lookup for {} failed".format(item_type))

            return False

        return behavior in fti.behaviors

    def get_filter_terms(self):
        return utils.get_filter_terms(self.context, self.request)

    @property
    def is_itemview(self):
        return IDirectoryItemBase.providedBy(self.context)

    @property
    def filtered(self):
        if self.is_itemview:
            directory = self.context.get_parent()

            return session.has_last_search(directory) \
                or session.has_last_filter(directory)

        else:
            return self.filtered

    def has_mapdata(self, item):
        try:
            return IGeoreferenced(item).type is not None
        except TypeError:
            return False

    @property
    def show_banner(self):
        return ('banner' in self.request) or not self.filtered

    @property
    @view.memoize
    def mapfields(self):
        "Returns the mapwidgets to be shown on in the directory and item view."

        if not self.show_map:
            return tuple()

        mapwidget = MapWidget(self, self.request, self.context)

        if self.is_itemview:
            if self.has_mapdata(self.context):
                layer = DirectoryMapLayer(context=self.context)
                layer.zoom = True
                layer.letter = None
                mapwidget._layers = [layer]
        else:

            # in a directory view we can expect a batch
            # (only items in the shown batch are painted on the map as
            # performance is going to be a problem otherwise)
            if not hasattr(self, 'batch'):
                log.error('%s view has no batch attribute' % type(self))

            index = 0
            maxindex = len(letters) - 1

            self.lettermap.clear()
            mapwidget._layers = list()

            for item in self.batch:

                if hasattr(item, 'getObject'):
                    item = item.getObject()

                if item.id not in self.lettermap and self.has_mapdata(item):

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


class DirectoryLayoutPolicy(LayoutPolicy):
    """ Adds a seantis-directory-all, seantis-directory-results and
    seantis-directory-item class to the body of all DirectoryPages.

    """

    def bodyClass(self, template, view):
        """Returns the CSS class to be used on the body tag.
        """

        body_class = LayoutPolicy.bodyClass(self, template, view)

        additional_classes = ['seantis-directory-all']

        if IDirectoryBase.providedBy(self.context):
            additional_classes.append('seantis-directory-results')

        if IDirectoryItemBase.providedBy(self.context):
            additional_classes.append('seantis-directory-item')

        return '{} {}'.format(body_class, ' '.join(additional_classes))
