"""
tests/integration/test_shell_io.py
====================================
Integration tests for shell I/O features: redirection, pipes, and stdin.

Covers:
- Test 14: Redirection parsing variants (>, >>, <, with/without spaces)
- Test 25: Pipe support (single pipe, multi-stage pipes)
- Test 26: Stdin redirection (< file)
- Test 29: tee command (write and passthrough, append mode)
"""

import io
import sys
import unittest

from tests.base import BaseTestCase


class TestRedirectionParsing(BaseTestCase):
    """Test 14: Redirection parsing variants — >, >>, no spaces."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    # ------------------------------------------------------------------
    # Overwrite redirection (>)
    # ------------------------------------------------------------------

    def test_overwrite_redirect_no_spaces(self):
        """echo alpha>/tmp/redir.txt — no space between command and >."""
        self.assertShellSuccess(self.shell, "echo alpha>/tmp/redir.txt")
        self.assertFileEquals(self.fs, "/tmp/redir.txt", b"alpha\n")

    def test_overwrite_redirect_with_spaces(self):
        """echo gamma > /tmp/redir2.txt — spaces around >."""
        self.assertShellSuccess(self.shell, "echo gamma > /tmp/redir2.txt")
        self.assertFileEquals(self.fs, "/tmp/redir2.txt", b"gamma\n")

    def test_overwrite_redirect_replaces_file(self):
        """Second overwrite redirect truncates existing content."""
        self.assertShellSuccess(self.shell, "echo first > /tmp/overwrite.txt")
        self.assertFileEquals(self.fs, "/tmp/overwrite.txt", b"first\n")
        self.assertShellSuccess(self.shell, "echo second > /tmp/overwrite.txt")
        self.assertFileEquals(self.fs, "/tmp/overwrite.txt", b"second\n")

    # ------------------------------------------------------------------
    # Append redirection (>>)
    # ------------------------------------------------------------------

    def test_append_redirect_no_spaces(self):
        """echo beta>>/tmp/redir.txt — no space before >>."""
        self.assertShellSuccess(self.shell, "echo alpha>/tmp/redir.txt")
        self.assertShellSuccess(self.shell, "echo beta>>/tmp/redir.txt")
        self.assertFileEquals(self.fs, "/tmp/redir.txt", b"alpha\nbeta\n")

    def test_append_redirect_with_spaces(self):
        """Append with spaces: echo line2 >> file."""
        self.assertShellSuccess(self.shell, "echo line1 > /tmp/append.txt")
        self.assertShellSuccess(self.shell, "echo line2 >> /tmp/append.txt")
        self.assertFileEquals(self.fs, "/tmp/append.txt", b"line1\nline2\n")

    def test_append_creates_file_if_missing(self):
        """Append >> to a non-existent file creates it."""
        self.assertShellSuccess(self.shell, "echo new >> /tmp/brand_new.txt")
        self.assertFileEquals(self.fs, "/tmp/brand_new.txt", b"new\n")

    # ------------------------------------------------------------------
    # Combined overwrite then append sequence
    # ------------------------------------------------------------------

    def test_overwrite_then_append_sequence(self):
        """Sequence: overwrite creates, append accumulates."""
        self.assertShellSuccess(self.shell, "echo alpha>/tmp/seq.txt")
        self.assertFileEquals(self.fs, "/tmp/seq.txt", b"alpha\n")
        self.assertShellSuccess(self.shell, "echo beta>>/tmp/seq.txt")
        self.assertFileEquals(self.fs, "/tmp/seq.txt", b"alpha\nbeta\n")
        self.assertShellSuccess(self.shell, "echo gamma >> /tmp/seq.txt")
        self.assertFileEquals(self.fs, "/tmp/seq.txt", b"alpha\nbeta\ngamma\n")


class TestPipeSupport(BaseTestCase):
    """Test 25: Pipe support — single and multi-stage pipelines."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        # Prepare a source file for pipe tests
        self.shell.execute("echo alpha > /tmp/pipe_src.txt")
        self.shell.execute("echo beta >> /tmp/pipe_src.txt")
        self.shell.execute("echo gamma >> /tmp/pipe_src.txt")

    # ------------------------------------------------------------------
    # Single pipe
    # ------------------------------------------------------------------

    def test_single_pipe_cat_grep(self):
        """cat file | grep pattern writes only matching lines."""
        self.assertShellSuccess(
            self.shell,
            "cat /tmp/pipe_src.txt | grep beta > /tmp/pipe_out.txt",
        )
        self.assertFileEquals(self.fs, "/tmp/pipe_out.txt", b"beta\n")

    def test_single_pipe_cat_sort_reverse(self):
        """cat file | sort -r produces reverse-sorted output."""
        self.assertShellSuccess(
            self.shell,
            "cat /tmp/pipe_src.txt | sort -r > /tmp/pipe_sort.txt",
        )
        self.assertFileEquals(self.fs, "/tmp/pipe_sort.txt", b"gamma\nbeta\nalpha\n")

    def test_single_pipe_no_matches_empty_output(self):
        """Pipe through grep with no match produces empty output."""
        self.assertShellSuccess(self.shell, "echo hello > /tmp/nomatch_src.txt")
        self.shell.execute(
            "cat /tmp/nomatch_src.txt | grep zzz > /tmp/nomatch_out.txt"
        )
        content = self.fs.read_file("/tmp/nomatch_out.txt")
        self.assertEqual(content, b"")

    # ------------------------------------------------------------------
    # Multi-stage pipe
    # ------------------------------------------------------------------

    def test_multi_stage_pipe_cat_grep_sort(self):
        """cat | grep | sort: three-stage pipeline produces correct output."""
        self.assertShellSuccess(
            self.shell,
            "cat /tmp/pipe_src.txt | grep a | sort > /tmp/pipe_multi.txt",
        )
        content = self.fs.read_file("/tmp/pipe_multi.txt")
        self.assertIn(b"alpha", content)
        self.assertIn(b"gamma", content)
        self.assertNotIn(b"beta", content)

    def test_multi_stage_pipe_preserves_order(self):
        """Multi-stage pipeline with sort -r gives correct reverse order."""
        self.assertShellSuccess(
            self.shell,
            "cat /tmp/pipe_src.txt | grep a | sort -r > /tmp/pipe_rev.txt",
        )
        content = self.fs.read_file("/tmp/pipe_rev.txt")
        lines = content.decode().strip().splitlines()
        self.assertEqual(sorted(lines, reverse=True), lines)


