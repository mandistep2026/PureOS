"""
tests/unit/test_kernel.py
==========================
Unit tests for the :class:`~core.kernel.Kernel` class.

Covers:
- Kernel initialisation and start/stop lifecycle (Test 1)
- Process creation and positive PID assignment (Test 3)
- Uptime tracking after start (Test 9)
- Signal system: SIGSTOP, SIGCONT, SIGKILL (Test 48)
"""

import time
import unittest

from tests.base import BaseTestCase
from core.kernel import Kernel, ProcessState, Signal


# ---------------------------------------------------------------------------
# Initialisation and lifecycle
# ---------------------------------------------------------------------------

class TestKernelInit(BaseTestCase):
    """Tests for Kernel construction and the start/stop lifecycle (Test 1)."""

    def test_kernel_creates_successfully(self):
        """Kernel() constructor should succeed without raising."""
        kernel = self.create_kernel()
        self.assertIsNotNone(kernel, "Kernel instance must not be None.")

    def test_kernel_starts_without_error(self):
        """kernel.start() should not raise and should set the boot time."""
        kernel = self.create_kernel(start=True)
        self.assertIsNotNone(
            kernel._boot_time,
            "kernel._boot_time should be set after start().",
        )

    def test_kernel_stops_cleanly(self):
        """kernel.stop() should set _shutdown=True and join the thread."""
        kernel = self.create_kernel(start=True)
        kernel.stop()
        self.assertTrue(kernel._shutdown, "kernel._shutdown should be True after stop().")

    def test_kernel_has_empty_process_table_on_init(self):
        """A freshly constructed kernel should have an empty process table."""
        kernel = self.create_kernel()
        self.assertEqual(
            len(kernel.processes),
            0,
            "Process table should be empty on a fresh kernel.",
        )

    def test_kernel_next_pid_starts_at_one(self):
        """next_pid should start at 1 on a fresh kernel."""
        kernel = self.create_kernel()
        self.assertEqual(kernel.next_pid, 1, "next_pid should start at 1.")

    def test_kernel_has_memory_manager(self):
        """Kernel should initialise a MemoryManager."""
        kernel = self.create_kernel()
        self.assertIsNotNone(kernel.memory_manager, "Kernel must have a memory_manager.")

    def test_kernel_has_scheduler(self):
        """Kernel should initialise a Scheduler."""
        kernel = self.create_kernel()
        self.assertIsNotNone(kernel.scheduler, "Kernel must have a scheduler.")

    def test_get_system_info_returns_dict(self):
        """get_system_info() should return a dict with expected keys."""
        kernel = self.create_kernel(start=True)
        info = kernel.get_system_info()
        for key in ("total_memory", "free_memory", "process_count", "uptime_seconds"):
            self.assertIn(key, info, f"get_system_info() dict should contain '{key}'.")


# ---------------------------------------------------------------------------
# Process creation
# ---------------------------------------------------------------------------

class TestKernelProcessCreation(BaseTestCase):
    """Tests for create_process and PID assignment (Test 3)."""

    def test_create_process_returns_positive_pid(self):
        """create_process should return a positive integer PID."""
        kernel = self.create_kernel(start=True)
        pid = kernel.create_process("test_proc", lambda: None)
        self.assertGreater(pid, 0, "create_process should return a positive PID.")

    def test_create_process_increments_pid(self):
        """Each successive create_process call should yield a higher PID."""
        kernel = self.create_kernel(start=True)
        pid1 = kernel.create_process("proc1", lambda: None)
        pid2 = kernel.create_process("proc2", lambda: None)
        self.assertGreater(pid2, pid1, "PID should increase with each new process.")

    def test_created_process_appears_in_process_table(self):
        """A newly created process should be retrievable from the kernel."""
        kernel = self.create_kernel(start=True)
        pid = kernel.create_process("visible", lambda: None)
        self.assertProcessExists(kernel, pid)

    def test_create_process_sets_process_name(self):
        """The Process object should carry the name supplied to create_process."""
        kernel = self.create_kernel(start=True)
        pid = kernel.create_process("my_worker", lambda: None)
        proc = kernel.get_process(pid)
        self.assertEqual(
            proc.name,
            "my_worker",
            "Process name should match the name passed to create_process.",
        )

    def test_create_process_executes_callable(self):
        """The callable passed to create_process should be executed."""
        results = []
        kernel = self.create_kernel(start=True)
        kernel.create_process("runner", lambda: results.append(42))
        time.sleep(0.3)  # allow the scheduler to run the process
        self.assertIn(42, results, "The process callable should have been executed.")

    def test_get_process_returns_none_for_unknown_pid(self):
        """get_process with an unknown PID should return None."""
        kernel = self.create_kernel()
        result = kernel.get_process(99999)
        self.assertIsNone(result, "get_process should return None for an unknown PID.")

    def test_list_processes_returns_list(self):
        """list_processes should return a list (empty or not)."""
        kernel = self.create_kernel()
        procs = kernel.list_processes()
        self.assertIsInstance(procs, list, "list_processes should return a list.")

    def test_terminate_process_marks_terminated(self):
        """terminate_process should set the process state to TERMINATED."""
        kernel = self.create_kernel(start=True)
        pid = kernel.create_process("to_kill", lambda: time.sleep(10))
        time.sleep(0.05)
        result = kernel.terminate_process(pid)
        self.assertTrue(result, "terminate_process should return True on success.")
        proc = kernel.get_process(pid)
        self.assertEqual(
            proc.state,
            ProcessState.TERMINATED,
            "Process state should be TERMINATED after terminate_process.",
        )


