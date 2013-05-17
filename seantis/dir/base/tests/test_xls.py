from StringIO import StringIO

from xlwt import Workbook
from xlrd import open_workbook

from seantis.dir.base.interfaces import IDirectoryCategorized
from seantis.dir.base.xlsimport import import_xls
from seantis.dir.base.xlsexport import export_xls
from seantis.dir.base.tests import IntegrationTestCase


class TempXLS(object):

    def __init__(self):
        self.file = StringIO()

    def save(self, workbook):
        workbook.save(self.file)

    def load(self):
        return open_workbook(file_contents=self.file.getvalue())


class TestXLS(IntegrationTestCase):

    def write_row(self, sheet, row, values):
        for ix, val in enumerate(values):
            sheet.write(row, ix, val)

    def test_template(self):
        xls = TempXLS()

        title = u'\xc3\xb6\xc3\xa4$' * 10

        directory = self.add_directory()
        directory.title = title
        directory.cat1 = u'One'
        directory.cat2 = u'Two'
        directory.cat3 = u'Three'
        directory.cat4 = u'Four'

        self.add_item(directory)

        export_xls(directory, xls.file, 'de', True)

        wb = xls.load()
        ws = wb.sheet_by_index(0)

        self.assertEqual(ws.nrows, 1)
        self.assertTrue(ws.name in title)

        self.assertEqual(ws.cell(0, 2).value, u'One')
        self.assertEqual(ws.cell(0, 3).value, u'Two')
        self.assertEqual(ws.cell(0, 4).value, u'Three')
        self.assertEqual(ws.cell(0, 5).value, u'Four')

    def test_export(self):
        xls = TempXLS()

        directory = self.add_directory()
        directory.title = u'test'
        directory.cat1 = u'Testkategorie 1'
        directory.cat2 = u'Testkategorie 2'

        item = self.add_item(directory, 'item1')
        item.description = u'description1'

        categorized = IDirectoryCategorized(item)
        categorized.cat1 = [u'Eins']
        categorized.cat2 = [u'Zwei']

        item = self.add_item(directory, 'item2')
        categorized = IDirectoryCategorized(item)
        categorized.cat1 = [u'One']
        categorized.cat2 = [u'Two']

        export_xls(directory, xls.file, 'de', False)

        wb = xls.load()
        ws = wb.sheet_by_index(0)

        self.assertEqual(ws.nrows, 3)

        self.assertEqual(ws.cell(1, 0).value, u'item1')
        self.assertEqual(ws.cell(1, 1).value, u'description1')
        self.assertEqual(ws.cell(1, 2).value, u'Eins')
        self.assertEqual(ws.cell(1, 3).value, u'Zwei')

        self.assertEqual(ws.cell(2, 0).value, u'item2')
        self.assertEqual(ws.cell(2, 1).value, u'')
        self.assertEqual(ws.cell(2, 2).value, u'One')
        self.assertEqual(ws.cell(2, 3).value, u'Two')

    def test_import(self):
        wb = Workbook()
        sheet = wb.add_sheet('test')

        # These should end up grouped into one
        self.write_row(
            sheet,
            1,
            ['First', 'Description', 'Cat1', 'Cat2', 'Cat3', 'Cat4', '', 'Url']
        )
        self.write_row(
            sheet,
            2,
            ['First', 'Description', 'Cat1', 'Cat2', 'Cat3', 'Cat4', '', 'Url']
        )

        # Another one
        self.write_row(
            sheet,
            3,
            [
                'Second', 'Description', 'Cat1', 'Cat2', 'Cat3', 'Cat4',
                '', 'Url'
            ]
        )

        directory = self.add_directory()
        errors = []

        # xlwt workbooks behave differently than xlrd workbooks, so it is
        # necessary to write the workbook and reopen it using TempXLS
        xls = TempXLS()
        xls.save(wb)

        error = lambda err: errors.append(err)
        results = import_xls(directory, xls.load(), error=error)

        self.assertEqual(len(results), 2)
        self.assertEqual(len(errors), 0)

        for result in results.keys():
            self.assertTrue(result.title in (u'First', u'Second'))
            self.assertEqual(result.description, u'Description')
            self.assertEqual(result.cat1, [u'Cat1'])
            self.assertEqual(result.cat2, [u'Cat2'])
            self.assertEqual(result.cat3, [u'Cat3'])
            self.assertEqual(result.cat4, [u'Cat4'])
            self.assertTrue(callable(result.absolute_url))

    def test_invalid_import(self):
        wb = Workbook()
        sheet = wb.add_sheet('test')

        self.write_row(
            sheet,
            1,
            [' ', ' ', ' ', ' ', ' ', ' ']
        )
        self.write_row(
            sheet,
            2,
            [' ', ' ', ' ', ' ', ' ', ' ']
        )

        xls = TempXLS()

        xls.save(wb)

        directory = self.add_directory()

        errors = []
        error = lambda err: errors.append(err)

        results = import_xls(directory, xls.load(), error=error)

        self.assertEqual(len(errors), 1)
        self.assertEqual(len(results), 0)
