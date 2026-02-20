"""
tests/integration/test_shell_filesystem.py
===========================================
Integration tests for PureOS filesystem shell commands.

Covers:
- Test 12: File metadata (chmod, chown, stat)
- Test 13: Find command (all variants: -name, -type, -maxdepth, -mindepth)
- Test 17: rm option parsing (-rf, --recursive --force, --, invalid flags)
- Test 24: basename/dirname commands
- Test 27: ln command (hard links and symlinks)
"""

import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tests.base import BaseTestCase


class TestFileMetadataCommands(BaseTestCase):
    """Test 12: File metadata — chmod, chown, stat."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file('/tmp/meta_test.txt', b'metadata file\n')

    # ------------------------------------------------------------------
    # chmod
    # ------------------------------------------------------------------

    def test_chmod_octal_succeeds(self):
        """chmod with a valid octal mode succeeds."""
        self.assertShellSuccess(self.shell, 'chmod 644 /tmp/meta_test.txt')

    def test_chmod_executable_bit_succeeds(self):
        """chmod +x succeeds on an existing file."""
        self.assertShellSuccess(self.shell, 'chmod +x /tmp/meta_test.txt')

    def test_chmod_remove_write_bit_succeeds(self):
        """chmod -w succeeds on an existing file."""
        self.assertShellSuccess(self.shell, 'chmod -w /tmp/meta_test.txt')

    def test_chmod_symbolic_mode_succeeds(self):
        """chmod with symbolic mode string (e.g. u+x) succeeds."""
        self.assertShellSuccess(self.shell, 'chmod u+x /tmp/meta_test.txt')

    def test_chmod_nonexistent_file_fails(self):
        """chmod on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'chmod 644 /tmp/no_such_file_xyz.txt')

    def test_chmod_no_args_fails(self):
        """chmod with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'chmod')

    # ------------------------------------------------------------------
    # chown
    # ------------------------------------------------------------------

    def test_chown_succeeds(self):
        """chown with a valid user:group succeeds on an existing file."""
        self.assertShellSuccess(self.shell, 'chown root:root /tmp/meta_test.txt')

    def test_chown_user_only_succeeds(self):
        """chown with only a user name succeeds."""
        self.assertShellSuccess(self.shell, 'chown root /tmp/meta_test.txt')

    def test_chown_nonexistent_file_fails(self):
        """chown on a non-existent path returns non-zero."""
        self.assertShellFails(self.shell, 'chown root /tmp/no_such_file_xyz.txt')

    def test_chown_no_args_fails(self):
        """chown with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'chown')

    # ------------------------------------------------------------------
    # stat
    # ------------------------------------------------------------------

    def test_stat_existing_file_succeeds(self):
        """stat on an existing file returns 0."""
        self.assertShellSuccess(self.shell, 'stat /tmp/meta_test.txt')

    def test_stat_existing_directory_succeeds(self):
        """stat on an existing directory returns 0."""
        self.assertShellSuccess(self.shell, 'stat /tmp')

    def test_stat_nonexistent_path_fails(self):
        """stat on a non-existent path returns non-zero."""
        self.assertShellFails(self.shell, 'stat /tmp/no_such_file_xyz.txt')

    def test_stat_no_args_fails(self):
        """stat with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'stat')


class TestFindCommand(BaseTestCase):
    """Test 13: Find command — all variants."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        # Build a small directory tree under /tmp/findtest/
        fs = self.shell.fs
        fs.mkdir('/tmp/findtest')
        fs.mkdir('/tmp/findtest/subdir')
        fs.mkdir('/tmp/findtest/subdir/deep')
        fs.create_file('/tmp/findtest/alpha.txt', b'alpha\n')
        fs.create_file('/tmp/findtest/beta.log', b'beta\n')
        fs.create_file('/tmp/findtest/subdir/gamma.txt', b'gamma\n')
        fs.create_file('/tmp/findtest/subdir/deep/delta.txt', b'delta\n')

    # ------------------------------------------------------------------
    # Basic find
    # ------------------------------------------------------------------

    def test_find_directory_succeeds(self):
        """find on an existing directory returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest')

    def test_find_nonexistent_directory_fails(self):
        """find on a non-existent path returns non-zero."""
        self.assertShellFails(self.shell, 'find /tmp/no_such_dir_xyz')

    # ------------------------------------------------------------------
    # -name filter
    # ------------------------------------------------------------------

    def test_find_name_glob_succeeds(self):
        """find -name '*.txt' returns 0."""
        self.assertShellSuccess(self.shell, "find /tmp/findtest -name '*.txt'")

    def test_find_name_exact_match_succeeds(self):
        """find -name 'alpha.txt' returns 0."""
        self.assertShellSuccess(self.shell, "find /tmp/findtest -name 'alpha.txt'")

    def test_find_name_no_match_succeeds(self):
        """find -name for a non-matching pattern still returns 0 (no results, not an error)."""
        self.assertShellSuccess(self.shell, "find /tmp/findtest -name '*.xyz'")

    # ------------------------------------------------------------------
    # -type filter
    # ------------------------------------------------------------------

    def test_find_type_f_succeeds(self):
        """find -type f returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -type f')

    def test_find_type_d_succeeds(self):
        """find -type d returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -type d')

    # ------------------------------------------------------------------
    # -maxdepth
    # ------------------------------------------------------------------

    def test_find_maxdepth_zero_succeeds(self):
        """find -maxdepth 0 returns 0 (only root itself)."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -maxdepth 0')

    def test_find_maxdepth_one_succeeds(self):
        """find -maxdepth 1 returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -maxdepth 1')

    def test_find_maxdepth_with_name_succeeds(self):
        """find -maxdepth 1 -name '*.txt' returns 0."""
        self.assertShellSuccess(self.shell, "find /tmp/findtest -maxdepth 1 -name '*.txt'")

    # ------------------------------------------------------------------
    # -mindepth
    # ------------------------------------------------------------------

    def test_find_mindepth_one_succeeds(self):
        """find -mindepth 1 returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -mindepth 1')

    def test_find_mindepth_two_succeeds(self):
        """find -mindepth 2 returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -mindepth 2')

    def test_find_mindepth_maxdepth_combined_succeeds(self):
        """find -mindepth 1 -maxdepth 2 returns 0."""
        self.assertShellSuccess(self.shell, 'find /tmp/findtest -mindepth 1 -maxdepth 2')

    # ------------------------------------------------------------------
    # Combined filters
    # ------------------------------------------------------------------

    def test_find_type_f_name_combined_succeeds(self):
        """find -type f -name '*.txt' returns 0."""
        self.assertShellSuccess(self.shell, "find /tmp/findtest -type f -name '*.txt'")

    def test_find_no_args_fails(self):
        """find with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'find')


