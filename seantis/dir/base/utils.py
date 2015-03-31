from collections import Iterable
from time import time
from itertools import tee, islice, chain, izip
from os import path

from Acquisition import aq_inner
from Products.PortalTransforms.transforms.safe_html import scrubHTML
from zope.component import getMultiAdapter
from zope.schema import getFieldsInOrder
from zope import i18n

import pyuca

from seantis.dir.base import _


allkeys = path.join('/'.join(path.split(pyuca.__file__)[:-1]), 'allkeys.txt')
collator = pyuca.Collator(allkeys)


def safe_html(html):
        return scrubHTML(html, raise_error=False)


def flatten(l):
    """Generator for flattening irregularly nested lists. 'Borrowed' from here:
    http://stackoverflow.com
    /questions/2158395/flatten-an-irregular-list-of-lists-in-python

    """
    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, basestring):
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

    http://plone.org/
    documentation/kb/show-context-dependent-folder-icons-in-navigation-portlet
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
    portal_state = getMultiAdapter(
        (context, request), name=u'plone_portal_state'
    )
    return portal_state.language()


def get_filter_terms(context, request):
    """Unpacks the filter terms from a request.

    For example:
        url?cat1=One&cat2=Two

    Will result in:
        {
            'cat1': 'One',
            'cat2': 'Two'
        }
    """
    terms = {}

    # "Any" is also defined in search.pt
    empty = (u'', translate(context, request, _(u'Any')))

    for key, value in request.items():
        if key.startswith('cat'):
            if isinstance(value, basestring):
                text = request[key].decode('utf-8')
                if text not in empty:
                    terms[key] = remove_count(text)
            else:
                texts = [item.decode('utf-8') for item in request[key]]
                terms[key] = [remove_count(item) for item in texts]

    return terms


def add_count(text, count):
    """Adds a count to a text."""
    return '%s (%i)' % (text, count)


def remove_count(text):
    """Removes the count from with_count from a text."""
    pos = text.rfind(' (')
    if pos == -1:
        return text
    else:
        return text[:pos]


def translate(context, request, text):
    lang = get_current_language(context, request)
    return i18n.translate(text, target_language=lang)


def unicode_collate_sortkey():
    """ Returns a sort function to sanely sort unicode values.

    A more exact solution would be to use pyUCA but that relies on an external
    C Library and is more complicated

    See:
    http://stackoverflow.com
    /questions/1097908/how-do-i-sort-unicode-strings-alphabetically-in-python
    http://en.wikipedia.org/wiki/ISO_14651
    http://unicode.org/reports/tr10/
    http://pypi.python.org/pypi/PyICU
    http://jtauber.com/blog/2006/01/27/python_unicode_collation_algorithm/
    https://github.com/href/Python-Unicode-Collation-Algorithm

    """

    return collator.sort_key


def get_marker_url(item, letter=None):
    baseurl = item.absolute_url()
    imagedir = "/++resource++seantis.dir.base.images"
    if letter:
        image = "/markers/marker-" + letter
    else:
        image = "/singlemarker"

    return baseurl + imagedir + image + '.png'


# loving this: http://stackoverflow.com/a/1012089/138103
def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return izip(prevs, items, nexts)


def naive_time(fn):
    def wrapper(*args, **kwargs):
        start = time()
        result = fn(*args, **kwargs)
        print "%s took %i ms" % (fn.__name__, int((time() - start) * 1000))
        return result

    return wrapper


def remove_empty(iterable):
    if iterable is None or isinstance(iterable, basestring):
        return iterable

    return filter(lambda i: bool(i), iterable)


class cached_property(object):
    """A read-only @property that is only evaluated once. The value is cached
    on the object itself rather than the function or class; this should prevent
    memory leakage."""

    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result
