# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and uses
the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

---

## [1.3.0] - Unreleased

### Fixed

- Pinned Nuitka to `4.2.2` after reproducing document-opening crashes with
  `4.3` on Python `3.13.16` / PySide6 `6.12.0`. A compiled GUI diagnostic exited
  with code `3` for both DOCX and PDF: traces stopped at the DOCX header
  generator and creation of the PDF progress callback respectively. Rebuilding
  the same application source with `4.2.2` opened both fixtures successfully
  and returned code `0`. LTO-enabled compiled GUI checks also passed for TXT,
  DOCX, ODT, EPUB, sequential PDF extraction, and background PDF extraction.
  Rebuilt the release executable and passed all five existing tests. The earlier
  About startup import workaround is retained.

- Fixed clicking Help → About terminating the Nuitka executable with exit code
  `3` under Python 3.13 / PySide6 6.12 / Nuitka 4.3. The execution trace stopped
  during `AboutDialog` class definition when its module was imported from the
  menu callback. Importing the dialog at startup avoids this observed crash.
  Compiled smoke tests with LTO disabled and enabled verified opening About,
  Copy Info, and OK, then exited normally with code `0`; the same test passed in
  the interpreter. Rebuilt `mainwindow.dist/OpenccPyo3Gui.exe` with the release
  build script; all five existing tests passed.

- Fixed immediate startup failure of the Windows Nuitka standalone executable
  after switching the build environment from `.venv` to `.venv313`.
    - **Observed on 2026-10-12:** `scripts/build-nuitka.ps1` completed successfully,
      but `mainwindow.dist/OpenccPyo3Gui.exe` exited immediately with code `3`.
      Capturing its output revealed Nuitka's "A segmentation fault has occurred"
      diagnostic instead of a Python exception.
    - **Environment comparison:** the working environment used Python `3.8.10`
      with PySide6/Shiboken `6.6.3.1`; the failing environment used Python `3.13.16`
      with PySide6/Shiboken `6.12.0`. Both used Nuitka `4.3` and
      `opencc-pyo3` `0.12.0`. The Python 3.13 interpreter could import the app and
      construct its main window successfully; the failure occurred in the compiled
      executable.
    - **Isolation:** a separate build with `--trace-execution` and `--lto=no`
      reproduced the crash while connecting the Custom Dictionary Apply button in
      `widgets/dictionary_widget.py`:
      `self.apply_button.clicked.connect(lambda: self.apply_requested.emit(self.rows()))`.
      The crash occurred during startup connection setup, before clicking Apply.
    - **Fix:** replaced the lambda with the named `_apply_rows` method, decorated
      with `@Slot()`, and connected the button directly to that method. The method
      still emits `apply_requested` with the current dictionary rows. Explicit slot
      registration supplies Qt with a zero-argument signature and avoids the
      failing compiled-lambda connection path.
    - **Scope of the finding:** this is a verified workaround for the observed
      Nuitka/Python/PySide6 combination, not proof of a defect in one specific
      component or evidence that lambdas are generally unsupported. Python and
      PySide6 changed together, and the fix changed both the callable form and slot
      registration; a named method without `@Slot()` was not tested separately.
    - **Verification:** the diagnostic executable opened and closed normally.
      Rebuilding with `scripts/build-nuitka.ps1 -PythonExe ./.venv313/Scripts/python.exe`
      also produced a working release executable with the script's default LTO
      setting enabled. Launching that executable from `mainwindow.dist` showed the
      main window and closing it returned exit code `0`. All five existing tests
      passed under both environments, and an interpreted Apply-button smoke check
      confirmed that the current rows were emitted.
    - **Future troubleshooting:** capture executable stdout/stderr even for builds
      with a hidden console, compare Python/PySide6/Shiboken/Nuitka versions, and
      use a separate console-enabled `--trace-execution` build to locate a startup
      crash. Prefer named `@Slot(...)` methods for QObject callbacks when practical.
      See [Qt's signal and slot documentation](https://doc.qt.io/qtforpython-6.11/tutorials/basictutorial/signals_and_slots.html)
      and [Nuitka's segmentation-fault debugging guidance](https://nuitka.net/info/segfault.html).

- Fixed EPUB extraction of HTML named entities by converting them
  into XML-safe numeric character references, preventing XHTML
  parsing errors while preserving inline text spacing.

---

## [1.2.0] - 2026-05-25

## Changed

- Update `opencc-pyo3` to v0.9.0

---

## [1.1.0] - 2026-04-29

## Changed

- Update `opencc-pyo3` to v0.8.12

---

## [1.0.0] – 2025-09-05

### Added

- Initial release of `OpenccPyo3Gui` for `opencc-pyo3`.
- High performance Python OpenCC-compatible engine for Traditional and Simplified Chinese text conversion.
- Supported standard OpenCC configs:
    - `s2t`, `s2tw`, `s2twp`, `s2hk`, `t2s`, `tw2s`, `tw2sp`, `hk2s`, `jp2t`, `t2jp`
- Support conversion of plain text, Office documents, Epub and PDF extracted text.
