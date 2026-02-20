"""
tests/integration/test_shell_text.py
=====================================
Integration tests for PureOS text-processing shell commands.

Covers:
- Test 18: Sort command (basic, -u, -r, invalid flags)
- Test 19: Head/Tail commands (with -n, invalid inputs, multi-file)
- Test 20: Grep command (basic, -i, -n, -v, multi-file, invalid flags)
- Test 21: Uniq command (-c, -d, -u, conflicting flags)
- Test 22: Cut command (-f, -d, missing args)
- Test 23: wc command (stdin, flags)
- Test 34: sed command (substitute, delete)
- Test 35: awk command (print field, pattern match)
- Test 36: tr command (uppercase, delete)
"""

import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tests.base import BaseTestCase


class TestSortCommand(BaseTestCase):
    """Test 18: sort command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/sort_input.txt',
            b'banana\napple\ncherry\napple\ndate\n',
        )

    def test_sort_basic_succeeds(self):
        """sort on a file returns 0."""
        self.assertShellSuccess(self.shell, 'sort /tmp/sort_input.txt')

    def test_sort_unique_flag_succeeds(self):
        """sort -u removes duplicate lines and returns 0."""
        self.assertShellSuccess(self.shell, 'sort -u /tmp/sort_input.txt')

    def test_sort_reverse_flag_succeeds(self):
        """sort -r sorts in reverse order and returns 0."""
        self.assertShellSuccess(self.shell, 'sort -r /tmp/sort_input.txt')

    def test_sort_reverse_unique_combined_succeeds(self):
        """sort -ru combines reverse and unique and returns 0."""
        self.assertShellSuccess(self.shell, 'sort -ru /tmp/sort_input.txt')

    def test_sort_nonexistent_file_fails(self):
        """sort on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'sort /tmp/no_such_file_sort_xyz.txt')

    def test_sort_output_redirected_to_file(self):
        """sort output can be redirected to a file."""
        self.assertShellSuccess(
            self.shell, 'sort /tmp/sort_input.txt > /tmp/sort_out.txt'
        )
        self.assertFileExists(self.shell.fs, '/tmp/sort_out.txt')

    def test_sort_numeric_flag_succeeds(self):
        """sort -n sorts numerically and returns 0."""
        self.shell.fs.create_file('/tmp/nums.txt', b'10\n2\n1\n20\n')
        self.assertShellSuccess(self.shell, 'sort -n /tmp/nums.txt')


