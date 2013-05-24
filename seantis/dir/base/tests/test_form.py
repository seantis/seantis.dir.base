from seantis.dir.base.tests import FunctionalTestCase


class TestDirectoryForm(FunctionalTestCase):

    def test_category_labels(self):
        """ Categories defined / labeled on the directory must show up with
        adjusted labels when a new directory item is added or edited.

        Unlabeled categories must not show up in those forms.

        """

        browser = self.new_browser()
        browser.login_admin()
        browser.open('/++add++seantis.dir.base.directory')

        browser.getControl(name='form.widgets.title').value = 'Verzeichnis'
        browser.getControl('1st Category Name').value = 'Kategorie'

        browser.getControl('Save').click()

        browser.open('/verzeichnis/++add++seantis.dir.base.item')

        # category one must be there
        browser.assert_present('#form-widgets-IDirectoryCategorized-cat1')

        # the others shouldn't
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat2')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat3')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat4')

        # the label must also be right
        label = 'label[for="form-widgets-IDirectoryCategorized-cat1"]'
        self.assertTrue('Kategorie' in browser.query(label).text())

        # this must still be true once the item is saved and edited
        browser.getControl(name='form.widgets.title').value = 'Eintrag'
        browser.getControl('Save').click()

        browser.open('/verzeichnis/eintrag/edit')

        browser.assert_present('#form-widgets-IDirectoryCategorized-cat1')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat2')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat3')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat4')

        label = 'label[for="form-widgets-IDirectoryCategorized-cat1"]'
        self.assertTrue('Kategorie' in browser.query(label).text())

        # and it should change once we rename a category and add another
        browser.open('/verzeichnis/edit')
        browser.getControl('1st Category Name').value = 'Eins'
        browser.getControl('2nd Category Name').value = 'Zwei'
        browser.getControl('Save').click()

        browser.open('/verzeichnis/eintrag/edit')

        browser.assert_present('#form-widgets-IDirectoryCategorized-cat1')
        browser.assert_present('#form-widgets-IDirectoryCategorized-cat2')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat3')
        browser.assert_missing('#form-widgets-IDirectoryCategorized-cat4')

        label = 'label[for="form-widgets-IDirectoryCategorized-cat1"]'
        self.assertTrue('Eins' in browser.query(label).text())
        label = 'label[for="form-widgets-IDirectoryCategorized-cat2"]'
        self.assertTrue('Zwei' in browser.query(label).text())

        # remove the directory again
        browser.open('/verzeichnis/delete_confirmation')
        browser.getControl('Delete').click()

    def test_locked_fields(self):
        """ Categories may be locked on the directory, which means that all
        entries added may not define, but only choose categories. If the
        categories need to be chosen, they need to be added as suggestions.

        This behavior can be switched at any time.

        """

        browser = self.new_browser()
        browser.login_admin()

        cities = ['New York', 'Hong Kong', 'Baar']

        browser.open('/++add++seantis.dir.base.directory')
        browser.getControl(name='form.widgets.title').value = 'Verzeichnis'
        browser.getControl('1st Category Name').value = 'Ort'
        browser.getControl('Suggested Values for the 1st Category').value = (
            '\n'.join(cities)
        )
        browser.getControl('Allow custom categories').selected = False
        browser.getControl('Save').click()

        browser.open('/verzeichnis/++add++seantis.dir.base.item')

        # we should find three checkboxes
        options = '#formfield-form-widgets-IDirectoryCategorized-cat1 .option'
        browser.assert_count(options, 3)

        values = [o.text().strip() for o in browser.query(options).items()]
        self.assertEqual(values, cities)

        # select two
        browser.getControl(name='form.widgets.title').value = 'Eintrag'
        browser.getControl('New York').selected = True
        browser.getControl('Baar').selected = True

        browser.getControl('Save').click()

        # ensure that they are checked when opening the edit form
        browser.open('/verzeichnis/eintrag/edit')

        self.assertTrue(browser.getControl('New York').selected)
        self.assertFalse(browser.getControl('Hong Kong').selected)
        self.assertTrue(browser.getControl('Baar').selected)

        # switch back to unlocked fields, which should result in a textarea
        # which replaces the checkboxes and contains the values of the selected
        # controls
        browser.open('/verzeichnis/edit')
        browser.getControl('Allow custom categories').selected = True
        browser.getControl('Save').click()

        browser.open('/verzeichnis/eintrag/edit')
        options = '#formfield-form-widgets-IDirectoryCategorized-cat1 .option'
        browser.assert_count(options, 0)

        textarea = '#form-widgets-IDirectoryCategorized-cat1'
        values = browser.query(textarea).text().split('\n')

        self.assertEqual(['New York', 'Baar'], values)

        # remove the directory again
        browser.open('/verzeichnis/delete_confirmation')
        browser.getControl('Delete').click()
