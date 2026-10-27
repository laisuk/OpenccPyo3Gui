"""Find/replace behavior and main-window integration (offscreen Qt)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPlainTextEdit
from helpers.find_replace_dialog import FindReplaceDialog
from mainwindow import MainWindow


class FindReplaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.settings_dir = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, cls.settings_dir.name)
        cls.app.setOrganizationName('FindReplaceTests')
        cls.app.setApplicationName('FindReplaceTests')

    @classmethod
    def tearDownClass(cls):
        cls.settings_dir.cleanup()

    def setUp(self):
        QSettings().clear()
        self.editor = QPlainTextEdit()
        self.dialog = FindReplaceDialog(self.editor)
        self.addCleanup(self.editor.close)
        self.addCleanup(self.dialog.close)

    def query(self, text, content):
        self.editor.setPlainText(content)
        self.dialog.find_edit.setText(text)
        self.dialog.refresh()

    def test_options_highlights_and_wrap(self):
        self.query('cat', 'cat Cat scatter cat')
        self.assertEqual(self.dialog.counter.text(), '1 of 4')
        self.assertEqual(len(self.editor.extraSelections()), 4)
        self.dialog.whole_words.setChecked(True)
        self.dialog.match_case.setChecked(True)
        self.dialog.refresh()
        self.assertEqual(self.dialog.counter.text(), '1 of 2')
        self.dialog.navigate(True)
        self.assertEqual(self.dialog.counter.text(), '2 of 2')
        self.dialog.navigate()
        self.assertEqual(self.dialog.counter.text(), '1 of 2')

    def test_replace_all_unicode_single_undo(self):
        self.query('猫', '猫猫 cat 猫')
        self.dialog.replace_edit.setText('🐈猫')
        self.dialog.replace_all()
        self.assertEqual(self.editor.toPlainText(), '🐈猫🐈猫 cat 🐈猫')
        self.assertEqual(self.dialog.message.text(), 'Replaced 3 occurrence(s).')
        self.editor.undo()
        self.assertEqual(self.editor.toPlainText(), '猫猫 cat 猫')

    def test_regex_invalid_empty_matches_and_readonly(self):
        self.dialog.regex.setChecked(True)
        self.query('[', 'abc 123 def 456')
        self.assertFalse(self.dialog.next_button.isEnabled())
        self.assertTrue(self.dialog.message.text())
        self.dialog.find_edit.setText(r'\d+')
        self.dialog.replace_edit.setText('N')
        self.dialog.replace_all()
        self.assertEqual(self.editor.toPlainText(), 'abc N def N')
        self.dialog.find_edit.setText('^')
        self.dialog.replace_all()
        self.assertEqual(self.editor.toPlainText(), 'abc N def N')
        self.editor.setReadOnly(True)
        self.dialog.find_edit.setText('N')
        self.dialog.refresh()
        self.assertFalse(self.dialog.replace_all_button.isEnabled())
        self.dialog.replace_all()
        self.assertEqual(self.editor.toPlainText(), 'abc N def N')

    def test_switch_editor_refreshes_and_disconnects_old_editor(self):
        self.query('cat', 'cat')
        other = QPlainTextEdit()
        self.addCleanup(other.close)
        other.setPlainText('cat cat')
        self.dialog.show()
        self.dialog.set_editor(other)
        self.assertEqual(len(self.editor.extraSelections()), 0)
        self.dialog.refresh_timer.stop()
        self.editor.appendPlainText('cat')
        self.assertFalse(self.dialog.refresh_timer.isActive())
        other.appendPlainText('cat')
        self.assertTrue(self.dialog.refresh_timer.isActive())
        self.dialog.refresh()
        self.assertEqual(len(other.extraSelections()), 3)

    def test_destination_focus_while_replace_is_open(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.show()
        source, destination = window.ui.tbSource, window.ui.tbDestination
        source.setPlainText('cat cat')
        destination.setPlainText('cat destination cat')
        window.show_find_replace(True)
        dialog = window._find_replace_dialog
        self.addCleanup(dialog.close)
        dialog.find_edit.setText('cat')
        dialog.replace_edit.setText('dog')
        dialog.refresh()

        window.activateWindow()
        destination.setFocus()
        self.app.processEvents()
        self.assertTrue(destination.hasFocus())
        self.assertIs(dialog.editor, source)
        self.assertTrue(dialog.replace_row.isVisible())
        dialog.replace_one()
        self.assertEqual(source.toPlainText(), 'dog cat')
        dialog.replace_all()
        self.assertEqual(source.toPlainText(), 'dog dog')
        self.assertEqual(destination.toPlainText(), 'cat destination cat')

        # Explicitly opening Find in Destination changes to find-only mode.
        destination.setFocus()
        window.show_find_replace(False)
        self.assertIs(dialog.editor, destination)
        self.assertFalse(dialog.replace_row.isVisible())
        self.assertFalse(dialog.replace_button.isEnabled())
        self.assertFalse(dialog.replace_all_button.isEnabled())
        dialog.replace_one()
        dialog.replace_all()
        self.assertEqual(destination.toPlainText(), 'cat destination cat')

        # Reopening Replace always returns to Source, preserving replacement text.
        window.show_find_replace(True)
        self.assertIs(dialog.editor, source)
        self.assertTrue(dialog.replace_row.isVisible())
        self.assertEqual(dialog.replace_edit.text(), 'dog')

    def test_mainwindow_shortcuts_and_targets(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.show()
        window.activateWindow()
        window.ui.tbDestination.setPlainText('destination')
        window.ui.tbDestination.setFocus()
        self.app.processEvents()
        QTest.keyClick(window.ui.tbDestination, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        dialog = window._find_replace_dialog
        self.assertIsNotNone(dialog)
        self.addCleanup(dialog.close)
        self.assertIs(dialog.editor, window.ui.tbDestination)
        window.ui.actionReplace.trigger()
        self.assertIs(dialog.editor, window.ui.tbSource)
        self.assertTrue(dialog.replace_row.isVisible())
        self.assertEqual(window.ui.actionReplace.shortcut().toString(), 'Ctrl+H')
        window.ui.tbSource.setPlainText('cat cat')
        dialog.find_edit.setText('cat')
        dialog.refresh()
        dialog.hide()
        window.ui.tbSource.setFocus()
        self.app.processEvents()
        QTest.keyClick(window.ui.tbSource, Qt.Key.Key_F3)
        self.assertEqual(window.ui.tbSource.textCursor().selectionStart(), 4)


if __name__ == '__main__':
    unittest.main()
