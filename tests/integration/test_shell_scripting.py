"""
tests/integration/test_shell_scripting.py
==========================================
Integration tests for shell scripting features.

Covers:
- Test 37: Arithmetic expansion ($((expr)))
- Test 38: seq command
- Test 41: case..esac statement
- Test 42: expr command
- Test 45: printf command
- Test 46: Parameter expansion (${var:-default}, ${#var})
"""

import unittest

from tests.base import BaseTestCase


class TestArithmeticExpansion(BaseTestCase):
    """Test 37: Arithmetic expansion — $((expr))."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_simple_addition(self):
        """$((2 + 3)) evaluates to 5."""
        self.assertShellSuccess(self.shell, "echo $((2 + 3)) > /tmp/arith_add.txt")
        content = self.fs.read_file("/tmp/arith_add.txt")
        self.assertIn(b"5", content)

    def test_combined_multiplication_subtraction(self):
        """$((10 * 4 - 2)) evaluates to 38."""
        self.assertShellSuccess(
            self.shell, "echo $((10 * 4 - 2)) > /tmp/arith_mul.txt"
        )
        content = self.fs.read_file("/tmp/arith_mul.txt")
        self.assertIn(b"38", content)

    def test_division(self):
        """$((10 / 2)) evaluates to 5."""
        self.assertShellSuccess(self.shell, "echo $((10 / 2)) > /tmp/arith_div.txt")
        content = self.fs.read_file("/tmp/arith_div.txt")
        self.assertIn(b"5", content)

    def test_modulo(self):
        """$((7 % 3)) evaluates to 1."""
        self.assertShellSuccess(self.shell, "echo $((7 % 3)) > /tmp/arith_mod.txt")
        content = self.fs.read_file("/tmp/arith_mod.txt")
        self.assertIn(b"1", content)

    def test_nested_expression(self):
        """Nested arithmetic $((( 2 + 3 ) * 4)) evaluates correctly."""
        self.assertShellSuccess(
            self.shell, "echo $(((2 + 3) * 4)) > /tmp/arith_nested.txt"
        )
        content = self.fs.read_file("/tmp/arith_nested.txt")
        self.assertIn(b"20", content)

    def test_zero_result(self):
        """$((5 - 5)) evaluates to 0."""
        self.assertShellSuccess(self.shell, "echo $((5 - 5)) > /tmp/arith_zero.txt")
        content = self.fs.read_file("/tmp/arith_zero.txt")
        self.assertIn(b"0", content)


class TestSeqCommand(BaseTestCase):
    """Test 38: seq command — generate sequences of numbers."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_seq_basic_range(self):
        """seq 1 5 produces 1 through 5."""
        self.assertShellSuccess(self.shell, "seq 1 5 > /tmp/seq_out.txt")
        content = self.fs.read_file("/tmp/seq_out.txt")
        self.assertIn(b"1", content)
        self.assertIn(b"3", content)
        self.assertIn(b"5", content)

    def test_seq_with_step(self):
        """seq 2 2 10 produces even numbers 2, 4, 6, 8, 10."""
        self.assertShellSuccess(self.shell, "seq 2 2 10 > /tmp/seq_step.txt")
        content = self.fs.read_file("/tmp/seq_step.txt")
        self.assertIn(b"2", content)
        self.assertIn(b"4", content)
        self.assertIn(b"6", content)
        self.assertIn(b"10", content)

    def test_seq_single_number(self):
        """seq 5 produces just '5'."""
        self.assertShellSuccess(self.shell, "seq 5 > /tmp/seq_single.txt")
        content = self.fs.read_file("/tmp/seq_single.txt")
        self.assertIsNotNone(content)

    def test_seq_pipe_to_wc(self):
        """seq 1 5 | wc -l gives 5 lines."""
        self.assertShellSuccess(
            self.shell, "seq 1 5 | wc -l > /tmp/seq_wc.txt"
        )
        content = self.fs.read_file("/tmp/seq_wc.txt")
        self.assertIn(b"5", content)

    def test_seq_is_registered(self):
        """The seq command is present in the shell's command table."""
        self.assertIn("seq", self.shell.commands)