# ---------------------------------------------------------------------------
# Uptime tracking
# ---------------------------------------------------------------------------

class TestKernelUptime(BaseTestCase):
    """Tests for uptime tracking after the kernel is started (Test 9)."""

    def test_uptime_is_zero_before_start(self):
        """get_uptime() should return 0.0 before the kernel is started."""
        kernel = self.create_kernel()
        uptime = kernel.get_uptime()
        self.assertEqual(uptime, 0.0, "Uptime should be 0.0 before start().")

    def test_uptime_is_positive_after_start(self):
        """get_uptime() should return a positive value after the kernel starts."""
        kernel = self.create_kernel(start=True)
        time.sleep(0.05)
        uptime = kernel.get_uptime()
        self.assertGreater(uptime, 0.0, "Uptime should be positive after start().")

    def test_system_info_uptime_positive(self):
        """get_system_info()['uptime_seconds'] should be positive after start."""
        kernel = self.create_kernel(start=True)
        time.sleep(0.05)
        info = kernel.get_system_info()
        self.assertGreater(
            info["uptime_seconds"],
            0.0,
            "get_system_info()['uptime_seconds'] should be > 0 after start().",
        )

    def test_uptime_grows_over_time(self):
        """Uptime reported at two points in time should increase."""
        kernel = self.create_kernel(start=True)
        time.sleep(0.05)
        uptime_a = kernel.get_uptime()
        time.sleep(0.05)
        uptime_b = kernel.get_uptime()
        self.assertGreater(
            uptime_b,
            uptime_a,
            "Uptime should increase between two successive calls.",
        )


# ---------------------------------------------------------------------------
# Signal system
# ---------------------------------------------------------------------------

class TestKernelSignals(BaseTestCase):
    """Tests for the kernel signal system: SIGSTOP, SIGCONT, SIGKILL (Test 48)."""

    def setUp(self):
        super().setUp()
        self.kernel = self.create_kernel(start=True)
        # Create a long-running process to send signals to
        self.pid = self.kernel.create_process(
            "signal_target",
            lambda: time.sleep(60),
        )
        time.sleep(0.05)  # allow scheduler to pick it up

    def test_sigstop_suspends_process(self):
        """SIGSTOP should transition a running/ready process to STOPPED state."""
        result = self.kernel.send_signal(self.pid, Signal.SIGSTOP)
        self.assertTrue(result, "send_signal(SIGSTOP) should return True.")
        proc = self.kernel.get_process(self.pid)
        self.assertEqual(
            proc.state,
            ProcessState.STOPPED,
            "Process should be in STOPPED state after SIGSTOP.",
        )

    def test_sigcont_resumes_stopped_process(self):
        """SIGCONT should transition a STOPPED process back to READY."""
        self.kernel.send_signal(self.pid, Signal.SIGSTOP)
        result = self.kernel.send_signal(self.pid, Signal.SIGCONT)
        self.assertTrue(result, "send_signal(SIGCONT) should return True.")
        proc = self.kernel.get_process(self.pid)
        self.assertEqual(
            proc.state,
            ProcessState.READY,
            "Process should be READY after SIGCONT.",
        )

    def test_sigkill_terminates_process(self):
        """SIGKILL should set the process state to TERMINATED."""
        result = self.kernel.send_signal(self.pid, Signal.SIGKILL)
        self.assertTrue(result, "send_signal(SIGKILL) should return True.")
        proc = self.kernel.get_process(self.pid)
        self.assertEqual(
            proc.state,
            ProcessState.TERMINATED,
            "Process should be TERMINATED after SIGKILL.",
        )

    def test_send_signal_returns_false_for_unknown_pid(self):
        """send_signal to an unknown PID should return False."""
        result = self.kernel.send_signal(99999, Signal.SIGKILL)
        self.assertFalse(result, "send_signal should return False for an unknown PID.")

    def test_sigusr1_queued_as_pending_signal(self):
        """Non-lifecycle signals (e.g. SIGUSR1) without a handler should be queued."""
        self.kernel.send_signal(self.pid, Signal.SIGUSR1)
        pending = self.kernel.get_pending_signals(self.pid)
        self.assertIn(
            Signal.SIGUSR1.value,
            pending,
            "SIGUSR1 should appear in the pending signal queue.",
        )

    def test_register_signal_handler_called_on_signal(self):
        """A registered signal handler should be invoked when the signal is sent."""
        received = []
        self.kernel.register_signal_handler(
            self.pid,
            Signal.SIGUSR2,
            lambda sig: received.append(sig),
        )
        self.kernel.send_signal(self.pid, Signal.SIGUSR2)
        self.assertIn(
            Signal.SIGUSR2.value,
            received,
            "Registered signal handler should be called with the signal value.",
        )

    def test_suspend_process_stops_running_process(self):
        """suspend_process should transition RUNNING/READY -> STOPPED."""
        result = self.kernel.suspend_process(self.pid)
        self.assertTrue(result, "suspend_process should return True.")
        proc = self.kernel.get_process(self.pid)
        self.assertEqual(
            proc.state,
            ProcessState.STOPPED,
            "Process should be STOPPED after suspend_process.",
        )

    def test_resume_process_readies_stopped_process(self):
        """resume_process should transition STOPPED -> READY."""
        self.kernel.suspend_process(self.pid)
        result = self.kernel.resume_process(self.pid)
        self.assertTrue(result, "resume_process should return True.")
        proc = self.kernel.get_process(self.pid)
        self.assertEqual(
            proc.state,
            ProcessState.READY,
            "Process should be READY after resume_process.",
        )


if __name__ == "__main__":
    unittest.main()
