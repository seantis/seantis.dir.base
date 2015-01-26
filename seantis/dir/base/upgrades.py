from StringIO import StringIO

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot

from seantis.dir.base.interfaces import IDirectoryItemBase

from plone.namedfile.file import NamedImage, NamedFile


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


def reset_images(context, interfaces):
    # for backwards compatibility
    reset_images_and_attachments(context, interfaces, ['image', 'attachment'])


def reset_images_and_attachments(context, interfaces, fields):
    """ Plone 4.3 uses plone.namedfile 2.0.1 which fails on all images and
    files created by the old version. This function reapplies all those
    files, fixing the problem.

    """

    catalog = getToolByName(context, 'portal_catalog')

    def brains():
        for interface in interfaces:
            for result in catalog(object_provides=interface.__identifier__):
                yield result

    objects = [i.getObject() for i in brains()]

    for obj in objects:
        for field in fields:
            if not hasattr(obj, field):
                continue

            value = getattr(obj, field)

            if value is None:
                continue

            if isinstance(value, NamedImage):
                setattr(obj, field, NamedImage(
                    StringIO(value.data),
                    value.contentType)
                )
            elif isinstance(value, NamedFile):
                setattr(obj, field, NamedFile(
                    StringIO(value.data),
                    value.contentType,
                    value.filename)
                )
            else:
                continue


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


def upgrade_to_2014040301(context):
    """ Update css """
    getToolByName(context, 'portal_css').cookResources()


def upgrade_to_2015012601(context):
    """ Update type registry """

    setup = getToolByName(context, 'portal_setup')
    setup.runImportStepFromProfile(
        'profile-seantis.dir.base:default', 'typeinfo'
    )
