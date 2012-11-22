# Introduction

seantis.dir.base allows to put dexterity objects into 1-4 categories, showing those categories in a browsable and searchable catalog.

The idea of this plone module is to provide all basic functionality needed to categorize, search and filter objects. These objects may be extended with custom fields using dexterity.

An example, offering a directory of contacts can be found here:
[https://github.com/seantis/seantis.dir.contacts](https://github.com/seantis/seantis.dir.contacts)

This module is probably only really useful for anyone if used as a base to build on. By itself it only offers the categorization and search functionalities.

# Build Status

[![Build Status](https://secure.travis-ci.org/seantis/seantis.dir.base.png)](https://travis-ci.org/seantis/seantis.dir.base)

# Dependencies

seantis.dir.base relies on Plone 4.0+ with the following modules:
    plone.app.dexterity
    plone.behavior
    plone.directives.form
    collective.dexteritytextindexer
    xlrd
    xlwt

# Installation

1. Add dexterity to Plone by adding the following Known Good Set to your buildout.cfg:

        extends =
            ...
            http://good-py.appspot.com/release/dexterity/1.1?plone=4.1.2

2. Add the module to your instance eggs

        [instance]
        ...
        eggs =
            ...
            seantis.dir.base


3. Ensure that the i18n files are compiled by adding

        [instance]
        ...
        environment-vars = 
            ...
            zope_i18n_compile_mo_files true

4. Install dexterity and seantis.dir.base using portal_quickinstaller

# License

seantis.dir.base is released under GPL v2

# Maintainer

seantis.dir.base is maintained by Seantis GmbH (www.seantis.ch)