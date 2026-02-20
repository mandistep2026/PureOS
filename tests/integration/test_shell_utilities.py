"""
tests/integration/test_shell_utilities.py
==========================================
Integration tests for shell utility commands.

Covers:
- Test 39: bc command (pipe and direct)
- Test 40: xargs command
- Test 43: cal command
- Test 44: mktemp command
- Test 54: nl command (number lines)
- Test 55: od/xxd commands (hex dump)
- Test 56: column command
"""

import unittest

from tests.base import BaseTestCase


class TestBcCommand(BaseTestCase):
    """Test 39: bc calculator — arithmetic via pipe and direct input."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_bc_simple_addition_via_pipe(self):
        """echo '2+3' | bc outputs 5."""
        self.assertShellSuccess(
            self.shell, "echo '2+3' | bc > /tmp/bc_add.txt"
        )
        content = self.fs.read_file("/tmp/bc_add.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"5", content)

    def test_bc_multiplication_via_pipe(self):
        """echo '6*7' | bc outputs 42."""
        self.assertShellSuccess(
            self.shell, "echo '6*7' | bc > /tmp/bc_mul.txt"
        )
        content = self.fs.read_file("/tmp/bc_mul.txt")
        self.assertIn(b"42", content)

    def test_bc_subtraction_via_pipe(self):
        """echo '10-3' | bc outputs 7."""
        self.assertShellSuccess(
            self.shell, "echo '10-3' | bc > /tmp/bc_sub.txt"
        )
        content = self.fs.read_file("/tmp/bc_sub.txt")
        self.assertIn(b"7", content)

    def test_bc_division_via_pipe(self):
        """echo '20/4' | bc outputs 5."""
        self.assertShellSuccess(
            self.shell, "echo '20/4' | bc > /tmp/bc_div.txt"
        )
        content = self.fs.read_file("/tmp/bc_div.txt")
        self.assertIn(b"5", content)

    def test_bc_is_registered(self):
        """The bc command is present in the shell's command table."""
        self.assertIn("bc", self.shell.commands)

    def test_bc_direct_expression(self):
        """bc with direct expression argument evaluates it."""
        self.assertShellSuccess(
            self.shell, "bc 3+4 > /tmp/bc_direct.txt"
        )
        content = self.fs.read_file("/tmp/bc_direct.txt")
        self.assertIsNotNone(content)


class TestXargsCommand(BaseTestCase):
    """Test 40: xargs command — build and execute commands from stdin."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_xargs_basic_echo(self):
        """echo arg | xargs echo passes arg to echo."""
        self.assertShellSuccess(
            self.shell, "echo hello | xargs echo > /tmp/xargs_echo.txt"
        )
        content = self.fs.read_file("/tmp/xargs_echo.txt")
        self.assertIn(b"hello", content)

    def test_xargs_multiple_args(self):
        """printf with newlines | xargs echo collapses into one call."""
        self.assertShellSuccess(
            self.shell,
            "printf 'a\\nb\\nc\\n' | xargs echo > /tmp/xargs_multi.txt",
        )
        content = self.fs.read_file("/tmp/xargs_multi.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"a", content)

    def test_xargs_is_registered(self):
        """The xargs command is present in the shell's command table."""
        self.assertIn("xargs", self.shell.commands)

    def test_xargs_with_mkdir(self):
        """echo dirname | xargs mkdir -p creates the directory."""
        self.assertShellSuccess(
            self.shell, "echo /tmp/xargs_dir | xargs mkdir -p"
        )
        self.assertDirectoryExists(self.fs, "/tmp/xargs_dir")

    def test_xargs_pipe_from_find(self):
        """find results piped into xargs processes each path."""
        self.assertShellSuccess(
            self.shell, "mkdir -p /tmp/xargs_find_test"
        )
        self.assertShellSuccess(
            self.shell, "touch /tmp/xargs_find_test/a.txt"
        )
        self.assertShellSuccess(
            self.shell,
            "find /tmp/xargs_find_test -type f | xargs echo > /tmp/xargs_find_out.txt",
        )
        content = self.fs.read_file("/tmp/xargs_find_out.txt")
        self.assertIn(b"a.txt", content)


class TestCalCommand(BaseTestCase):
    """Test 43: cal command — display a calendar."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_cal_exits_successfully(self):
        """cal runs and exits with code 0."""
        self.assertShellSuccess(self.shell, "cal > /tmp/cal_out.txt")

    def test_cal_output_contains_days(self):
        """cal output contains recognisable day abbreviations."""
        self.assertShellSuccess(self.shell, "cal > /tmp/cal_days.txt")
        content = self.fs.read_file("/tmp/cal_days.txt")
        self.assertIsNotNone(content)
        # At least one common day-of-week abbreviation
        self.assertTrue(
            any(day in content for day in [b"Su", b"Mo", b"Tu", b"We", b"Th", b"Fr", b"Sa", b"Sun", b"Mon"]),
            "Calendar output should contain day abbreviations",
        )

    def test_cal_specific_month_and_year(self):
        """cal MONTH YEAR exits successfully."""
        self.assertShellSuccess(self.shell, "cal 1 2024 > /tmp/cal_spec.txt")
        content = self.fs.read_file("/tmp/cal_spec.txt")
        self.assertIsNotNone(content)

    def test_cal_is_registered(self):
        """The cal command is present in the shell's command table."""
        self.assertIn("cal", self.shell.commands)


