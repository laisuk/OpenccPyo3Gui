"""Run with python -m unittest discover -s tests (Qt uses an offscreen platform)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QHeaderView
from mainwindow import MainWindow
from widgets.dictionary_widget import DictionaryWidget
from workers.batch_worker import BatchWorker
from opencc_pyo3 import OpenCC


class CustomDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.settings_dir = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, cls.settings_dir.name)
        cls.app.setOrganizationName("DictionaryTests")
        cls.app.setApplicationName("DictionaryTests")

    @classmethod
    def tearDownClass(cls):
        cls.settings_dir.cleanup()

    def setUp(self):
        QSettings().clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "custom.txt"
        self.path.write_text("自定义词典\t自訂詞庫\n", encoding="utf-8")
        self.row = {"slot": "STPhrases", "mode": "append", "path": str(self.path)}
        self.window = MainWindow()
        self.addCleanup(self.window.close)
        self.window.ui.rbS2t.setChecked(True)
        self.window.ui.rbStd.setChecked(True)

    def test_apply_interactive_failure_and_restore(self):
        self.window.apply_custom_dictionaries([self.row])
        self.window.ui.tbSource.setPlainText("自定义词典")
        self.window.btn_process_click()
        self.assertEqual(self.window.ui.tbDestination.toPlainText(), "自訂詞庫")
        active = self.window.converter
        with patch("mainwindow.QMessageBox.warning"):
            self.window.apply_custom_dictionaries([dict(self.row, path=str(self.root / "missing.txt"))])
        self.assertIs(self.window.converter, active)
        self.window._batch_thread = object()
        self.window.apply_custom_dictionaries([])
        self.assertIs(self.window.converter, active)
        self.window._batch_thread = None
        self.window.apply_custom_dictionaries([])
        self.assertEqual(self.window.converter.convert("自定义词典"), "自定義詞典")

    def test_saved_rows_are_not_automatically_applied(self):
        widget = self.window.dictionary_widget
        widget.add_row(**self.row)
        restored = DictionaryWidget(OpenCC.available_slots())
        self.addCleanup(restored.close)
        self.assertEqual(restored.rows(), [self.row])
        self.assertEqual(restored.status.text(), "Default dictionary")
        widget._remove(widget.table.cellWidget(0, 3))
        self.assertEqual(widget.rows(), [])

    def test_ordered_override_and_configuration_switch(self):
        second = self.root / "override.txt"
        second.write_text("自定义词典\t客製詞庫\n", encoding="utf-8")
        widget = self.window.dictionary_widget
        widget.add_row(**self.row)
        widget.add_row("STPhrases", "override", str(second))
        widget.apply_button.click()
        self.assertEqual(self.window.converter.convert("自定义词典"), "客製詞庫")
        self.window.converter.apply_config("t2s")
        self.window.converter.apply_config("s2t")
        self.assertEqual(self.window.converter.convert("自定义词典"), "客製詞庫")

    def test_reference_layout_and_native_controls(self):
        widget = self.window.dictionary_widget
        tab_index = self.window.ui.tabWidget.indexOf(self.window.dictionary_tab)
        self.assertFalse(self.window.ui.tabWidget.tabIcon(tab_index).isNull())
        self.assertEqual(self.window.ui.tabWidget.tabText(tab_index), "Dictionary（字典）")
        self.assertIs(self.window.dictionary_tab.layout().itemAt(0).widget(), widget)
        title = next(label for label in widget.findChildren(QLabel) if label.text() == "Custom Dictionary")
        self.assertTrue(title.font().bold())
        self.assertEqual(title.font().pointSize(), widget.font().pointSize() + 2)
        self.assertEqual(widget.status.objectName(), "dictionaryStatus")
        self.assertIn("border-radius: 12px", widget.status.styleSheet())
        self.assertEqual(widget.table.horizontalHeader().sectionResizeMode(2), QHeaderView.Stretch)
        add = widget.findChild(QPushButton, "dictionaryAdd")
        self.assertEqual(add.text(), "✚ Add Custom Dictionary")
        self.assertTrue(add.font().bold())
        self.assertTrue(widget.apply_button.font().bold())
        add.click()
        self.assertEqual(widget.rows()[0]["mode"], "append")
        self.assertEqual(widget.table.cellWidget(0, 1).currentText(), "Append")
        self.assertIn("#D32F2F", widget.table.cellWidget(0, 3).styleSheet())
        widget.set_active_count(1)
        self.assertEqual(widget.status.text(), "Custom dictionary (1 slots)")

    def test_custom_converter_batch_text_and_office(self):
        self.window.apply_custom_dictionaries([self.row])
        source = self.root / "source.txt"
        source.write_text("自定义词典", encoding="utf-8")
        docx = self.root / "source.docx"
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:t>自定义词典</w:t></w:document>')
        output = self.root / "output"
        worker = BatchWorker([str(source), str(docx)], output, self.window.converter,
                             "s2t", False, False, False, False, False)
        errors = []
        worker.error.connect(errors.append)
        worker.run()
        self.assertEqual(errors, [])
        self.assertEqual((output / "source_s2t.txt").read_text(encoding="utf-8"), "自訂詞庫")
        with zipfile.ZipFile(output / "source_s2t.docx") as archive:
            self.assertIn("自訂詞庫", archive.read("word/document.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
