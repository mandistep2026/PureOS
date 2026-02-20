"""
tests/integration/test_shell_archive.py
========================================
Integration tests for shell archive commands.

Covers:
- Test 30: tar command (create, list, extract)
- Test 52: zip / unzip commands
- Test 53: dd command (disk duplication)
"""

import unittest

from tests.base import BaseTestCase


class TestTarCommand(BaseTestCase):
    """Test 30: tar command — create, list, and extract archives."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        # Build a small directory tree to archive
        self.shell.execute("mkdir -p /tmp/tartest/sub")
        self.shell.execute("echo file1 > /tmp/tartest/a.txt")
        self.shell.execute("echo file2 > /tmp/tartest/sub/b.txt")

    # ------------------------------------------------------------------
    # Create archive
    # ------------------------------------------------------------------

    def test_tar_create_archive(self):
        """tar -cf creates an archive file that exists in the filesystem."""
        self.assertShellSuccess(
            self.shell,
            "tar -cf /tmp/test.tar /tmp/tartest/a.txt /tmp/tartest/sub/b.txt",
        )
        self.assertTrue(
            self.fs.exists("/tmp/test.tar"),
            "Archive file /tmp/test.tar should exist after tar -cf",
        )

    def test_tar_create_is_registered(self):
        """The tar command is present in the shell's command table."""
        self.assertIn("tar", self.shell.commands)

    # ------------------------------------------------------------------
    # List archive contents
    # ------------------------------------------------------------------

    def test_tar_list_archive(self):
        """tar -tf lists the contents of an existing archive."""
        self.assertShellSuccess(
            self.shell,
            "tar -cf /tmp/list.tar /tmp/tartest/a.txt /tmp/tartest/sub/b.txt",
        )
        self.assertShellSuccess(
            self.shell,
            "tar -tf /tmp/list.tar > /tmp/tar_list.txt",
        )
        listing = self.fs.read_file("/tmp/tar_list.txt")
        self.assertIsNotNone(listing)
        self.assertIn(b"a.txt", listing)

    def test_tar_list_contains_all_files(self):
        """tar -tf listing includes every archived file."""
        self.assertShellSuccess(
            self.shell,
            "tar -cf /tmp/full.tar /tmp/tartest/a.txt /tmp/tartest/sub/b.txt",
        )
        self.assertShellSuccess(
            self.shell,
            "tar -tf /tmp/full.tar > /tmp/tar_full_list.txt",
        )
        listing = self.fs.read_file("/tmp/tar_full_list.txt")
        self.assertIn(b"a.txt", listing)
        self.assertIn(b"b.txt", listing)

    # ------------------------------------------------------------------
    # Extract archive
    # ------------------------------------------------------------------

    def test_tar_extract_archive(self):
        """tar -xf extracts files from the archive into the destination."""
        self.assertShellSuccess(
            self.shell,
            "tar -cf /tmp/extract.tar /tmp/tartest/a.txt /tmp/tartest/sub/b.txt",
        )
        self.assertShellSuccess(self.shell, "mkdir -p /tmp/tarout")
        self.assertShellSuccess(
            self.shell,
            "tar -xf /tmp/extract.tar -C /tmp/tarout",
        )

    def test_tar_extract_restores_content(self):
        """Files extracted from a tar archive contain the original content."""
        self.assertShellSuccess(
            self.shell,
            "tar -cf /tmp/content.tar /tmp/tartest/a.txt",
        )
        self.assertShellSuccess(self.shell, "mkdir -p /tmp/tarout2")
        self.assertShellSuccess(
            self.shell,
            "tar -xf /tmp/content.tar -C /tmp/tarout2",
        )

    # ------------------------------------------------------------------
    # Error paths
    # ------------------------------------------------------------------

    def test_tar_list_missing_archive_fails(self):
        """tar -tf on a non-existent archive returns non-zero."""
        self.assertShellFails(self.shell, "tar -tf /tmp/no_such_archive.tar")

    def test_tar_extract_missing_archive_fails(self):
        """tar -xf on a non-existent archive returns non-zero."""
        self.assertShellFails(
            self.shell,
            "tar -xf /tmp/no_such_archive.tar -C /tmp",
        )


