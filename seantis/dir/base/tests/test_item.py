from Acquisition import aq_base

from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base.interfaces import (
    IDirectoryItem,
    IDirectoryCategorized
)


class TestDirectoryItem(IntegrationTestCase):

    def test_add(self):
        directory = self.add_directory()
        item = self.add_item(directory, 'Bloody Sunshine Daycare')
        self.assertTrue(IDirectoryItem.providedBy(item))
        self.assertEqual(item.id, 'bloody-sunshine-daycare')

    def test_categories(self):
        directory = self.add_directory()
        directory.cat1 = 'One'
        directory.cat2 = 'Two'
        directory.cat3 = 'Three'

        item = self.add_item(directory)

        # only present after setting them on the behavior
        self.assertFalse(hasattr(aq_base(item), 'cat1'))
        self.assertFalse(hasattr(aq_base(item), 'cat2'))
        self.assertFalse(hasattr(aq_base(item), 'cat3'))
        self.assertFalse(hasattr(aq_base(item), 'cat4'))

        categorized = IDirectoryCategorized(item)
        self.assertTrue(hasattr(categorized, 'cat1'))
        self.assertTrue(hasattr(categorized, 'cat2'))
        self.assertTrue(hasattr(categorized, 'cat3'))
        self.assertTrue(hasattr(categorized, 'cat4'))

        categorized.cat1 = '1'
        categorized.cat2 = '2'
        categorized.cat3 = '3'
        categorized.cat4 = '4'  # Will be ignored

        self.assertTrue(hasattr(aq_base(item), 'cat1'))
        self.assertTrue(hasattr(aq_base(item), 'cat2'))
        self.assertTrue(hasattr(aq_base(item), 'cat3'))
        self.assertTrue(hasattr(aq_base(item), 'cat4'))

        categories = categorized.categories()
        self.assertEqual(len(categories), 3)

        item_used = [c[0] for c in categories]
        dir_used = directory.used_categories()
        self.assertEqual(item_used, dir_used)

        item_labels = [c[1] for c in categories]
        dir_labels = directory.labels().values()
        self.assertEqual(item_labels, dir_labels)

        values = [c[2] for c in categories]
        self.assertEqual(values, ['1', '2', '3'])

        # Set the category to contain multiple keywords and use only
        # one category
        categorized.cat1 = ['tag one', 'tag two']
        directory.cat2 = None
        directory.cat3 = None

        categories = categorized.categories()

        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0][2], ['tag one', 'tag two'])

        # Set more categories and see if the keywords function correctly
        # returns all keywords flattened, even if invisible

        categorized.cat1 = ['Ready', 'Or']
        categorized.cat2 = 'Not'
        categorized.cat3 = ['Here', 'I']
        categorized.cat4 = 'Come'

        keywords = categorized.keywords()
        self.assertEqual(keywords, ['Ready', 'Or', 'Not', 'Here', 'I', 'Come'])
