from itertools import groupby
from StringIO import StringIO

import xlrd
from xlrd import XL_CELL_EMPTY
from xlrd import XL_CELL_TEXT
from xlrd import XL_CELL_NUMBER
from xlrd import XL_CELL_BLANK

import transaction

from five import grok
from plone.directives import form
from plone.namedfile.field import NamedFile
from z3c.form import field
from z3c.form.button import buttonAndHandler
from z3c.form.error import InvalidErrorViewSnippet
from zope.i18n import translate
from plone.dexterity.utils import createContentInContainer
from zope.interface import Invalid

from seantis.dir.base import _
from seantis.dir.base.utils import get_current_language
from seantis.dir.base.fieldmap import get_map
from seantis.dir.base.directory import IDirectoryBase
from seantis.dir.base.utils import get_interface_fields


class FatalImportError(Exception):
    """Import error caused by a programming error."""


class IImportDirectorySchema(form.Schema):
    """ Define fields used on the form """
    xls_file = NamedFile(title=_(u"XLS file"), description=u'{xlshelp}')

IMPORTHELP = _(u"Import directory items using xls. The xls is expected to have the format defined in the template which you can <a href='#xlstemplate'>download here</a>")


class Import(form.Form):
    label = _(u'Import directory items')
    fields = field.Fields(IImportDirectorySchema)

    grok.context(IDirectoryBase)
    grok.require('cmf.AddPortalContent')
    grok.name('import')

    ignoreContext = True

    def abort_action(self, action, messages):
        """ Aborts the given actiona and adds the list of messages as
        error-widgets to the form.

        """
        form = action.form
        formcontent = form.getContent()
        request = action.request

        for msg in messages:
            args = (Invalid(msg), request, None, None, form, formcontent)
            err = InvalidErrorViewSnippet(*args)
            err.update()
            form.widgets.errors += (err, )

        form.status = form.formErrorsMessage

        transaction.abort()

    def add_help(self, result):
        """ Adds an url to the description of the xls import file. Probably
        not the plone way of doing it, but I have yet to find a working
        alternative.

        """
        importlink = self.context.absolute_url() + '/export?template=1'
        language = get_current_language(self.context, self.request)
        text = translate(IMPORTHELP, target_language=language)
        help = text.replace('#xlstemplate', importlink)
        return result.replace('{xlshelp}', help)

    def render(self, *args, **kwargs):
        """ Overrides the render function to meddle with the html. """
        result = form.Form.render(self, *args, **kwargs)
        return self.add_help(result)

    @buttonAndHandler(_(u'Import'), name='import')
    def importXLS(self, action):
        """ Create and handle form button."""

        # Extract form field values and errors from HTTP request
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        try:
            io = StringIO(data["xls_file"].data)
            workbook = xlrd.open_workbook(file_contents=io.read())
        except (KeyError, TypeError, xlrd.XLRDError):
            self.abort_action(action, (_(u'Invalid XLS file'),))
            return

        errors = []
        report_error = lambda err: errors.append(err)

        records = len(import_xls(self.context, workbook, report_error))

        if errors:
            self.abort_action(action, errors)
        else:
            self.status = _(u'Imported ${number} items', mapping={u'number': records})


def import_xls(directory, workbook, error=lambda e: None):
    # Get the fieldmap defining hierarchies and the cell/field mapping
    fieldmap = get_map(directory)

    # Load the sorted values from the workbook
    try:
        values = get_values(workbook, fieldmap)
    except IndexError:
        error(_(u'Invalid XLS file'))
        return dict()

    # Fill the database
    if values:
        return generate_objects(directory, fieldmap, values, error)
    else:
        return dict()


