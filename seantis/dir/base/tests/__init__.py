import random

from plone.dexterity.utils import createContentInContainer
from Products.PloneTestCase.ptc import PloneTestCase
from seantis.dir.base.tests.layer import Layer


class IntegrationTestCase(PloneTestCase):
    layer = Layer

    def add_directory(self, title='Directory'):
        return createContentInContainer(
            self.folder, 'seantis.dir.base.directory', title=title
        )

    def add_item(self, directory, title='Directory Item'):
        return createContentInContainer(
            directory, 'seantis.dir.base.item', title=title
        )

    def add_item_bulk(self, directory, values):
        items = []
        ids = random.sample(xrange(10000), len(values))

        for i, val in enumerate(values):
            name = '%i' % ids[i]
            item = self.add_item(directory, name)
            for i in xrange(1, len(val) + 1):
                setattr(item, 'cat%i' % i, val[i - 1])
            items.append(item)

        return items
