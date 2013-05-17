from Acquisition import aq_base
from zope import component

from seantis.dir.base.directory import CATEGORIES
from seantis.dir.base.item import IDirectoryItemBase
from seantis.dir.base.interfaces import (
    IFieldMapExtender,
    IDirectoryCategorized
)

from seantis.dir.base import _


class FieldMap(object):
    """ Hierarchically maps columns in a row to objects. Each Fieldmap
    defines one object. Each child is another Fieldmap (and so on.)

    """
    def __init__(self):
        self.keyfields = None      # Keyfields define the way rows are grouped
        self.typename = None       # The type of the object
        self.fieldmap = dict()     # A list with fieldnames -> indexes
        self.indexmap = dict()     # A list with indexes -> fieldnames
        self.children = []         # A list of child Fieldmaps
        self.wrapper = dict()      # A list of wrappers for field values
        self.unwrapper = dict()    # A list of unwrappers for field values
        self.root = False          # True when there is no parent fieldmap
        self.titles = dict()       # A list of custom titles
        self.readonly = set()      # A list of readonly fieldnames
        self.transformer = dict()  # A list of transformer functions

        # Interface containg the fields used in the fieldmap
        self.baseinterface = self.interface = IDirectoryItemBase

    def __len__(self):
        return len(self.fieldmap)

    def add_fields(self, fields, startindex=0):
        """ Adds a list of fields to the field- and indexmap. """
        for ix, field in enumerate(fields, startindex):
            self.fieldmap[field] = ix
            self.indexmap[ix] = field

    def add_title(self, fieldname, title):
        self.titles[fieldname] = title

    def mark_readonly(self, fieldname):
        self.readonly.add(fieldname)

    def get_field(self, index, including_children):
        """ Returns the fieldname of an index (optionally looking up the
        children as well).

        """
        if index in self.indexmap:
            return self.indexmap[index]
        elif including_children:
            for child in self.children:
                field = child.get_field(index, True)
                if field:
                    return field

        return None

    def indexes(self):
        """ Returns a list of all index values. """
        return self.fieldmap.values()

    def readonlyindexes(self, including_children):
        """ Returns a list of all readonly indexes. """
        indexes = set()
        if including_children:
            for child in self.children:
                for index in child.readonlyindexes(True):
                    indexes.add(index)

        for field in self.readonly:
            indexes.add(self.fieldmap[field])

        return indexes

    def keyindexes(self, including_children):
        """ Returns a list of all key indexes. """
        indexes = set()

        if including_children:
            for child in self.children:
                for index in child.keyindexes(True):
                    indexes.add(index)

        for field in self.keyfields:
            indexes.add(self.fieldmap[field])

        return indexes

    def maxindex(self):
        """Returns the topmost index of the Fieldmap including the children."""
        childmax = self.children and max(
            [c.maxindex() for c in self.children]
        ) or 0
        selfmax = max(self.indexes())
        return max(childmax, selfmax)

    def minindex(self):
        """ Opposite of maxindex."""
        childmin = self.children and min(
            [c.minindex() for c in self.children]
        ) or 0
        selfmin = min(self.indexes())
        return min(childmin, selfmin)

    def bind_transformer(self, field, transformerfn):
        """ Binds a transformer function to the given field. The transformer
        function is called with the object before the object's attributes are
        read. It allows for acquisition context changes or behavior wrapping.

        """
        self.transformer[field] = transformerfn

    def get_transformer(self, field):
        if field in self.transformer:
            return self.transformer[field]
        else:
            # the default is the object stripped from the acquisition context
            return lambda obj: aq_base(obj)

    def bind_wrapper(self, field, wrapperfn):
        """ Binds a wrapper function to the given field. The wrapper function
        is called when the value is read from the XLS with the value of the
        cell.

        """
        self.wrapper[field] = wrapperfn

    def get_wrapper(self, field=None, ix=None):
        """Returns a bound wrapper or a function returning the value itself."""
        assert(field or (ix or ix >= 0))

        field = field or self.get_field(ix, including_children=True)

        if field and field in self.wrapper:
            return self.wrapper[field]
        else:
            return lambda value: value

    def bind_unwrapper(self, field, unwrapperfn):
        """ The opposite of bind_wrapper for export. """
        self.unwrapper[field] = unwrapperfn

    def get_unwrapper(self, field=None, ix=None):
        assert(field or (ix or ix >= 0))

        field = field or self.get_field(ix, including_children=True)

        if field and field in self.unwrapper:
            return self.unwrapper[field]
        else:
            return lambda value: value


def add_category_binds(fieldmap):
    listwrap = lambda val: ','.join(val) if val else ''
    listunwrap = lambda val: [v.strip() for v in val.split(',') if v.strip()]
    cattransform = lambda obj: IDirectoryCategorized(obj)

    for cat in CATEGORIES:
        fieldmap.bind_wrapper(cat, listwrap)
        fieldmap.bind_unwrapper(cat, listunwrap)
        fieldmap.bind_transformer(cat, cattransform)


def get_map(context):
    itemfields = (
        'title',
        'description',
        'cat1', 'cat2', 'cat3', 'cat4',
        'coordinates_json',
        'absolute_url'
    )

    itemmap = FieldMap()
    itemmap.root = True
    itemmap.keyfields = ('title',)
    itemmap.typename = 'seantis.dir.base.item'
    itemmap.add_fields(itemfields)
    itemmap.add_title('coordinates_json', _(u'Coordinates (JSON)'))
    itemmap.add_title('absolute_url', 'Url')
    itemmap.mark_readonly('absolute_url')

    # the acqusition context needs to be intact for absolute_url, which is
    # not the default
    itemmap.bind_transformer('absolute_url', lambda obj: obj)

    add_category_binds(itemmap)

    try:
        adapter = component.getAdapter(context, IFieldMapExtender)
        adapter.extend_import(itemmap)
    except component.ComponentLookupError:
        pass

    return itemmap
