from zope.component import getMultiAdapter, getUtility
from zope.component.interfaces import ComponentLookupError

from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.constants import USER_CATEGORY
from plone.portlets.constants import GROUP_CATEGORY
from plone.portlets.constants import CONTENT_TYPE_CATEGORY
from plone.portlets.constants import CONTEXT_CATEGORY


def block_portlets_on_creation(context, event):
    """ Block the portlets when an item is created. They may be added later. """

    for manager_name in ('plone.leftcolumn', 'plone.rightcolumn'):
        manager = getUtility(IPortletManager, name=manager_name)

        try:
            assignable = getMultiAdapter(
                (context, manager,), ILocalPortletAssignmentManager
            )
        except ComponentLookupError:
            pass

        categories = (
            GROUP_CATEGORY, CONTENT_TYPE_CATEGORY, CONTEXT_CATEGORY, USER_CATEGORY
        )

        for category in categories:
            assignable.setBlacklistStatus(category, 1)
