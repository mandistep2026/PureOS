"""
tests/unit/test_persistence.py
================================
Unit tests for the :class:`~core.persistence.PersistenceManager` class.

Covers:
- Alias persistence: save/load shell aliases (Test 11 from main.py)
- Filesystem save/load: inodes round-trip through JSON
- User save/load: UserManager.to_dict / from_dict round-trip
- Edge cases: nonexistent state file, state_exists, delete_state
"""

import unittest

from tests.base import BaseTestCase
from core.filesystem import FileSystem
from core.persistence import PersistenceManager
from core.user import UserManager
from shell.shell import Shell
from core.kernel import Kernel


# ---------------------------------------------------------------------------
# Alias persistence
# ---------------------------------------------------------------------------

class TestPersistenceAlias(BaseTestCase):
    """Tests for alias save/load via PersistenceManager (Test 11)."""

    def _make_shell(self, kernel=None, fs=None):
        """Return a minimal Shell instance for persistence testing."""
        if kernel is None:
            kernel = self.create_kernel()
        if fs is None:
            fs = self.create_filesystem()
        return Shell(kernel, fs)

    def test_save_state_returns_true(self):
        """save_state should return True on success."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = self._make_shell(kernel, fs)
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            result = pm.save_state(fs, shell, kernel)
        self.assertTrue(result, "save_state should return True when writing succeeds.")

    def test_load_state_returns_true_when_file_exists(self):
        """load_state should return True when a valid state file exists."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = self._make_shell(kernel, fs)
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)
            result = pm.load_state(fs, shell, kernel)
        self.assertTrue(result, "load_state should return True when state file exists.")

    def test_load_state_returns_false_when_no_file(self):
        """load_state should return False when no state file has been saved yet."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = self._make_shell(kernel, fs)
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            result = pm.load_state(fs, shell, kernel)
        self.assertFalse(
            result,
            "load_state should return False when no state file is present.",
        )

    def test_custom_alias_survives_save_load_cycle(self):
        """A custom alias added before save should be present after load."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = self._make_shell(kernel, fs)
        shell.execute("alias gs='echo status'")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            reloaded_fs = self.create_filesystem()
            reloaded_shell = self._make_shell(kernel, reloaded_fs)
            pm.load_state(reloaded_fs, reloaded_shell, kernel)

        self.assertEqual(
            reloaded_shell.aliases.get("gs"),
            "echo status",
            "Custom alias 'gs' should be present after a save/load cycle.",
        )

    def test_removed_alias_absent_after_save_load_cycle(self):
        """An alias removed before save should not appear after load."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = self._make_shell(kernel, fs)
        shell.execute("unalias ll")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            reloaded_fs = self.create_filesystem()
            reloaded_shell = self._make_shell(kernel, reloaded_fs)
            pm.load_state(reloaded_fs, reloaded_shell, kernel)

        self.assertNotIn(
            "ll",
            reloaded_shell.aliases,
            "Alias 'll' should not be present after being removed and reloaded.",
        )

    def test_multiple_aliases_all_preserved(self):
        """All aliases present at save time should appear after load."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = self._make_shell(kernel, fs)
        shell.execute("alias foo='echo foo'")
        shell.execute("alias bar='echo bar'")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            reloaded_fs = self.create_filesystem()
            reloaded_shell = self._make_shell(kernel, reloaded_fs)
            pm.load_state(reloaded_fs, reloaded_shell, kernel)

        self.assertEqual(reloaded_shell.aliases.get("foo"), "echo foo",
                         "Alias 'foo' should survive a save/load cycle.")
        self.assertEqual(reloaded_shell.aliases.get("bar"), "echo bar",
                         "Alias 'bar' should survive a save/load cycle.")


# ---------------------------------------------------------------------------
# Filesystem save/load
# ---------------------------------------------------------------------------

