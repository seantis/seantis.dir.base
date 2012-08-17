from zope.interface import (
    Interface,
    invariant,
    Invalid
)
from zope.schema import (
    Text,
    TextLine,
    List,
    Datetime,
    Bool
)

from plone.directives import form
from collective.dexteritytextindexer import searchable

from seantis.dir.base import _

class IDirectoryRoot(form.Schema):
    """Root interface for directories and items alike."""

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

    cat2 = TextLine(
            title=_(u'2nd Category Name'),
            required=False,
            default=u''
        )

    cat3 = TextLine(
            title=_(u'3rd Category Name'),
            required=False,
            default=u''
        )

    cat4 = TextLine(
            title=_(u'4th Category Name'),
            required=False,
            default=u''
        )

    child_modified = Datetime(
            title=_(u'Last time a DirectoryItem was modified'),
            required=False,
            readonly=True
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

class IDirectory(IDirectoryBase):
    pass

class IDirectoryItemBase(IDirectoryRoot):
    """Single entry of a directory. Usually you would not want to directly
    work with this class. Instead refer to IDirectoryItem below.

    """

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

    searchable('cat1')
    cat1 = List(
            title=_(u'1st Category Name'),
            description=_(u'Start typing and select a category. To add a new category write the name and hit enter.'),
            value_type=TextLine(),
            required=False,
        )

    searchable('cat2')
    cat2 = List(
            title=_(u'2nd Category Name'),
            description=_(u'Start typing and select a category. To add a new category write the name and hit enter.'),
            value_type=TextLine(),
            required=False,
        )

    searchable('cat3')
    cat3 = List(
            title=_(u'3rd Category Name'),
            description=_(u'Start typing and select a category. To add a new category write the name and hit enter.'),
            value_type=TextLine(),
            required=False,
        )

    searchable('cat4')
    cat4 = List(
            title=_(u'4th Category Name'),
            description=_(u'Start typing and select a category. To add a new category write the name and hit enter.'),
            value_type=TextLine(),
            required=False,
        )

class IDirectoryItem(IDirectoryItemBase):
    """Marker interface for IDirectory. Exists foremostely to allow
    the overriding of adapters/views in seantis.dir.base. (Given a 
    number of adapters the most specific is used. So if there's an 
    adapter for IDirectoryItem and IDirectoryItemBase, the former
    takes precedence.

    """

class IFieldMapExtender(Interface):
    """Interface describing an object which can extend the FieldMap class used
    for xlsimport/xlsexport.

    """
    def extend_import(self):
        """Extends the fieldmap with custom fields. The default fieldmap for
        the directory item is set as context.

        """