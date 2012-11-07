from zope.component import getMultiAdapter, getUtility
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.constants import USER_CATEGORY
from plone.portlets.constants import GROUP_CATEGORY
from plone.portlets.constants import CONTENT_TYPE_CATEGORY
from plone.portlets.constants import CONTEXT_CATEGORY

def block_portlets_on_creation(context, event):
    for manager_name in ('plone.leftcolumn','plone.rightcolumn'):
        manager = getUtility(IPortletManager, name=manager_name)
        assignable = getMultiAdapter((context, manager,), ILocalPortletAssignmentManager)
        for category in (GROUP_CATEGORY, CONTENT_TYPE_CATEGORY,CONTEXT_CATEGORY,USER_CATEGORY):
            assignable.setBlacklistStatus(category, 1)