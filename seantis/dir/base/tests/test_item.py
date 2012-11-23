from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base.interfaces import IDirectoryItem


class TestDirectoryItem(IntegrationTestCase):

    def test_add(self):
        directory = self.add_directory()
        item = self.add_item(directory, 'Bloody Sunshine Daycare')
        self.assertTrue(IDirectoryItem.providedBy(item))
        self.assertEqual(item.id, 'Bloody Sunshine Daycare')

    def test_categories(self):
        directory = self.add_directory()
        directory.cat1 = 'One'
        directory.cat2 = 'Two'
        directory.cat3 = 'Three'

        item = self.add_item(directory)

        item.cat1 = '1'
        item.cat2 = '2'
        item.cat3 = '3'
        item.cat4 = '4'  # Will be ignored

        categories = item.categories()
        self.assertEqual(len(categories), 3)

        item_used = [c[0] for c in categories]
        dir_used = directory.used_categories()
        self.assertEqual(item_used, dir_used)

        item_labels = [c[1] for c in categories]
        dir_labels = directory.labels().values()
        self.assertEqual(item_labels, dir_labels)

        values = [c[2] for c in categories]
        self.assertEqual(values, ['1', '2', '3'])

        # Set the category to contain multiple keywords and use only one category
        item.cat1 = ['tag one', 'tag two']
        directory.cat2 = None
        directory.cat3 = None

        categories = item.categories()

        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0][2], ['tag one', 'tag two'])

        # Set more categories and see if the keywords function correctly
        # returns all keywords flattened, even if invisible

        item.cat1 = ['Ready', 'Or']
        item.cat2 = 'Not'
        item.cat3 = ['Here', 'I']
        item.cat4 = 'Come'

        keywords = item.keywords()
        self.assertEqual(keywords, ['Ready', 'Or', 'Not', 'Here', 'I', 'Come'])
