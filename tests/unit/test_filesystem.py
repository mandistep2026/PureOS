"""
tests/unit/test_filesystem.py
==============================
Unit tests for the :class:`~core.filesystem.FileSystem` class.

Covers:
- Basic CRUD operations: create_file, read_file, write_file, exists, delete_file
- Standard boot-time directory tree (/home, /tmp, /etc, /var, /usr, …)
- Recursive deletion via remove_tree
- System files pre-populated at boot (/etc/passwd, /etc/group, /etc/hostname)
- Symlink creation and inode-level inspection
- Path normalisation (. and .. components)
- chmod / chown at the inode level
"""

import time
import unittest

from tests.base import BaseTestCase
from core.filesystem import FileSystem, FileType, Inode


# ---------------------------------------------------------------------------
# Basic filesystem operations
# ---------------------------------------------------------------------------

class TestFileSystemOperations(BaseTestCase):
    """Tests for the core CRUD API of FileSystem (Test 2 from main.py)."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    # --- exists / root ---

    def test_root_exists_on_init(self):
        """The root directory must exist immediately after construction."""
        self.assertTrue(
            self.fs.exists("/"),
            "Root directory '/' should exist on a fresh FileSystem.",
        )

    # --- mkdir ---

    def test_mkdir_creates_directory(self):
        """mkdir should create a new directory and make it discoverable via exists."""
        result = self.fs.mkdir("/test_dir")
        self.assertTrue(result, "mkdir('/test_dir') should return True.")
        self.assertTrue(
            self.fs.exists("/test_dir"),
            "/test_dir should exist after mkdir.",
        )

    def test_mkdir_returns_false_for_duplicate(self):
        """mkdir on an already-existing path should return False."""
        self.fs.mkdir("/dup_dir")
        result = self.fs.mkdir("/dup_dir")
        self.assertFalse(result, "mkdir on an existing path should return False.")

    def test_mkdir_returns_false_for_missing_parent(self):
        """mkdir without parents=True should fail when the parent is absent."""
        result = self.fs.mkdir("/no_such_parent/child")
        self.assertFalse(
            result,
            "mkdir should fail when the parent directory does not exist.",
        )

    def test_mkdir_parents_creates_intermediate_dirs(self):
        """mkdir with parents=True should create all intermediate directories."""
        result = self.fs.mkdir("/a/b/c", parents=True)
        self.assertTrue(result, "mkdir(parents=True) should succeed.")
        self.assertDirectoryExists(self.fs, "/a")
        self.assertDirectoryExists(self.fs, "/a/b")
        self.assertDirectoryExists(self.fs, "/a/b/c")

    def test_is_directory_true_for_dir(self):
        """is_directory should return True for a directory path."""
        self.fs.mkdir("/mydir")
        self.assertTrue(self.fs.is_directory("/mydir"))

    def test_is_directory_false_for_file(self):
        """is_directory should return False for a regular file path."""
        self.fs.create_file("/tmp/f.txt", b"data")
        self.assertFalse(self.fs.is_directory("/tmp/f.txt"))

    # --- create_file ---

    def test_create_file_success(self):
        """create_file should return True and make the file accessible."""
        self.fs.mkdir("/test_dir")
        result = self.fs.create_file("/test_dir/file.txt", b"Hello, PureOS!")
        self.assertTrue(result, "create_file should return True on success.")
        self.assertFileExists(self.fs, "/test_dir/file.txt")

    def test_create_file_duplicate_returns_false(self):
        """create_file on an existing path should return False without overwriting."""
        self.fs.create_file("/tmp/once.txt", b"original")
        result = self.fs.create_file("/tmp/once.txt", b"overwrite")
        self.assertFalse(result, "create_file on an existing path should return False.")
        self.assertFileEquals(self.fs, "/tmp/once.txt", b"original")

    def test_create_file_missing_parent_returns_false(self):
        """create_file should fail when the parent directory does not exist."""
        result = self.fs.create_file("/nonexistent/file.txt", b"data")
        self.assertFalse(
            result,
            "create_file should return False when parent directory is missing.",
        )

    # --- read_file ---

    def test_read_file_returns_correct_content(self):
        """read_file should return the exact bytes written by create_file."""
        self.fs.mkdir("/test_dir")
        self.fs.create_file("/test_dir/file.txt", b"Hello, PureOS!")
        content = self.fs.read_file("/test_dir/file.txt")
        self.assertEqual(
            content,
            b"Hello, PureOS!",
            "read_file should return the exact bytes written at creation.",
        )

    def test_read_nonexistent_file_returns_none(self):
        """read_file on a path that does not exist should return None."""
        result = self.fs.read_file("/does_not_exist.txt")
        self.assertIsNone(
            result,
            "read_file on a nonexistent path should return None.",
        )

    def test_read_directory_returns_none(self):
        """read_file on a directory path should return None."""
        result = self.fs.read_file("/tmp")
        self.assertIsNone(
            result,
            "read_file on a directory should return None.",
        )

    # --- write_file ---

    def test_write_file_updates_existing_content(self):
        """write_file should overwrite an existing file's content."""
        self.fs.create_file("/tmp/writable.txt", b"old content")
        self.fs.write_file("/tmp/writable.txt", b"new content")
        self.assertFileEquals(self.fs, "/tmp/writable.txt", b"new content")

    def test_write_file_creates_file_if_absent(self):
        """write_file on a nonexistent path should create the file."""
        result = self.fs.write_file("/tmp/brand_new.txt", b"created by write")
        self.assertTrue(result, "write_file should return True when creating a new file.")
        self.assertFileEquals(self.fs, "/tmp/brand_new.txt", b"created by write")

    # --- delete_file ---

    def test_delete_file_success(self):
        """delete_file should remove the file and make the path absent."""
        self.fs.create_file("/tmp/to_delete.txt", b"bye")
        result = self.fs.delete_file("/tmp/to_delete.txt")
        self.assertTrue(result, "delete_file should return True on success.")
        self.assertFileNotExists(self.fs, "/tmp/to_delete.txt")

    def test_delete_nonexistent_file_returns_false(self):
        """delete_file on a nonexistent path should return False."""
        result = self.fs.delete_file("/tmp/ghost.txt")
        self.assertFalse(result, "delete_file on a nonexistent path should return False.")

    def test_delete_directory_returns_false(self):
        """delete_file should refuse to delete a directory."""
        result = self.fs.delete_file("/tmp")
        self.assertFalse(
            result,
            "delete_file should not remove directories; use rmdir or remove_tree instead.",
        )

    # --- is_file ---

    def test_is_file_true_for_regular_file(self):
        """is_file should return True for a regular file."""
        self.fs.create_file("/tmp/check.txt", b"x")
        self.assertTrue(self.fs.is_file("/tmp/check.txt"))

    def test_is_file_false_for_directory(self):
        """is_file should return False for a directory."""
        self.assertFalse(self.fs.is_file("/tmp"))

    # --- get_inode / stat ---

    def test_get_inode_returns_inode_for_existing_path(self):
        """get_inode should return an Inode object for a known path."""
        inode = self.fs.get_inode("/tmp")
        self.assertIsNotNone(inode, "get_inode should return an Inode for '/tmp'.")
        self.assertIsInstance(inode, Inode)

    def test_get_inode_returns_none_for_missing_path(self):
        """get_inode should return None for a path that does not exist."""
        result = self.fs.get_inode("/no/such/path")
        self.assertIsNone(result, "get_inode should return None for a nonexistent path.")

    def test_stat_returns_dict_with_expected_keys(self):
        """stat should return a dict containing standard metadata keys."""
        self.fs.create_file("/tmp/stat_me.txt", b"data")
        info = self.fs.stat("/tmp/stat_me.txt")
        self.assertIsNotNone(info, "stat should not return None for an existing file.")
        for key in ("name", "type", "size", "permissions", "owner", "group"):
            self.assertIn(key, info, f"stat dict should contain key '{key}'.")

    def test_stat_returns_none_for_missing_path(self):
        """stat on a nonexistent path should return None."""
        result = self.fs.stat("/nonexistent")
        self.assertIsNone(result, "stat should return None for nonexistent paths.")