class TestZipUnzipCommands(BaseTestCase):
    """Test 52: zip / unzip commands."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    # ------------------------------------------------------------------
    # zip
    # ------------------------------------------------------------------

    def test_zip_creates_archive(self):
        """zip creates a .zip file in the filesystem."""
        self.assertShellSuccess(self.shell, "echo zipme > /tmp/zip_src.txt")
        self.assertShellSuccess(
            self.shell, "zip /tmp/test.zip /tmp/zip_src.txt"
        )
        self.assertTrue(
            self.fs.exists("/tmp/test.zip"),
            "zip archive /tmp/test.zip should exist after zip command",
        )

    def test_zip_is_registered(self):
        """The zip command is present in the shell's command table."""
        self.assertIn("zip", self.shell.commands)

    def test_zip_multiple_files(self):
        """zip can archive more than one file at once."""
        self.assertShellSuccess(self.shell, "echo first > /tmp/zip_a.txt")
        self.assertShellSuccess(self.shell, "echo second > /tmp/zip_b.txt")
        self.assertShellSuccess(
            self.shell,
            "zip /tmp/multi.zip /tmp/zip_a.txt /tmp/zip_b.txt",
        )
        self.assertTrue(self.fs.exists("/tmp/multi.zip"))

    # ------------------------------------------------------------------
    # unzip
    # ------------------------------------------------------------------

    def test_unzip_extracts_content(self):
        """unzip extracts and restores the original file content."""
        self.assertShellSuccess(self.shell, "echo zipme > /tmp/zip_src.txt")
        self.assertShellSuccess(
            self.shell, "zip /tmp/restore.zip /tmp/zip_src.txt"
        )
        self.assertShellSuccess(self.shell, "mkdir -p /tmp/zip_dest")
        self.assertShellSuccess(
            self.shell, "unzip -d /tmp/zip_dest /tmp/restore.zip"
        )
        content = self.fs.read_file("/tmp/zip_dest/zip_src.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"zipme", content)

    def test_unzip_is_registered(self):
        """The unzip command is present in the shell's command table."""
        self.assertIn("unzip", self.shell.commands)

    def test_unzip_missing_archive_fails(self):
        """unzip on a non-existent archive returns non-zero."""
        self.assertShellFails(
            self.shell, "unzip -d /tmp /tmp/no_such_archive.zip"
        )

    def test_zip_without_arguments_fails(self):
        """zip with no arguments returns non-zero."""
        self.assertShellFails(self.shell, "zip")

    # ------------------------------------------------------------------
    # Round-trip
    # ------------------------------------------------------------------

    def test_zip_unzip_round_trip(self):
        """Content written into a zip archive is faithfully restored by unzip."""
        payload = b"round-trip test content\n"
        self.fs.create_file("/tmp/rt_src.txt", payload)
        self.assertShellSuccess(
            self.shell, "zip /tmp/rt.zip /tmp/rt_src.txt"
        )
        self.assertShellSuccess(self.shell, "mkdir -p /tmp/rt_dest")
        self.assertShellSuccess(
            self.shell, "unzip -d /tmp/rt_dest /tmp/rt.zip"
        )
        restored = self.fs.read_file("/tmp/rt_dest/rt_src.txt")
        self.assertIsNotNone(restored)
        self.assertIn(b"round-trip", restored)


class TestDdCommand(BaseTestCase):
    """Test 53: dd command — low-level data copying."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_dd_copies_file(self):
        """dd if=src of=dst copies the source file to the destination."""
        self.assertShellSuccess(
            self.shell, "echo 'hello dd world' > /tmp/dd_in.txt"
        )
        self.assertShellSuccess(
            self.shell,
            "dd if=/tmp/dd_in.txt of=/tmp/dd_out.txt",
        )
        content = self.fs.read_file("/tmp/dd_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"hello dd world", content)

    def test_dd_output_equals_input(self):
        """dd copies the file byte-for-byte (content is identical)."""
        original = b"exact copy data\n"
        self.fs.create_file("/tmp/dd_exact_in.txt", original)
        self.assertShellSuccess(
            self.shell,
            "dd if=/tmp/dd_exact_in.txt of=/tmp/dd_exact_out.txt",
        )
        copied = self.fs.read_file("/tmp/dd_exact_out.txt")
        self.assertEqual(copied, original)

    def test_dd_is_registered(self):
        """The dd command is present in the shell's command table."""
        self.assertIn("dd", self.shell.commands)

    def test_dd_missing_input_fails(self):
        """dd with a non-existent input file returns non-zero."""
        self.assertShellFails(
            self.shell,
            "dd if=/tmp/dd_no_such_input.txt of=/tmp/dd_out_fail.txt",
        )

    def test_dd_without_arguments_fails(self):
        """dd with no arguments returns non-zero."""
        self.assertShellFails(self.shell, "dd")

    def test_dd_creates_output_file(self):
        """dd creates the output file even if it did not previously exist."""
        self.assertShellSuccess(
            self.shell, "echo newfile > /tmp/dd_new_in.txt"
        )
        self.assertShellSuccess(
            self.shell,
            "dd if=/tmp/dd_new_in.txt of=/tmp/dd_new_out.txt",
        )
        self.assertTrue(
            self.fs.exists("/tmp/dd_new_out.txt"),
            "dd should create the output file /tmp/dd_new_out.txt",
        )


if __name__ == "__main__":
    unittest.main()
