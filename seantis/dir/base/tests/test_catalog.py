# -*- coding: utf-8 -*-

from zope.component import getAdapter

from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.base.catalog import is_exact_match


def get_catalog(directory):
    return getAdapter(directory, IDirectoryCatalog)


class TestCatalog(IntegrationTestCase):

    def toy_data(self):
        directory = self.add_directory()
        directory.cat1 = 'Target-Group'
        directory.cat2 = 'Type'
        directory.cat3 = 'Name'
        directory.reindexObject()

        values = (
            ['For Kids', 'Cartoons', 'Mickey Mouse'],
            ['For Kids', 'Cartoons', 'Donald Duck'],
            ['For Kids', 'Toys', 'Lego'],
            ['For Adults', 'Toys', 'Lego'],
            [('For Kids', 'For Adults'), 'Toys', 'Lego Robotics'],
            ['For Adults', 'Cartoons', 'The Walking Dead'],
            ['Cartoons', 'For Kids', 'Unstructured Data'],
            ['Nothing', '', '']
        )

        items = self.add_item_bulk(directory, values)
        self.assertEqual(len(items), len(values))

        #self.assertEqual(sorted(catalog.items(directory)), sorted(items))

        # Add the same items to another dictionary to ensure that only
        # one directory is filtered at a time
        other_dir = self.add_directory('Some other directory')
        self.add_item_bulk(other_dir, values)

        catalog = get_catalog(directory)
        for item in catalog.query():
            item.getObject().reindexObject()

        return directory

    def test_sorting(self):
        directory = self.add_directory()
        self.add_item(directory, title='last').title = u'ööö'
        self.add_item(directory, title='second').title = u'äää'
        self.add_item(directory, title='third').title = u'bbb'
        self.add_item(directory, title='first').title = u'aaa'

        catalog = get_catalog(directory)

        for i in catalog.items():
            i.getObject().reindexObject()

        items = catalog.items()

        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].getObject().title, u'aaa')
        self.assertEqual(items[1].getObject().title, u'äää')
        self.assertEqual(items[2].getObject().title, u'bbb')
        self.assertEqual(items[3].getObject().title, u'ööö')

    def test_query(self):
        directory = self.add_directory()
        catalog = get_catalog(directory)
        self.assertEqual(0, len(catalog.query()))

        self.add_item(directory)
        self.assertEqual(1, len(catalog.query()))

    def test_items(self):
        directory = self.add_directory()
        catalog = get_catalog(directory)
        self.assertEqual([], catalog.items())

        item = self.add_item(directory)
        self.assertEqual([item], [i.getObject() for i in catalog.items()])

    def test_filter(self):

        directory = self.toy_data()
        catalog = get_catalog(directory)

        found = catalog.filter(dict(cat1='For Kids'))
        self.assertEqual(len(found), 4)

        found = catalog.filter(dict(cat1='For Adults'))
        self.assertEqual(len(found), 3)

        found = catalog.filter(dict(cat2='Toys'))
        self.assertEqual(len(found), 3)

        found = catalog.filter(dict(cat3='Lego'))
        self.assertEqual(len(found), 2)

        found = catalog.filter(dict(
            cat1='For Kids',
            cat2='Cartoons',
            cat3='Mickey Mouse'
        ))
        self.assertEqual(len(found), 1)

        found = catalog.filter(dict(cat1=''))
        self.assertEqual(len(found), 0)

        found = catalog.filter(dict(cat2=''))
        self.assertEqual(len(found), 1)

        found = catalog.filter(dict(cat1=['For Kids', 'For Adults']))
        self.assertEqual(len(found), 1)
        found = catalog.filter(dict(cat1=['For Adults', 'For Kids']))
        self.assertEqual(len(found), 1)

    def test_search(self):

        directory = self.toy_data()
        catalog = get_catalog(directory)

        items = [i.getObject() for i in catalog.items()]

        items[0].description = 'Unique'
        items[0].reindexObject()

        found = catalog.search('Unique')
        self.assertEqual(len(found), 1)

        items[1].description = 'Unique (Not really)'
        items[1].reindexObject()

        found = catalog.search('Unique')
        self.assertEqual(len(found), 2)

        found = catalog.search('Unique (Not really)')
        self.assertEqual(len(found), 1)

    def test_possible_values(self):

        directory = self.toy_data()
        catalog = get_catalog(directory)

        possible = catalog.possible_values()
        self.assertEqual(directory.all_categories(), possible.keys())

        self.assertEqual(len(possible['cat1']), 9)
        self.assertEqual(len(possible['cat2']), 7)  # Empty values not counted
        self.assertEqual(len(possible['cat3']), 7)  # Empty values not counted
        self.assertEqual(len(possible['cat4']), 0)

        found = catalog.filter(dict(cat2='Toys'))
        possible = catalog.possible_values(found)

        self.assertEqual(len(possible['cat1']), 4)  # Item lists are flattend
        self.assertEqual(len(possible['cat2']), 3)
        self.assertEqual(len(possible['cat3']), 3)
        self.assertEqual(len(possible['cat4']), 0)

        possible = catalog.possible_values(found, categories=("cat1", "cat2"))

        self.assertTrue('cat1' in possible)
        self.assertTrue('cat2' in possible)
        self.assertFalse('cat3' in possible)
        self.assertFalse('cat4' in possible)

    def test_grouped_possible_values(self):

        directory = self.toy_data()
        catalog = get_catalog(directory)

        possible = catalog.grouped_possible_values()

        self.assertEqual(len(possible['cat1'].keys()), 4)
        self.assertEqual(possible['cat1']['For Kids'], 4)
        self.assertEqual(possible['cat1']['For Adults'], 3)
        self.assertEqual(possible['cat1']['Cartoons'], 1)
        self.assertEqual(possible['cat1']['Nothing'], 1)
        self.assertEqual(len(possible['cat2'].keys()), 3)
        self.assertEqual(possible['cat2']['Cartoons'], 3)
        self.assertEqual(possible['cat2']['For Kids'], 1)
        self.assertEqual(possible['cat2']['Toys'], 3)
        self.assertEqual(len(possible['cat3'].keys()), 6)
        self.assertEqual(possible['cat3']['Mickey Mouse'], 1)
        self.assertEqual(possible['cat3']['Lego'], 2)
        self.assertEqual(len(possible['cat4'].keys()), 0)

    def test_exact_match(self):
        values = (
            ['far'],
            ['faraway'],
            [('far', 'faraway')],
            ['far ']
        )

        directory = self.add_directory()
        directory.cat1 = 'Test'
        directory.reindexObject()

        self.add_item_bulk(directory, values)

        catalog = get_catalog(directory)
        items = catalog.query()

        for item in items:
            item.getObject().reindexObject()

        items = catalog.query()

        term = dict(cat1='far')

        self.assertTrue(is_exact_match(items[0], term))
        self.assertFalse(is_exact_match(items[1], term))
        self.assertTrue(is_exact_match(items[2], term))
        self.assertTrue(is_exact_match(items[3], term))