class TestHeadTailCommands(BaseTestCase):
    """Test 19: head and tail commands."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        lines = '\n'.join(str(i) for i in range(1, 21)) + '\n'
        self.shell.fs.create_file('/tmp/ht_input.txt', lines.encode())
        self.shell.fs.create_file('/tmp/ht_second.txt', b'file2_line1\nfile2_line2\n')

    # ------------------------------------------------------------------
    # head
    # ------------------------------------------------------------------

    def test_head_default_succeeds(self):
        """head on a file (default 10 lines) returns 0."""
        self.assertShellSuccess(self.shell, 'head /tmp/ht_input.txt')

    def test_head_n_flag_succeeds(self):
        """head -n 5 returns 0."""
        self.assertShellSuccess(self.shell, 'head -n 5 /tmp/ht_input.txt')

    def test_head_n_zero_succeeds(self):
        """head -n 0 returns 0 (produces no output but is valid)."""
        self.assertShellSuccess(self.shell, 'head -n 0 /tmp/ht_input.txt')

    def test_head_nonexistent_file_fails(self):
        """head on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'head /tmp/no_such_file_head_xyz.txt')

    def test_head_invalid_n_fails(self):
        """head -n with a non-numeric value returns non-zero."""
        self.assertShellFails(self.shell, 'head -n abc /tmp/ht_input.txt')

    def test_head_multi_file_succeeds(self):
        """head with multiple files returns 0."""
        self.assertShellSuccess(
            self.shell, 'head /tmp/ht_input.txt /tmp/ht_second.txt'
        )

    # ------------------------------------------------------------------
    # tail
    # ------------------------------------------------------------------

    def test_tail_default_succeeds(self):
        """tail on a file (default 10 lines) returns 0."""
        self.assertShellSuccess(self.shell, 'tail /tmp/ht_input.txt')

    def test_tail_n_flag_succeeds(self):
        """tail -n 5 returns 0."""
        self.assertShellSuccess(self.shell, 'tail -n 5 /tmp/ht_input.txt')

    def test_tail_n_zero_succeeds(self):
        """tail -n 0 returns 0."""
        self.assertShellSuccess(self.shell, 'tail -n 0 /tmp/ht_input.txt')

    def test_tail_nonexistent_file_fails(self):
        """tail on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'tail /tmp/no_such_file_tail_xyz.txt')

    def test_tail_invalid_n_fails(self):
        """tail -n with a non-numeric value returns non-zero."""
        self.assertShellFails(self.shell, 'tail -n abc /tmp/ht_input.txt')

    def test_tail_multi_file_succeeds(self):
        """tail with multiple files returns 0."""
        self.assertShellSuccess(
            self.shell, 'tail /tmp/ht_input.txt /tmp/ht_second.txt'
        )


class TestGrepCommand(BaseTestCase):
    """Test 20: grep command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/grep_input.txt',
            b'Hello World\nhello world\nfoo bar\nHELLO WORLD\n',
        )
        self.shell.fs.create_file(
            '/tmp/grep_second.txt',
            b'second file line one\nsecond file line two\n',
        )

    def test_grep_basic_match_succeeds(self):
        """grep with a matching pattern returns 0."""
        self.assertShellSuccess(self.shell, 'grep Hello /tmp/grep_input.txt')

    def test_grep_no_match_fails(self):
        """grep with no matching lines returns non-zero."""
        self.assertShellFails(self.shell, 'grep NOMATCH_XYZ /tmp/grep_input.txt')

    def test_grep_case_insensitive_flag_succeeds(self):
        """grep -i matches regardless of case."""
        self.assertShellSuccess(self.shell, 'grep -i hello /tmp/grep_input.txt')

    def test_grep_line_number_flag_succeeds(self):
        """grep -n includes line numbers and returns 0."""
        self.assertShellSuccess(self.shell, 'grep -n Hello /tmp/grep_input.txt')

    def test_grep_invert_match_flag_succeeds(self):
        """grep -v returns lines that do NOT match and exits 0 when such lines exist."""
        self.assertShellSuccess(self.shell, 'grep -v Hello /tmp/grep_input.txt')

    def test_grep_invert_match_all_lines_match_fails(self):
        """grep -v returns non-zero when every line matches (nothing to invert)."""
        self.shell.fs.create_file('/tmp/grep_all_hello.txt', b'Hello\nHello\n')
        self.assertShellFails(self.shell, 'grep -v Hello /tmp/grep_all_hello.txt')

    def test_grep_multi_file_succeeds(self):
        """grep across multiple files returns 0 when pattern is found."""
        self.assertShellSuccess(
            self.shell,
            'grep Hello /tmp/grep_input.txt /tmp/grep_second.txt',
        )

    def test_grep_nonexistent_file_fails(self):
        """grep on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'grep foo /tmp/no_such_grep_xyz.txt')

    def test_grep_no_args_fails(self):
        """grep with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'grep')

    def test_grep_combined_flags_succeeds(self):
        """grep -i -n combined returns 0."""
        self.assertShellSuccess(self.shell, 'grep -i -n hello /tmp/grep_input.txt')


class TestUniqCommand(BaseTestCase):
    """Test 21: uniq command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/uniq_input.txt',
            b'apple\napple\nbanana\nbanana\nbanana\ncherry\n',
        )

    def test_uniq_basic_succeeds(self):
        """uniq on a file with duplicates returns 0."""
        self.assertShellSuccess(self.shell, 'uniq /tmp/uniq_input.txt')

    def test_uniq_count_flag_succeeds(self):
        """uniq -c prefixes lines with occurrence counts and returns 0."""
        self.assertShellSuccess(self.shell, 'uniq -c /tmp/uniq_input.txt')

    def test_uniq_repeated_flag_succeeds(self):
        """uniq -d outputs only duplicate lines and returns 0."""
        self.assertShellSuccess(self.shell, 'uniq -d /tmp/uniq_input.txt')

    def test_uniq_unique_flag_succeeds(self):
        """uniq -u outputs only non-repeated lines and returns 0."""
        self.assertShellSuccess(self.shell, 'uniq -u /tmp/uniq_input.txt')

    def test_uniq_nonexistent_file_fails(self):
        """uniq on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'uniq /tmp/no_such_uniq_xyz.txt')

    def test_uniq_output_redirected_succeeds(self):
        """uniq output can be redirected to a file."""
        self.assertShellSuccess(
            self.shell, 'uniq /tmp/uniq_input.txt > /tmp/uniq_out.txt'
        )
        self.assertFileExists(self.shell.fs, '/tmp/uniq_out.txt')

    def test_uniq_conflicting_d_u_flags(self):
        """uniq -d and -u together: command should handle gracefully (succeed or fail, not crash)."""
        # The shell should not raise an exception; exit code is implementation-defined
        exit_code = self.shell.execute('uniq -d -u /tmp/uniq_input.txt')
        self.assertIsInstance(exit_code, int)