def generate_objects(folder, fieldmap, values, error):
    """Recursively creates the objects and its children."""

    created = dict()

    # Group the values according to the keys defined on the fieldmap
    keyindexes = fieldmap.keyindexes(False)
    groupfn = lambda row: ''.join([row[i].encode('utf-8') for i in keyindexes])
    for key, group in groupby(values, key=groupfn):
        # Missing keys are tolerated (not existing record), unless it's a root
        # fieldmap (first record in line), in which case it must either be
        # in the xls completely or not at all.. no empty rows!
        if not key and not fieldmap.root:
            continue

        groupvalues = [val for val in group]

        # For each group create the group (think folder)
        obj = generate_object(folder, fieldmap, key, groupvalues[0], error)

        if not obj:
            continue
        else:
            created[obj] = []

        # If there are children but the newly created parent isn't folderish
        # it is best to fail hard as there is a programming error
        if not obj.isPrincipiaFolderish and fieldmap.children:
            raise FatalImportError

        # Go through the children and add them to the folder
        for child in fieldmap.children:
            created[obj].append(generate_objects(obj, child, groupvalues, error))

    return created


def generate_object(folder, fieldmap, key, objvalues, error):
    """Creates an object and adds it to the folder."""

    # The key does not exist, create a new object
    attributes = dict()
    for attr, ix in fieldmap.fieldmap.items():
        if not attr in fieldmap.readonly:
            attributes[attr] = objvalues[ix]

    # Unmapped fields are filled with defaults
    add_defaults(attributes, fieldmap)

    # Only really works with dexterity types.. might change that if needed
    obj = createContentInContainer(folder, fieldmap.typename, **attributes)

    if hasattr(fieldmap, 'on_object_add'):
        fieldmap.on_object_add(obj, objvalues)

    # If the verification doesn't check it will grigger a rollback later
    return verify(obj, fieldmap, error) and obj or None


def verify(obj, fieldmap, error):
    msgs = []

    if not has_requirements(obj, fieldmap):
        msgs.append(_(u'Not all required fields have a value'))
    try:
        fieldmap.interface.validateInvariants(obj)
    except Exception, e:
        msgs.append(unicode(e.message))

    map(error, msgs)
    return len(msgs) == 0


def has_requirements(obj, fieldmap):
    for field in get_required_fields(obj, fieldmap):
        if not hasattr(obj, field):
            return False
        if not getattr(obj, field):
            return False

    return True


def get_required_fields(obj, fieldmap):
    fields = get_interface_fields(fieldmap.interface)
    return [k for k, v in fields.items() if v.required]


def add_defaults(attributes, fieldmap):
    mapfields = fieldmap.fieldmap.keys()

    # The whole reason to add these defaults is that by manually creating
    # these values they are not applied (and without defaults some objects
    # end up with missing attributes if the respective fields were left out).
    # Needs some more investigating...

    ifields = get_interface_fields(fieldmap.interface)
    fields = set(ifields.keys()) - set(mapfields)

    for field in fields:
        default = ifields[field].default
        attributes[field] = default


def cell2value(cell):
    """ Converts cells to string at this point. Could be extended by
    introducing module/value specific adaptors, but this is not needed atm.

    """
    if cell.ctype == XL_CELL_TEXT:
        return cell.value.rstrip()
    elif cell.ctype in (XL_CELL_BLANK, XL_CELL_EMPTY):
        return u''
    elif cell.ctype == XL_CELL_NUMBER:
        return u'%0.f' % cell.value

    raise NotImplementedError


def get_values(workbook, fieldmap):
    """ Returns the values from the workbook orderd according to the fieldmaps
    keyindexes.

    """
    ws = workbook.sheet_by_index(0)

    minix, maxix = fieldmap.minindex(), fieldmap.maxindex()
    values = []

    startrow = 1
    for row in xrange(startrow, ws.nrows):
        cell = lambda c: ws.cell(row, c)

        if not cell(minix).value:
            break

        cells = []

        for i in range(minix, maxix + 1):
            value = cell2value(cell(i))

            # Some values need to be wrapped to be useful
            unwrapped = fieldmap.get_unwrapper(ix=i)(value)
            cells.append(unwrapped)

        values.append(cells)

    # Sort according to all keys and subkeys to allow grouping later
    keyindexes = fieldmap.keyindexes(True)
    sortfn = lambda row: ''.join([row[i].encode('utf-8') for i in keyindexes])
    return sorted(values, key=sortfn)
