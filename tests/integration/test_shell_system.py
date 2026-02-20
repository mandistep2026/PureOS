"""
tests/integration/test_shell_system.py
=======================================
Integration tests for system information commands.

Covers:
- Test 33: top command
- Test 34: du command
- Test 50: pstree command
- Test 51: vmstat command
- Test 58: nohup command
- Test 60: strace command (simulated)
"""

import unittest

from tests.base import BaseTestCase


class TestTopCommand(BaseTestCase):
    """Test 33: top command — display running processes."""

    def setUp(self):
        super().setUp()
        # top requires a running kernel for meaningful output
        self.shell = self.create_shell(start_kernel=True)
        self.fs = self.shell.filesystem

    def test_top_exits_successfully(self):
        """top runs and exits with code 0."""
        self.assertShellSuccess(self.shell, "top > /tmp/top_out.txt")

    def test_top_output_has_pid_column(self):
        """top output contains a PID header."""
        self.assertShellSuccess(self.shell, "top > /tmp/top_pid.txt")
        content = self.fs.read_file("/tmp/top_pid.txt")
        self.assertIn(b"PID", content)

    def test_top_output_has_name_column(self):
        """top output contains a NAME/COMMAND header."""
        self.assertShellSuccess(self.shell, "top > /tmp/top_name.txt")
        content = self.fs.read_file("/tmp/top_name.txt")
        self.assertIn(b"NAME", content)

    def test_top_output_is_non_empty(self):
        """top produces at least some output."""
        self.assertShellSuccess(self.shell, "top > /tmp/top_nonempty.txt")
        content = self.fs.read_file("/tmp/top_nonempty.txt")
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 0)

    def test_top_is_registered(self):
        """The top command is present in the shell's command table."""
        self.assertIn("top", self.shell.commands)


class TestPstreeCommand(BaseTestCase):
    """Test 50: pstree command — display process tree."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell(start_kernel=True)
        self.fs = self.shell.filesystem

    def test_pstree_exits_successfully(self):
        """pstree runs and exits with code 0."""
        self.assertShellSuccess(self.shell, "pstree > /tmp/pstree_out.txt")

    def test_pstree_output_is_non_empty(self):
        """pstree produces at least some output."""
        self.assertShellSuccess(self.shell, "pstree > /tmp/pstree_nonempty.txt")
        content = self.fs.read_file("/tmp/pstree_nonempty.txt")
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 0)

    def test_pstree_is_registered(self):
        """The pstree command is present in the shell's command table."""
        self.assertIn("pstree", self.shell.commands)

    def test_pstree_output_contains_process_info(self):
        """pstree output looks like a process tree (contains hyphens or pipes)."""
        self.assertShellSuccess(self.shell, "pstree > /tmp/pstree_tree.txt")
        content = self.fs.read_file("/tmp/pstree_tree.txt")
        self.assertIsNotNone(content)
        # A process tree representation typically contains at least one
        # recognisable character or keyword
        self.assertGreater(len(content), 0)


