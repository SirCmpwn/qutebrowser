# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for qutebrowser.utils.editor."""

import os
import os.path
import unittest
import logging
from unittest.mock import Mock

from PyQt5.QtCore import QProcess

import qutebrowser.utils.editor as editorutils
from qutebrowser.test.stubs import ConfigStub, FakeQProcess


def setUpModule():
    """Disable logging and mock out some imports."""
    logging.disable(logging.INFO)
    editorutils.message = Mock()
    editorutils.QProcess = FakeQProcess


def tearDownModule():
    """Restore logging."""
    logging.disable(logging.NOTSET)


class ArgTests(unittest.TestCase):

    """Test argument handling.

    Attributes:
        editor: The ExternalEditor instance to test.
    """

    def setUp(self):
        self.editor = editorutils.ExternalEditor()

    def test_simple_start_args(self):
        """Test starting editor without arguments."""
        editorutils.config = ConfigStub({'general': {'editor': ['bin']}})
        self.editor.edit("")
        self.editor.proc.start.assert_called_with("bin", [])

    def test_start_args(self):
        """Test starting editor with static arguments."""
        editorutils.config = ConfigStub(
            {'general': {'editor': ['bin', 'foo', 'bar']}})
        self.editor.edit("")
        self.editor.proc.start.assert_called_with("bin", ["foo", "bar"])

    def test_placeholder(self):
        """Test starting editor with placeholder argument."""
        editorutils.config = ConfigStub(
            {'general': {'editor': ['bin', 'foo', '{}', 'bar']}})
        self.editor.edit("")
        filename = self.editor.filename
        self.editor.proc.start.assert_called_with("bin",
                                                  ["foo", filename, "bar"])

    def test_in_arg_placeholder(self):
        """Test starting editor with placeholder argument inside argument."""
        editorutils.config = ConfigStub(
            {'general': {'editor': ['bin', 'foo{}bar']}})
        self.editor.edit("")
        self.editor.proc.start.assert_called_with("bin", ["foo{}bar"])

    def tearDown(self):
        self.editor._cleanup()  # pylint: disable=protected-access


class FileHandlingTests(unittest.TestCase):

    """Test creation/deletion of tempfile.

    Attributes:
        editor: The ExternalEditor instance to test.
    """

    def setUp(self):
        self.editor = editorutils.ExternalEditor()
        editorutils.config = ConfigStub({'general': {'editor': ['']}})

    def test_file_handling_closed_ok(self):
        """Test file handling when closing with an exitstatus == 0."""
        self.editor.edit("")
        filename = self.editor.filename
        self.assertTrue(os.path.exists(filename))
        self.editor.on_proc_closed(0, QProcess.NormalExit)
        self.assertFalse(os.path.exists(filename))

    def test_file_handling_closed_error(self):
        """Test file handling when closing with an exitstatus != 0."""
        self.editor.edit("")
        filename = self.editor.filename
        self.assertTrue(os.path.exists(filename))
        self.editor.on_proc_closed(1, QProcess.NormalExit)
        self.assertFalse(os.path.exists(filename))

    def test_file_handling_closed_crash(self):
        """Test file handling when closing with a crash."""
        self.editor.edit("")
        filename = self.editor.filename
        self.assertTrue(os.path.exists(filename))
        self.editor.on_proc_error(QProcess.Crashed)
        self.editor.on_proc_closed(0, QProcess.CrashExit)
        self.assertFalse(os.path.exists(filename))


class TextModifyTests(unittest.TestCase):

    """Tests to test if the text gets saved/loaded correctly.

    Attributes:
        editor: The ExternalEditor instance to test.
    """

    def setUp(self):
        self.editor = editorutils.ExternalEditor()
        self.editor.editing_finished = Mock()
        editorutils.config = ConfigStub({'general': {'editor': ['']}})

    def _write(self, text):
        """Write a text to the file opened in the fake editor.

        Args:
            text: The text to write to the file.
        """
        filename = self.editor.filename
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)

    def _read(self):
        """Read a text from the file opened in the fake editor.

        Return:
            The text which was read.
        """
        filename = self.editor.filename
        with open(filename, 'r', encoding='utf-8') as f:
            data = f.read()
        return data

    def test_empty_input(self):
        """Test if an empty input gets modified correctly."""
        self.editor.edit("")
        self.assertEqual(self._read(), "")
        self._write("Hello")
        self.editor.on_proc_closed(0, QProcess.NormalExit)
        self.editor.editing_finished.emit.assert_called_with("Hello")

    def test_simple_input(self):
        """Test if an empty input gets modified correctly."""
        self.editor.edit("Hello")
        self.assertEqual(self._read(), "Hello")
        self._write("World")
        self.editor.on_proc_closed(0, QProcess.NormalExit)
        self.editor.editing_finished.emit.assert_called_with("World")

    def test_umlaut(self):
        """Test if umlauts works correctly."""
        self.editor.edit("Hällö Wörld")
        self.assertEqual(self._read(), "Hällö Wörld")
        self._write("Überprüfung")
        self.editor.on_proc_closed(0, QProcess.NormalExit)
        self.editor.editing_finished.emit.assert_called_with("Überprüfung")

    def test_unicode(self):
        """Test if other UTF8 chars work correctly."""
        self.editor.edit("\u2603")  # Unicode snowman
        self.assertEqual(self._read(), "\u2603")
        self._write("\u2601")  # Cloud
        self.editor.on_proc_closed(0, QProcess.NormalExit)
        self.editor.editing_finished.emit.assert_called_with("\u2601")


class ErrorMessageTests(unittest.TestCase):

    """Test if statusbar error messages get emitted correctly.

    Attributes:
        editor: The ExternalEditor instance to test.
    """

    # pylint: disable=maybe-no-member

    def setUp(self):
        self.editor = editorutils.ExternalEditor()
        editorutils.config = ConfigStub({'general': {'editor': ['']}})

    def test_proc_error(self):
        """Test on_proc_error."""
        self.editor.edit("")
        self.editor.on_proc_error(QProcess.Crashed)
        self.assertTrue(editorutils.message.error.called)

    def test_proc_return(self):
        """Test on_proc_finished with a bad exit status."""
        self.editor.edit("")
        self.editor.on_proc_closed(1, QProcess.NormalExit)
        self.assertTrue(editorutils.message.error.called)


if __name__ == '__main__':
    unittest.main()
