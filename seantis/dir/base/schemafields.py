import logging
log = logging.getLogger('seantis.dir.base')

from urlparse import urlparse
from zope.schema import TextLine, URI
from zope.schema.interfaces import InvalidURI
from seantis.dir.base.validators import validate_email


class Email(TextLine):

    def __init__(self, *args, **kwargs):
        super(TextLine, self).__init__(*args, **kwargs)

    def _validate(self, value):
        super(TextLine, self)._validate(value)
        validate_email(value)


class AutoProtocolURI(URI):
    """URI field which assumes http:// if no protocol is specified."""

    def fromUnicode(self, value):
        try:
            if not urlparse(value).scheme:
                value = u'http://' + value
        except:
            log.exception('invalid url %s' % value)
            raise InvalidURI(value)

        return super(AutoProtocolURI, self).fromUnicode(value)