# ---------------------------------------------------------------------------
# Standard directories
# ---------------------------------------------------------------------------

class TestFileSystemStandardDirectories(BaseTestCase):
    """Verify the standard directory tree exists at boot time (Test 5)."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    def test_bin_exists(self):
        self.assertDirectoryExists(self.fs, "/bin", "/bin must exist on a fresh filesystem.")

    def test_etc_exists(self):
        self.assertDirectoryExists(self.fs, "/etc", "/etc must exist on a fresh filesystem.")

    def test_home_exists(self):
        self.assertDirectoryExists(self.fs, "/home", "/home must exist on a fresh filesystem.")

    def test_tmp_exists(self):
        self.assertDirectoryExists(self.fs, "/tmp", "/tmp must exist on a fresh filesystem.")

    def test_var_exists(self):
        self.assertDirectoryExists(self.fs, "/var", "/var must exist on a fresh filesystem.")

    def test_var_log_exists(self):
        self.assertDirectoryExists(self.fs, "/var/log", "/var/log must exist on a fresh filesystem.")

    def test_proc_exists(self):
        self.assertDirectoryExists(self.fs, "/proc", "/proc must exist on a fresh filesystem.")

    def test_proc_net_exists(self):
        self.assertDirectoryExists(self.fs, "/proc/net", "/proc/net must exist on a fresh filesystem.")

    def test_dev_exists(self):
        self.assertDirectoryExists(self.fs, "/dev", "/dev must exist on a fresh filesystem.")

    def test_root_home_exists(self):
        self.assertDirectoryExists(self.fs, "/root", "/root must exist on a fresh filesystem.")

    def test_usr_exists(self):
        self.assertDirectoryExists(self.fs, "/usr", "/usr must exist on a fresh filesystem.")

    def test_usr_bin_exists(self):
        self.assertDirectoryExists(self.fs, "/usr/bin", "/usr/bin must exist on a fresh filesystem.")

    def test_usr_local_exists(self):
        self.assertDirectoryExists(self.fs, "/usr/local", "/usr/local must exist on a fresh filesystem.")


# ---------------------------------------------------------------------------
# Recursive deletion
# ---------------------------------------------------------------------------

class TestFileSystemRemoveTree(BaseTestCase):
    """Tests for the remove_tree (recursive deletion) operation (Test 6)."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    def test_remove_tree_removes_nested_structure(self):
        """remove_tree should delete a directory and all its descendants."""
        self.fs.mkdir("/tmp/tree")
        self.fs.mkdir("/tmp/tree/branch")
        self.fs.create_file("/tmp/tree/branch/leaf.txt", b"leaf")

        result = self.fs.remove_tree("/tmp/tree")

        self.assertTrue(result, "remove_tree should return True on success.")
        self.assertFileNotExists(self.fs, "/tmp/tree",
                                 "Parent directory should be gone after remove_tree.")
        self.assertFalse(
            self.fs.exists("/tmp/tree/branch"),
            "Child directory should be gone after remove_tree.",
        )
        self.assertFalse(
            self.fs.exists("/tmp/tree/branch/leaf.txt"),
            "Leaf file should be gone after remove_tree.",
        )

    def test_remove_tree_removes_single_file(self):
        """remove_tree on a regular file should delete it cleanly."""
        self.fs.create_file("/tmp/single.txt", b"alone")
        result = self.fs.remove_tree("/tmp/single.txt")
        self.assertTrue(result, "remove_tree on a single file should return True.")
        self.assertFileNotExists(self.fs, "/tmp/single.txt")

    def test_remove_tree_nonexistent_path_returns_false(self):
        """remove_tree on a nonexistent path should return False."""
        result = self.fs.remove_tree("/tmp/does_not_exist")
        self.assertFalse(result, "remove_tree on a nonexistent path should return False.")

    def test_remove_tree_refuses_root(self):
        """remove_tree must refuse to delete the root directory."""
        result = self.fs.remove_tree("/")
        self.assertFalse(result, "remove_tree should never delete the root directory.")
        self.assertTrue(self.fs.exists("/"), "Root must still exist after remove_tree('/').")

    def test_remove_tree_parent_survives(self):
        """The parent of the deleted subtree should still exist after remove_tree."""
        self.fs.mkdir("/tmp/subtree")
        self.fs.create_file("/tmp/subtree/file.txt", b"content")
        self.fs.remove_tree("/tmp/subtree")
        self.assertDirectoryExists(self.fs, "/tmp",
                                   "/tmp should survive after its child subtree is deleted.")


