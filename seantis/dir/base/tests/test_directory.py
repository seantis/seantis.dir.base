# -*- coding: utf-8 -*-

from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base.interfaces import IDirectory


class TestDirectory(IntegrationTestCase):

    def test_add(self):
        directory = self.add_directory('Daycare Centers')
        self.assertTrue(IDirectory.providedBy(directory))
        self.assertEqual(directory.id, 'daycare-centers')

    def test_categories(self):
        directory = self.add_directory()
        directory.cat1 = 'One'
        directory.cat3 = 'Three'

        categories = directory.all_categories()
        self.assertEqual(categories, ['cat1', 'cat2', 'cat3', 'cat4'])

        used = directory.used_categories()
        self.assertEqual(used, ['cat1', 'cat3'])

        unused = directory.unused_categories()
        self.assertEqual(unused, ['cat2', 'cat4'])

        labels = directory.labels()
        self.assertEqual(labels.keys(), used)
        self.assertEqual(labels['cat1'], 'One')
        self.assertEqual(labels['cat3'], 'Three')
