from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base import catalog
from seantis.dir.base.catalog import category_filter
from seantis.dir.base.catalog import possible_values
from seantis.dir.base.catalog import grouped_possible_values

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

    def test_category_filter(self):

        directory = self.toy_data()

        found = category_filter(directory, dict(cat1='For Kids'))
        self.assertEqual(len(found), 4)

        found = category_filter(directory, dict(cat1='For Adults'))
        self.assertEqual(len(found), 3)

        found = category_filter(directory, dict(cat2='Toys'))
        self.assertEqual(len(found), 3)

        found = category_filter(directory, dict(cat3='Lego'))
        self.assertEqual(len(found), 3)

        found = category_filter(directory, dict(
                cat1='For Kids', 
                cat2='Cartoons',
                cat3='Mickey Mouse'
            ))
        self.assertEqual(len(found), 1)

        found = category_filter(directory, dict(cat1=''))
        self.assertEqual(len(found), 0)

        found = category_filter(directory, dict(cat2=''))
        self.assertEqual(len(found), 1)

        # The order of multiple items matters. To change this have a look at
        # the is_exact_item funciton in catalog.py

        found = category_filter(directory, dict(cat1=['For Kids', 'For Adults']))
        self.assertEqual(len(found), 1)
        found = category_filter(directory, dict(cat1=['For Adults', 'For Kids']))
        self.assertEqual(len(found), 0)

    def test_possible_values(self):

        directory = self.toy_data()

        possible = possible_values(directory, catalog.items(directory))
        self.assertEqual(directory.all_categories(), possible.keys())

        self.assertEqual(len(possible['cat1']), 9)
        self.assertEqual(len(possible['cat2']), 7) # Empty values are not counted 
        self.assertEqual(len(possible['cat3']), 7) # Empty values are not counted
        self.assertEqual(len(possible['cat4']), 0)

        found = category_filter(directory, dict(cat2='Toys'))
        possible = possible_values(directory, found)

        self.assertEqual(len(possible['cat1']), 4) # Lists in items are flattend
        self.assertEqual(len(possible['cat2']), 3) 
        self.assertEqual(len(possible['cat3']), 3)
        self.assertEqual(len(possible['cat4']), 0)

    def test_grouped_possible_values(self):

        directory = self.toy_data()

        possible = grouped_possible_values(directory, catalog.items(directory))

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

    def test_cache(self):
        directory = self.toy_data()

        items = catalog._items(directory)
        self.assertFalse(hasattr(items, '_cache_time'))
        self.assertEqual(len(items.values()), 8)

        self.logout()

        items = catalog._items(directory)
        self.assertTrue(hasattr(items, '_cache_time'))
        self.assertEqual(len(items.values()), 0)