class TestPersistenceFilesystem(BaseTestCase):
    """Tests for filesystem state round-tripping through PersistenceManager."""

    def test_user_created_file_survives_save_load(self):
        """A file written before save should be readable after load."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = Shell(kernel, fs)
        fs.create_file("/tmp/persist_me.txt", b"persisted content")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            target_fs = FileSystem()
            target_shell = Shell(kernel, target_fs)
            pm.load_state(target_fs, target_shell, kernel)

        content = target_fs.read_file("/tmp/persist_me.txt")
        self.assertEqual(
            content,
            b"persisted content",
            "File content should be identical after a filesystem save/load cycle.",
        )

    def test_user_directory_survives_save_load(self):
        """A directory created before save should exist after load."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = Shell(kernel, fs)
        fs.mkdir("/tmp/myproject")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            target_fs = FileSystem()
            target_shell = Shell(kernel, target_fs)
            pm.load_state(target_fs, target_shell, kernel)

        self.assertTrue(
            target_fs.exists("/tmp/myproject"),
            "User-created directory should exist after a filesystem save/load cycle.",
        )

    def test_current_directory_restored_after_load(self):
        """The working directory at save time should be restored after load."""
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = Shell(kernel, fs)
        fs.change_directory("/tmp")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            target_fs = FileSystem()
            target_shell = Shell(kernel, target_fs)
            pm.load_state(target_fs, target_shell, kernel)

        self.assertEqual(
            target_fs.get_current_directory(),
            "/tmp",
            "Current directory should be restored to '/tmp' after load.",
        )

    def test_file_content_round_trips_binary_data(self):
        """Binary file content should survive a save/load cycle unchanged."""
        binary_data = bytes(range(256))
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = Shell(kernel, fs)
        fs.create_file("/tmp/binary.bin", binary_data)

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            target_fs = FileSystem()
            target_shell = Shell(kernel, target_fs)
            pm.load_state(target_fs, target_shell, kernel)

        result = target_fs.read_file("/tmp/binary.bin")
        self.assertEqual(
            result,
            binary_data,
            "Binary file content should be identical after a save/load cycle.",
        )


# ---------------------------------------------------------------------------
# User save/load
# ---------------------------------------------------------------------------

class TestPersistenceUserManager(BaseTestCase):
    """Tests for UserManager.to_dict / from_dict round-trip."""

    def test_to_dict_contains_users_key(self):
        """to_dict should produce a dict with a 'users' key."""
        um = self.create_user_manager()
        data = um.to_dict()
        self.assertIn("users", data, "to_dict() result should have a 'users' key.")

    def test_to_dict_contains_groups_key(self):
        """to_dict should produce a dict with a 'groups' key."""
        um = self.create_user_manager()
        data = um.to_dict()
        self.assertIn("groups", data, "to_dict() result should have a 'groups' key.")

    def test_to_dict_includes_all_users(self):
        """to_dict should include all users currently in the manager."""
        um = self.create_user_manager()
        um.create_user("roundtrip_user", "pass")
        data = um.to_dict()
        self.assertIn(
            "roundtrip_user",
            data["users"],
            "to_dict() should include the newly created user.",
        )

    def test_from_dict_restores_users(self):
        """from_dict should restore users that were present at serialisation time."""
        fs = self.create_filesystem()
        um = self.create_user_manager(fs)
        um.create_user("serialised_user", "pass")
        data = um.to_dict()

        fs2 = self.create_filesystem()
        um2 = UserManager.__new__(UserManager)
        um2.fs = fs2
        um2.users = {}
        um2.groups = {}
        um2.next_uid = 1000
        um2.next_gid = 1000
        um2.from_dict(data)

        self.assertIn(
            "serialised_user",
            um2.users,
            "from_dict() should restore the serialised user.",
        )

    def test_from_dict_restores_groups(self):
        """from_dict should restore groups that were present at serialisation time."""
        fs = self.create_filesystem()
        um = self.create_user_manager(fs)
        um.create_user("grouptest_user", "pass")
        data = um.to_dict()

        fs2 = self.create_filesystem()
        um2 = UserManager.__new__(UserManager)
        um2.fs = fs2
        um2.users = {}
        um2.groups = {}
        um2.next_uid = 1000
        um2.next_gid = 1000
        um2.from_dict(data)

        self.assertIn(
            "grouptest_user",
            um2.groups,
            "from_dict() should restore the user's primary group.",
        )

    def test_from_dict_restores_uid_counter(self):
        """from_dict should restore the next_uid counter."""
        um = self.create_user_manager()
        um.create_user("uidtest", "pass")
        expected_next_uid = um.next_uid
        data = um.to_dict()

        fs2 = self.create_filesystem()
        um2 = UserManager.__new__(UserManager)
        um2.fs = fs2
        um2.users = {}
        um2.groups = {}
        um2.next_uid = 1000
        um2.next_gid = 1000
        um2.from_dict(data)

        self.assertEqual(
            um2.next_uid,
            expected_next_uid,
            "from_dict() should restore the next_uid counter.",
        )


