from zope.component.hooks import getSite


def get_fti(typename):
    types = getSite().portal_types

    if typename in types:
        return types[typename]
    else:
        return None


def add_behavior(fti, behavior):
    if fti:
        behaviors = list(fti.behaviors)
        if not behavior in behaviors:
            behaviors.append(behavior)
            fti.behaviors = tuple(behaviors)


def remove_behavior(fti, behavior):
    if fti:
        behaviors = list(fti.behaviors)
        if behavior in behaviors:
            behaviors.remove(behavior)
            fti.behaviors = tuple(behaviors)
