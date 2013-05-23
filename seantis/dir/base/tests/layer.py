import transaction

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting

from Testing import ZopeTestCase as ztc
from OFS.Folder import Folder


class Fixture(PloneSandboxLayer):

    default_bases = (PLONE_FIXTURE, )

    class Session(dict):
        def set(self, key, value):
            self[key] = value

    def setUpZope(self, app, configurationContext):

        import seantis.dir.base
        self.loadZCML(package=seantis.dir.base)

        app.REQUEST['SESSION'] = self.Session()

        if not hasattr(app, 'temp_folder'):
            app._setObject('temp_folder', Folder('temp_folder'))
            transaction.commit()
            ztc.utils.setupCoreSessions(app)

    def setUpPloneSite(self, portal):
        from Products.GenericSetup import EXTENSION, profile_registry
        profile_registry.registerProfile(
            'basetype',
            'seantis.dir.base base type extension profile',
            'Provides a base type without special fields for testing',
            'profiles/basetype',
            'seantis.dir.base',
            EXTENSION
        )

        self.applyProfile(portal, 'seantis.dir.base:basetype')

FIXTURE = Fixture()
INTEGRATION_TESTING = IntegrationTesting(
    bases=(FIXTURE,),
    name='seantis.dir.base:Integration'
)
FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FIXTURE,),
    name='seantis.dir.base:Functional'
)