class TestCutCommand(BaseTestCase):
    """Test 22: cut command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/cut_input.txt',
            b'one:two:three\nfour:five:six\nalpha:beta:gamma\n',
        )

    def test_cut_f_flag_succeeds(self):
        """cut -f1 returns 0."""
        self.assertShellSuccess(self.shell, 'cut -f1 /tmp/cut_input.txt')

    def test_cut_f_with_delimiter_succeeds(self):
        """cut -d: -f2 selects the second colon-delimited field."""
        self.assertShellSuccess(self.shell, 'cut -d: -f2 /tmp/cut_input.txt')

    def test_cut_f_range_succeeds(self):
        """cut -f1-2 selects a field range and returns 0."""
        self.assertShellSuccess(self.shell, 'cut -f1-2 /tmp/cut_input.txt')

    def test_cut_f_multiple_fields_succeeds(self):
        """cut -f1,3 selects non-contiguous fields and returns 0."""
        self.assertShellSuccess(self.shell, 'cut -d: -f1,3 /tmp/cut_input.txt')

    def test_cut_nonexistent_file_fails(self):
        """cut on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'cut -f1 /tmp/no_such_cut_xyz.txt')

    def test_cut_missing_f_arg_fails(self):
        """cut without -f (or -c) returns non-zero."""
        self.assertShellFails(self.shell, 'cut /tmp/cut_input.txt')

    def test_cut_no_args_fails(self):
        """cut with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'cut')


class TestWcCommand(BaseTestCase):
    """Test 23: wc command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/wc_input.txt',
            b'one two three\nfour five\nsix\n',
        )

    def test_wc_file_succeeds(self):
        """wc on a file returns 0."""
        self.assertShellSuccess(self.shell, 'wc /tmp/wc_input.txt')

    def test_wc_lines_flag_succeeds(self):
        """wc -l counts lines and returns 0."""
        self.assertShellSuccess(self.shell, 'wc -l /tmp/wc_input.txt')

    def test_wc_words_flag_succeeds(self):
        """wc -w counts words and returns 0."""
        self.assertShellSuccess(self.shell, 'wc -w /tmp/wc_input.txt')

    def test_wc_chars_flag_succeeds(self):
        """wc -c counts bytes/chars and returns 0."""
        self.assertShellSuccess(self.shell, 'wc -c /tmp/wc_input.txt')

    def test_wc_multiple_flags_succeeds(self):
        """wc -l -w -c combined returns 0."""
        self.assertShellSuccess(self.shell, 'wc -l -w -c /tmp/wc_input.txt')

    def test_wc_nonexistent_file_fails(self):
        """wc on a non-existent file returns non-zero."""
        self.assertShellFails(self.shell, 'wc /tmp/no_such_wc_xyz.txt')

    def test_wc_stdin_via_pipe_succeeds(self):
        """wc receives input from a pipe and returns 0."""
        self.assertShellSuccess(self.shell, 'cat /tmp/wc_input.txt | wc -l')


class TestSedCommand(BaseTestCase):
    """Test 34: sed command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/sed_input.txt',
            b'hello world\nhello again\nfoo bar\n',
        )

    def test_sed_substitute_succeeds(self):
        """sed s/pattern/replacement/ returns 0."""
        self.assertShellSuccess(
            self.shell, "sed 's/hello/goodbye/' /tmp/sed_input.txt"
        )

    def test_sed_substitute_global_succeeds(self):
        """sed s/pattern/replacement/g global substitution returns 0."""
        self.assertShellSuccess(
            self.shell, "sed 's/hello/goodbye/g' /tmp/sed_input.txt"
        )

    def test_sed_delete_line_succeeds(self):
        """sed /pattern/d deletes matching lines and returns 0."""
        self.assertShellSuccess(
            self.shell, "sed '/hello/d' /tmp/sed_input.txt"
        )

    def test_sed_delete_by_line_number_succeeds(self):
        """sed 1d deletes the first line and returns 0."""
        self.assertShellSuccess(self.shell, "sed '1d' /tmp/sed_input.txt")

    def test_sed_substitute_output_to_file(self):
        """sed substitution output redirected to file produces a valid file."""
        self.assertShellSuccess(
            self.shell,
            "sed 's/hello/goodbye/' /tmp/sed_input.txt > /tmp/sed_out.txt",
        )
        self.assertFileExists(self.shell.fs, '/tmp/sed_out.txt')

    def test_sed_no_args_fails(self):
        """sed with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'sed')

    def test_sed_nonexistent_file_fails(self):
        """sed on a non-existent file returns non-zero."""
        self.assertShellFails(
            self.shell, "sed 's/a/b/' /tmp/no_such_sed_xyz.txt"
        )

    def test_sed_via_pipe_succeeds(self):
        """sed receives input from a pipe and returns 0."""
        self.assertShellSuccess(
            self.shell, "cat /tmp/sed_input.txt | sed 's/hello/hi/'"
        )


