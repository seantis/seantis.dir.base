from five import grok

from zope.component import adapts
from plone.dexterity.interfaces import IDexterityContent

from plone.app.dexterity.behaviors.metadata import DCFieldProperty

from seantis.dir.base.utils import is_izug_portal
from seantis.dir.base.utils import get_current_language
from seantis.dir.base.utils import remove_count

class View(grok.View):
    grok.baseclass()

    @property
    def is_izug_portal(self):
        return is_izug_portal(self)

    @property
    def current_language(self):
        return get_current_language(self.context, self.request)

    def get_filter_terms(self):
        """Unpacks the filter terms from a request."""

        terms = {}
        request = self.request

        filterable = lambda k: k.startswith('cat') and request[k] != ''
        category_keys = (k for k in request.keys() if filterable(k))

        for key in category_keys:
            text = request[key].decode('utf-8')
            terms[key] = remove_count(text)

        return terms

def ExtendedDirectory(directory):
    interface = directory.interface
    fields = [(f, interface[f]) for f in interface]
    for name, field in fields:
        if not hasattr(directory, name):
            setattr(directory, name, DCFieldProperty(field))

    return directory

class DirectoryMetadataBase(object):

    adapts(IDexterityContent)
    
    def __init__(self, context):
        self.context = context

        for fieldname in self.interface:
            if not hasattr(self.context, fieldname):
                setattr(self.context, fieldname, None)