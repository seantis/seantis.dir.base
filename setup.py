from setuptools import setup, find_packages
import os

version = '1.8.1'

tests_require = [
    'collective.testcaselayer',
    'plone.app.testing',
    'collective.betterbrowser[pyquery]'
]

extended_data_require = [
    'collective.geo.fastkml>=0.3',
    'fastkml>=0.5'
]

setup(name='seantis.dir.base',
      version=version,
      description="Directory module for Plone using Dexterity",
      long_description='\n'.join((
          open("README.rst").read(),
          open(os.path.join("docs", "HISTORY.txt")).read()
      )),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          'Framework :: Plone',
          'Framework :: Plone :: 4.3',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Programming Language :: Python',
      ],
      keywords='directory plone dexterity',
      author='Seantis GmbH',
      author_email='info@seantis.ch',
      url='https://github.com/seantis/seantis.dir.base',
      license='GPL v2',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['seantis', 'seantis.dir'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Plone>=4.3',
          'plone.namedfile>=2.0.1',
          'plone.app.dexterity',
          'collective.autopermission',
          'plone.behavior',
          'plone.directives.form',
          'collective.dexteritytextindexer',
          'xlrd',
          'xlwt',
          'collective.geo.geographer>=2.0',
          'collective.geo.contentlocations>=3.0',
          'collective.geo.settings>=3.0',
          'collective.geo.mapwidget>=2.0',
          'collective.geo.openlayers>=3.1',
          'collective.geo.kml>=3.1',
          'collective.geo.behaviour>=1.0',
          'seantis.plonetools>=0.9'
      ],
      tests_require=tests_require,
      extras_require=dict(
          tests=tests_require,
          extended_data=extended_data_require
      ),
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
