from zope.interface import Interface, alsoProvides, Attribute
from zope.schema import (
    Text,
    TextLine,
    List,
    Bool
)

from plone.directives import form
from collective.dexteritytextindexer import searchable

from seantis.dir.base import _


class IDirectoryPage(Interface):
    """Marker interface for directory views."""


class IDirectoryRoot(form.Schema):
    """Root interface for directories and items alike."""


class IDirectorySpecific(Interface):
    """Layer for seantis.dir.base."""


class IDirectoryBase(IDirectoryRoot):
    """Container for all directory items."""

    title = TextLine(
        title=_(u'Name'),
    )

    subtitle = TextLine(
        title=_(u'Subtitle'),
        required=False
    )

    description = Text(
        title=_(u'Description'),
        required=False,
        default=u''
    )

    cat1 = TextLine(
        title=_(u'1st Category Name'),
        required=False,
        default=u''
    )

    cat1_suggestions = List(
        title=_(u'Suggested Values for the 1st Category'),
        required=False,
        description=_(
            u'These values are suggested when typing category values in the '
            u'category items, in addition to values found in other items.'
        ),
        value_type=TextLine(),
    )

    cat2 = TextLine(
        title=_(u'2nd Category Name'),
        required=False,
        default=u''
    )

    cat2_suggestions = List(
        title=_(u'Suggested Values for the 2nd Category'),
        required=False,
        description=_(
            u'These values are suggested when typing category values in the '
            u'category items, in addition to values found in other items.'
        ),
        value_type=TextLine(),
    )

    cat3 = TextLine(
        title=_(u'3rd Category Name'),
        required=False,
        default=u''
    )

    cat3_suggestions = List(
        title=_(u'Suggested Values for the 3rd Category'),
        required=False,
        description=_(
            u'These values are suggested when typing category values in the '
            u'category items, in addition to values found in other items.'
        ),
        value_type=TextLine(),
    )

    cat4 = TextLine(
        title=_(u'4th Category Name'),
        required=False,
        default=u''
    )

    cat4_suggestions = List(
        title=_(u'Suggested Values for the 4th Category'),
        required=False,
        description=_(
            u'These values are suggested when typing category values in the '
            u'category items, in addition to values found in other items.'
        ),
        value_type=TextLine(),
    )

    enable_filter = Bool(
        title=_(u'Enable filtering'),
        required=True,
        default=True
    )

    enable_search = Bool(
        title=_(u'Enable searching'),
        required=True,
        default=True
    )

    enable_map = Bool(
        title=_(u'Enable the map'),
        required=True,
        default=True
    )

    allow_custom_categories = Bool(
        title=_(u'Allow custom categories'),
        description=_(
            u'If custom categories are allowed, items may specify new '
            u'categories. If they are not allowed, people can only choose '
            u'from the given suggestions.'
        ),
        required=True,
        default=True,
    )


class IDirectory(IDirectoryBase):
    pass


class IDirectoryItemBase(IDirectoryRoot):
    searchable('title')
    title = TextLine(
        title=_(u'Name'),
    )

    searchable('description')
    description = Text(
        title=_(u'Description'),
        required=False,
        default=u'',
        missing_value=u''
    )


class IDirectoryItemCategories(IDirectoryRoot):
    searchable('cat1')
    cat1 = List(
        title=_(u'1st Category Name'),
        description=_(u'Start typing and select a category. '
                      u'To add a new category write the name and hit enter.'),
        value_type=TextLine(),
        required=False,
    )

    searchable('cat2')
    cat2 = List(
        title=_(u'2nd Category Name'),
        description=_(u'Start typing and select a category. '
                      u'To add a new category write the name and hit enter.'),
        value_type=TextLine(),
        required=False,
    )

    searchable('cat3')
    cat3 = List(
        title=_(u'3rd Category Name'),
        description=_(u'Start typing and select a category. '
                      u'To add a new category write the name and hit enter.'),
        value_type=TextLine(),
        required=False,
    )

    searchable('cat4')
    cat4 = List(
        title=_(u'4th Category Name'),
        description=_(u'Start typing and select a category. '
                      u'To add a new category write the name and hit enter.'),
        value_type=TextLine(),
        required=False,
    )