# ---------------------------------------------------------------------------
# System files
# ---------------------------------------------------------------------------

class TestFileSystemSystemFiles(BaseTestCase):
    """Verify system files are populated at boot time (Test 32)."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    def test_etc_hostname_exists(self):
        self.assertFileExists(self.fs, "/etc/hostname",
                              "/etc/hostname must exist on a fresh filesystem.")

    def test_etc_hostname_contains_pureos(self):
        self.assertFileContains(self.fs, "/etc/hostname", b"pureos",
                                "/etc/hostname should contain 'pureos'.")

    def test_etc_motd_exists(self):
        self.assertFileExists(self.fs, "/etc/motd",
                              "/etc/motd must exist on a fresh filesystem.")

    def test_etc_motd_contains_pureos_branding(self):
        self.assertFileContains(self.fs, "/etc/motd", b"PureOS",
                                "/etc/motd should contain 'PureOS' branding.")

    def test_etc_os_release_exists(self):
        self.assertFileExists(self.fs, "/etc/os-release",
                              "/etc/os-release must exist on a fresh filesystem.")

    def test_etc_passwd_exists(self):
        self.assertFileExists(self.fs, "/etc/passwd",
                              "/etc/passwd must exist on a fresh filesystem.")

    def test_etc_passwd_contains_root_entry(self):
        self.assertFileContains(self.fs, "/etc/passwd", b"root",
                                "/etc/passwd should contain the root user entry.")

    def test_etc_group_exists(self):
        self.assertFileExists(self.fs, "/etc/group",
                              "/etc/group must exist on a fresh filesystem.")

    def test_etc_group_contains_root_group(self):
        self.assertFileContains(self.fs, "/etc/group", b"root",
                                "/etc/group should contain the root group entry.")

    def test_proc_version_exists(self):
        self.assertFileExists(self.fs, "/proc/version",
                              "/proc/version must exist on a fresh filesystem.")

    def test_proc_uptime_exists(self):
        self.assertFileExists(self.fs, "/proc/uptime",
                              "/proc/uptime must exist on a fresh filesystem.")

    def test_proc_net_dev_exists(self):
        self.assertFileExists(self.fs, "/proc/net/dev",
                              "/proc/net/dev must exist on a fresh filesystem.")

    def test_etc_shells_exists(self):
        self.assertFileExists(self.fs, "/etc/shells",
                              "/etc/shells must exist on a fresh filesystem.")


# ---------------------------------------------------------------------------
# Symlink creation
# ---------------------------------------------------------------------------

class TestFileSystemSymlinks(BaseTestCase):
    """Tests for symlink creation and inode-level inspection."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    def _create_symlink(self, target: str, link_path: str) -> bool:
        """Helper: create a SYMLINK inode directly in the filesystem."""
        import os as _os
        normalized_link = self.fs._normalize_path(link_path)
        if normalized_link in self.fs.inodes:
            return False
        parent_path = self.fs._get_parent(normalized_link)
        if parent_path not in self.fs.inodes:
            return False
        name = _os.path.basename(normalized_link)
        inode = Inode(
            name=name,
            type=FileType.SYMLINK,
            parent=parent_path,
            content=b"",
            target=target,
        )
        self.fs.inodes[normalized_link] = inode
        self.fs._add_to_parent(normalized_link, name)
        return True

    def test_symlink_inode_type_is_symlink(self):
        """A symlink inode should have type FileType.SYMLINK."""
        self.fs.create_file("/tmp/original.txt", b"source content")
        self._create_symlink("/tmp/original.txt", "/tmp/link.txt")
        inode = self.fs.get_inode("/tmp/link.txt")
        self.assertIsNotNone(inode, "Symlink inode must exist.")
        self.assertEqual(
            inode.type,
            FileType.SYMLINK,
            "Symlink inode must have FileType.SYMLINK.",
        )

    def test_symlink_inode_target_is_correct(self):
        """A symlink inode's target attribute should point to the original path."""
        self.fs.create_file("/tmp/original.txt", b"source content")
        self._create_symlink("/tmp/original.txt", "/tmp/link.txt")
        inode = self.fs.get_inode("/tmp/link.txt")
        self.assertEqual(
            inode.target,
            "/tmp/original.txt",
            "Symlink inode.target should be the destination path.",
        )

    def test_read_file_follows_symlink(self):
        """read_file should follow a symlink and return the target's content."""
        self.fs.create_file("/tmp/original.txt", b"linked content")
        self._create_symlink("/tmp/original.txt", "/tmp/link.txt")
        content = self.fs.read_file("/tmp/link.txt")
        self.assertEqual(
            content,
            b"linked content",
            "read_file should follow the symlink and return the target's content.",
        )


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------

