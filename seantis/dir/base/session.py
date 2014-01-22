from seantis.dir.base.const import CATEGORIES


def get_session(context, key):
    """Gets the key from the session."""
    session_manager = context.session_data_manager

    if not session_manager.hasSessionData():
        return None

    session = session_manager.getSessionData()

    if not key in session.keys():
        return None

    return session[key]


def set_session(context, key, value):
    """Stores the given value with the key in the session."""
    session_manager = context.session_data_manager
    session = session_manager.getSessionData()

    # avoid triggering a write if not necessary
    if session.get(key) != value:
        session[key] = value


def has_last_search(directory):
    return get_last_search(directory) != u''


def get_last_search(directory):
    """Returns the most recently used search text."""
    sid = directory.id + 'searchtext'
    return get_session(directory, sid) or u''


def has_last_filter(directory):
    return get_last_filter().values() != ['!empty'] * 4


def get_last_filter(directory):
    sid = directory.id + 'filterterms'
    terms = get_session(directory, sid) or {}

    for cat in CATEGORIES:
        if not cat in terms:
            terms[cat] = u'!empty'

    return terms


def set_last_search(directory, searchtext):
    set_session(directory, directory.id + 'filterterms', None)
    set_session(directory, directory.id + 'searchtext', searchtext)


def set_last_filter(directory, terms):
    set_session(directory, directory.id + 'filterterms', terms)
    set_session(directory, directory.id + 'searchtext', None)


def reset_search_filter(directory):
    set_session(directory, directory.id + 'filterterms', None)
    set_session(directory, directory.id + 'searchtext', None)
