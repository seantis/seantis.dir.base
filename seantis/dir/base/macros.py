from five import grok
from zope.interface import Interface
from seantis.dir.base import core


class View(core.View):
    """A numer of macros for use with seantis.dir.base"""

    grok.context(Interface)
    grok.require('zope2.View')
    grok.name('seantis-dir-macros')

    template = grok.PageTemplateFile('templates/macros.pt')
    directory_template = grok.PageTemplateFile('templates/directory.pt')

    def __getitem__(self, key):
        if key == 'directory':
            return self.directory_template._template.macros['directory']
        return self.template._template.macros[key]
