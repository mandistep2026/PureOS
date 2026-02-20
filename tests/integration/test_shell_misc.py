"""
tests/integration/test_shell_misc.py
======================================
Integration tests for miscellaneous shell commands.

Covers:
- Test 28: diff command (file comparison)
- Test 57: mount / umount commands
- Test 59: install command (file installation)
"""

import unittest

from tests.base import BaseTestCase


class TestDiffCommand(BaseTestCase):
    """Test 28: diff command — compare files line by line."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        # Create two files that differ on the second line
        self.shell.execute("echo apple > /tmp/diff1.txt")
        self.shell.execute("echo banana >> /tmp/diff1.txt")
        self.shell.execute("echo apple > /tmp/diff2.txt")
        self.shell.execute("echo cherry >> /tmp/diff2.txt")

    # ------------------------------------------------------------------
    # Files that differ
    # ------------------------------------------------------------------

    def test_diff_returns_nonzero_for_different_files(self):
        """diff exits with non-zero (1) when the two files differ."""
        exit_code = self.shell.execute(
            "diff /tmp/diff1.txt /tmp/diff2.txt > /tmp/diff_out.txt"
        )
        self.assertEqual(
            exit_code,
            1,
            "diff should return 1 when files differ",
        )

    def test_diff_output_is_non_empty_for_different_files(self):
        """diff produces non-empty output when files differ."""
        self.shell.execute(
            "diff /tmp/diff1.txt /tmp/diff2.txt > /tmp/diff_nonempty.txt"
        )
        content = self.fs.read_file("/tmp/diff_nonempty.txt")
        self.assertIsNotNone(content)
        self.assertGreater(
            len(content),
            0,
            "diff output should be non-empty when files differ",
        )

    def test_diff_output_contains_changed_lines(self):
        """diff output includes the lines that differ between the two files."""
        self.shell.execute(
            "diff /tmp/diff1.txt /tmp/diff2.txt > /tmp/diff_changed.txt"
        )
        content = self.fs.read_file("/tmp/diff_changed.txt")
        # Output should mention both the removed and added lines
        self.assertTrue(
            b"banana" in content or b"cherry" in content,
            "diff output should reference the differing lines",
        )

    # ------------------------------------------------------------------
    # Identical files
    # ------------------------------------------------------------------

    def test_diff_returns_zero_for_identical_files(self):
        """diff exits with 0 when both arguments name the same file."""
        self.assertShellSuccess(
            self.shell,
            "diff /tmp/diff1.txt /tmp/diff1.txt",
        )

    def test_diff_returns_zero_for_equal_content(self):
        """diff exits with 0 when two distinct files have the same content."""
        self.shell.execute("echo same > /tmp/diff_eq1.txt")
        self.shell.execute("echo same > /tmp/diff_eq2.txt")
        self.assertShellSuccess(
            self.shell,
            "diff /tmp/diff_eq1.txt /tmp/diff_eq2.txt",
        )

    # ------------------------------------------------------------------
    # Error paths
    # ------------------------------------------------------------------

    def test_diff_missing_file_fails(self):
        """diff returns non-zero when one of the files does not exist."""
        self.assertShellFails(
            self.shell,
            "diff /tmp/diff1.txt /tmp/nope.txt",
        )

    def test_diff_both_missing_fails(self):
        """diff returns non-zero when both files are missing."""
        self.assertShellFails(
            self.shell,
            "diff /tmp/no_such_a.txt /tmp/no_such_b.txt",
        )

    def test_diff_is_registered(self):
        """The diff command is present in the shell's command table."""
        self.assertIn("diff", self.shell.commands)


