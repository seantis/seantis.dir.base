from Acquisition import aq_parent
from zope.component import getAdapter

from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.base.catalog import is_exact_match


def get_catalog(directory):
    return getAdapter(directory, IDirectoryCatalog)


class TestCatalog(IntegrationTestCase):

    def toy_data(self):
        # It is not necessary to define any categories on the directory,
        # as they play no role in the filter
        directory = self.add_directory()

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

        return directory

    def test_query(self):
        directory = self.add_directory()
        catalog = get_catalog(directory)
        self.assertEqual(0, len(catalog.query()))

        self.add_item(directory)
        self.assertEqual(1, len(catalog.query()))

    def test_get_object(self):
        directory = self.add_directory()
        item = self.add_item(directory)
        item._p_changed = False
        catalog = get_catalog(directory)
        brains = catalog.query()
        result = catalog.get_object(brains[0])
        self.assertEqual(item, result)
        self.assertEqual(directory, aq_parent(item))
        self.assertFalse(result._p_changed)

    def test_items(self):
        directory = self.add_directory()
        catalog = get_catalog(directory)
        self.assertEqual([], catalog.items())

        item = self.add_item(directory)
        self.assertEqual([item], catalog.items())

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

    def test_possible_values(self):

        directory = self.toy_data()
        catalog = get_catalog(directory)

        possible = catalog.possible_values()
        self.assertEqual(directory.all_categories(), possible.keys())

        self.assertEqual(len(possible['cat1']), 9)
        self.assertEqual(len(possible['cat2']), 7)  # Empty values are not counted
        self.assertEqual(len(possible['cat3']), 7)  # Empty values are not counted
        self.assertEqual(len(possible['cat4']), 0)

        found = catalog.filter(dict(cat2='Toys'))
        possible = catalog.possible_values(found)

        self.assertEqual(len(possible['cat1']), 4)  # Lists in items are flattend
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
            [('far', 'faraway')]
        )

        items = self.add_item_bulk(self.add_directory(), values)
        term = dict(cat1='far')

        self.assertTrue(is_exact_match(items[0], term))
        self.assertFalse(is_exact_match(items[1], term))
        self.assertTrue(is_exact_match(items[2], term))
