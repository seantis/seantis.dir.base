import random
import unittest2 as unittest

from plone.dexterity.utils import createContentInContainer
from plone.testing import z2
from plone.app import testing

from collective.betterbrowser import new_browser
from zope.component.hooks import getSite

from seantis.dir.base.tests.layer import INTEGRATION_TESTING
from seantis.dir.base.tests.layer import FUNCTIONAL_TESTING


class IntegrationTestCase(unittest.TestCase):

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.login_admin()  # integration tests don't for authorization yet

    def tearDown(self):
        self.logout()

    def login_admin(self):
        """ Login as site owner (does not work with testing.login)"""
        z2.login(self.layer['app']['acl_users'], 'admin')

    def login_testuser(self):
        """ Login as test-user (does not work with z2.login)"""
        testing.login(self.layer['portal'], 'test-user')

    def logout(self):
        testing.logout()

    def add_directory(self, title='Directory'):
        return createContentInContainer(
            getSite(), 'seantis.dir.base.directory', title=title
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


class FunctionalTestCase(IntegrationTestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def new_browser(self):
        return new_browser(self.layer)