class TestFileSystemPathNormalisation(BaseTestCase):
    """Tests for _normalize_path behaviour."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    def test_normalize_absolute_path_unchanged(self):
        """An already-absolute path with no special components should be unchanged."""
        result = self.fs._normalize_path("/tmp/file.txt")
        self.assertEqual(result, "/tmp/file.txt")

    def test_normalize_dot_components_removed(self):
        """Single-dot components (current dir) should be collapsed away."""
        result = self.fs._normalize_path("/tmp/./file.txt")
        self.assertEqual(result, "/tmp/file.txt")

    def test_normalize_double_dot_traverses_up(self):
        """Double-dot components should traverse up one directory level."""
        result = self.fs._normalize_path("/tmp/subdir/../file.txt")
        self.assertEqual(result, "/tmp/file.txt")

    def test_normalize_trailing_slash_removed(self):
        """Trailing slashes should be collapsed (root stays as '/')."""
        result = self.fs._normalize_path("/tmp/")
        self.assertEqual(result, "/tmp")

    def test_normalize_relative_path_resolved_against_cwd(self):
        """A relative path should be resolved against the current working directory."""
        self.fs.change_directory("/tmp")
        result = self.fs._normalize_path("file.txt")
        self.assertEqual(result, "/tmp/file.txt")

    def test_normalize_null_byte_raises_value_error(self):
        """A path containing a null byte should raise ValueError."""
        with self.assertRaises(ValueError):
            self.fs._normalize_path("/tmp/bad\x00path")

    def test_normalize_too_long_path_raises_value_error(self):
        """A path exceeding 4096 characters should raise ValueError."""
        long_path = "/" + "a" * 4097
        with self.assertRaises(ValueError):
            self.fs._normalize_path(long_path)


# ---------------------------------------------------------------------------
# chmod / chown at inode level
# ---------------------------------------------------------------------------

class TestFileSystemChmodChown(BaseTestCase):
    """Tests for chmod and chown operations on inodes."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()
        self.fs.create_file("/tmp/target.txt", b"data")

    def test_chmod_updates_permissions_string(self):
        """chmod with a symbolic permission string should update the inode."""
        result = self.fs.chmod("/tmp/target.txt", "rwxr-x---")
        self.assertTrue(result, "chmod should return True on success.")
        inode = self.fs.get_inode("/tmp/target.txt")
        self.assertEqual(
            inode.permissions,
            "rwxr-x---",
            "chmod should update inode.permissions to the supplied string.",
        )

    def test_chmod_returns_false_for_nonexistent_path(self):
        """chmod on a nonexistent path should return False."""
        result = self.fs.chmod("/no/such/file.txt", "rwxrwxrwx")
        self.assertFalse(result, "chmod should return False for a nonexistent path.")

    def test_chown_updates_owner(self):
        """chown should update the owner field on the inode."""
        result = self.fs.chown("/tmp/target.txt", "alice")
        self.assertTrue(result, "chown should return True on success.")
        inode = self.fs.get_inode("/tmp/target.txt")
        self.assertEqual(
            inode.owner,
            "alice",
            "chown should set inode.owner to the new owner.",
        )

    def test_chown_updates_group_when_supplied(self):
        """chown with a group argument should update both owner and group."""
        self.fs.chown("/tmp/target.txt", "alice", "staff")
        inode = self.fs.get_inode("/tmp/target.txt")
        self.assertEqual(inode.owner, "alice", "Owner should be 'alice'.")
        self.assertEqual(inode.group, "staff", "Group should be 'staff'.")

    def test_chown_leaves_group_unchanged_when_not_supplied(self):
        """chown without a group argument should not alter the group field."""
        original_group = self.fs.get_inode("/tmp/target.txt").group
        self.fs.chown("/tmp/target.txt", "bob")
        inode = self.fs.get_inode("/tmp/target.txt")
        self.assertEqual(
            inode.group,
            original_group,
            "Group should remain unchanged when chown is called without a group.",
        )

    def test_chown_returns_false_for_nonexistent_path(self):
        """chown on a nonexistent path should return False."""
        result = self.fs.chown("/no/such/file.txt", "alice")
        self.assertFalse(result, "chown should return False for a nonexistent path.")


