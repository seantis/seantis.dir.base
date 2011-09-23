from datetime import datetime
from itertools import groupby
from Products.CMFCore.utils import getToolByName
from plone.memoize import ram

from seantis.dir.base import utils

class WrappedDict(dict):
    """Wrapper around normal dictionary to allow the dynamic creation of
    attributes on the instance, which is not possible in a normal dict.

    """

def _items(directory):
    """Returns all items of a directory. If the user is anonymous, the result
    is cached until a modification to any directory item or the directory itself
    is made. See events in item.py for reference.

    """
    membership = getToolByName(directory, 'portal_membership')
    if membership.isAnonymousUser():
        items = _cached_items(directory)
    else:
        items = _uncached_items(directory)

    return items

def directory_cachekey(method, directory):
    """Returns the cache key for a directory."""
    return (directory.id, directory.modified(), directory.child_modified)

@ram.cache(directory_cachekey)
def _cached_items(directory):
    """_uncached_items with a cache."""
    items = _uncached_items(directory)

    #mark the dictionary for testing
    items._cache_time = datetime.now()
    return items

def _uncached_items(directory):
    """Returns all items of the given directory uncached."""
    catalog = getToolByName(directory, 'portal_catalog')
    path = '/'.join(directory.getPhysicalPath())

    results = catalog(
        path={'query': path, 'depth':1}
    )

    items = WrappedDict()
    for result in results:
        items[result.getRID()] = result.getObject()
    
    return items

def items(directory):
    """Returns all items of the given directory."""
    return _items(directory).values()

def getObjects(directory, results):
    """Returns a list of objects from a ZCatalog resultset either by loading
    the item from cache or by calling getObject directly.

    """
    cache = _items(directory)
    objects = []
    for result in results:
        loaded = cache.get(result.getRID(), None) or result.getObject()
        objects.append(loaded)
        
    return objects

def possible_values(directory, items):
    """Returns a dictionary with the keys being the categories of the directory,
    filled with a list of all possible values for each category. If an item 
    contains a list of values (as opposed to a single string) those values 
    flattened. In other words, there is no hierarchy in the resulting list.

    """
    values = dict([(cat,list()) for cat in directory.all_categories()])
    
    for item in items:
        for cat in values.keys():
            for word in item.keywords(categories=(cat,)):
                word and values[cat].append(word)

    return values

def grouped_possible_values(directory, items):
    """Same as possible_values, but with the categories of the dictionary being
    unique and each value being wrapped in a tuple with the first element
    as the actual value and the second element as the count non-unique values.

    It's really the grouped result of possible_values.

    """

    possible = possible_values(directory, items)
    grouped = dict([(k, dict()) for k in possible.keys()])

    for category, items in possible.items():
        groups = groupby(sorted(items))
        for group, values in groups:
            grouped[category][group] = len(list(values))

    return grouped

def grouped_possible_values_counted(directory, items):
    """Returns a dictionary of categories with a list of possible values
    including counts in brackets.

    """
    possible = grouped_possible_values(directory, items)
    result = dict((k, []) for k in possible.keys())

    for category, values in possible.items():
        counted = []
        for text, count in values.items():
            counted.append(utils.add_count(text, count))
        
        result[category] = sorted(counted, key=utils.din5007)

    return result

def fuzzy_filter(directory, categories):
    """Filter the given list of categories in the directory. This utilizes
    the categories index which is a list of all categories on any given item.

    Since a value may be part of multiple categories in the same item this
    does not return an exact result. In other words, in this function you
    can't search for items with a specific value on category x. 

    It would be possible to do by using different indexes for each category,
    but it would probably not be much faster but more cumbersome for general
    searches over the catalog.

    """

    catalog = getToolByName(directory, 'portal_catalog')
    path = '/'.join(directory.getPhysicalPath())
    
    results = catalog(
        path={'query': path, 'depth':1}, 
        categories={'query':categories, 'operator':'and'}
    )

    return getObjects(directory, results)

def category_filter(directory, term):
    """Filter a list of category values. The term argument is a 
    dictionary with the keys being the categories to search and the values
    being the category values to look for.

    So given an item with the following values
    item.cat1 = 'asdf', item.cat2='qwerty'

    One will find it by using one of these terms:
    term = dict(cat1='asdf')
    term = dict(cat2='qwerty')
    term = dict(cat1='asdf', cat2='qwerty')

    This method will return all items that mach the term.

    Note that to filter for empty values one should use '' instead of None.
    
    Categories with the value '!empty' are considered nonselected and will
    therefore not be used for filtering.

    For more examples see test_catalog.py
    """
    term = dict([(k,v) for k, v in term.items() if not u'!empty' in v])
    assert(all([v != None for v in term.values()]))
    
    results = fuzzy_filter(directory, term.values())
    return [r for r in results if is_exact_match(r, term)]

def fulltext_search(directory, text):
    """Search for a text in the descendants of a directory. Although this
    function searches for descendents up to a depth of three, only 
    DirectoryItems are returned. 

    """
    catalog = getToolByName(directory, 'portal_catalog')
    path = '/'.join(directory.getPhysicalPath())

    # Perform fulltext search
    results = catalog(
        path={'query': path, 'depth':3},
        SearchableText=text
    )

    # Go through the results which may include descendents of DirectoryItem
    # and get the unique paths of the the DirectoryItem parents
    items = set()
    directorypath = directory.absolute_url_path()
    for result in results:
        item = get_item_path(directorypath, result.getPath())
        items.add(item)

    # Use the unique paths to get the directory items. Though a path lookup
    # is very fast this whole thing could possibly done smarter by looking
    # at ZCatalog internals and using that knowledge to avoid these roundtrips
    results = []
    for path in items:
        result = catalog(path={'query': path, 'depth':0})
        results.extend(result)

    return getObjects(directory, results)

def get_item_path(directorypath, descendantpath):
    """Given a directory path and the path of any subpath of the directory,
    return the path of the directory item which contains the descendant.

    The descendant may also be the path to a directory item.

    """
    if not directorypath in descendantpath:
        return None
    
    directory = directorypath.split('/')
    descendant = descendantpath.split('/')

    directorydepth = len(directory)
    assert(directorydepth +1 <= len(descendant))

    child = []
    for i in range(0, directorydepth+1):
        child.append(descendant[i])
    
    return u'/'.join(child)
    
def is_exact_match(item, term):
    """Returns true if a given item is an exact match of term. Term is the same
    as in category_search. 

    """
    for key in term.keys():
        attribute = getattr(item, key)
        itemvalue = "".join(attribute != None and attribute or u'')
        termvalue = "".join(term[key])
        if termvalue == '' and termvalue != itemvalue:
            return False
        if not termvalue in itemvalue:
            return False

    return True

def children(folder, portal_type):
    """Returns the descendants of a folder that match the given portal type."""
    
    catalog = getToolByName(folder, 'portal_catalog')
    path = '/'.join(folder.getPhysicalPath())
    
    results = catalog(
        path={'query': path, 'depth':1}, 
        portal_type=portal_type
    )

    return [r.getObject() for r in results]