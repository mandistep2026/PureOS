"""
tests/integration/test_shell_core.py
=====================================
Integration tests for PureOS shell core features.

Covers:
- Test 4:  Shell commands (command registration)
- Test 10: Command discovery (which, type)
- Test 15: Environment variable expansion ($VAR, ${VAR}, $?, "$VAR", '$VAR')
- Test 16: Export/unset commands with validation
"""

import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tests.base import BaseTestCase


class TestShellCommandRegistration(BaseTestCase):
    """Test 4: Shell commands — command registration and dispatch."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()

    # ------------------------------------------------------------------
    # Core built-in commands are registered
    # ------------------------------------------------------------------

    def test_builtin_commands_registered(self):
        """All expected built-in commands are present in the command table."""
        expected = [
            'ls', 'cd', 'pwd', 'cat', 'mkdir', 'rmdir', 'rm',
            'touch', 'cp', 'mv', 'chmod', 'chown', 'stat',
            'grep', 'head', 'tail', 'wc', 'cut', 'sort', 'uniq', 'find',
            'echo', 'export', 'unset', 'env', 'which', 'type',
            'basename', 'dirname', 'ln',
            'sed', 'awk', 'tr',
        ]
        for cmd in expected:
            self.assertIn(
                cmd, self.shell.commands,
                f"Expected built-in command '{cmd}' to be registered.",
            )

    def test_unknown_command_returns_127(self):
        """Executing an unknown command returns exit code 127."""
        exit_code = self.shell.execute('nonexistent_command_xyz')
        self.assertEqual(exit_code, 127)

    def test_empty_command_returns_zero(self):
        """Executing an empty line returns 0 without error."""
        exit_code = self.shell.execute('')
        self.assertEqual(exit_code, 0)

    def test_whitespace_only_command_returns_zero(self):
        """Executing whitespace-only input returns 0 without error."""
        exit_code = self.shell.execute('   ')
        self.assertEqual(exit_code, 0)

    def test_echo_command_succeeds(self):
        """echo command exits 0."""
        self.assertShellSuccess(self.shell, 'echo hello')

    def test_command_table_is_not_empty(self):
        """Shell command table contains commands after initialisation."""
        self.assertGreater(len(self.shell.commands), 0)

    def test_register_command_adds_to_table(self):
        """register_command() adds the command under its name key."""
        from shell.shell import ShellCommand

        class DummyCommand(ShellCommand):
            def __init__(self):
                super().__init__('_dummy_test_cmd', 'test')

            def execute(self, args, shell):
                return 42

        cmd = DummyCommand()
        self.shell.register_command(cmd)
        self.assertIn('_dummy_test_cmd', self.shell.commands)
        self.assertIs(self.shell.commands['_dummy_test_cmd'], cmd)

    def test_last_exit_code_updated_on_success(self):
        """last_exit_code is 0 after a successful command."""
        self.shell.execute('echo ok')
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_last_exit_code_updated_on_failure(self):
        """last_exit_code is non-zero after a failing command."""
        self.shell.execute('ls /nonexistent_path_xyz_123')
        self.assertNotEqual(self.shell.last_exit_code, 0)


class TestCommandDiscovery(BaseTestCase):
    """Test 10: Command discovery — which and type."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()

    # ------------------------------------------------------------------
    # which
    # ------------------------------------------------------------------

    def test_which_known_builtin_succeeds(self):
        """which returns 0 for a registered built-in."""
        self.assertShellSuccess(self.shell, 'which echo')

    def test_which_multiple_known_builtins_succeeds(self):
        """which returns 0 when all supplied names are known."""
        self.assertShellSuccess(self.shell, 'which ls cat grep')

    def test_which_unknown_command_fails(self):
        """which returns non-zero for an unknown command."""
        self.assertShellFails(self.shell, 'which _totally_unknown_cmd_xyz')

    def test_which_no_args_fails(self):
        """which with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'which')

    # ------------------------------------------------------------------
    # type
    # ------------------------------------------------------------------

    def test_type_known_builtin_succeeds(self):
        """type returns 0 for a registered built-in."""
        self.assertShellSuccess(self.shell, 'type echo')

    def test_type_multiple_commands_succeeds(self):
        """type returns 0 for multiple known commands."""
        self.assertShellSuccess(self.shell, 'type ls cat echo')

    def test_type_unknown_command_fails(self):
        """type returns non-zero for an unknown command."""
        self.assertShellFails(self.shell, 'type _totally_unknown_cmd_xyz')

    def test_type_alias_succeeds(self):
        """type returns 0 for a defined alias."""
        # 'll' is a default alias in the shell
        self.assertShellSuccess(self.shell, 'type ll')

    def test_type_no_args_fails(self):
        """type with no arguments returns non-zero."""
        self.assertShellFails(self.shell, 'type')


class TestEnvironmentVariableExpansion(BaseTestCase):
    """Test 15: Environment variable expansion."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        # Plant a known variable for expansion tests
        self.shell.environment['TESTVAR'] = 'hello_world'

    # ------------------------------------------------------------------
    # $VAR form
    # ------------------------------------------------------------------

    def test_expand_simple_var(self):
        """$VAR expands to the variable value."""
        expanded = self.shell._expand_environment_variables('echo $TESTVAR')
        self.assertIn('hello_world', expanded)

    def test_expand_unset_var_gives_empty(self):
        """An unset $VAR expands to an empty string."""
        expanded = self.shell._expand_environment_variables('$NOTSET_XYZ_999')
        self.assertEqual(expanded.strip(), '')

    # ------------------------------------------------------------------
    # ${VAR} form
    # ------------------------------------------------------------------

    def test_expand_braced_var(self):
        """${VAR} expands to the variable value."""
        expanded = self.shell._expand_environment_variables('${TESTVAR}')
        self.assertEqual(expanded, 'hello_world')

    def test_expand_braced_unset_var_gives_empty(self):
        """${NOTSET} expands to empty string."""
        expanded = self.shell._expand_environment_variables('${NOTSET_XYZ_999}')
        self.assertEqual(expanded, '')

    # ------------------------------------------------------------------
    # $? form
    # ------------------------------------------------------------------

    def test_expand_last_exit_code(self):
        """$? expands to the last exit code."""
        self.shell.last_exit_code = 42
        expanded = self.shell._expand_environment_variables('$?')
        self.assertEqual(expanded, '42')

    def test_expand_exit_code_zero(self):
        """$? expands to '0' when last exit code is zero."""
        self.shell.last_exit_code = 0
        expanded = self.shell._expand_environment_variables('$?')
        self.assertEqual(expanded, '0')

    # ------------------------------------------------------------------
    # "$VAR" — expands inside double quotes
    # ------------------------------------------------------------------

    def test_expand_var_inside_double_quotes(self):
        """$VAR expands even inside double-quoted strings."""
        expanded = self.shell._expand_environment_variables('"$TESTVAR"')
        self.assertIn('hello_world', expanded)

    # ------------------------------------------------------------------
    # '$VAR' — NO expansion inside single quotes
    # ------------------------------------------------------------------

    def test_no_expansion_inside_single_quotes(self):
        """$VAR is NOT expanded inside single-quoted strings."""
        expanded = self.shell._expand_environment_variables("'$TESTVAR'")
        # The literal dollar sign must survive
        self.assertIn('$TESTVAR', expanded)
        self.assertNotIn('hello_world', expanded)

    # ------------------------------------------------------------------
    # Round-trip via shell.execute
    # ------------------------------------------------------------------

    def test_execute_with_var_expansion(self):
        """shell.execute expands variables before dispatching the command."""
        self.shell.environment['_TFILE'] = '/tmp/expand_test.txt'
        self.shell.fs.create_file('/tmp/expand_test.txt', b'expansion works\n')
        self.assertShellSuccess(self.shell, 'cat $_TFILE')

    def test_execute_braced_var_expansion(self):
        """shell.execute expands ${VAR} form correctly."""
        self.shell.environment['_TFILE2'] = '/tmp/expand_test2.txt'
        self.shell.fs.create_file('/tmp/expand_test2.txt', b'braced\n')
        self.assertShellSuccess(self.shell, 'cat ${_TFILE2}')

    def test_path_env_var_present(self):
        """PATH environment variable is set in the default shell."""
        self.assertIn('PATH', self.shell.environment)
        self.assertTrue(self.shell.environment['PATH'])

    def test_home_env_var_present(self):
        """HOME environment variable is set in the default shell."""
        self.assertIn('HOME', self.shell.environment)