# ---------------------------------------------------------------------------
# PersistenceManager meta-operations
# ---------------------------------------------------------------------------

class TestPersistenceManagerMeta(BaseTestCase):
    """Tests for state_exists, delete_state, and get_state_info."""

    def _make_components(self):
        kernel = self.create_kernel()
        fs = self.create_filesystem()
        shell = Shell(kernel, fs)
        return kernel, fs, shell

    def test_state_exists_false_before_save(self):
        """state_exists should return False before any state has been saved."""
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            self.assertFalse(
                pm.state_exists(),
                "state_exists should be False before the first save.",
            )

    def test_state_exists_true_after_save(self):
        """state_exists should return True after a successful save."""
        kernel, fs, shell = self._make_components()
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)
            self.assertTrue(
                pm.state_exists(),
                "state_exists should be True after save_state completes.",
            )

    def test_delete_state_removes_file(self):
        """delete_state should make state_exists return False again."""
        kernel, fs, shell = self._make_components()
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)
            pm.delete_state()
            self.assertFalse(
                pm.state_exists(),
                "state_exists should be False after delete_state.",
            )

    def test_delete_state_returns_true(self):
        """delete_state should return True whether or not a file existed."""
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            result = pm.delete_state()
            self.assertTrue(result, "delete_state should return True.")

    def test_get_state_info_returns_none_when_no_file(self):
        """get_state_info should return None when no state file exists."""
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            result = pm.get_state_info()
            self.assertIsNone(
                result,
                "get_state_info should return None when no state file is present.",
            )

    def test_get_state_info_returns_dict_after_save(self):
        """get_state_info should return a dict with expected keys after save."""
        kernel, fs, shell = self._make_components()
        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)
            info = pm.get_state_info()
        self.assertIsNotNone(info, "get_state_info should return a dict after save.")
        for key in ("version", "files", "directories", "total_items"):
            self.assertIn(key, info, f"get_state_info dict should contain '{key}'.")

    def test_environment_survives_save_load(self):
        """Shell environment variables set before save should persist after load."""
        kernel, fs, shell = self._make_components()
        shell.environment["MY_VAR"] = "hello_world"

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            target_fs = self.create_filesystem()
            target_shell = Shell(kernel, target_fs)
            pm.load_state(target_fs, target_shell, kernel)

        self.assertEqual(
            target_shell.environment.get("MY_VAR"),
            "hello_world",
            "Environment variable MY_VAR should survive a save/load cycle.",
        )

    def test_history_survives_save_load(self):
        """Shell command history entries should be restored after load."""
        kernel, fs, shell = self._make_components()
        shell.execute("echo hello")
        shell.execute("echo world")

        with self.temporary_state_dir() as state_dir:
            pm = PersistenceManager(state_dir=state_dir)
            pm.save_state(fs, shell, kernel)

            target_fs = self.create_filesystem()
            target_shell = Shell(kernel, target_fs)
            pm.load_state(target_fs, target_shell, kernel)

        self.assertGreater(
            len(target_shell.history),
            0,
            "Shell history should be non-empty after a save/load cycle.",
        )


if __name__ == "__main__":
    unittest.main()
