"""
tests/fixtures.py
=================
Shared, reusable test fixtures for PureOS tests.

This module provides factory functions and pre-configured component states
that are commonly needed across multiple test modules.  Fixtures are plain
functions (not classes) so they compose cleanly and remain easy to reason
about.

All fixture functions are **pure** in the sense that each call returns a
brand-new object; no state is shared between calls unless the caller
explicitly passes the same object into multiple fixtures.

Typical usage inside a ``BaseTestCase`` subclass
-------------------------------------------------
::

    from tests.fixtures import (
        standard_filesystem,
        minimal_kernel,
        preconfigured_shell,
        test_users,
    )

    class MyTest(BaseTestCase):
        def setUp(self):
            super().setUp()
            self.fs = standard_filesystem()
            self.kernel = minimal_kernel()
            self.shell = preconfigured_shell(self.kernel, self.fs)
"""

import os
import sys

# ---------------------------------------------------------------------------
# Ensure the project root is importable regardless of invocation method.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.kernel import Kernel
from core.filesystem import FileSystem
from core.user import UserManager
from shell.shell import Shell


# ---------------------------------------------------------------------------
# Filesystem fixtures
# ---------------------------------------------------------------------------

def standard_filesystem() -> FileSystem:
    """Return a freshly initialised :class:`~core.filesystem.FileSystem`.

    The filesystem is identical to what PureOS creates at boot: the full
    standard directory tree (``/bin``, ``/etc``, ``/home``, ``/tmp``,
    ``/var``, ``/proc``, …) and all default system files (``/etc/hostname``,
    ``/etc/motd``, ``/etc/os-release``, ``/proc/version``, …).

    Returns
    -------
    FileSystem
        A clean, boot-time filesystem with no user data.
    """
    return FileSystem()


def filesystem_with_test_files() -> FileSystem:
    """Return a filesystem pre-populated with a small set of test files.

    The extra files live under ``/tmp/testdata/`` and are intended for tests
    that need to read, write, or search files without first setting them up
    manually.

    Layout::

        /tmp/testdata/
            hello.txt       — b"Hello, PureOS!\\n"
            numbers.txt     — b"one\\ntwo\\nthree\\n"
            empty.txt       — b""
            subdir/
                nested.txt  — b"nested content\\n"

    Returns
    -------
    FileSystem
        Standard filesystem plus the ``/tmp/testdata/`` tree.
    """
    fs = FileSystem()

    fs.mkdir("/tmp/testdata")
    fs.mkdir("/tmp/testdata/subdir")
    fs.create_file("/tmp/testdata/hello.txt", b"Hello, PureOS!\n")
    fs.create_file("/tmp/testdata/numbers.txt", b"one\ntwo\nthree\n")
    fs.create_file("/tmp/testdata/empty.txt", b"")
    fs.create_file("/tmp/testdata/subdir/nested.txt", b"nested content\n")

    return fs


# ---------------------------------------------------------------------------
# Kernel fixtures
# ---------------------------------------------------------------------------

def minimal_kernel(*, start: bool = False) -> Kernel:
    """Return a freshly constructed :class:`~core.kernel.Kernel`.

    Parameters
    ----------
    start:
        When *True* the kernel scheduler thread is started immediately.
        **The caller is responsible for calling** ``kernel.stop()`` **when
        the kernel is no longer needed** (or use
        :meth:`~tests.base.BaseTestCase.create_kernel` which does this
        automatically via ``tearDown``).

    Returns
    -------
    Kernel
        A kernel with an empty process table and zeroed performance counters.
    """
    kernel = Kernel()
    if start:
        kernel.start()
    return kernel


# ---------------------------------------------------------------------------
# User-manager fixtures
# ---------------------------------------------------------------------------

_TEST_USERS = [
    # (username, password, home_dir)
    ("testuser", "testpass1", "/home/testuser"),
    ("devuser",  "devpass2",  "/home/devuser"),
    ("readonly", "ropass3",   "/home/readonly"),
]


def test_users(filesystem: FileSystem = None) -> UserManager:
    """Return a :class:`~core.user.UserManager` with pre-configured test accounts.

    The manager always contains:

    * ``root`` — system super-user (no password required for tests).
    * ``alice`` — default user created by ``UserManager._initialize_system``
      (password ``password123``).
    * ``testuser`` (password ``testpass1``) — generic test subject.
    * ``devuser``  (password ``devpass2``) — second test subject for
      multi-user tests.
    * ``readonly`` (password ``ropass3``) — third test subject.

    Parameters
    ----------
    filesystem:
        Filesystem the manager will operate on.  A fresh one is created when
        *None* is supplied.

    Returns
    -------
    UserManager
        A user-manager with the accounts listed above already created.

    Notes
    -----
    *Do not use production-strength passwords here.*  These credentials are
    intentionally short and human-readable so tests are easy to read and fast
    to run (PBKDF2 iterations still apply, but the values are predictable).
    """
    if filesystem is None:
        filesystem = standard_filesystem()

    um = UserManager(filesystem)

    for username, password, home_dir in _TEST_USERS:
        if not um.user_exists(username):
            um.create_user(username, password, home_dir=home_dir)

    return um