class TestAwkCommand(BaseTestCase):
    """Test 35: awk command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/awk_input.txt',
            b'alice 30 engineer\nbob 25 designer\ncharlie 35 manager\n',
        )

    def test_awk_print_field_succeeds(self):
        """awk '{print $1}' prints the first field and returns 0."""
        self.assertShellSuccess(
            self.shell, "awk '{print $1}' /tmp/awk_input.txt"
        )

    def test_awk_print_multiple_fields_succeeds(self):
        """awk '{print $1, $3}' prints two fields and returns 0."""
        self.assertShellSuccess(
            self.shell, "awk '{print $1, $3}' /tmp/awk_input.txt"
        )

    def test_awk_pattern_match_succeeds(self):
        """awk '/alice/ {print $0}' filters by pattern and returns 0."""
        self.assertShellSuccess(
            self.shell, "awk '/alice/ {print $0}' /tmp/awk_input.txt"
        )

    def test_awk_field_separator_flag_succeeds(self):
        """awk -F: with a custom field separator returns 0."""
        self.shell.fs.create_file(
            '/tmp/awk_colon.txt', b'a:b:c\nd:e:f\n'
        )
        self.assertShellSuccess(
            self.shell, "awk -F: '{print $2}' /tmp/awk_colon.txt"
        )

    def test_awk_numeric_comparison_succeeds(self):
        """awk '$2 > 28 {print $1}' filters rows numerically and returns 0."""
        self.assertShellSuccess(
            self.shell, "awk '$2 > 28 {print $1}' /tmp/awk_input.txt"
        )

    def test_awk_no_args_fails(self):
        """awk with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'awk')

    def test_awk_nonexistent_file_fails(self):
        """awk on a non-existent file returns non-zero."""
        self.assertShellFails(
            self.shell, "awk '{print $1}' /tmp/no_such_awk_xyz.txt"
        )

    def test_awk_via_pipe_succeeds(self):
        """awk receives input from a pipe and returns 0."""
        self.assertShellSuccess(
            self.shell, "cat /tmp/awk_input.txt | awk '{print $1}'"
        )


class TestTrCommand(BaseTestCase):
    """Test 36: tr command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file(
            '/tmp/tr_input.txt',
            b'hello world\nfoo bar baz\n',
        )

    def test_tr_uppercase_via_pipe_succeeds(self):
        """tr a-z A-Z converts lowercase to uppercase and returns 0."""
        self.assertShellSuccess(
            self.shell, "cat /tmp/tr_input.txt | tr 'a-z' 'A-Z'"
        )

    def test_tr_delete_flag_via_pipe_succeeds(self):
        """tr -d deletes specified characters and returns 0."""
        self.assertShellSuccess(
            self.shell, "cat /tmp/tr_input.txt | tr -d 'aeiou'"
        )

    def test_tr_squeeze_flag_via_pipe_succeeds(self):
        """tr -s squeezes repeated characters and returns 0."""
        self.shell.fs.create_file('/tmp/tr_spaces.txt', b'hello   world\n')
        self.assertShellSuccess(
            self.shell, "cat /tmp/tr_spaces.txt | tr -s ' '"
        )

    def test_tr_replace_char_succeeds(self):
        """tr replaces one character set with another and returns 0."""
        self.assertShellSuccess(
            self.shell, "cat /tmp/tr_input.txt | tr ' ' '_'"
        )

    def test_tr_no_args_fails(self):
        """tr with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'tr')

    def test_tr_redirect_input_succeeds(self):
        """tr with input redirected from a file returns 0."""
        self.assertShellSuccess(
            self.shell, "tr 'a-z' 'A-Z' < /tmp/tr_input.txt"
        )


class TestPasteCommand(BaseTestCase):
    """Test: paste command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.shell.fs.create_file('/tmp/paste_a.txt', b'a1\na2\na3\n')
        self.shell.fs.create_file('/tmp/paste_b.txt', b'b1\nb2\n')

    def test_paste_two_files_succeeds(self):
        """paste merges files line-wise and returns 0."""
        self.assertShellSuccess(self.shell, 'paste /tmp/paste_a.txt /tmp/paste_b.txt')

    def test_paste_custom_delimiter_succeeds(self):
        """paste -d uses custom delimiter and returns 0."""
        self.assertShellSuccess(self.shell, 'paste -d : /tmp/paste_a.txt /tmp/paste_b.txt')

    def test_paste_nonexistent_file_fails(self):
        """paste on a missing file returns non-zero."""
        self.assertShellFails(self.shell, 'paste /tmp/paste_a.txt /tmp/does_not_exist_paste.txt')

    def test_paste_missing_operand_fails(self):
        """paste with no files returns non-zero."""
        self.assertShellFails(self.shell, 'paste')