class TestMktempCommand(BaseTestCase):
    """Test 44: mktemp command — create temporary files/directories."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_mktemp_creates_a_file(self):
        """mktemp returns a path and creates the temporary file."""
        self.assertShellSuccess(
            self.shell, "mktemp > /tmp/mktemp_path.txt"
        )
        path_content = self.fs.read_file("/tmp/mktemp_path.txt")
        self.assertIsNotNone(path_content)
        # The path printed by mktemp should itself exist in the filesystem
        tmp_path = path_content.decode().strip()
        self.assertTrue(
            self.fs.exists(tmp_path),
            f"mktemp path {tmp_path!r} should exist in filesystem",
        )

    def test_mktemp_with_suffix_template(self):
        """mktemp with a template creates a file matching the pattern."""
        self.assertShellSuccess(
            self.shell, "mktemp /tmp/test_XXXXXX > /tmp/mktemp_tpl.txt"
        )
        content = self.fs.read_file("/tmp/mktemp_tpl.txt")
        self.assertIsNotNone(content)

    def test_mktemp_directory_flag(self):
        """mktemp -d creates a temporary directory."""
        self.assertShellSuccess(
            self.shell, "mktemp -d > /tmp/mktemp_dir_path.txt"
        )
        path_content = self.fs.read_file("/tmp/mktemp_dir_path.txt")
        self.assertIsNotNone(path_content)

    def test_mktemp_is_registered(self):
        """The mktemp command is present in the shell's command table."""
        self.assertIn("mktemp", self.shell.commands)


class TestNlCommand(BaseTestCase):
    """Test 54: nl command — number lines of input files."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        # Prepare a simple test file
        self.shell.execute("echo apple > /tmp/nl_in.txt")
        self.shell.execute("echo banana >> /tmp/nl_in.txt")
        self.shell.execute("echo cherry >> /tmp/nl_in.txt")

    def test_nl_numbers_all_lines(self):
        """nl numbers each non-empty line."""
        self.assertShellSuccess(
            self.shell, "nl /tmp/nl_in.txt > /tmp/nl_out.txt"
        )
        content = self.fs.read_file("/tmp/nl_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"apple", content)
        self.assertIn(b"banana", content)
        self.assertIn(b"cherry", content)
        # Line numbers should appear
        self.assertIn(b"1", content)

    def test_nl_output_has_correct_line_count(self):
        """nl produces the same number of lines as the input."""
        self.assertShellSuccess(
            self.shell, "nl /tmp/nl_in.txt > /tmp/nl_count.txt"
        )
        content = self.fs.read_file("/tmp/nl_count.txt")
        lines = [l for l in content.decode().splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)

    def test_nl_missing_file_fails(self):
        """nl on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, "nl /tmp/nl_no_such_file.txt")

    def test_nl_is_registered(self):
        """The nl command is present in the shell's command table."""
        self.assertIn("nl", self.shell.commands)


class TestOdXxdCommands(BaseTestCase):
    """Test 55: od/xxd commands — hex dump of files."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        # Prepare a small binary-friendly test file
        self.fs.create_file("/tmp/od_in.txt", b"ABC\n")

    def test_od_produces_output(self):
        """od on a file produces non-empty output."""
        self.assertShellSuccess(
            self.shell, "od /tmp/od_in.txt > /tmp/od_out.txt"
        )
        content = self.fs.read_file("/tmp/od_out.txt")
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 0)

    def test_od_hex_flag(self):
        """od -x outputs hexadecimal representation."""
        self.assertShellSuccess(
            self.shell, "od -x /tmp/od_in.txt > /tmp/od_hex.txt"
        )
        content = self.fs.read_file("/tmp/od_hex.txt")
        self.assertIsNotNone(content)

    def test_od_is_registered(self):
        """The od command is present in the shell's command table."""
        self.assertIn("od", self.shell.commands)

    def test_xxd_produces_output(self):
        """xxd on a file produces non-empty output."""
        self.assertShellSuccess(
            self.shell, "xxd /tmp/od_in.txt > /tmp/xxd_out.txt"
        )
        content = self.fs.read_file("/tmp/xxd_out.txt")
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 0)

    def test_xxd_is_registered(self):
        """The xxd command is present in the shell's command table."""
        self.assertIn("xxd", self.shell.commands)

    def test_od_missing_file_fails(self):
        """od on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, "od /tmp/od_no_such_file.bin")


class TestColumnCommand(BaseTestCase):
    """Test 56: column command — format input into aligned columns."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        # Prepare tab-separated input
        self.fs.create_file(
            "/tmp/col_in.txt",
            b"name\tage\tcity\nalice\t30\tNYC\nbob\t25\tLA\n",
        )

    def test_column_formats_output(self):
        """column produces non-empty, aligned output."""
        self.assertShellSuccess(
            self.shell, "column -t /tmp/col_in.txt > /tmp/col_out.txt"
        )
        content = self.fs.read_file("/tmp/col_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"alice", content)
        self.assertIn(b"bob", content)

    def test_column_preserves_all_data(self):
        """column output contains all fields from input."""
        self.assertShellSuccess(
            self.shell, "column -t /tmp/col_in.txt > /tmp/col_data.txt"
        )
        content = self.fs.read_file("/tmp/col_data.txt")
        for field in [b"name", b"age", b"city", b"alice", b"30", b"NYC"]:
            self.assertIn(field, content)

    def test_column_is_registered(self):
        """The column command is present in the shell's command table."""
        self.assertIn("column", self.shell.commands)

    def test_column_missing_file_fails(self):
        """column on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, "column -t /tmp/col_no_such.txt")


if __name__ == "__main__":
    unittest.main()