class IDirectoryItemLike(IDirectoryRoot):
    pass


class IDirectoryCategorized(IDirectoryItemCategories):
    pass

alsoProvides(IDirectoryCategorized, form.IFormFieldProvider)


class IDirectoryItem(IDirectoryItemBase):
    """Marker interface for IDirectory. Exists foremostely to allow
    the overriding of adapters/views in seantis.dir.base. (Given a
    number of adapters the most specific is used. So if there's an
    adapter for IDirectoryItem and IDirectoryItemBase, the former
    takes precedence.

    """


class IDirectoryCatalog(Interface):
    """Describes the adapter interface for directory objects that deals
    with iterating over directory items. The Directory Catalog Adapter is
    used throughout seantis.dir.base, allowing for extension modules to define
    their own data backend. """

    def items(self):
        """Returns the items of the directory."""

    def filter(self, term):
        """Returns the items filtered by the term. The term is a dictionary
        of categories with the values being strings to search for.

        e.g.

        term=dict(cat1='category-value-1', cat2='category-value-2')

        If the value is equal to '!empty', the category is not searched.
        This is a bit of a relic and might be dropped in the future.
        In fact, these two terms should yield the exact same result:

        1: dict(cat1='category-value-1', cat2='!empty')
        2: dict(cat1='category-value-1')

        """

    def search(self, text):
        """Returns a list of items that turn up in the fulltext search."""

    def sortkey(self):
        """Returns a sort keyfunction to sort the items of the catalog.
        The items, filter and search functions return the items sorted
        by this key.

        Note that the object will not be loaded using getObject before it is
        passed to the sortkey, so the sortkey has to do that (slow!) or
        get the values from the ZCatalog Metadata (fast).

        See seantis.dir.base.catalog.sortkey for a good example.

        """

    def possible_values(self, items=None, categories=None):
        """Returns a dictionary with keys being cat1-4, and values being
        a list of possible values for the given category. Values which are
        available in different items should not be merged or grouped. For each
        value in an item a value in the values list must exist.

        e.g.
            { 'cat1': ["Rock", "Pop", "Pop", "Pop", "Rock"]}

        Might be moved away from the interface in the future.

        """

    def grouped_possible_values(self, items=None, categories=None):
        """Same as possible_values, but with the values being a list of tuples
        with index 0 being the value and index 1 being the mergecount.

        e.g.
            { 'cat1': [("Rock", 2), ("Pop", 3)] }

        Might be moved away from the interface in the future.

        """

    def grouped_possible_values_counted(self, items=None, categories=None):
        """Same as possible_values, but with the values being a list of
        categories as strings, containing a count.

        e.g.
            { 'cat1': ["Rock (2)", "Pop (2)"] }

        Might be moved away from the interface in the future.

        """


class IFieldMapExtender(Interface):
    """Interface describing an object which can extend the FieldMap class used
    for xlsimport/xlsexport.

    """
    def extend_import(self):
        """Extends the fieldmap with custom fields. The default fieldmap for
        the directory item is set as context.

        """


class IMapMarker(Interface):
    """Interface for providing the URL of the marker image on the map."""
    def url(self, letter):
        """
        Returns the absolute URL of the marker image.
        """


class IExportProvider(Interface):
    """
    Interface for Subscription Adapters providing exports for directories.
    See xlsexport.py for more information and an example (the default export)

    """

    id = Attribute('unique id of the export provider')
    layer = Attribute("""
        layer required for the provider to be considered, None if always
    """)

    # the following two attributes must be i18n messages as they are translated
    title = Attribute('title shown for the export')
    description = Attribute('a lengthy description for the export')

    url = Attribute('url of the export view or external site (may be None)')

    def export(self, request):
        """ Creates the export and returns the body of the response. The
        request object may be used to set response headers.

        If an url is provided this function is NOT CALLED

        """
