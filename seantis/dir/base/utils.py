import collections

from Acquisition import aq_inner
from zope.component import getMultiAdapter
from zope.schema import getFieldsInOrder
from Products.CMFCore.utils import getToolByName

def flatten(l):
    """Generator for flattening irregularly nested lists. 'Borrowed' from here:
    http://stackoverflow.com/questions/2158395/flatten-an-irregular-list-of-lists-in-python

    """
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el

def get_interface_fields(interface):
    """ Retrieve the field values from a schema interface. Returns a dictionary
    with the keys being the field names and the values being the fields.

    """
    return dict(getFieldsInOrder(interface))

def anonymousHasRight(folder, right='View'):
    """
    For a given Plone folder, determine whether Anonymous has the right
    given by parameter 'right' (String). This recurses to parents if
    'Acquire' is checked.
    Returns 1 if Anonymous has the right, 0 otherwise.

    via http://plone.org/documentation/kb/show-context-dependent-folder-icons-in-navigation-portlet
    """
    ps = folder.permission_settings()
    for p in ps:
        if (p['name'] == right):
            acquired = not not p['acquire']
            break
    if acquired:
        # recurse upwardly:
        parent = folder.aq_parent
        return anonymousHasRight(parent, right)
    else:
        for p in folder.rolesOfPermission(right):
            if p['name'] == "Anonymous":
                selected = not not p['selected']
                return selected

def get_current_language(context, request):
    """Returns the current language"""
    context = aq_inner(context)
    portal_state = getMultiAdapter((context, request), name=u'plone_portal_state')
    return portal_state.language()

def is_izug_portal(obj):
    """Returns true if the dictionary is running on the izug portal. 
    This function should not exist and will be removed as soon as possible.

    """
    skins = getToolByName(obj, 'portal_skins')
    return 'iZug' in skins.getDefaultSkin()

def add_count(text, count):
    """Adds a count to a text."""
    return '%s (%i)' % (text, count)

def remove_count(text):
    """Removes the count from with_count from a text."""
    return text[:text.rfind(' (')]

def din5007(input):
    """ This function implements sort keys for the german language according to 
    DIN 5007.

    """
    
    # key1: compare words lowercase and replace umlauts according to DIN 5007
    key1=input.lower()
    key1=key1.replace(u"\xe4", u"a")
    key1=key1.replace(u"\xf6", u"o")
    key1=key1.replace(u"\xfc", u"u")
    
    # key2: sort the lowercase word before the uppercase word and sort
    # the word with umlaut after the word without umlaut
    key2=input.swapcase()
    
    # in case two words are the same according to key1, sort the words
    # according to key2. 
    return (key1, key2)