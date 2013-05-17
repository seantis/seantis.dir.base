from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot

from seantis.dir.base.interfaces import IDirectoryItemBase


def get_site(context):
    if IPloneSiteRoot.providedBy(context):
        return context

    return get_site(context.aq_parent)


def add_behavior_to_item(context, module, interface):
    """ Helper function for 1.5 update, will move the item with the given
    interface in the given module to use the new IDirectoryCategorized
    behavior.

    Other modules need to add the IDirectoryCategoirzed behavior to the item
    type xml and define an upgrade step in which they call this funciton
    as follows:

    add_behavior_to_item(context, 'seantis.dir.example', IExampleDirectoryItem)

    """

    # adds a new behvaior
    setup = getToolByName(context, 'portal_setup')
    setup.runImportStepFromProfile(
        'profile-{}:default'.format(module), 'typeinfo'
    )

    # which is why there needs to be some reindexing
    catalog = getToolByName(context, 'portal_catalog')
    items = catalog(object_provides=interface.__identifier__)

    for item in items:
        item.getObject().reindexObject()


def upgrade_to_2012110201(context):
    """ Get rid of the implementedBy leftovers as outlined here:
    http://blog.fourdigits.nl/how-to-break-your-plone-site-with-implementedby
    """
    site = get_site(context)

    import transaction

    catalog = getToolByName(site, 'portal_catalog')
    path = '/'.join(site.getPhysicalPath())

    items = [i.getObject() for i in catalog(
        path={'query': path},
        object_provides=IDirectoryItemBase.__identifier__
    )]

    for item in items:
        try:
            del item.__implemented__
        except AttributeError:
            pass

    transaction.commit()


def upgrade_to_2013050701(context):
    """ Reapply jsregistry step """

    setup = getToolByName(context, 'portal_setup')
    setup.runImportStepFromProfile(
        'profile-seantis.dir.base:default', 'jsregistry'
    )


def upgrade_to_2013050801(context):
    """ Add seantis.dir.base browserlayer """

    setup = getToolByName(context, 'portal_setup')
    setup.runImportStepFromProfile(
        'profile-seantis.dir.base:default', 'browserlayer'
    )


def upgrade_to_2013050802(context):
    """ Use new cssregistry """

    setup = getToolByName(context, 'portal_setup')
    setup.runImportStepFromProfile(
        'profile-seantis.dir.base:default', 'cssregistry'
    )