def minimal_user_manager(filesystem: FileSystem = None) -> UserManager:
    """Return a :class:`~core.user.UserManager` with only the system defaults.

    Contains only ``root`` and ``alice`` — the two accounts created by
    ``UserManager._initialize_system``.  Use this when you need a lean
    manager and the extra test accounts would be a distraction.

    Parameters
    ----------
    filesystem:
        Filesystem the manager will operate on.  Created fresh when *None*.

    Returns
    -------
    UserManager
        Manager with default system accounts only.
    """
    if filesystem is None:
        filesystem = standard_filesystem()
    return UserManager(filesystem)


# ---------------------------------------------------------------------------
# Shell fixtures
# ---------------------------------------------------------------------------

def preconfigured_shell(
    kernel: Kernel = None,
    filesystem: FileSystem = None,
    user_manager: UserManager = None,
) -> Shell:
    """Return a :class:`~shell.shell.Shell` with sensible defaults for testing.

    All missing components are created automatically.  The shell has the
    standard environment (``PATH``, ``HOME``, ``USER``, …) and all built-in
    commands registered, mirroring a freshly-booted interactive session.

    The shell environment is augmented with ``TEST_MODE=1`` so that shell
    scripts and commands can detect they are running under tests if needed.

    Parameters
    ----------
    kernel:
        Kernel to attach.  Created fresh (not started) when *None*.
    filesystem:
        Filesystem to attach.  Created fresh when *None*.
    user_manager:
        User-manager to attach.  Created fresh when *None*.

    Returns
    -------
    Shell
        A fully registered shell instance ready to accept commands.
    """
    if kernel is None:
        kernel = Kernel()
    if filesystem is None:
        filesystem = standard_filesystem()
    if user_manager is None:
        user_manager = UserManager(filesystem)

    shell = Shell(kernel, filesystem, user_manager=user_manager)
    shell.environment["TEST_MODE"] = "1"
    return shell


def shell_with_test_files(
    kernel: Kernel = None,
) -> Shell:
    """Return a shell backed by :func:`filesystem_with_test_files`.

    Convenience wrapper for tests that need the pre-populated ``/tmp/testdata``
    tree without building it by hand.

    Parameters
    ----------
    kernel:
        Kernel to attach.  Created fresh (not started) when *None*.

    Returns
    -------
    Shell
        Shell instance backed by a filesystem that already contains test data.
    """
    if kernel is None:
        kernel = Kernel()
    fs = filesystem_with_test_files()
    um = UserManager(fs)
    shell = Shell(kernel, fs, user_manager=um)
    shell.environment["TEST_MODE"] = "1"
    return shell


# ---------------------------------------------------------------------------
# Reusable kernel configuration snippets
# ---------------------------------------------------------------------------

#: Default memory size used when constructing kernels for tests (16 MB).
#: Smaller than the production default (100 MB) to keep tests lean.
TEST_KERNEL_MEMORY = 16 * 1024 * 1024


def kernel_config() -> dict:
    """Return a dictionary of recommended kernel constructor kwargs for tests.

    Currently the :class:`~core.kernel.Kernel` constructor takes no arguments,
    so this returns an empty dict.  It exists as a stable hook for the future:
    if configurable parameters are added, tests can call ``kernel_config()``
    to pick up sensible defaults without each test hard-coding values.

    Returns
    -------
    dict
        Keyword arguments to pass to ``Kernel(**kernel_config())``.
    """
    return {}


# ---------------------------------------------------------------------------
# Standard filesystem state snapshot (read-only reference data)
# ---------------------------------------------------------------------------

#: Directories that must exist in every freshly-initialised FileSystem.
STANDARD_DIRECTORIES = [
    "/",
    "/bin",
    "/etc",
    "/home",
    "/tmp",
    "/var",
    "/var/log",
    "/proc",
    "/proc/net",
    "/dev",
    "/root",
    "/usr",
    "/usr/bin",
    "/usr/local",
]

#: Files that must exist in every freshly-initialised FileSystem.
STANDARD_FILES = [
    "/etc/hostname",
    "/etc/motd",
    "/etc/shells",
    "/etc/os-release",
    "/etc/passwd",
    "/etc/group",
    "/proc/version",
    "/proc/uptime",
    "/proc/net/dev",
]

#: Default aliases present in every freshly-constructed Shell.
DEFAULT_ALIASES = {
    "ll": "ls -la",
    "la": "ls -a",
    "l":  "ls -CF",
}

#: Default environment variables present in every freshly-constructed Shell.
DEFAULT_ENVIRONMENT_KEYS = [
    "PATH",
    "HOME",
    "USER",
    "HOSTNAME",
    "SHELL",
    "TERM",
    "PS1",
    "PS2",
]