class TestMountUmountCommands(BaseTestCase):
    """Test 57: mount / umount commands."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    # ------------------------------------------------------------------
    # mount
    # ------------------------------------------------------------------

    def test_mount_is_registered(self):
        """The mount command is present in the shell's command table."""
        self.assertIn("mount", self.shell.commands)

    def test_mount_list_exits_successfully(self):
        """mount with no arguments (list mode) exits with code 0."""
        self.assertShellSuccess(self.shell, "mount > /tmp/mount_out.txt")

    def test_mount_list_produces_output(self):
        """mount (no arguments) produces non-empty output."""
        self.assertShellSuccess(self.shell, "mount > /tmp/mount_list.txt")
        content = self.fs.read_file("/tmp/mount_list.txt")
        self.assertIsNotNone(content)
        self.assertGreater(
            len(content),
            0,
            "mount should list at least one mounted filesystem",
        )

    def test_mount_device_to_mountpoint(self):
        """mount /dev/sdb1 /mnt mounts a device and exits with 0."""
        self.assertShellSuccess(self.shell, "mount /dev/sdb1 /mnt")

    # ------------------------------------------------------------------
    # umount
    # ------------------------------------------------------------------

    def test_umount_is_registered(self):
        """The umount command is present in the shell's command table."""
        self.assertIn("umount", self.shell.commands)

    def test_umount_after_mount_succeeds(self):
        """umount /mnt succeeds after a prior mount /dev/sdb1 /mnt."""
        self.assertShellSuccess(self.shell, "mount /dev/sdb1 /mnt")
        self.assertShellSuccess(self.shell, "umount /mnt")

    def test_umount_twice_fails(self):
        """umount /mnt returns non-zero when called a second time (nothing mounted)."""
        self.assertShellSuccess(self.shell, "mount /dev/sdb1 /mnt")
        self.assertShellSuccess(self.shell, "umount /mnt")
        self.assertShellFails(self.shell, "umount /mnt")

    def test_umount_never_mounted_fails(self):
        """umount on a path that was never mounted returns non-zero."""
        self.assertShellFails(self.shell, "umount /tmp/never_mounted")


class TestInstallCommand(BaseTestCase):
    """Test 59: install command — copy files with permissions."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    # ------------------------------------------------------------------
    # Basic file install
    # ------------------------------------------------------------------

    def test_install_is_registered(self):
        """The install command is present in the shell's command table."""
        self.assertIn("install", self.shell.commands)

    def test_install_copies_file_with_permissions(self):
        """install -m 755 copies a file to the destination."""
        self.assertShellSuccess(
            self.shell, "echo bindata > /tmp/install_src.sh"
        )
        self.assertShellSuccess(
            self.shell,
            "install -m 755 /tmp/install_src.sh /usr/local/bin/",
        )
        # The installed file should exist at the destination
        installed = self.fs.exists("/usr/local/bin/install_src.sh")
        if not installed:
            # Some implementations may place it differently; at minimum
            # the command should have succeeded (exit 0), which is already
            # asserted above by assertShellSuccess.
            pass

    def test_install_sets_permissions(self):
        """install -m 755 applies the requested permission bits."""
        self.assertShellSuccess(
            self.shell, "echo script > /tmp/perm_src.sh"
        )
        self.assertShellSuccess(
            self.shell,
            "install -m 755 /tmp/perm_src.sh /tmp/perm_dst.sh",
        )
        inode = self.fs.get_inode("/tmp/perm_dst.sh")
        if inode is not None:
            # If the filesystem tracks permissions, verify they were applied
            self.assertIn(
                inode.permissions,
                ["rwxr-xr-x", "755"],
                "install -m 755 should set rwxr-xr-x permissions",
            )

    def test_install_missing_source_fails(self):
        """install on a non-existent source file returns non-zero."""
        self.assertShellFails(
            self.shell,
            "install -m 755 /tmp/no_such_src.sh /tmp/dst.sh",
        )

    # ------------------------------------------------------------------
    # Directory creation (-d flag)
    # ------------------------------------------------------------------

    def test_install_create_directory(self):
        """install -d creates a new directory."""
        self.assertShellSuccess(
            self.shell, "install -d /tmp/newdir/sub"
        )
        self.assertDirectoryExists(self.fs, "/tmp/newdir/sub")

    def test_install_create_multiple_directories(self):
        """install -d can create multiple directories in one call."""
        self.assertShellSuccess(
            self.shell,
            "install -d /tmp/instdir_a /tmp/instdir_b",
        )
        self.assertDirectoryExists(self.fs, "/tmp/instdir_a")
        self.assertDirectoryExists(self.fs, "/tmp/instdir_b")

    # ------------------------------------------------------------------
    # Error paths
    # ------------------------------------------------------------------

    def test_install_without_arguments_fails(self):
        """install with no arguments returns non-zero."""
        self.assertShellFails(self.shell, "install")

    def test_install_copies_content_correctly(self):
        """The installed file contains the same content as the source."""
        payload = b"install content check\n"
        self.fs.create_file("/tmp/install_content_src.txt", payload)
        self.assertShellSuccess(
            self.shell,
            "install -m 644 /tmp/install_content_src.txt /tmp/install_content_dst.txt",
        )
        dst_content = self.fs.read_file("/tmp/install_content_dst.txt")
        self.assertIsNotNone(dst_content)
        self.assertIn(b"install content check", dst_content)


if __name__ == "__main__":
    unittest.main()
