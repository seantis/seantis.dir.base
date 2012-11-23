import random

from seantis.dir.base.tests.layer import Layer
from Products.PloneTestCase.ptc import PloneTestCase


class IntegrationTestCase(PloneTestCase):
    layer = Layer

    def add_directory(self, name='Directory'):
        self.folder.invokeFactory('seantis.dir.base.directory', name)
        return self.folder[name]

    def add_item(self, directory, name='DirectoryItem'):
        directory.invokeFactory('seantis.dir.base.item', name)
        return directory[name]

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
