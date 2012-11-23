from StringIO import StringIO

from five import grok

import xlwt
import codecs
import os

from zope.i18n import translate

from seantis.dir.base.utils import get_interface_fields
from seantis.dir.base import catalog
from seantis.dir.base.fieldmap import get_map
from seantis.dir.base import core
from seantis.dir.base.directory import IDirectoryBase
from seantis.dir.base.directory import CATEGORIES


class XlsExportView(core.View):
    """Exports a directory as xml"""

    grok.context(IDirectoryBase)
    grok.require('cmf.ManagePortal')
    grok.name('export')

    def render(self, **kwargs):

        xlsfile = StringIO()
        filename = '%s.xls' % self.context.title
        filename = codecs.utf_8_encode('filename="%s"' % filename)[0]

        language = self.current_language
        as_template = 'template' in self.request.keys()

        try:
            export_xls(self.context, xlsfile, language, as_template)
            output = xlsfile.getvalue()
        finally:
            xlsfile.seek(0, os.SEEK_END)
            filesize = xlsfile.tell()
            xlsfile.close()

        RESPONSE = self.request.RESPONSE
        RESPONSE.setHeader("Content-disposition", filename)
        RESPONSE.setHeader("Content-Type", "application/xls")
        RESPONSE.setHeader("Content-Length", filesize)

        return output


def export_xls(directory, filehandle, language, as_template):
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(directory.title[:30])

    fieldmap = get_map(directory)

    write_title(fieldmap, ws, language, directory)

    if not as_template:
        items = catalog.children(directory, fieldmap.typename)
        write_objects(items, fieldmap, ws, 1)

    wb.save(filehandle)


def colstyle(fieldmap, col):
    if col in fieldmap.keyindexes(True):
        return xlwt.easyxf('pattern: fore_color light_yellow, pattern solid;')
    elif col in fieldmap.readonlyindexes(True):
        return xlwt.easyxf('pattern: fore_color gray25, pattern solid;')

    return xlwt.easyxf('')


def color_required(fieldmap, worksheet):
    style = xlwt.easyxf('pattern: fore_color light_yellow, pattern solid;')
    indexes = fieldmap.keyindexes(including_children=True)
    for ix in indexes:
        worksheet.col(ix).set_style(style)


def color_readonly(fieldmap, worksheet):
    style = xlwt.easyxf('pattern: fore_color gray25, pattern solid;')
    indexes = fieldmap.readonlyindexes(including_children=True)
    for ix in indexes:
        worksheet.cell(1, ix).set_style(style)


def write_title(fieldmap, worksheet, language, directory=None):
    fields = get_interface_fields(fieldmap.interface)
    basefields = get_interface_fields(fieldmap.baseinterface)

    indexes = fieldmap.indexes()
    minix = min(indexes)
    maxix = max(indexes)

    write = lambda col, value: worksheet.write(0, col, value, colstyle(fieldmap, col))

    for ix in xrange(minix, maxix + 1):
        name = fieldmap.indexmap[ix]

        typ = fieldmap.typename
        title = None

        if directory and '.item' in typ and name in CATEGORIES:
            title = getattr(directory, name)

        if not title:
            if name in fields:
                title = fields[name].title
            elif name in basefields:
                title = basefields[name].title
            elif name in fieldmap.titles:
                title = fieldmap.titles[name]
            else:
                title = name

        write(ix, translate(title, target_language=language))

    for childmap in fieldmap.children:
        write_title(childmap, worksheet, language)


def write_objects(objects, fieldmap, worksheet, row, writeparent=None):
    ws = worksheet

    startrow = row
    for obj in objects:

        write = lambda r: write_object(obj, fieldmap, worksheet, r, writeparent)

        for childmap in fieldmap.children:
            children = catalog.children(obj, childmap.typename)
            if children:
                row += write_objects(children, childmap, ws, row, write)
            else:
                write(row)
                row += 1

        if not fieldmap.children:
            write(row)
            row += 1

    return row - startrow


def write_object(obj, fieldmap, worksheet, row, writeparent=None):
    if writeparent:
        writeparent(row)

    for field, ix in fieldmap.fieldmap.items():
        write = lambda col, value: worksheet.write(row, col, value.encode('utf-8'), colstyle(fieldmap, col))

        if not hasattr(obj, field):
            continue

        value = getattr(obj, field)
        if value:
            wrapper = fieldmap.get_wrapper(field)
            attr = getattr(obj, field)

            # A field in the map may be a function in which case it is
            # called here and ignored on import
            if callable(attr):
                write(ix, wrapper(attr()))
            else:
                write(ix, wrapper(attr))