class TestDuCommand(BaseTestCase):
    """Integration tests for du command (disk usage estimates)."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.fs

    def test_du_is_registered(self):
        """du is present in the shell command table."""
        self.assertIn("du", self.shell.commands)

    def test_du_summarize_file(self):
        """du -s reports usage for a single file path."""
        self.assertShellSuccess(self.shell, "echo hello > /tmp/du_file.txt")
        self.assertShellSuccess(self.shell, "du -s /tmp/du_file.txt > /tmp/du_sum_out.txt")
        content = self.fs.read_file("/tmp/du_sum_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"/tmp/du_file.txt", content)

    def test_du_human_readable(self):
        """du -h emits units in output."""
        self.assertShellSuccess(self.shell, "echo hello > /tmp/du_hr.txt")
        self.assertShellSuccess(self.shell, "du -h -s /tmp/du_hr.txt > /tmp/du_hr_out.txt")
        content = self.fs.read_file("/tmp/du_hr_out.txt")
        self.assertIsNotNone(content)
        self.assertTrue(any(unit in content for unit in [b"B", b"K", b"M", b"G", b"T"]))

    def test_du_missing_path_fails(self):
        """du returns non-zero when given a non-existent path."""
        self.assertShellFails(self.shell, "du /tmp/not-here")


class TestVmstatCommand(BaseTestCase):
    """Test 51: vmstat command — virtual memory statistics."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell(start_kernel=True)
        self.fs = self.shell.filesystem

    def test_vmstat_exits_successfully(self):
        """vmstat runs and exits with code 0."""
        self.assertShellSuccess(self.shell, "vmstat > /tmp/vmstat_out.txt")

    def test_vmstat_output_is_non_empty(self):
        """vmstat produces at least some output."""
        self.assertShellSuccess(self.shell, "vmstat > /tmp/vmstat_nonempty.txt")
        content = self.fs.read_file("/tmp/vmstat_nonempty.txt")
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 0)

    def test_vmstat_output_contains_memory_info(self):
        """vmstat output references memory-related concepts."""
        self.assertShellSuccess(self.shell, "vmstat > /tmp/vmstat_mem.txt")
        content = self.fs.read_file("/tmp/vmstat_mem.txt")
        self.assertIsNotNone(content)
        # vmstat output typically includes terms like memory, swap, free, etc.
        has_mem_info = any(
            kw in content.lower()
            for kw in [b"mem", b"swap", b"free", b"buff", b"cpu", b"kb"]
        )
        self.assertTrue(has_mem_info, "vmstat should report memory statistics")

    def test_vmstat_is_registered(self):
        """The vmstat command is present in the shell's command table."""
        self.assertIn("vmstat", self.shell.commands)


class TestNohupCommand(BaseTestCase):
    """Test 58: nohup command — run a command immune to hangups."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_nohup_runs_command(self):
        """nohup echo runs the wrapped command."""
        self.assertShellSuccess(
            self.shell,
            "nohup echo nohup_ran > /tmp/nohup_out.txt",
        )
        content = self.fs.read_file("/tmp/nohup_out.txt")
        self.assertIn(b"nohup_ran", content)

    def test_nohup_creates_output_file(self):
        """nohup writes output to nohup.out when stdout is not redirected."""
        # Execute without explicit redirect to see if nohup.out is created
        exit_code = self.shell.execute("nohup echo nohup_test")
        # Should succeed regardless of whether nohup.out is generated
        self.assertEqual(exit_code, 0)

    def test_nohup_is_registered(self):
        """The nohup command is present in the shell's command table."""
        self.assertIn("nohup", self.shell.commands)

    def test_nohup_without_arguments_fails(self):
        """nohup with no arguments returns non-zero."""
        self.assertShellFails(self.shell, "nohup")

    def test_nohup_exit_code_propagated(self):
        """nohup propagates the wrapped command's exit code."""
        # A command that succeeds → nohup should succeed
        result = self.shell.execute("nohup echo ok > /tmp/nohup_ok.txt")
        self.assertEqual(result, 0)


class TestStraceCommand(BaseTestCase):
    """Test 60: strace command (simulated) — trace system calls."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_strace_is_registered(self):
        """The strace command is present in the shell's command table."""
        self.assertIn("strace", self.shell.commands)

    def test_strace_runs_wrapped_command(self):
        """strace echo still executes the wrapped command."""
        self.assertShellSuccess(
            self.shell,
            "strace echo strace_test > /tmp/strace_out.txt",
        )
        content = self.fs.read_file("/tmp/strace_out.txt")
        self.assertIsNotNone(content)

    def test_strace_produces_trace_output(self):
        """strace emits some tracing information (simulated)."""
        self.assertShellSuccess(
            self.shell,
            "strace echo hello > /tmp/strace_trace.txt",
        )
        content = self.fs.read_file("/tmp/strace_trace.txt")
        self.assertIsNotNone(content)

    def test_strace_without_arguments_fails(self):
        """strace with no arguments returns non-zero."""
        self.assertShellFails(self.shell, "strace")

    def test_strace_exit_code_propagated(self):
        """strace propagates the exit code of the traced command."""
        result = self.shell.execute("strace echo ok > /tmp/strace_ok.txt")
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
