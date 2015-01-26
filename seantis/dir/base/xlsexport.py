from collections import namedtuple
from StringIO import StringIO

from five import grok

import xlwt
import codecs
import os

from zope.i18n import translate
from zope.component import subscribers

from seantis.dir.base import _
from seantis.dir.base import utils
from seantis.dir.base.utils import (
    get_interface_fields,
    cached_property
)
from seantis.dir.base import catalog
from seantis.dir.base.fieldmap import get_map
from seantis.dir.base import core
from seantis.dir.base.directory import IDirectoryBase
from seantis.dir.base.directory import CATEGORIES
from seantis.dir.base.interfaces import IExportProvider


class XlsExportsView(grok.View):
    """Shows a list of possible exports."""

    grok.context(IDirectoryBase)
    grok.require('cmf.ModifyPortalContent')
    grok.name('exports')

    _template = grok.PageTemplateFile('templates/exports.pt')

    def title(self):
        return ' '.join((_(u'Exports for'), self.context.title))

    @cached_property
    def providers(self):
        providers = []
        for provider in subscribers([self.context], IExportProvider):
            if provider.layer:
                if not provider.layer.providedBy(self.request):
                    continue

            providers.append(provider)

        return providers

    def exports(self):

        ExportDefinition = namedtuple(
            'ExportDefinition', ('url', 'title', 'description')
        )

        exports = []
        for provider in self.providers:

            url = provider.url or ''.join(
                (self.url(), '?export-id=', provider.id)
            )

            exports.append(
                ExportDefinition(
                    url=url,
                    title=utils.translate(
                        self.context, self.request, provider.title
                    ),
                    description=utils.translate(
                        self.context, self.request, provider.description
                    )
                )
            )

        return exports

    def render(self):
        id = self.request.get('export-id', None)

        for provider in self.providers:
            if provider.id == id:
                return provider.export(self.request)

        return self._template.render(self)


class DefaultExport(grok.Subscription):

    grok.context(IDirectoryBase)
    grok.provides(IExportProvider)

    id = 'default'
    title = _(u'Default Export')
    layer = None

    description = _(
        u'The default export contains the basic fields of the '
        u'directory, without additional fields defined by client specific '
        u'fields. It is the only export which may be also be imported.'
    )

    @property
    def url(self):
        return self.context.absolute_url() + '/export'

    def export(self, request):
        pass


def xls_response(request, filename, filehandle):
    filename = codecs.utf_8_encode('filename="%s"' % filename)[0]
    request.RESPONSE.setHeader('Content-disposition', filename)
    request.RESPONSE.setHeader('Content-Type', 'application/xls')

    response = filehandle.getvalue()

    filehandle.seek(0, os.SEEK_END)
    filesize = filehandle.tell()
    filehandle.close()

    request.RESPONSE.setHeader('Content-Length', filesize)

    return response


class XlsExportView(core.View):
    """Exports a directory as xml"""

    grok.context(IDirectoryBase)
    grok.require('cmf.ModifyPortalContent')
    grok.name('export')

    def render(self, **kwargs):

        xlsfile = StringIO()

        export_xls(
            directory=self.context,
            filehandle=xlsfile,
            language=self.current_language,
            as_template='template' in self.request.keys()
        )

        return xls_response(
            self.request, '%s.xls' % self.context.title, xlsfile
        )


def export_xls(directory, filehandle, language, as_template, fieldmap=None):
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(directory.title[:30])

    fieldmap = fieldmap or get_map(directory)

    write_title(fieldmap, ws, language, directory)

    if not as_template:
        items = catalog.children(directory, fieldmap.typename)
        write_objects(items, fieldmap, ws, 1)

    wb.save(filehandle)


UNSTYLED = xlwt.easyxf('')
REQUIRED = xlwt.easyxf('pattern: fore_color light_yellow, pattern solid;')
READONLY = xlwt.easyxf('pattern: fore_color gray25, pattern solid;')


def colstyle(fieldmap, col):
    if col in fieldmap.keyindexes(True):
        return REQUIRED
    elif col in fieldmap.readonlyindexes(True):
        return READONLY

    return UNSTYLED


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

    write = lambda col, value: worksheet.write(
        0, col, value, colstyle(fieldmap, col)
    )

    for ix in xrange(minix, maxix + 1):
        field = fieldmap.indexmap[ix]
        typ = fieldmap.typename

        if field in fieldmap.titles:
            title = fieldmap.titles[field]
        elif directory and '.item' in typ and field in CATEGORIES:
            title = getattr(directory, field)
        elif field in fields:
            title = fields[field].title
        elif field in basefields:
            title = basefields[field].title
        else:
            title = field

        write(ix, translate(title, target_language=language))

    for childmap in fieldmap.children:
        write_title(childmap, worksheet, language)


def write_objects(objects, fieldmap, worksheet, row, writeparent=None):
    ws = worksheet

    startrow = row
    for obj in objects:

        write = lambda r: write_object(
            obj, fieldmap, worksheet, r, writeparent
        )

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
        write = lambda col, value: worksheet.write(
            row, col,
            value and value.encode('utf-8') or '',
            colstyle(fieldmap, col)
        )

        transformer = fieldmap.get_transformer(field)

        attr = getattr(transformer(obj), field)
        wrapper = fieldmap.get_wrapper(field)

        # A field in the map may be a function in which case it is
        # called here and ignored on import
        if callable(attr):
            write(ix, wrapper(attr()))
        else:
            write(ix, wrapper(attr))