class TestCaseEsacStatement(BaseTestCase):
    """Test 41: case..esac statement in shell scripting."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_case_matching_first_pattern(self):
        """case matches the first pattern and executes its commands."""
        self.assertShellSuccess(
            self.shell,
            "case hello in hello) echo matched > /tmp/case_out.txt ;; esac",
        )
        content = self.fs.read_file("/tmp/case_out.txt")
        self.assertIn(b"matched", content)

    def test_case_matching_second_pattern(self):
        """case skips non-matching patterns and matches the correct one."""
        self.assertShellSuccess(
            self.shell,
            "case world in hello) echo wrong ;; world) echo right > /tmp/case2.txt ;; esac",
        )
        content = self.fs.read_file("/tmp/case2.txt")
        self.assertIn(b"right", content)

    def test_case_wildcard_pattern(self):
        """case with * wildcard matches any value."""
        self.assertShellSuccess(
            self.shell,
            "case anything in *) echo wildcard > /tmp/case_wild.txt ;; esac",
        )
        content = self.fs.read_file("/tmp/case_wild.txt")
        self.assertIn(b"wildcard", content)

    def test_case_no_match_is_silent(self):
        """case with no matching pattern exits cleanly."""
        self.assertShellSuccess(
            self.shell,
            "case nomatch in yes) echo yes ;; no) echo no ;; esac",
        )

    def test_case_with_variable(self):
        """case works with a shell variable as the test value."""
        self.shell.environment["FRUIT"] = "apple"
        self.assertShellSuccess(
            self.shell,
            "case $FRUIT in apple) echo got_apple > /tmp/case_var.txt ;; esac",
        )
        content = self.fs.read_file("/tmp/case_var.txt")
        self.assertIn(b"got_apple", content)


class TestExprCommand(BaseTestCase):
    """Test 42: expr command — evaluate arithmetic and string expressions."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_expr_addition(self):
        """expr 3 + 4 outputs 7."""
        self.assertShellSuccess(self.shell, "expr 3 + 4 > /tmp/expr_add.txt")
        content = self.fs.read_file("/tmp/expr_add.txt")
        self.assertIn(b"7", content)

    def test_expr_subtraction(self):
        """expr 10 - 3 outputs 7."""
        self.assertShellSuccess(self.shell, "expr 10 - 3 > /tmp/expr_sub.txt")
        content = self.fs.read_file("/tmp/expr_sub.txt")
        self.assertIn(b"7", content)

    def test_expr_multiplication(self):
        """expr 4 * 5 outputs 20 (using escaped *)."""
        self.assertShellSuccess(self.shell, r"expr 4 \* 5 > /tmp/expr_mul.txt")
        content = self.fs.read_file("/tmp/expr_mul.txt")
        self.assertIn(b"20", content)

    def test_expr_division(self):
        """expr 15 / 3 outputs 5."""
        self.assertShellSuccess(self.shell, "expr 15 / 3 > /tmp/expr_div.txt")
        content = self.fs.read_file("/tmp/expr_div.txt")
        self.assertIn(b"5", content)

    def test_expr_string_length(self):
        """expr length hello outputs 5."""
        self.assertShellSuccess(
            self.shell, "expr length hello > /tmp/expr_len.txt"
        )
        content = self.fs.read_file("/tmp/expr_len.txt")
        self.assertIn(b"5", content)

    def test_expr_is_registered(self):
        """The expr command is present in the shell's command table."""
        self.assertIn("expr", self.shell.commands)


class TestPrintfCommand(BaseTestCase):
    """Test 45: printf command — formatted output."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_printf_basic_string(self):
        """printf outputs a plain string."""
        self.assertShellSuccess(
            self.shell, "printf hello > /tmp/printf_str.txt"
        )
        content = self.fs.read_file("/tmp/printf_str.txt")
        self.assertIn(b"hello", content)

    def test_printf_with_newline(self):
        """printf 'hello\\n' includes the newline."""
        self.assertShellSuccess(
            self.shell, r"printf 'hello\n' > /tmp/printf_nl.txt"
        )
        content = self.fs.read_file("/tmp/printf_nl.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"hello", content)

    def test_printf_format_string(self):
        """printf '%s world' hello outputs 'hello world'."""
        self.assertShellSuccess(
            self.shell, "printf '%s world' hello > /tmp/printf_fmt.txt"
        )
        content = self.fs.read_file("/tmp/printf_fmt.txt")
        self.assertIn(b"hello", content)
        self.assertIn(b"world", content)

    def test_printf_integer_format(self):
        """printf '%d' 42 outputs '42'."""
        self.assertShellSuccess(
            self.shell, "printf '%d' 42 > /tmp/printf_int.txt"
        )
        content = self.fs.read_file("/tmp/printf_int.txt")
        self.assertIn(b"42", content)

    def test_printf_is_registered(self):
        """The printf command is present in the shell's command table."""
        self.assertIn("printf", self.shell.commands)


class TestParameterExpansion(BaseTestCase):
    """Test 46: Parameter expansion — ${var:-default}, ${#var}."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_default_value_when_unset(self):
        """${VAR:-default} expands to 'default' when VAR is unset."""
        # Ensure the variable is not set
        self.shell.environment.pop("MYVAR", None)
        self.assertShellSuccess(
            self.shell,
            "echo ${MYVAR:-fallback} > /tmp/param_default.txt",
        )
        content = self.fs.read_file("/tmp/param_default.txt")
        self.assertIn(b"fallback", content)

    def test_default_value_when_set(self):
        """${VAR:-default} expands to VAR's value when VAR is set."""
        self.shell.environment["MYVAR"] = "actual"
        self.assertShellSuccess(
            self.shell,
            "echo ${MYVAR:-fallback} > /tmp/param_set.txt",
        )
        content = self.fs.read_file("/tmp/param_set.txt")
        self.assertIn(b"actual", content)
        self.assertNotIn(b"fallback", content)

    def test_string_length_expansion(self):
        """${#VAR} expands to the length of VAR's value."""
        self.shell.environment["WORD"] = "hello"
        self.assertShellSuccess(
            self.shell,
            "echo ${#WORD} > /tmp/param_len.txt",
        )
        content = self.fs.read_file("/tmp/param_len.txt")
        self.assertIn(b"5", content)

    def test_string_length_of_empty(self):
        """${#VAR} is 0 when VAR is empty string."""
        self.shell.environment["EMPTYVAR"] = ""
        self.assertShellSuccess(
            self.shell,
            "echo ${#EMPTYVAR} > /tmp/param_empty_len.txt",
        )
        content = self.fs.read_file("/tmp/param_empty_len.txt")
        self.assertIn(b"0", content)

    def test_braced_variable_expansion(self):
        """${VAR} is equivalent to $VAR for normal expansion."""
        self.shell.environment["PROJECT"] = "PureOS"
        self.assertShellSuccess(
            self.shell,
            "echo ${PROJECT} > /tmp/param_brace.txt",
        )
        content = self.fs.read_file("/tmp/param_brace.txt")
        self.assertIn(b"PureOS", content)


if __name__ == "__main__":
    unittest.main()
