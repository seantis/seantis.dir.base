from Products.PloneTestCase import ptc
import collective.testcaselayer.ptc

ptc.setupPloneSite()


class IntegrationTestLayer(collective.testcaselayer.ptc.BasePTCLayer):

    def afterSetUp(self):
        from Products.GenericSetup import EXTENSION, profile_registry
        profile_registry.registerProfile(
            'basetype',
            'seantis.dir.base base type extension profile',
            'Provides a base type without special fields for testing',
            'profiles/basetype',
            'seantis.dir.base',
            EXTENSION
        )

        self.addProfile('seantis.dir.base:basetype')

Layer = IntegrationTestLayer([collective.testcaselayer.ptc.ptc_layer])