class TestRmCommand(BaseTestCase):
    """Test 17: rm option parsing."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()

    def _make_file(self, path, content=b'data\n'):
        self.shell.fs.create_file(path, content)

    def _make_dir_with_file(self, dirpath, filename='inner.txt'):
        self.shell.fs.mkdir(dirpath)
        self.shell.fs.create_file(f'{dirpath}/{filename}', b'inner\n')

    # ------------------------------------------------------------------
    # Basic removal
    # ------------------------------------------------------------------

    def test_rm_single_file_succeeds(self):
        """rm removes a single existing file."""
        self._make_file('/tmp/rm_single.txt')
        self.assertShellSuccess(self.shell, 'rm /tmp/rm_single.txt')
        self.assertFileNotExists(self.shell.fs, '/tmp/rm_single.txt')

    def test_rm_nonexistent_file_fails(self):
        """rm on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'rm /tmp/no_such_file_rm_xyz.txt')

    # ------------------------------------------------------------------
    # -r / --recursive
    # ------------------------------------------------------------------

    def test_rm_rf_removes_directory_tree(self):
        """rm -rf removes a directory and its contents."""
        self._make_dir_with_file('/tmp/rm_rf_dir')
        self.assertShellSuccess(self.shell, 'rm -rf /tmp/rm_rf_dir')
        self.assertFileNotExists(self.shell.fs, '/tmp/rm_rf_dir')

    def test_rm_r_flag_removes_directory(self):
        """rm -r removes a directory recursively."""
        self._make_dir_with_file('/tmp/rm_r_dir')
        self.assertShellSuccess(self.shell, 'rm -r /tmp/rm_r_dir')
        self.assertFileNotExists(self.shell.fs, '/tmp/rm_r_dir')

    def test_rm_recursive_force_long_flags(self):
        """rm --recursive --force removes a directory tree."""
        self._make_dir_with_file('/tmp/rm_long_dir')
        self.assertShellSuccess(self.shell, 'rm --recursive --force /tmp/rm_long_dir')
        self.assertFileNotExists(self.shell.fs, '/tmp/rm_long_dir')

    def test_rm_directory_without_r_fails(self):
        """rm on a directory without -r returns non-zero."""
        self.shell.fs.mkdir('/tmp/rm_no_r_dir')
        self.assertShellFails(self.shell, 'rm /tmp/rm_no_r_dir')

    # ------------------------------------------------------------------
    # -- end-of-options marker
    # ------------------------------------------------------------------

    def test_rm_end_of_options_marker(self):
        """rm -- <file> removes a file whose name follows the -- marker."""
        self._make_file('/tmp/rm_dashdash.txt')
        self.assertShellSuccess(self.shell, 'rm -- /tmp/rm_dashdash.txt')
        self.assertFileNotExists(self.shell.fs, '/tmp/rm_dashdash.txt')

    # ------------------------------------------------------------------
    # No arguments
    # ------------------------------------------------------------------

    def test_rm_no_args_fails(self):
        """rm with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'rm')


class TestBasenameDirnameCommands(BaseTestCase):
    """Test 24: basename and dirname commands."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()

    # ------------------------------------------------------------------
    # basename
    # ------------------------------------------------------------------

    def test_basename_simple_path_succeeds(self):
        """basename /path/to/file.txt returns 0."""
        self.assertShellSuccess(self.shell, 'basename /path/to/file.txt')

    def test_basename_root_path_succeeds(self):
        """basename /file.txt returns 0."""
        self.assertShellSuccess(self.shell, 'basename /file.txt')

    def test_basename_with_suffix_succeeds(self):
        """basename /path/to/file.txt .txt strips the suffix."""
        self.assertShellSuccess(self.shell, 'basename /path/to/file.txt .txt')

    def test_basename_no_args_fails(self):
        """basename with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'basename')

    def test_basename_trailing_slash_succeeds(self):
        """basename /path/to/dir/ succeeds."""
        self.assertShellSuccess(self.shell, 'basename /path/to/dir/')

    def test_basename_dot_path_succeeds(self):
        """basename . returns 0."""
        self.assertShellSuccess(self.shell, 'basename .')

    # ------------------------------------------------------------------
    # dirname
    # ------------------------------------------------------------------

    def test_dirname_simple_path_succeeds(self):
        """dirname /path/to/file.txt returns 0."""
        self.assertShellSuccess(self.shell, 'dirname /path/to/file.txt')

    def test_dirname_root_file_succeeds(self):
        """dirname /file.txt returns 0."""
        self.assertShellSuccess(self.shell, 'dirname /file.txt')

    def test_dirname_trailing_slash_succeeds(self):
        """dirname /path/to/dir/ succeeds."""
        self.assertShellSuccess(self.shell, 'dirname /path/to/dir/')

    def test_dirname_dot_succeeds(self):
        """dirname . returns 0."""
        self.assertShellSuccess(self.shell, 'dirname .')

    def test_dirname_no_args_fails(self):
        """dirname with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'dirname')


