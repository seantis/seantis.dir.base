# -*- coding: utf-8 -*-

from seantis.dir.base.tests import IntegrationTestCase
from seantis.dir.base.interfaces import IDirectory
from seantis.dir.base.descriptions import (
    parse_category_description, valid_category_description
)


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

    def test_descriptions(self):
        description = u"""
            >> HTTP >> Hypertext Protocol @@ http://www.w3.org/Protocols/
            >> IMHO >> IMHO is a shortcut meaning the following:
                       in my humble opinion
            >> body >> Englisch für 'Körper'
            >> email-address >>  Mail  Address in the following form: user@host
        """

        parsed = parse_category_description(description)

        self.assertEqual(
            sorted(parsed.keys()), ['HTTP', 'IMHO', 'body', 'email-address']
        )

        self.assertEqual(parsed['HTTP'].description, 'Hypertext Protocol')
        self.assertEqual(parsed['HTTP'].url, 'http://www.w3.org/Protocols/')

        self.assertEqual(
            parsed['IMHO'].description,
            'IMHO is a shortcut meaning the following: in my humble opinion'
        )
        self.assertEqual(parsed['IMHO'].url, None)

        self.assertEqual(
            parsed['body'].description, u"Englisch für 'Körper'"
        )

        self.assertEqual(parsed['body'].url, None)

        self.assertEqual(
            parsed['email-address'].description,
            'Mail Address in the following form: user@host'
        )

        self.assertTrue(valid_category_description(description))

        description = u"""
            HTTP > Hypertext Protocol @@ http://www.w3.org/Protocols/
        """

        self.assertFalse(valid_category_description(description))

        description = u'>> Test >> Asdf'
        self.assertTrue(valid_category_description(description))
