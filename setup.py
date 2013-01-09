from setuptools import setup, find_packages
import os

version = '1.2'

tests_require = [
    'collective.testcaselayer',
    ]

setup(name='seantis.dir.base',
      version=version,
      description="Directory module for Plone using Dexterity",
      long_description=open("README.rst").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 4.2',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "Programming Language :: Python",
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
          'Plone',
          'plone.app.dexterity',
          'collective.autopermission',
          'plone.behavior',
          'plone.directives.form',
          'collective.dexteritytextindexer',
          'xlrd',
          'xlwt',
          'collective.geo.geographer',
          'collective.geo.contentlocations',
          'collective.geo.settings',
          'collective.geo.mapwidget',
          'collective.geo.openlayers',
          'collective.geo.kml',
      ],
      tests_require=tests_require,
      extras_require=dict(tests=tests_require),
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