class TestLnCommand(BaseTestCase):
    """Test 27: ln command — hard links and symlinks."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file('/tmp/ln_source.txt', b'link source content\n')

    # ------------------------------------------------------------------
    # Hard links
    # ------------------------------------------------------------------

    def test_ln_hard_link_succeeds(self):
        """ln creates a hard link and returns 0."""
        self.assertShellSuccess(
            self.shell, 'ln /tmp/ln_source.txt /tmp/ln_hard.txt'
        )

    def test_ln_hard_link_target_exists(self):
        """After a hard link the target path exists in the filesystem."""
        self.shell.execute('ln /tmp/ln_source.txt /tmp/ln_hard2.txt')
        self.assertFileExists(self.shell.fs, '/tmp/ln_hard2.txt')

    def test_ln_hard_link_nonexistent_source_fails(self):
        """ln on a non-existent source file returns non-zero."""
        self.assertShellFails(
            self.shell, 'ln /tmp/no_such_src_xyz.txt /tmp/ln_bad.txt'
        )

    # ------------------------------------------------------------------
    # Symbolic links (-s)
    # ------------------------------------------------------------------

    def test_ln_s_creates_symlink_succeeds(self):
        """ln -s creates a symbolic link and returns 0."""
        self.assertShellSuccess(
            self.shell, 'ln -s /tmp/ln_source.txt /tmp/ln_sym.txt'
        )

    def test_ln_s_symlink_target_exists(self):
        """After ln -s the symlink path exists in the filesystem."""
        self.shell.execute('ln -s /tmp/ln_source.txt /tmp/ln_sym2.txt')
        self.assertTrue(
            self.shell.fs.exists('/tmp/ln_sym2.txt'),
            "Symlink target should exist after ln -s",
        )

    def test_ln_s_nonexistent_source_succeeds(self):
        """ln -s to a non-existent source succeeds (dangling symlinks are valid)."""
        self.assertShellSuccess(
            self.shell, 'ln -s /tmp/dangling_source.txt /tmp/ln_dangling.txt'
        )

    # ------------------------------------------------------------------
    # Error cases
    # ------------------------------------------------------------------

    def test_ln_no_args_fails(self):
        """ln with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'ln')

    def test_ln_one_arg_fails(self):
        """ln with only one argument (missing target) returns non-zero."""
        self.assertShellFails(self.shell, 'ln /tmp/ln_source.txt')
