"""
tests/base.py
=============
Base test case class providing shared fixtures, factory methods, and assertion
helpers for all PureOS tests.

Every test class in the suite should inherit from ``BaseTestCase`` instead of
``unittest.TestCase`` directly so that it automatically gets:

* Fresh, fully-isolated component instances for every test via the factory
  methods.
* A temporary-directory context manager suitable for persistence tests.
* Extra assertion helpers that map naturally onto PureOS concepts.
* Guaranteed teardown that stops any kernel thread started during the test.
"""

import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from typing import Optional

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so that ``import core.*`` and
# ``import shell.*`` work regardless of how the tests are invoked.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.kernel import Kernel
from core.filesystem import FileSystem
from core.user import UserManager
from shell.shell import Shell


class BaseTestCase(unittest.TestCase):
    """Base class for all PureOS unit and integration tests.

    Provides factory methods that create fresh, pre-wired component instances
    and common assertion helpers that express intent clearly without boiler-
    plate.

    Lifecycle
    ---------
    ``setUp`` is intentionally left empty so subclasses may override it freely.
    ``tearDown`` stops any kernel thread that was created through
    ``create_kernel(start=True)`` so threads never leak between tests.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setUp(self) -> None:
        """Prepare a clean slate before each test.

        Subclasses that override ``setUp`` *must* call ``super().setUp()``
        first to ensure the kernel-tracking list is always initialised.
        """
        # Track kernels started by factory methods so we can stop them.
        self._started_kernels: list = []

    def tearDown(self) -> None:
        """Stop any running kernels and release resources after each test.

        Subclasses that override ``tearDown`` *must* call
        ``super().tearDown()`` to guarantee kernel threads are cleaned up.
        """
        for kernel in self._started_kernels:
            try:
                kernel.stop()
            except Exception:
                pass
        self._started_kernels.clear()

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    def create_kernel(self, *, start: bool = False) -> Kernel:
        """Create and return a fresh :class:`~core.kernel.Kernel` instance.

        Parameters
        ----------
        start:
            When *True* the kernel scheduler thread is started immediately.
            The kernel will be stopped automatically in :meth:`tearDown`.

        Returns
        -------
        Kernel
            A newly-constructed kernel instance with no processes.
        """
        kernel = Kernel()
        if start:
            kernel.start()
            self._started_kernels.append(kernel)
        return kernel

    def create_filesystem(self) -> FileSystem:
        """Create and return a fresh :class:`~core.filesystem.FileSystem`.

        The returned filesystem has the standard directory tree already
        initialised (``/bin``, ``/etc``, ``/home``, ``/tmp``, ``/var``, …)
        exactly as it would be at boot time.

        Returns
        -------
        FileSystem
            A newly-constructed, fully-initialised in-memory filesystem.
        """
        return FileSystem()

    def create_user_manager(self, filesystem: Optional[FileSystem] = None) -> UserManager:
        """Create and return a :class:`~core.user.UserManager` instance.

        If no *filesystem* is provided one is created automatically so the
        caller does not have to construct one solely for this purpose.

        Parameters
        ----------
        filesystem:
            The filesystem the user-manager will read and write ``/etc``
            files to.  When *None* a fresh :class:`FileSystem` is created.

        Returns
        -------
        UserManager
            A user-manager pre-seeded with the ``root`` user and the default
            ``alice`` account (password ``password123``).
        """
        if filesystem is None:
            filesystem = self.create_filesystem()
        return UserManager(filesystem)

    def create_shell(
        self,
        kernel: Optional[Kernel] = None,
        filesystem: Optional[FileSystem] = None,
        user_manager: Optional[UserManager] = None,
        *,
        start_kernel: bool = False,
    ) -> Shell:
        """Create and return a fully-wired :class:`~shell.shell.Shell`.

        Missing components are constructed automatically so you only need to
        supply the instances you care about in a particular test.

        Parameters
        ----------
        kernel:
            Kernel to attach.  Created fresh when *None*.
        filesystem:
            Filesystem to attach.  Created fresh when *None*.
        user_manager:
            User-manager to attach.  Created fresh (sharing *filesystem*)
            when *None*.
        start_kernel:
            When *True* the kernel scheduler thread is started and the kernel
            will be stopped automatically in :meth:`tearDown`.

        Returns
        -------
        Shell
            A shell with all built-in commands registered and environment
            variables initialised.
        """
        if kernel is None:
            kernel = self.create_kernel(start=start_kernel)
        elif start_kernel:
            kernel.start()
            self._started_kernels.append(kernel)

        if filesystem is None:
            filesystem = self.create_filesystem()

        if user_manager is None:
            user_manager = UserManager(filesystem)

        return Shell(kernel, filesystem, user_manager=user_manager)

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    @contextmanager
    def temporary_state_dir(self):
        """Context manager that yields a temporary directory path.

        Intended for persistence tests that need to write and read state files
        without polluting ``~/.pureos`` or the project directory.

        Usage
        -----
        ::

            with self.temporary_state_dir() as state_dir:
                pm = PersistenceManager(state_dir=state_dir)
                pm.save_state(fs, shell, kernel)
                ...

        The directory and all its contents are deleted when the ``with`` block
        exits, even if an exception is raised.
        """
        with tempfile.TemporaryDirectory(prefix="pureos_test_") as tmpdir:
            yield tmpdir

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def assertFileExists(self, filesystem: FileSystem, path: str, msg: str = None) -> None:
        """Assert that *path* exists as a regular file in *filesystem*.

        Parameters
        ----------
        filesystem:
            The :class:`FileSystem` to inspect.
        path:
            Absolute path to check.
        msg:
            Optional custom failure message.
        """
        if not filesystem.exists(path):
            self.fail(msg or f"Expected file to exist: {path}")
        if not filesystem.is_file(path):
            self.fail(msg or f"Path exists but is not a regular file: {path}")

    def assertFileNotExists(self, filesystem: FileSystem, path: str, msg: str = None) -> None:
        """Assert that *path* does **not** exist in *filesystem*.

        Parameters
        ----------
        filesystem:
            The :class:`FileSystem` to inspect.
        path:
            Absolute path that should be absent.
        msg:
            Optional custom failure message.
        """
        if filesystem.exists(path):
            self.fail(msg or f"Expected path to not exist, but it does: {path}")

    def assertDirectoryExists(self, filesystem: FileSystem, path: str, msg: str = None) -> None:
        """Assert that *path* exists as a directory in *filesystem*.

        Parameters
        ----------
        filesystem:
            The :class:`FileSystem` to inspect.
        path:
            Absolute path to check.
        msg:
            Optional custom failure message.
        """
        if not filesystem.exists(path):
            self.fail(msg or f"Expected directory to exist: {path}")
        if not filesystem.is_directory(path):
            self.fail(msg or f"Path exists but is not a directory: {path}")

    def assertFileContains(
        self,
        filesystem: FileSystem,
        path: str,
        expected: bytes,
        msg: str = None,
    ) -> None:
        """Assert that the file at *path* contains *expected* as a substring.

        Parameters
        ----------
        filesystem:
            The :class:`FileSystem` to read from.
        path:
            Absolute path of the file to inspect.
        expected:
            Byte string that must appear somewhere in the file's content.
        msg:
            Optional custom failure message.
        """
        content = filesystem.read_file(path)
        self.assertIsNotNone(
            content,
            msg or f"File does not exist or could not be read: {path}",
        )
        if expected not in content:
            self.fail(
                msg
                or (
                    f"File {path!r} does not contain {expected!r}.\n"
                    f"Actual content: {content!r}"
                )
            )

    def assertFileEquals(
        self,
        filesystem: FileSystem,
        path: str,
        expected: bytes,
        msg: str = None,
    ) -> None:
        """Assert that the file at *path* has exactly *expected* as its content.

        Parameters
        ----------
        filesystem:
            The :class:`FileSystem` to read from.
        path:
            Absolute path of the file to inspect.
        expected:
            Exact byte content the file must have.
        msg:
            Optional custom failure message.
        """
        content = filesystem.read_file(path)
        self.assertIsNotNone(
            content,
            msg or f"File does not exist or could not be read: {path}",
        )
        self.assertEqual(
            content,
            expected,
            msg or f"File {path!r} content mismatch.",
        )

    def assertShellSuccess(self, shell: Shell, command: str, msg: str = None) -> None:
        """Assert that *command* exits with code ``0`` when run in *shell*.

        Parameters
        ----------
        shell:
            The :class:`Shell` instance to execute the command in.
        command:
            Shell command string to execute.
        msg:
            Optional custom failure message.
        """
        exit_code = shell.execute(command)
        self.assertEqual(
            exit_code,
            0,
            msg or f"Command {command!r} exited with {exit_code}, expected 0.",
        )

    def assertShellFails(self, shell: Shell, command: str, msg: str = None) -> None:
        """Assert that *command* exits with a **non-zero** code in *shell*.

        Parameters
        ----------
        shell:
            The :class:`Shell` instance to execute the command in.
        command:
            Shell command string to execute.
        msg:
            Optional custom failure message.
        """
        exit_code = shell.execute(command)
        self.assertNotEqual(
            exit_code,
            0,
            msg or f"Command {command!r} was expected to fail but exited 0.",
        )

    def assertUserExists(self, user_manager: UserManager, username: str, msg: str = None) -> None:
        """Assert that *username* is a known user in *user_manager*.

        Parameters
        ----------
        user_manager:
            The :class:`UserManager` to query.
        username:
            Name of the user that should exist.
        msg:
            Optional custom failure message.
        """
        self.assertTrue(
            user_manager.user_exists(username),
            msg or f"Expected user {username!r} to exist.",
        )

    def assertUserNotExists(self, user_manager: UserManager, username: str, msg: str = None) -> None:
        """Assert that *username* is **not** present in *user_manager*.

        Parameters
        ----------
        user_manager:
            The :class:`UserManager` to query.
        username:
            Name of the user that should be absent.
        msg:
            Optional custom failure message.
        """
        self.assertFalse(
            user_manager.user_exists(username),
            msg or f"Expected user {username!r} to not exist.",
        )

    def assertProcessExists(self, kernel: Kernel, pid: int, msg: str = None) -> None:
        """Assert that a process with *pid* is registered in *kernel*.

        Parameters
        ----------
        kernel:
            The :class:`Kernel` whose process table to inspect.
        pid:
            Process ID that should be present.
        msg:
            Optional custom failure message.
        """
        proc = kernel.get_process(pid)
        self.assertIsNotNone(
            proc,
            msg or f"Expected process with PID {pid} to exist in kernel.",
        )