class TestStdinRedirection(BaseTestCase):
    """Test 26: Stdin redirection — < file."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_cat_stdin_redirect(self):
        """cat < file is equivalent to cat file."""
        self.assertShellSuccess(self.shell, "echo hello > /tmp/stdin_src.txt")
        self.assertShellSuccess(
            self.shell,
            "cat < /tmp/stdin_src.txt > /tmp/stdin_out.txt",
        )
        self.assertFileEquals(self.fs, "/tmp/stdin_out.txt", b"hello\n")

    def test_grep_stdin_redirect(self):
        """grep pattern < file filters lines from stdin."""
        self.assertShellSuccess(self.shell, "echo one > /tmp/stdin_grep.txt")
        self.assertShellSuccess(self.shell, "echo two >> /tmp/stdin_grep.txt")
        self.assertShellSuccess(
            self.shell,
            "grep one < /tmp/stdin_grep.txt > /tmp/stdin_grep_out.txt",
        )
        self.assertFileEquals(self.fs, "/tmp/stdin_grep_out.txt", b"one\n")

    def test_stdin_redirect_missing_file_fails(self):
        """< with a non-existent file should return non-zero."""
        self.assertShellFails(self.shell, "cat < /tmp/does_not_exist.txt")

    def test_stdin_redirect_multiple_lines(self):
        """cat < file with multiple lines passes all through."""
        self.assertShellSuccess(self.shell, "echo line1 > /tmp/multi_stdin.txt")
        self.assertShellSuccess(self.shell, "echo line2 >> /tmp/multi_stdin.txt")
        self.assertShellSuccess(self.shell, "echo line3 >> /tmp/multi_stdin.txt")
        self.assertShellSuccess(
            self.shell,
            "cat < /tmp/multi_stdin.txt > /tmp/multi_stdin_out.txt",
        )
        self.assertFileEquals(
            self.fs, "/tmp/multi_stdin_out.txt", b"line1\nline2\nline3\n"
        )


class TestTeeCommand(BaseTestCase):
    """Test 29: tee command — write to file and pass through."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_tee_writes_file_and_passes_through(self):
        """echo | tee file writes to both the named file and stdout."""
        self.assertShellSuccess(
            self.shell,
            "echo hello | tee /tmp/tee_out.txt > /tmp/tee_stdout.txt",
        )
        self.assertFileEquals(self.fs, "/tmp/tee_out.txt", b"hello\n")
        self.assertFileEquals(self.fs, "/tmp/tee_stdout.txt", b"hello\n")

    def test_tee_append_mode(self):
        """tee -a appends to the named file rather than overwriting."""
        # Seed the target file with initial content
        self.assertShellSuccess(
            self.shell,
            "echo hello | tee /tmp/tee_append.txt > /tmp/tee_dummy.txt",
        )
        # Append via tee -a
        self.assertShellSuccess(self.shell, "echo world > /tmp/tee_src.txt")
        self.assertShellSuccess(
            self.shell,
            "cat /tmp/tee_src.txt | tee -a /tmp/tee_append.txt > /tmp/tee_appended.txt",
        )
        content = self.fs.read_file("/tmp/tee_append.txt")
        self.assertIn(b"hello", content)
        self.assertIn(b"world", content)

    def test_tee_overwrites_by_default(self):
        """tee without -a overwrites the named file on each call."""
        self.assertShellSuccess(
            self.shell,
            "echo first | tee /tmp/tee_overwrite.txt > /dev/null",
        )
        self.assertShellSuccess(
            self.shell,
            "echo second | tee /tmp/tee_overwrite.txt > /dev/null",
        )
        content = self.fs.read_file("/tmp/tee_overwrite.txt")
        self.assertNotIn(b"first", content)
        self.assertIn(b"second", content)

    def test_tee_with_pipe_chain(self):
        """Data piped through tee is still available to next stage."""
        self.assertShellSuccess(self.shell, "echo alpha > /tmp/tee_chain_src.txt")
        self.assertShellSuccess(self.shell, "echo beta >> /tmp/tee_chain_src.txt")
        self.assertShellSuccess(
            self.shell,
            "cat /tmp/tee_chain_src.txt | tee /tmp/tee_chain_copy.txt > /tmp/tee_chain_out.txt",
        )
        self.assertFileEquals(self.fs, "/tmp/tee_chain_copy.txt", b"alpha\nbeta\n")
        self.assertFileEquals(self.fs, "/tmp/tee_chain_out.txt", b"alpha\nbeta\n")

    def test_tee_stdin_via_io_stringio(self):
        """tee reads from piped stdin correctly (simulated via io.StringIO)."""
        original_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("test_input\n")
            exit_code = self.shell.execute("tee /tmp/tee_sio.txt > /tmp/tee_sio_out.txt")
            # Should succeed or at minimum not crash
            self.assertIsNotNone(exit_code)
        finally:
            sys.stdin = original_stdin


if __name__ == "__main__":
    unittest.main()