class TestExportUnsetCommands(BaseTestCase):
    """Test 16: export and unset commands with validation."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------

    def test_export_sets_variable(self):
        """export VAR=value sets VAR in the environment."""
        self.assertShellSuccess(self.shell, 'export MYVAR=testvalue')
        self.assertEqual(self.shell.environment.get('MYVAR'), 'testvalue')

    def test_export_existing_variable_updates_value(self):
        """export VAR=newvalue updates an already-exported variable."""
        self.shell.environment['MYVAR'] = 'old'
        self.assertShellSuccess(self.shell, 'export MYVAR=new')
        self.assertEqual(self.shell.environment.get('MYVAR'), 'new')

    def test_export_no_value_marks_for_export(self):
        """export VAR (without =) should succeed for a pre-set variable."""
        self.shell.environment['PRESETVAR'] = 'abc'
        # Exporting an already-set variable with no value form should succeed
        self.assertShellSuccess(self.shell, 'export PRESETVAR')

    def test_export_multiple_vars(self):
        """export can set multiple variables in one call."""
        self.assertShellSuccess(self.shell, 'export VARA=1 VARB=2')
        self.assertEqual(self.shell.environment.get('VARA'), '1')
        self.assertEqual(self.shell.environment.get('VARB'), '2')

    def test_export_with_empty_value(self):
        """export VAR= sets the variable to an empty string."""
        self.assertShellSuccess(self.shell, 'export EMPTYVAR=')
        self.assertIn('EMPTYVAR', self.shell.environment)

    # ------------------------------------------------------------------
    # unset
    # ------------------------------------------------------------------

    def test_unset_removes_variable(self):
        """unset VAR removes the variable from the environment."""
        self.shell.environment['RMVAR'] = 'remove_me'
        self.assertShellSuccess(self.shell, 'unset RMVAR')
        self.assertNotIn('RMVAR', self.shell.environment)

    def test_unset_nonexistent_variable_succeeds(self):
        """unset of a variable that does not exist returns 0."""
        self.assertShellSuccess(self.shell, 'unset VARIABLE_THAT_NEVER_EXISTED_XYZ')

    def test_unset_multiple_variables(self):
        """unset can remove multiple variables at once."""
        self.shell.environment['V1'] = 'a'
        self.shell.environment['V2'] = 'b'
        self.assertShellSuccess(self.shell, 'unset V1 V2')
        self.assertNotIn('V1', self.shell.environment)
        self.assertNotIn('V2', self.shell.environment)

    def test_export_then_unset(self):
        """A variable that was exported can be unset."""
        self.assertShellSuccess(self.shell, 'export CYCLE_VAR=hello')
        self.assertIn('CYCLE_VAR', self.shell.environment)
        self.assertShellSuccess(self.shell, 'unset CYCLE_VAR')
        self.assertNotIn('CYCLE_VAR', self.shell.environment)

    def test_unset_no_args_succeeds(self):
        """unset with no arguments returns 0 (nothing to do)."""
        # Behaviour: no arguments → nothing removed, exit 0
        exit_code = self.shell.execute('unset')
        self.assertEqual(exit_code, 0)