# ---------------------------------------------------------------------------
# I/O statistics
# ---------------------------------------------------------------------------

class TestFileSystemIOStats(BaseTestCase):
    """Tests for the I/O statistics counters tracked by FileSystem."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()

    def test_write_increments_total_writes(self):
        """Creating or writing a file should increment total_writes."""
        before = self.fs.total_writes
        self.fs.create_file("/tmp/stats.txt", b"hello")
        self.assertGreater(
            self.fs.total_writes,
            before,
            "total_writes should increase after creating a file.",
        )

    def test_read_increments_total_reads(self):
        """Reading a file should increment total_reads."""
        self.fs.create_file("/tmp/stats.txt", b"hello")
        before = self.fs.total_reads
        self.fs.read_file("/tmp/stats.txt")
        self.assertGreater(
            self.fs.total_reads,
            before,
            "total_reads should increase after reading a file.",
        )

    def test_get_io_rates_returns_dict(self):
        """get_io_rates should return a dict with the expected keys."""
        rates = self.fs.get_io_rates()
        for key in ("read_bytes_per_sec", "write_bytes_per_sec",
                    "total_reads", "total_writes"):
            self.assertIn(key, rates, f"get_io_rates dict should contain '{key}'.")


if __name__ == "__main__":
    unittest.main()
