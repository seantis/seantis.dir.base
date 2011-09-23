from zope.interface import Interface

class IFieldMapExtender(Interface):
    """Interface describing an object which can extend the FieldMap class used
    for xlsimport/xlsexport.

    """
    def extend_import(self):
        """Extends the fieldmap with custom fields. The default fieldmap for
        the directory item is set as context.

        """
