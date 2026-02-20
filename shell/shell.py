"""
PureOS Shell
Command interpreter for the operating system.
"""

import sys
import shlex
import time
import fnmatch
import re
import posixpath
from io import StringIO
from typing import List, Dict, Callable, Optional, Tuple, Any
from pathlib import Path


class ShellCommand:
    """Base class for shell commands."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    def execute(self, args: List[str], shell) -> int:
        """Execute the command. Returns exit code."""
        raise NotImplementedError
    
    def get_help(self) -> str:
        """Get help text for the command."""
        return f"{self.name}: {self.description}"


class Shell:
    """Main shell interpreter."""

    _VAR_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

    def __init__(self, kernel, filesystem, authenticator=None, user_manager=None):
        self.kernel = kernel
        self.fs = filesystem
        self.auth = authenticator
        self.um = user_manager
        self.commands: Dict[str, ShellCommand] = {}
        self.running = False
        self.last_exit_code = 0
        self.aliases: Dict[str, str] = {
            'll': 'ls -la',
            'la': 'ls -a',
            'l': 'ls -CF',
        }
        self.environment: Dict[str, str] = {
            "PATH": "/bin",
            "HOME": "/root",
            "USER": "root",
            "HOSTNAME": "pureos",
            "SHELL": "/bin/sh",
            "TERM": "xterm",
            "PS1": "\\u@\\h:\\w\\$ ",
            "PS2": "> ",
        }
        # Command history
        self.history: List[str] = []
        self.history_position = 0
        # Job management
        self.job_manager = None
        try:
            from core.jobs import JobManager
            self.job_manager = JobManager(kernel)
        except:
            pass
        # Foreground job tracking
        self.foreground_job = None
        self.foreground_job_id = None
        # Here-doc line buffer (used by scripting engine)
        self._heredoc_lines: List[str] = []
        # Line editor for advanced input
        self.line_editor = None
        try:
            from shell.completion import LineEditor
            self.line_editor = LineEditor(self)
        except:
            pass
        # Package manager
        self.package_manager = None
        try:
            from core.package import PackageManager
            self.package_manager = PackageManager(filesystem)
        except:
            pass
        # Network manager
        self.network_manager = None
        try:
            from core.network import NetworkManager
            self.network_manager = NetworkManager()
        except:
            pass
        self._register_commands()
    
    def _register_commands(self) -> None:
        """Register all built-in commands."""
        # File operations
        self.register_command(LsCommand())
        self.register_command(CdCommand())
        self.register_command(PwdCommand())
        self.register_command(CatCommand())
        self.register_command(MkdirCommand())
        self.register_command(RmdirCommand())
        self.register_command(RmCommand())
        self.register_command(TouchCommand())
        self.register_command(CpCommand())
        self.register_command(MvCommand())
        self.register_command(ChmodCommand())
        self.register_command(ChownCommand())
        self.register_command(StatCommand())
        self.register_command(NanoCommand())
        self.register_command(GrepCommand())
        self.register_command(HeadCommand())
        self.register_command(TailCommand())
        self.register_command(WcCommand())
        self.register_command(CutCommand())
        self.register_command(SortCommand())
        self.register_command(UniqCommand())
        self.register_command(FindCommand())
        
        # System info
        self.register_command(PsCommand())
        self.register_command(KillCommand())
        self.register_command(UnameCommand())
        self.register_command(FreeCommand())
        self.register_command(DfCommand())
        
        # User management
        self.register_command(UseraddCommand())
        self.register_command(UserdelCommand())
        self.register_command(PasswdCommand())
        self.register_command(SuCommand())
        self.register_command(LoginCommand())
        self.register_command(LogoutCommand())
        self.register_command(WhoCommand())
        self.register_command(IdCommand())
        
        # Scripting
        self.register_command(BashCommand())
        self.register_command(SourceCommand())
        self.register_command(TestCommand())
        
        # Job control
        self.register_command(JobsCommand())
        self.register_command(FgCommand())
        self.register_command(BgCommand())
        self.register_command(WaitCommand())
        
        # Utilities
        self.register_command(EchoCommand())
        self.register_command(HelpCommand())
        self.register_command(ClearCommand())
        self.register_command(DateCommand())
        self.register_command(UptimeCommand())
        self.register_command(WhoamiCommand())
        self.register_command(EnvCommand())
        self.register_command(ExportCommand())
        self.register_command(UnsetCommand())
        self.register_command(HistoryCommand())
        self.register_command(WhichCommand())
        self.register_command(TypeCommand())
        self.register_command(BasenameCommand())
        self.register_command(DirnameCommand())
        self.register_command(SleepCommand())
        self.register_command(SaveCommand())
        self.register_command(LoadCommand())
        
        # Aliases
        self.register_command(AliasCommand())
        self.register_command(UnaliasCommand())

        # System
        self.register_command(RebootCommand())
        self.register_command(ShutdownCommand())
        self.register_command(ExitCommand())
        
        # Package manager
        try:
            from shell.pkgcommand import PkgCommand
            self.register_command(PkgCommand())
        except:
            pass
        
        # Network commands
        try:
            from shell.netcommand import (
                IfconfigCommand, PingCommand, NetstatCommand, IpCommand,
                HostnameCommand, TracerouteCommand, DigCommand, NslookupCommand,
                RouteCommand, ArpCommand
            )
            self.register_command(IfconfigCommand())
            self.register_command(PingCommand())
            self.register_command(NetstatCommand())
            self.register_command(IpCommand())
            self.register_command(HostnameCommand())
            self.register_command(TracerouteCommand())
            self.register_command(DigCommand())
            self.register_command(NslookupCommand())
            self.register_command(RouteCommand())
            self.register_command(ArpCommand())
        except:
            pass

        # v1.7 new commands
        self.register_command(LnCommand())
        self.register_command(DiffCommand())
        self.register_command(TeeCommand())
        self.register_command(TarCommand())
        self.register_command(CronCommand())
        self.register_command(TopCommand())
        # v1.8 commands
        self.register_command(SedCommand())
        self.register_command(AwkCommand())
        self.register_command(TrCommand())
        self.register_command(XargsCommand())
        self.register_command(MktempCommand())
        self.register_command(ReadlinkCommand())
        self.register_command(RealpathCommand())
        self.register_command(WatchCommand())
        self.register_command(FetchCommand())
        self.register_command(CalCommand())
        self.register_command(BcCommand())
        self.register_command(PrintfCommand())
        self.register_command(SeqCommand())
        self.register_command(YesCommand())
        self.register_command(StringsCommand())
        self.register_command(ExprCommand())
        self.register_command(RevCommand())
        # v1.9 commands
        self.register_command(GroupsCommand())
        self.register_command(PstreeCommand())
        self.register_command(VmstatCommand())
        self.register_command(LsofCommand())
        self.register_command(ZipCommand())
        self.register_command(UnzipCommand())
        self.register_command(DdCommand())
        self.register_command(NlCommand())
        self.register_command(OdCommand())
        self.register_command(XxdCommand())
        self.register_command(NohupCommand())
        self.register_command(MountCommand())
        self.register_command(UmountCommand())
        self.register_command(ColumnCommand())
        self.register_command(StraceCommand())
        self.register_command(InstallCommand())
        
        # v2.0 system commands (logging, IPC, services, resources)
        try:
            from shell.systemcommands import (
                DmesgCommand, LoggerCommand, JournalctlCommand,
                SystemctlCommand, UlimitCommand, IpcsCommand, CgroupCommand
            )
            self.register_command(DmesgCommand())
            self.register_command(LoggerCommand())
            self.register_command(JournalctlCommand())
            self.register_command(SystemctlCommand())
            self.register_command(UlimitCommand())
            self.register_command(IpcsCommand())
            self.register_command(CgroupCommand())
        except ImportError:
            pass

    def register_command(self, command: ShellCommand) -> None:
        """Register a command."""
        self.commands[command.name] = command
    
    def parse_input(self, line: str) -> Tuple[str, List[str]]:
        """Parse command line input."""
        line = line.strip()
        if not line:
            return "", []

        # Handle aliases
        for alias, expansion in self.aliases.items():
            if line.startswith(alias + " ") or line == alias:
                line = expansion + line[len(alias):]
                break

        # Expand environment variables
        line = self._expand_environment_variables(line)

        try:
            lex = shlex.shlex(line, posix=True)
            lex.whitespace_split = True
            lex.commenters = ''  # Don't treat # as comment (we handle it ourselves)
            parts = list(lex)
        except ValueError:
            parts = line.split()

        if not parts:
            return "", []

        # Expand wildcards in arguments (not command name)
        # Only expand if the pattern contains more than a bare '*' or '?'
        # (bare '*' alone should not be expanded to avoid breaking expr, etc.)
        _no_glob_cmds = {'expr', 'awk', 'sed', 'bc', 'printf', 'grep', 'find'}
        expanded_parts = [parts[0]]  # Keep command name as is
        skip_glob = parts[0] in _no_glob_cmds
        for arg in parts[1:]:
            if not skip_glob and ('*' in arg or '?' in arg or '[' in arg):
                # Don't expand pure operator symbols used in arithmetic/logic
                if arg in ('*', '?', '+', '-', '/', '%', '**'):
                    expanded_parts.append(arg)
                else:
                    matches = self._expand_wildcard(arg)
                    if matches:
                        expanded_parts.extend(matches)
                    else:
                        # No matches, keep original
                        expanded_parts.append(arg)
            else:
                expanded_parts.append(arg)

        return expanded_parts[0], expanded_parts[1:]

    def _expand_environment_variables(self, line: str) -> str:
        """Expand shell variables like $HOME, ${HOME}, and $? with quote-awareness."""
        result: List[str] = []
        i = 0
        in_single_quotes = False
        in_double_quotes = False

        while i < len(line):
            ch = line[i]

            # Preserve escaped characters, including escaped '$'.
            if ch == '\\' and i + 1 < len(line):
                result.append(ch)
                result.append(line[i + 1])
                i += 2
                continue

            if ch == "'" and not in_double_quotes:
                in_single_quotes = not in_single_quotes
                result.append(ch)
                i += 1
                continue

            if ch == '"' and not in_single_quotes:
                in_double_quotes = not in_double_quotes
                result.append(ch)
                i += 1
                continue

            # Match shell behavior: no expansion inside single quotes.
            if ch == '$' and not in_single_quotes:
                # Arithmetic expansion: $(( expr ))
                if i + 2 < len(line) and line[i+1:i+3] == '((':
                    end = line.find('))', i + 3)
                    if end != -1:
                        expr_str = line[i+3:end].strip()
                        # Expand variables inside the expression first
                        for var_name, var_val in self.environment.items():
                            try:
                                expr_str = expr_str.replace(f'${var_name}', var_val)
                                expr_str = expr_str.replace(var_name, var_val if var_val.lstrip('-').isdigit() else var_val)
                            except Exception:
                                pass
                        try:
                            arith_result = eval(expr_str, {"__builtins__": {}}, {})
                            result.append(str(int(arith_result)))
                        except Exception:
                            result.append('0')
                        i = end + 2
                        continue
                # Command substitution: $( cmd )
                if i + 1 < len(line) and line[i+1] == '(':
                    # Find matching closing paren
                    depth = 0
                    j = i + 1
                    while j < len(line):
                        if line[j] == '(':
                            depth += 1
                        elif line[j] == ')':
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    if j < len(line):
                        sub_cmd = line[i+2:j].strip()
                        old_stdout = sys.stdout
                        captured_io = StringIO()
                        sys.stdout = captured_io
                        try:
                            self.execute(sub_cmd, save_to_history=False)
                        except Exception:
                            pass
                        finally:
                            sys.stdout = old_stdout
                        sub_output = captured_io.getvalue().rstrip('\n')
                        result.append(sub_output)
                        i = j + 1
                        continue
                if i + 1 < len(line) and line[i + 1] == '{':
                    end_brace = line.find('}', i + 2)
                    if end_brace != -1:
                        name = line[i + 2:end_brace]
                        # Handle ${var:-default}, ${var:=default}, ${#var}
                        # IMPORTANT: ${#var} must be checked BEFORE plain $#
                        if name.startswith('#'):
                            var_name = name[1:]
                            val = self.environment.get(var_name, '')
                            result.append(str(len(val)))
                        elif ':-' in name:
                            var_name, default = name.split(':-', 1)
                            result.append(self.environment.get(var_name, '') or default)
                        elif ':=' in name:
                            var_name, default = name.split(':=', 1)
                            val = self.environment.get(var_name, '')
                            if not val:
                                self.environment[var_name] = default
                                val = default
                            result.append(val)
                        elif ':?' in name:
                            var_name, msg = name.split(':?', 1)
                            val = self.environment.get(var_name, '')
                            if not val:
                                print(f"bash: {var_name}: {msg}", file=sys.stderr)
                            else:
                                result.append(val)
                        elif ':+' in name:
                            var_name, alt = name.split(':+', 1)
                            val = self.environment.get(var_name, '')
                            result.append(alt if val else '')
                        elif self._VAR_NAME_PATTERN.match(name):
                            result.append(self.environment.get(name, ""))
                        i = end_brace + 1
                        continue
                elif i + 1 < len(line):
                    next_char = line[i + 1]
                    if next_char == '?':
                        result.append(str(self.last_exit_code))
                        i += 2
                        continue
                    if next_char == '#':
                        # $# = number of positional params (0 in interactive)
                        result.append(self.environment.get('#', '0'))
                        i += 2
                        continue
                    if next_char == '@' or next_char == '*':
                        result.append(self.environment.get('@', ''))
                        i += 2
                        continue
                    if next_char == '$':
                        import os as _os
                        result.append(str(_os.getpid()))
                        i += 2
                        continue
                    if next_char == '_' or next_char.isalpha():
                        j = i + 2
                        while j < len(line) and (line[j] == '_' or line[j].isalnum()):
                            j += 1
                        name = line[i + 1:j]
                        result.append(self.environment.get(name, ""))
                        i = j
                        continue

            result.append(ch)
            i += 1

        return ''.join(result)

    def _expand_wildcard(self, pattern: str) -> List[str]:
        """Expand wildcard pattern to matching files."""
        import fnmatch

        # Determine directory and file pattern
        if '/' in pattern:
            # Pattern with path
            if pattern.startswith('/'):
                # Absolute path
                dir_part = pattern.rsplit('/', 1)[0]
                file_pattern = pattern.rsplit('/', 1)[1]
            else:
                # Relative path
                current_dir = self.fs.get_current_directory()
                if '/' in pattern:
                    dir_part = pattern.rsplit('/', 1)[0]
                    file_pattern = pattern.rsplit('/', 1)[1]
                    if not dir_part.startswith('/'):
                        dir_part = current_dir + '/' + dir_part
                else:
                    dir_part = current_dir
                    file_pattern = pattern
        else:
            # Pattern in current directory
            dir_part = self.fs.get_current_directory()
            file_pattern = pattern

        # Normalize directory path
        dir_part = self._normalize_path(dir_part)

        # Get directory contents
        try:
            entries = self.fs.list_directory(dir_part)
        except:
            return []

        if not entries:
            return []

        # Match files against pattern
        matches = []
        for entry in entries:
            if fnmatch.fnmatch(entry.name, file_pattern):
                # Build full path
                if dir_part == '/':
                    full_path = '/' + entry.name
                else:
                    full_path = dir_part + '/' + entry.name
                matches.append(full_path)

        return sorted(matches)

    def _normalize_path(self, path: str) -> str:
        """Normalize a path."""
        # Remove double slashes
        while '//' in path:
            path = path.replace('//', '/')

        # Handle . and ..
        parts = path.split('/')
        result = []
        for part in parts:
            if part == '' or part == '.':
                continue
            elif part == '..':
                if result and result[-1] != '':
                    result.pop()
            else:
                result.append(part)

        normalized = '/' + '/'.join(result)
        return normalized if normalized != '' else '/'
    
    def _collect_heredoc(self, delimiter: str) -> str:
        """Collect here-doc lines from the pending heredoc buffer or interactively."""
        lines = []
        if self._heredoc_lines:
            # Already buffered from multi-line input
            for line in self._heredoc_lines:
                if line.strip() == delimiter:
                    break
                lines.append(line)
            self._heredoc_lines = []
        else:
            # Interactive: read until delimiter
            try:
                while True:
                    ln = input('> ')
                    if ln.strip() == delimiter:
                        break
                    lines.append(ln)
            except EOFError:
                pass
        return '\n'.join(lines) + '\n'

    def _preprocess_heredoc(self, line: str):
        """If line contains <<WORD, buffer the here-doc content and return (cmd, stdin_text)."""
        import re as _re
        m = _re.search(r'<<\s*([\'"]?)(\w+)\1', line)
        if not m:
            return line, None
        delim = m.group(2)
        cmd = line[:m.start()].strip()
        # The heredoc content follows the command (from _heredoc_lines or interactively)
        stdin_text = self._collect_heredoc(delim)
        return cmd, stdin_text

    def execute(self, line: str, save_to_history: bool = True) -> int:
        """Execute a command line."""
        stripped = line.strip()

        # Here-doc preprocessing  (cmd <<EOF … EOF)
        if '<<' in stripped:
            stripped, heredoc_stdin = self._preprocess_heredoc(stripped)
            if heredoc_stdin is not None:
                old_stdin = sys.stdin
                sys.stdin = StringIO(heredoc_stdin)
                try:
                    return self.execute(stripped, save_to_history=save_to_history)
                finally:
                    sys.stdin = old_stdin

        # Check for background execution (&)
        background = False
        if stripped.endswith('&'):
            background = True
            stripped = stripped[:-1].strip()
            line = stripped

        # Handle history commands
        if stripped == "!!":
            if not self.history:
                print("!!: event not found")
                return 1
            line = self.history[-1]
            print(f"{line}")
            return self.execute(line, save_to_history=False)

        if stripped.startswith("!") and stripped[1:].isdigit():
            n = int(stripped[1:])
            if n < 1 or n > len(self.history):
                print(f"{stripped}: event not found")
                return 1
            line = self.history[n - 1]
            print(f"{line}")
            return self.execute(line, save_to_history=False)

        # Save to history
        if save_to_history and stripped and not stripped.startswith("!"):
            self.history.append(stripped)
            self.history_position = len(self.history)

        # Handle boolean chains (&& / ||) before pipes
        bool_segments, bool_ops = self._split_boolean_chains(stripped)
        if len(bool_segments) > 1:
            return self._execute_boolean_chain(bool_segments, bool_ops, background)

        # Handle pipe chains: split on unquoted '|'
        pipe_segments = self._split_pipes(stripped)
        if len(pipe_segments) > 1:
            return self._execute_pipeline(pipe_segments, background)

        # Single command — parse redirections then execute
        return self._execute_single(line, background)

    def _split_pipes(self, line: str) -> List[str]:
        """Split a command line on unquoted pipe characters."""
        segments: List[str] = []
        current: List[str] = []
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '\\' and i + 1 < len(line) and not in_single:
                current.append(ch)
                current.append(line[i + 1])
                i += 2
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            if ch == '|' and not in_single and not in_double:
                segments.append(''.join(current).strip())
                current = []
                i += 1
                continue
            current.append(ch)
            i += 1
        segments.append(''.join(current).strip())
        return segments

    def _split_boolean_chains(self, line: str) -> Tuple[List[str], List[str]]:
        """Split a command line on unquoted && and || operators."""
        segments: List[str] = []
        operators: List[str] = []
        current: List[str] = []
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '\\' and i + 1 < len(line) and not in_single:
                current.append(ch)
                current.append(line[i + 1])
                i += 2
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            if not in_single and not in_double and i + 1 < len(line):
                pair = line[i:i + 2]
                if pair in ('&&', '||'):
                    segments.append(''.join(current).strip())
                    operators.append(pair)
                    current = []
                    i += 2
                    continue
            current.append(ch)
            i += 1
        segments.append(''.join(current).strip())
        return segments, operators

    def _execute_boolean_chain(self, segments: List[str], operators: List[str],
                               background: bool = False) -> int:
        """Execute command segments with &&/|| short-circuit semantics."""
        last_exit = 0
        for idx, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue

            if idx > 0:
                prev_op = operators[idx - 1]
                if prev_op == '&&' and last_exit != 0:
                    continue
                if prev_op == '||' and last_exit == 0:
                    continue

            # Boolean segments can contain pipes, so reuse execute() path
            last_exit = self.execute(segment, save_to_history=False)

        self.last_exit_code = last_exit
        return last_exit

    def _execute_pipeline(self, segments: List[str], background: bool = False) -> int:
        """Execute a pipeline of commands, connecting stdout → stdin."""
        pipeline_input: Optional[str] = None
        last_exit = 0

        for idx, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue

            # Parse redirections for this segment
            seg_cmd, both_file, both_append = self._parse_both_redirection(segment)
            seg_cmd, output_file, append_mode = self._parse_output_redirection(seg_cmd)
            seg_cmd, err_file, err_append = self._parse_error_redirection(seg_cmd)
            seg_cmd, input_file = self._parse_input_redirection(seg_cmd)

            if both_file:
                output_file = both_file
                append_mode = both_append
                err_file = both_file
                err_append = both_append

            command_name, args = self.parse_input(seg_cmd)
            if not command_name:
                continue

            # Build stdin
            old_stdin = sys.stdin
            if input_file is not None:
                content = self.fs.read_file(input_file)
                if content is None:
                    print(f"bash: {input_file}: No such file or directory")
                    return 1
                sys.stdin = StringIO(content.decode('utf-8', errors='replace'))
            elif pipeline_input is not None:
                sys.stdin = StringIO(pipeline_input)

            # Capture stdout/stderr (always for intermediate, or when redirecting)
            is_last = (idx == len(segments) - 1)
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            capture_output = (not is_last) or (output_file is not None)
            out_buf = StringIO() if capture_output else None
            err_buf = StringIO() if err_file is not None else None
            if out_buf:
                sys.stdout = out_buf
            if err_buf:
                sys.stderr = err_buf

            # Support 2>&1 by sharing stdout buffer
            if '2>&1' in seg_cmd and out_buf is not None:
                err_buf = out_buf
                sys.stderr = out_buf

            try:
                if command_name in self.commands:
                    try:
                        last_exit = self.commands[command_name].execute(args, self)
                    except Exception as e:
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr
                        sys.stdin = old_stdin
                        print(f"Error: {e}")
                        last_exit = 1
                else:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    sys.stdin = old_stdin
                    print(f"{command_name}: command not found")
                    last_exit = 127
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                sys.stdin = old_stdin

            # Handle output
            if out_buf:
                captured = out_buf.getvalue()
                out_buf.close()

                if output_file is not None:
                    existing = b""
                    if append_mode and self.fs.exists(output_file):
                        ex = self.fs.read_file(output_file)
                        if ex:
                            existing = ex
                    self.fs.write_file(output_file, existing + captured.encode('utf-8'))
                    pipeline_input = None
                else:
                    pipeline_input = captured
            else:
                pipeline_input = None

            if err_buf:
                captured_err = err_buf.getvalue()
                err_buf.close()
                existing_err = b""
                if err_append and self.fs.exists(err_file):
                    ex = self.fs.read_file(err_file)
                    if ex:
                        existing_err = ex
                self.fs.write_file(err_file, existing_err + captured_err.encode('utf-8'))

        self.last_exit_code = last_exit
        return last_exit

    def _parse_input_redirection(self, line: str) -> Tuple[str, Optional[str]]:
        """Parse stdin redirection (< file) from a command line.
        Returns (cleaned_line_without_<_part, input_file_or_None).
        Preserves any output redirection tokens in the returned line.
        """
        try:
            lexer = shlex.shlex(line, posix=True, punctuation_chars='<')
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            return line, None

        input_file = None
        result_tokens: List[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == '<' and i + 1 < len(tokens):
                input_file = tokens[i + 1]
                i += 2  # skip '<' and the filename
                continue
            elif token.startswith('<') and len(token) > 1:
                input_file = token[1:]
                i += 1
                continue
            result_tokens.append(token)
            i += 1

        if input_file is not None:
            return ' '.join(result_tokens).strip(), input_file
        return line, None

    def _execute_single(self, line: str, background: bool = False) -> int:
        """Execute a single (non-pipeline) command with full redirection support."""
        # Parse stdin redirection first
        line_no_stdin, input_file = self._parse_input_redirection(line)
        # Parse combined redirection (&> or &>>)
        line_cmd, both_file, both_append = self._parse_both_redirection(line_no_stdin)
        # Parse output redirection
        line_cmd, output_file, append_mode = self._parse_output_redirection(line_cmd)
        # Parse stderr redirection
        line_cmd, err_file, err_append = self._parse_error_redirection(line_cmd)

        if both_file:
            output_file = both_file
            append_mode = both_append
            err_file = both_file
            err_append = both_append

        command_name, args = self.parse_input(line_cmd)
        if not command_name:
            return 0

        if background and self.job_manager:
            return self._execute_background(command_name, args, line.strip())

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        output_buffer = None
        err_buffer = None

        # Set up stdin redirection
        if input_file is not None:
            content = self.fs.read_file(input_file)
            if content is None:
                print(f"bash: {input_file}: No such file or directory")
                return 1
            sys.stdin = StringIO(content.decode('utf-8', errors='replace'))

        if output_file and command_name in self.commands:
            output_buffer = StringIO()
            sys.stdout = output_buffer
        if err_file and command_name in self.commands:
            err_buffer = StringIO()
            sys.stderr = err_buffer

        # Support 2>&1 by sharing stdout buffer
        if '2>&1' in line_cmd and output_buffer is not None:
            err_buffer = output_buffer
            sys.stderr = output_buffer

        try:
            if command_name in self.commands:
                try:
                    self.last_exit_code = self.commands[command_name].execute(args, self)
                except Exception as e:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    sys.stdin = old_stdin
                    print(f"Error: {e}")
                    self.last_exit_code = 1
            else:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                sys.stdin = old_stdin
                print(f"{command_name}: command not found")
                self.last_exit_code = 127

            if output_file and output_buffer:
                sys.stdout = old_stdout
                output_content = output_buffer.getvalue()
                existing_content = b""
                if append_mode and self.fs.exists(output_file):
                    existing = self.fs.read_file(output_file)
                    if existing:
                        existing_content = existing
                new_content = existing_content + output_content.encode('utf-8')
                if not self.fs.write_file(output_file, new_content):
                    print(f"Cannot write to '{output_file}'")
                    self.last_exit_code = 1

            if err_file and err_buffer:
                sys.stderr = old_stderr
                err_content = err_buffer.getvalue()
                existing_err = b""
                if err_append and self.fs.exists(err_file):
                    existing = self.fs.read_file(err_file)
                    if existing:
                        existing_err = existing
                new_err = existing_err + err_content.encode('utf-8')
                if not self.fs.write_file(err_file, new_err):
                    print(f"Cannot write to '{err_file}'")
                    self.last_exit_code = 1
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            if output_buffer:
                output_buffer.close()
            if err_buffer:
                err_buffer.close()

        return self.last_exit_code

    def _parse_output_redirection(self, line: str) -> Tuple[str, Optional[str], bool]:
        """Parse output redirection in a command line, quote-aware.

        Supports both spaced and unspaced forms:
        - echo hello > file.txt
        - echo hello>>file.txt
        Does NOT strip quotes from the command portion.
        """
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '\\' and not in_single and i + 1 < len(line):
                i += 2
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == '>' and not in_single and not in_double:
                append = (i + 1 < len(line) and line[i + 1] == '>')
                op_len = 2 if append else 1
                cmd_part = line[:i].rstrip()
                rest = line[i + op_len:].lstrip()
                # Extract the filename (first token of rest)
                try:
                    fname_tokens = shlex.split(rest)
                except ValueError:
                    fname_tokens = rest.split()
                if not fname_tokens:
                    return line, None, False
                output_file = fname_tokens[0]
                return cmd_part, output_file, append
            i += 1
        return line, None, False

    def _parse_error_redirection(self, line: str) -> Tuple[str, Optional[str], bool]:
        """Parse stderr redirection (2> file or 2>> file) from a command line."""
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '\\' and not in_single and i + 1 < len(line):
                i += 2
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == '2' and not in_single and not in_double:
                if i + 1 < len(line) and line[i + 1] == '>':
                    # Handle 2>&1 specially
                    if i + 2 < len(line) and line[i + 2] == '&':
                        return line, None, False
                    append = (i + 2 < len(line) and line[i + 2] == '>')
                    op_len = 3 if append else 2
                    cmd_part = (line[:i] + line[i + op_len:]).rstrip()
                    rest = line[i + op_len:].lstrip()
                    try:
                        fname_tokens = shlex.split(rest)
                    except ValueError:
                        fname_tokens = rest.split()
                    if not fname_tokens:
                        return line, None, False
                    return cmd_part, fname_tokens[0], append
            i += 1
        return line, None, False

    def _parse_both_redirection(self, line: str) -> Tuple[str, Optional[str], bool]:
        """Parse combined stdout/stderr redirection (&> file or &>> file)."""
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '\\' and not in_single and i + 1 < len(line):
                i += 2
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == '&' and not in_single and not in_double:
                if i + 1 < len(line) and line[i + 1] == '>':
                    append = (i + 2 < len(line) and line[i + 2] == '>')
                    op_len = 3 if append else 2
                    cmd_part = (line[:i] + line[i + op_len:]).rstrip()
                    rest = line[i + op_len:].lstrip()
                    try:
                        fname_tokens = shlex.split(rest)
                    except ValueError:
                        fname_tokens = rest.split()
                    if not fname_tokens:
                        return line, None, False
                    return cmd_part, fname_tokens[0], append
            i += 1
        return line, None, False
    
    def _execute_background(self, command_name: str, args: List[str], 
                           command_line: str) -> int:
        """Execute a command in the background."""
        import threading
        
        if command_name not in self.commands:
            print(f"{command_name}: command not found")
            return 127
        
        def run_command():
            try:
                exit_code = self.commands[command_name].execute(args, self)
                if self.job_manager:
                    job = self.job_manager.get_job_by_pid(thread_id)
                    if job:
                        self.job_manager.finish_job(job.job_id, exit_code)
            except Exception as e:
                if self.job_manager:
                    job = self.job_manager.get_job_by_pid(thread_id)
                    if job:
                        self.job_manager.finish_job(job.job_id, 1)
        
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
        thread_id = thread.ident or 0
        
        job = self.job_manager.create_job(
            pid=thread_id,
            name=command_name,
            command=command_line,
            thread=thread
        )
        
        print(f"[{job.job_id}] {thread_id}")
        
        return 0
    
    def _check_background_jobs(self) -> None:
        """Check for completed background jobs and notify user."""
        if self.job_manager:
            notifications = self.job_manager.notify_completed()
            for notification in notifications:
                print(notification)
    
    def get_prompt(self, ps2: bool = False) -> str:
        """Generate shell prompt based on PS1/PS2 environment variables."""
        if ps2:
            ps = self.environment.get('PS2', '> ')
        else:
            ps = self.environment.get('PS1', '\\u@\\h:\\w\\$ ')

        # Get current values
        if self.auth and self.auth.is_authenticated():
            username = self.auth.get_current_user() or 'user'
        else:
            username = self.environment.get('USER', 'user')

        # Get hostname
        hostname = 'pureos'

        # Get working directory
        cwd = self.fs.get_current_directory()
        if self.auth:
            home = self.auth.get_user_home()
            if cwd.startswith(home):
                cwd = "~" + cwd[len(home):]

        # Get basename of cwd
        cwd_basename = cwd.split('/')[-1] if cwd != '/' else '/'

        # Get prompt character ($ for user, # for root)
        prompt_char = '#' if (self.auth and self.auth.get_current_uid() == 0) else '$'

        # Get current time
        import time
        current_time = time.strftime('%H:%M:%S')
        current_time_12h = time.strftime('%I:%M:%S')
        current_date = time.strftime('%a %b %d')

        # Replace escape sequences
        result = ps
        result = result.replace('\\u', username)
        result = result.replace('\\h', hostname)
        result = result.replace('\\H', hostname)
        result = result.replace('\\w', cwd)
        result = result.replace('\\W', cwd_basename)
        result = result.replace('\\$', prompt_char)
        result = result.replace('\\t', current_time)
        result = result.replace('\\T', current_time_12h)
        result = result.replace('\\d', current_date)
        result = result.replace('\\\\', '\\')
        result = result.replace('\\n', '\n')

        return result
    
    def run(self) -> None:
        """Run the shell interactively."""
        self.running = True

        print("PureOS Shell v1.8")
        print("Type 'help' for available commands")
        print("Use '!!' to repeat last command, '!n' to run command #n")
        print("Use 'command &' for background, 'jobs', 'fg', 'bg' for job control")
        print("Use 'cmd1 | cmd2' for pipes, 'cmd < file' for stdin redirection")
        print("Press Tab for completion, Ctrl+A/E for line editing")
        print()

        while self.running:
            try:
                self._check_background_jobs()

                prompt = self.get_prompt()

                # Use line editor if available, otherwise fallback to input()
                if self.line_editor:
                    try:
                        line = self.line_editor.read_line(prompt)
                    except:
                        line = input(prompt)
                else:
                    line = input(prompt)

                # Handle multi-line input (line continuation)
                while line.rstrip().endswith('\\'):
                    line = line[:-1]  # Remove backslash
                    ps2_prompt = self.get_prompt(ps2=True)
                    if self.line_editor:
                        try:
                            next_line = self.line_editor.read_line(ps2_prompt)
                        except:
                            next_line = input(ps2_prompt)
                    else:
                        next_line = input(ps2_prompt)
                    line += next_line

                self.execute(line)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print()
                self.running = False


# =============================================================================
# Built-in Commands
# =============================================================================

class LsCommand(ShellCommand):
    """List directory contents."""
    
    def __init__(self):
        super().__init__("ls", "List directory contents")
    
    def execute(self, args: List[str], shell) -> int:
        path = args[0] if args else "."
        entries = shell.fs.list_directory(path)
        
        if entries is None:
            print(f"ls: cannot access '{path}': No such file or directory")
            return 1
        
        # Sort entries
        entries.sort(key=lambda x: (x.type.value, x.name))
        
        # Check for -l flag
        long_format = "-l" in args or "-la" in args or "-al" in args
        show_all = "-a" in args or "-la" in args or "-al" in args
        
        for entry in entries:
            if not show_all and entry.name.startswith("."):
                continue
            
            if long_format:
                type_char = "d" if entry.type.value == "directory" else "-"
                print(f"{type_char}{entry.permissions} 1 {entry.owner} {entry.group} {entry.size:>8} {time.strftime('%b %d %H:%M', time.localtime(entry.modified))} {entry.name}")
            else:
                suffix = "/" if entry.type.value == "directory" else ""
                print(f"{entry.name}{suffix}")
        
        return 0


class CdCommand(ShellCommand):
    """Change directory."""
    
    def __init__(self):
        super().__init__("cd", "Change the current directory")
    
    def execute(self, args: List[str], shell) -> int:
        path = args[0] if args else shell.environment.get("HOME", "/")
        
        if not shell.fs.change_directory(path):
            print(f"cd: {path}: No such file or directory")
            return 1
        
        return 0


class PwdCommand(ShellCommand):
    """Print working directory."""
    
    def __init__(self):
        super().__init__("pwd", "Print name of current working directory")
    
    def execute(self, args: List[str], shell) -> int:
        print(shell.fs.get_current_directory())
        return 0


class CatCommand(ShellCommand):
    """Concatenate and print files."""
    
    def __init__(self):
        super().__init__("cat", "Concatenate files and print on the standard output")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            # Read from stdin (works with both real stdin and StringIO)
            try:
                data = sys.stdin.read()
                if data:
                    print(data, end='' if data.endswith('\n') else '\n')
            except EOFError:
                pass
            return 0
        
        for filename in args:
            content = shell.fs.read_file(filename)
            if content is None:
                print(f"cat: {filename}: No such file or directory")
                return 1
            print(content.decode('utf-8', errors='replace'), end='')
        
        return 0


class MkdirCommand(ShellCommand):
    """Make directories."""
    
    def __init__(self):
        super().__init__("mkdir", "Make directories")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("mkdir: missing operand")
            return 1
        
        parents = "-p" in args
        paths = [a for a in args if not a.startswith("-")]
        
        for path in paths:
            if not shell.fs.mkdir(path, parents=parents):
                print(f"mkdir: cannot create directory '{path}': File exists")
                return 1
        
        return 0


class RmdirCommand(ShellCommand):
    """Remove empty directories."""
    
    def __init__(self):
        super().__init__("rmdir", "Remove empty directories")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("rmdir: missing operand")
            return 1
        
        for path in args:
            if not shell.fs.rmdir(path):
                print(f"rmdir: failed to remove '{path}': Directory not empty or does not exist")
                return 1
        
        return 0


class RmCommand(ShellCommand):
    """Remove files or directories."""
    
    def __init__(self):
        super().__init__("rm", "Remove files or directories")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("rm: missing operand")
            return 1

        recursive = False
        force = False
        paths: List[str] = []
        parse_options = True

        for arg in args:
            if parse_options and arg == "--":
                parse_options = False
                continue

            if parse_options and arg.startswith("--"):
                if arg == "--recursive":
                    recursive = True
                    continue
                if arg == "--force":
                    force = True
                    continue
                print(f"rm: unrecognized option '{arg}'")
                return 1

            if parse_options and arg.startswith("-") and arg != "-":
                for flag in arg[1:]:
                    if flag == "r":
                        recursive = True
                    elif flag == "f":
                        force = True
                    else:
                        print(f"rm: invalid option -- '{flag}'")
                        return 1
                continue

            paths.append(arg)

        if not paths:
            print("rm: missing operand")
            return 1
        
        for path in paths:
            if shell.fs.is_directory(path):
                if not recursive:
                    if not force:
                        print(f"rm: cannot remove '{path}': Is a directory")
                    return 1
                if not shell.fs.remove_tree(path):
                    if not force:
                        print(f"rm: cannot remove '{path}': No such file or directory")
                    return 1
            else:
                if not shell.fs.delete_file(path):
                    if not force:
                        print(f"rm: cannot remove '{path}': No such file or directory")
                    return 1
        
        return 0


class TouchCommand(ShellCommand):
    """Create empty files."""
    
    def __init__(self):
        super().__init__("touch", "Create empty files")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("touch: missing file operand")
            return 1
        
        for path in args:
            if not shell.fs.exists(path):
                shell.fs.create_file(path)
        
        return 0


class CpCommand(ShellCommand):
    """Copy files and directories."""
    
    def __init__(self):
        super().__init__("cp", "Copy files and directories")
    
    def execute(self, args: List[str], shell) -> int:
        if len(args) < 2:
            print("cp: missing file operand")
            return 1
        
        src, dst = args[-2], args[-1]
        
        content = shell.fs.read_file(src)
        if content is None:
            print(f"cp: cannot stat '{src}': No such file or directory")
            return 1
        
        if not shell.fs.write_file(dst, content):
            print(f"cp: cannot create regular file '{dst}': Permission denied")
            return 1
        
        return 0


class MvCommand(ShellCommand):
    """Move/rename files and directories."""
    
    def __init__(self):
        super().__init__("mv", "Move/rename files and directories")
    
    def execute(self, args: List[str], shell) -> int:
        if len(args) < 2:
            print("mv: missing file operand")
            return 1
        
        src, dst = args[-2], args[-1]
        
        content = shell.fs.read_file(src)
        if content is None:
            print(f"mv: cannot stat '{src}': No such file or directory")
            return 1
        
        if not shell.fs.write_file(dst, content):
            print(f"mv: cannot move '{src}' to '{dst}': Permission denied")
            return 1
        
        shell.fs.delete_file(src)
        return 0


class ChmodCommand(ShellCommand):
    """Change file mode bits."""

    def __init__(self):
        super().__init__("chmod", "Change file permissions")

    def _parse_permissions(self, mode: str) -> Optional[str]:
        """Convert chmod mode into rwxrwxrwx-style permissions."""
        if len(mode) == 9 and all(ch in "rwx-" for ch in mode):
            return mode

        if len(mode) != 3 or any(ch not in "01234567" for ch in mode):
            return None

        symbolic = []
        for digit in mode:
            value = int(digit)
            symbolic.append("r" if value & 4 else "-")
            symbolic.append("w" if value & 2 else "-")
            symbolic.append("x" if value & 1 else "-")

        return "".join(symbolic)

    def execute(self, args: List[str], shell) -> int:
        if len(args) < 2:
            print("chmod: missing operand")
            print("Usage: chmod <permissions> <file> [file ...]")
            return 1

        permissions = self._parse_permissions(args[0])
        paths = args[1:]

        if permissions is None:
            print(f"chmod: invalid mode: '{args[0]}'")
            print("Use symbolic mode (rwxr-xr-x) or octal mode (755)")
            return 1

        for path in paths:
            if not shell.fs.chmod(path, permissions):
                print(f"chmod: cannot access '{path}': No such file or directory")
                return 1

        return 0


class ChownCommand(ShellCommand):
    """Change file owner and group."""

    def __init__(self):
        super().__init__("chown", "Change file owner and group")

    def execute(self, args: List[str], shell) -> int:
        if len(args) < 2:
            print("chown: missing operand")
            print("Usage: chown <owner>[:group] <file> [file ...]")
            return 1

        owner_spec = args[0]
        paths = args[1:]

        if ':' in owner_spec:
            owner, group = owner_spec.split(':', 1)
            if not owner and not group:
                print(f"chown: invalid spec: '{owner_spec}'")
                return 1
            if not owner:
                owner = None
            if not group:
                group = None
        else:
            owner, group = owner_spec, None

        for path in paths:
            inode = shell.fs.get_inode(path)
            if inode is None:
                print(f"chown: cannot access '{path}': No such file or directory")
                return 1

            new_owner = owner if owner is not None else inode.owner
            new_group = group if group is not None else inode.group

            if not shell.fs.chown(path, new_owner, new_group):
                print(f"chown: cannot access '{path}': No such file or directory")
                return 1

        return 0


class StatCommand(ShellCommand):
    """Display file or directory status."""

    def __init__(self):
        super().__init__("stat", "Display file or directory status")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("stat: missing operand")
            return 1

        exit_code = 0
        for path in args:
            info = shell.fs.stat(path)
            if info is None:
                print(f"stat: cannot stat '{path}': No such file or directory")
                exit_code = 1
                continue

            normalized_path = shell.fs._normalize_path(path)
            print(f"  File: {normalized_path}")
            print(f"  Type: {info['type']}")
            print(f"  Size: {info['size']} bytes")
            print(f"Access: ({info['permissions']})")
            print(f"Owner: {info['owner']}:{info['group']}")
            print(f"Modify: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info['modified']))}")
            print(f"Create: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info['created']))}")

        return exit_code


class PsCommand(ShellCommand):
    """Report process status."""
    
    def __init__(self):
        super().__init__("ps", "Report a snapshot of the current processes")
    
    def execute(self, args: List[str], shell) -> int:
        processes = shell.kernel.list_processes()
        
        print(f"{'PID':<8} {'NAME':<15} {'STATE':<12} {'CPU TIME':<12} {'MEMORY':<10}")
        print("-" * 65)
        
        for proc in processes:
            print(f"{proc.pid:<8} {proc.name:<15} {proc.state.value:<12} {proc.cpu_time:.2f}s{'':<6} {proc.memory_usage // 1024}KB")
        
        return 0


class KillCommand(ShellCommand):
    """Terminate a process."""
    
    def __init__(self):
        super().__init__("kill", "Send a signal to a process")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("kill: usage: kill <pid>")
            return 1
        
        try:
            pid = int(args[0])
        except ValueError:
            print(f"kill: invalid process id '{args[0]}'")
            return 1
        
        if not shell.kernel.terminate_process(pid):
            print(f"kill: ({pid}) - No such process")
            return 1
        
        return 0


class UnameCommand(ShellCommand):
    """Print system information."""
    
    def __init__(self):
        super().__init__("uname", "Print system information")
    
    def execute(self, args: List[str], shell) -> int:
        all_info = "-a" in args
        kernel_name = "-s" in args or all_info or not args
        nodename = "-n" in args or all_info
        kernel_release = "-r" in args or all_info
        machine = "-m" in args or all_info
        operating_system = "-o" in args or all_info
        
        info_parts = []
        
        if kernel_name:
            info_parts.append("PureOS")
        if nodename:
            info_parts.append("pureos")
        if kernel_release:
            info_parts.append("1.0.0")
        if machine:
            info_parts.append("python_vm")
        if operating_system:
            info_parts.append("PureOS")
        
        print(" ".join(info_parts))
        return 0


class FreeCommand(ShellCommand):
    """Display amount of free and used memory."""
    
    def __init__(self):
        super().__init__("free", "Display amount of free and used memory in the system")
    
    def execute(self, args: List[str], shell) -> int:
        info = shell.kernel.get_system_info()
        
        total = info["total_memory"]
        used = info["used_memory"]
        free = info["free_memory"]
        
        human_readable = "-h" in args
        
        def format_bytes(b):
            if human_readable:
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if b < 1024:
                        return f"{b:.1f}{unit}"
                    b /= 1024
                return f"{b:.1f}TB"
            return str(b)
        
        print(f"{'':>10} {'total':>12} {'used':>12} {'free':>12}")
        print(f"{'Mem:':>10} {format_bytes(total):>12} {format_bytes(used):>12} {format_bytes(free):>12}")
        
        return 0


class DfCommand(ShellCommand):
    """Report file system disk space usage."""
    
    def __init__(self):
        super().__init__("df", "Report file system disk space usage")
    
    def execute(self, args: List[str], shell) -> int:
        total_size = shell.fs.get_size()
        # Virtual disk with 100MB limit
        virtual_total = 100 * 1024 * 1024
        available = virtual_total - total_size
        used_percent = (total_size / virtual_total) * 100 if virtual_total > 0 else 0
        
        print(f"{'Filesystem':<20} {'Size':<10} {'Used':<10} {'Available':<10} {'Use%':<5} {'Mounted on'}")
        print(f"{'vfs':<20} {virtual_total // 1024 // 1024:<10}MB {total_size // 1024 // 1024:<10}MB {available // 1024 // 1024:<10}MB {int(used_percent):<5}% {'/'}")
        
        return 0


class EchoCommand(ShellCommand):
    """Display a line of text."""
    
    def __init__(self):
        super().__init__("echo", "Display a line of text")
    
    def execute(self, args: List[str], shell) -> int:
        no_newline = "-n" in args
        text = " ".join([a for a in args if not a.startswith("-")])
        
        if no_newline:
            print(text, end='')
        else:
            print(text)
        
        return 0


class HelpCommand(ShellCommand):
    """Display help information."""
    
    def __init__(self):
        super().__init__("help", "Display information about builtin commands")
    
    def execute(self, args: List[str], shell) -> int:
        if args:
            cmd_name = args[0]
            if cmd_name in shell.commands:
                print(shell.commands[cmd_name].get_help())
            else:
                print(f"help: no help topics match '{cmd_name}'")
                return 1
        else:
            print("PureOS Shell Commands:")
            print("=" * 50)
            
            categories = {
                "File Operations": ["ls", "cd", "pwd", "cat", "mkdir", "rmdir", "rm", "touch", "cp", "mv", "find"],
                "System Info": ["ps", "kill", "uname", "free", "df", "uptime"],
                "Utilities": ["echo", "help", "clear", "date", "whoami", "env", "export", "history", "which", "type"],
                "System": ["reboot", "shutdown", "exit"],
            }
            
            for category, commands in categories.items():
                print(f"\n{category}:")
                for cmd_name in commands:
                    if cmd_name in shell.commands:
                        cmd = shell.commands[cmd_name]
                        print(f"  {cmd.name:<15} {cmd.description}")
        
        return 0


class ClearCommand(ShellCommand):
    """Clear the terminal screen."""
    
    def __init__(self):
        super().__init__("clear", "Clear the terminal screen")
    
    def execute(self, args: List[str], shell) -> int:
        print("\033[2J\033[H", end='')
        return 0


class DateCommand(ShellCommand):
    """Print or set the system date and time."""
    
    def __init__(self):
        super().__init__("date", "Print or set the system date and time")
    
    def execute(self, args: List[str], shell) -> int:
        print(time.strftime("%a %b %d %H:%M:%S %Z %Y"))
        return 0


class UptimeCommand(ShellCommand):
    """Tell how long the system has been running."""

    def __init__(self):
        super().__init__("uptime", "Tell how long the system has been running")

    def execute(self, args: List[str], shell) -> int:
        uptime_seconds = shell.kernel.get_uptime()
        total_seconds = int(uptime_seconds)

        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        parts = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours or days:
            parts.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            parts.append(f"{minutes:02d}:{seconds:02d}")

        print(f"up {', '.join(parts)}")
        return 0


class WhoamiCommand(ShellCommand):
    """Print effective userid."""
    
    def __init__(self):
        super().__init__("whoami", "Print effective userid")
    
    def execute(self, args: List[str], shell) -> int:
        print(shell.environment.get("USER", "user"))
        return 0


class EnvCommand(ShellCommand):
    """Print environment variables."""
    
    def __init__(self):
        super().__init__("env", "Print environment")
    
    def execute(self, args: List[str], shell) -> int:
        for key, value in shell.environment.items():
            print(f"{key}={value}")
        return 0


class ExportCommand(ShellCommand):
    """Set environment variables."""
    
    def __init__(self):
        super().__init__("export", "Set environment variable")
    
    def execute(self, args: List[str], shell) -> int:
        if not args:
            # Print all exported variables
            return EnvCommand().execute(args, shell)

        status = 0
        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                if not shell._VAR_NAME_PATTERN.match(key):
                    print(f"export: `{key}`: not a valid identifier")
                    status = 1
                    continue
                shell.environment[key] = value
            elif arg in shell.environment:
                # Mark as exported (already in environment)
                pass
            else:
                if not shell._VAR_NAME_PATTERN.match(arg):
                    print(f"export: `{arg}`: not a valid identifier")
                    status = 1

        return status


class UnsetCommand(ShellCommand):
    """Unset environment variables."""

    def __init__(self):
        super().__init__("unset", "Unset environment variable")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("unset: usage: unset <name> [...]")
            return 1

        status = 0
        for name in args:
            if not shell._VAR_NAME_PATTERN.match(name):
                print(f"unset: `{name}`: not a valid identifier")
                status = 1
                continue

            shell.environment.pop(name, None)

        return status


class HistoryCommand(ShellCommand):
    """Show command history."""

    def __init__(self):
        super().__init__("history", "Show command history")

    def execute(self, args: List[str], shell) -> int:
        # Show last N commands (default: all)
        count = len(shell.history)
        if args:
            try:
                count = int(args[0])
            except ValueError:
                print(f"history: {args[0]}: invalid number")
                return 1

        start = max(0, len(shell.history) - count)
        for i, cmd in enumerate(shell.history[start:], start=start):
            print(f" {i+1:4d}  {cmd}")

        return 0


class WhichCommand(ShellCommand):
    """Locate a command."""

    def __init__(self):
        super().__init__("which", "Locate a command")

    def _find_in_path(self, name: str, shell) -> Optional[str]:
        if "/" in name:
            if shell.fs.exists(name) and not shell.fs.is_directory(name):
                return name
            return None

        path_env = shell.environment.get("PATH", "")
        for base in [p for p in path_env.split(":") if p]:
            candidate = base.rstrip("/") + "/" + name
            if shell.fs.exists(candidate) and not shell.fs.is_directory(candidate):
                return candidate
        return None

    def _find_all_in_path(self, name: str, shell) -> List[str]:
        if "/" in name:
            if shell.fs.exists(name) and not shell.fs.is_directory(name):
                return [name]
            return []

        matches: List[str] = []
        path_env = shell.environment.get("PATH", "")
        for base in [p for p in path_env.split(":") if p]:
            candidate = base.rstrip("/") + "/" + name
            if shell.fs.exists(candidate) and not shell.fs.is_directory(candidate):
                matches.append(candidate)
        return matches

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("which: usage: which [-a] <command> [...]")
            return 1

        show_all = False
        filtered_args: List[str] = []
        for arg in args:
            if arg == "-a":
                show_all = True
            else:
                filtered_args.append(arg)

        if not filtered_args:
            print("which: usage: which [-a] <command> [...]")
            return 1

        status = 0
        for name in filtered_args:
            found = False
            if name in shell.aliases:
                print(f"alias {name}='{shell.aliases[name]}'")
                found = True
                if not show_all:
                    continue

            if name in shell.commands:
                print(name)
                found = True
                if not show_all:
                    continue

            locations = self._find_all_in_path(name, shell) if show_all else [self._find_in_path(name, shell)]
            printed_locations = [loc for loc in locations if loc]
            for location in printed_locations:
                print(location)
            if printed_locations:
                found = True

            if not found:
                status = 1

        return status


class TypeCommand(ShellCommand):
    """Describe command type."""

    def __init__(self):
        super().__init__("type", "Describe command type")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("type: usage: type [-a] <command> [...]")
            return 1

        show_all = False
        filtered_args: List[str] = []
        for arg in args:
            if arg == "-a":
                show_all = True
            else:
                filtered_args.append(arg)

        if not filtered_args:
            print("type: usage: type [-a] <command> [...]")
            return 1

        which = WhichCommand()
        status = 0
        for name in filtered_args:
            found = False
            if name in shell.aliases:
                print(f"{name} is an alias for {shell.aliases[name]}")
                found = True
                if not show_all:
                    continue

            if name in shell.commands:
                print(f"{name} is a shell builtin")
                found = True
                if not show_all:
                    continue

            locations = which._find_all_in_path(name, shell) if show_all else [which._find_in_path(name, shell)]
            printed_locations = [loc for loc in locations if loc]
            for location in printed_locations:
                print(f"{name} is {location}")
            if printed_locations:
                found = True

            if not found:
                print(f"type: {name}: not found")
                status = 1

        return status


class BasenameCommand(ShellCommand):
    """Extract filename portion of a path."""

    def __init__(self):
        super().__init__("basename", "Strip directory and suffix from path")

    def execute(self, args: List[str], shell) -> int:
        if not args or len(args) > 2:
            print("basename: usage: basename <path> [suffix]")
            return 1

        path = args[0]
        suffix = args[1] if len(args) == 2 else ""

        stripped = path.rstrip("/")
        if not stripped:
            name = "/"
        else:
            name = posixpath.basename(stripped)

        if suffix and name.endswith(suffix) and name != suffix:
            name = name[:-len(suffix)]

        print(name)
        return 0


class DirnameCommand(ShellCommand):
    """Extract directory portion of a path."""

    def __init__(self):
        super().__init__("dirname", "Strip last path component")

    def execute(self, args: List[str], shell) -> int:
        if len(args) != 1:
            print("dirname: usage: dirname <path>")
            return 1

        path = args[0]
        stripped = path.rstrip("/")

        if not stripped:
            print("/")
            return 0

        directory = posixpath.dirname(stripped)
        print(directory if directory else ".")
        return 0


class RebootCommand(ShellCommand):
    """Reboot the system."""
    
    def __init__(self):
        super().__init__("reboot", "Reboot the system")
    
    def execute(self, args: List[str], shell) -> int:
        print("Rebooting system...")
        shell.running = False
        # In a real implementation, this would restart the kernel
        return 0


class ShutdownCommand(ShellCommand):
    """Power off the system."""
    
    def __init__(self):
        super().__init__("shutdown", "Power off the system")
    
    def execute(self, args: List[str], shell) -> int:
        print("Shutting down system...")
        shell.running = False
        shell.kernel.stop()
        return 0


class ExitCommand(ShellCommand):
    """Exit the shell."""

    def __init__(self):
        super().__init__("exit", "Exit the shell")

    def execute(self, args: List[str], shell) -> int:
        code = 0
        if args:
            try:
                code = int(args[0])
            except ValueError:
                pass

        shell.running = False
        return code


class NanoCommand(ShellCommand):
    """Text editor."""

    def __init__(self):
        super().__init__("nano", "Edit files")

    def execute(self, args: List[str], shell) -> int:
        filename = args[0] if args else None

        try:
            from bin.editor import edit_file
            return edit_file(shell.fs, filename)
        except ImportError:
            print("nano: editor module not available")
            return 1
        except Exception as e:
            print(f"nano: {e}")
            return 1


class GrepCommand(ShellCommand):
    """Search for patterns in files."""

    def __init__(self):
        super().__init__("grep", "Search for patterns in files")

    def execute(self, args: List[str], shell) -> int:
        ignore_case = False
        invert_match = False
        show_line_numbers = False
        positional: List[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--":
                positional.extend(args[i + 1:])
                break
            if arg == "-i":
                ignore_case = True
            elif arg == "-v":
                invert_match = True
            elif arg == "-n":
                show_line_numbers = True
            elif arg.startswith("-"):
                print(f"grep: invalid option -- '{arg}'")
                return 1
            else:
                positional.append(arg)
            i += 1

        if not positional:
            print("Usage: grep [-i] [-n] [-v] <pattern> <file...>")
            return 1

        pattern = positional[0]
        filenames = positional[1:]
        found = False

        match_pattern = pattern.lower() if ignore_case else pattern
        multiple_files = len(filenames) > 1

        # Read from stdin if no files given
        if not filenames:
            stdin_text = sys.stdin.read()
            stdin_lines = stdin_text.splitlines()
            for line_number, line in enumerate(stdin_lines, 1):
                candidate = line.lower() if ignore_case else line
                is_match = match_pattern in candidate
                if invert_match:
                    is_match = not is_match
                if not is_match:
                    continue
                prefix = f"{line_number}:" if show_line_numbers else ""
                print(f"{prefix}{line}")
                found = True
            return 0 if found else 1

        for filename in filenames:
            content = shell.fs.read_file(filename)
            if content is None:
                print(f"grep: {filename}: No such file or directory")
                return 1

            lines = content.decode('utf-8', errors='replace').splitlines()
            for line_number, line in enumerate(lines, 1):
                candidate = line.lower() if ignore_case else line
                is_match = match_pattern in candidate
                if invert_match:
                    is_match = not is_match

                if not is_match:
                    continue

                prefixes: List[str] = []
                if multiple_files:
                    prefixes.append(filename)
                if show_line_numbers:
                    prefixes.append(str(line_number))

                if prefixes:
                    print(f"{':'.join(prefixes)}:{line}")
                else:
                    print(line)
                found = True

        return 0 if found else 1


class HeadCommand(ShellCommand):
    """Output the first part of files."""

    def __init__(self):
        super().__init__("head", "Output the first part of files")

    def _parse_args(self, args: List[str]) -> Tuple[Optional[int], List[str], Optional[str]]:
        """Parse head-style options and return (line_count, files, error)."""
        lines_count = 10
        files: List[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-n":
                if i + 1 >= len(args):
                    return None, [], "head: option requires an argument -- 'n'"
                value = args[i + 1]
                i += 2
            elif arg.startswith("-n"):
                value = arg[2:]
                if not value:
                    return None, [], "head: option requires an argument -- 'n'"
                i += 1
            elif arg.startswith('-'):
                return None, [], f"head: invalid option -- '{arg}'"
            else:
                files.append(arg)
                i += 1
                continue

            try:
                lines_count = int(value)
            except ValueError:
                return None, [], f"head: invalid number of lines: '{value}'"

            if lines_count < 0:
                return None, [], f"head: invalid number of lines: '{value}'"

        return lines_count, files, None

    def execute(self, args: List[str], shell) -> int:
        lines_count, files, parse_error = self._parse_args(args)
        if parse_error:
            print(parse_error)
            return 1

        if not files:
            print("head: missing file operand")
            return 1

        for index, filename in enumerate(files):
            content = shell.fs.read_file(filename)
            if content is None:
                print(f"head: cannot open '{filename}' for reading: No such file or directory")
                return 1

            if len(files) > 1:
                if index > 0:
                    print()
                print(f"==> {filename} <==")

            lines = content.decode('utf-8', errors='replace').splitlines()
            for line in lines[:lines_count]:
                print(line)

        return 0


class TailCommand(ShellCommand):
    """Output the last part of files."""

    def __init__(self):
        super().__init__("tail", "Output the last part of files")

    def _parse_args(self, args: List[str]) -> Tuple[Optional[int], List[str], Optional[str]]:
        """Parse tail-style options and return (line_count, files, error)."""
        lines_count = 10
        files: List[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-n":
                if i + 1 >= len(args):
                    return None, [], "tail: option requires an argument -- 'n'"
                value = args[i + 1]
                i += 2
            elif arg.startswith("-n"):
                value = arg[2:]
                if not value:
                    return None, [], "tail: option requires an argument -- 'n'"
                i += 1
            elif arg.startswith('-'):
                return None, [], f"tail: invalid option -- '{arg}'"
            else:
                files.append(arg)
                i += 1
                continue

            try:
                lines_count = int(value)
            except ValueError:
                return None, [], f"tail: invalid number of lines: '{value}'"

            if lines_count < 0:
                return None, [], f"tail: invalid number of lines: '{value}'"

        return lines_count, files, None

    def execute(self, args: List[str], shell) -> int:
        lines_count, files, parse_error = self._parse_args(args)
        if parse_error:
            print(parse_error)
            return 1

        if not files:
            print("tail: missing file operand")
            return 1

        for index, filename in enumerate(files):
            content = shell.fs.read_file(filename)
            if content is None:
                print(f"tail: cannot open '{filename}' for reading: No such file or directory")
                return 1

            if len(files) > 1:
                if index > 0:
                    print()
                print(f"==> {filename} <==")

            lines = content.decode('utf-8', errors='replace').splitlines()
            start = max(0, len(lines) - lines_count)
            for line in lines[start:]:
                print(line)

        return 0


class WcCommand(ShellCommand):
    """Count lines, words, and bytes in files."""

    def __init__(self):
        super().__init__("wc", "Print line, word, and byte counts for files")

    def execute(self, args: List[str], shell) -> int:
        show_lines = False
        show_words = False
        show_bytes = False
        filenames = []

        parse_options = True
        for arg in args:
            if parse_options and arg == '--':
                parse_options = False
            elif parse_options and arg in ('-l', '-w', '-c'):
                if arg == '-l':
                    show_lines = True
                elif arg == '-w':
                    show_words = True
                elif arg == '-c':
                    show_bytes = True
            elif parse_options and arg.startswith('-') and arg != '-':
                # Support grouped flags like -lw and -lwc.
                if all(ch in 'lwc' for ch in arg[1:]):
                    show_lines = show_lines or ('l' in arg[1:])
                    show_words = show_words or ('w' in arg[1:])
                    show_bytes = show_bytes or ('c' in arg[1:])
                else:
                    print(f"wc: invalid option -- '{arg}'")
                    return 1
            else:
                filenames.append(arg)

        if not (show_lines or show_words or show_bytes):
            show_lines = True
            show_words = True
            show_bytes = True

        totals = {'lines': 0, 'words': 0, 'bytes': 0}

        # Match common wc behavior:
        # - No file operands => read stdin once.
        # - "-" => read stdin as a pseudo-file.
        sources = filenames if filenames else ['-']
        stdin_consumed = False

        for source in sources:
            if source == '-':
                if stdin_consumed:
                    content = b""
                else:
                    content = sys.stdin.read().encode('utf-8', errors='replace')
                    stdin_consumed = True
                display_name = '-'
            else:
                content = shell.fs.read_file(source)
                if content is None:
                    print(f"wc: {source}: No such file or directory")
                    return 1
                display_name = source

            text = content.decode('utf-8', errors='replace')
            line_count = len(text.splitlines())
            word_count = len(text.split())
            byte_count = len(content)

            totals['lines'] += line_count
            totals['words'] += word_count
            totals['bytes'] += byte_count

            output_parts = []
            if show_lines:
                output_parts.append(str(line_count))
            if show_words:
                output_parts.append(str(word_count))
            if show_bytes:
                output_parts.append(str(byte_count))
            output_parts.append(display_name)
            print(' '.join(output_parts))

        if len(sources) > 1:
            output_parts = []
            if show_lines:
                output_parts.append(str(totals['lines']))
            if show_words:
                output_parts.append(str(totals['words']))
            if show_bytes:
                output_parts.append(str(totals['bytes']))
            output_parts.append('total')
            print(' '.join(output_parts))

        return 0


class CutCommand(ShellCommand):
    """Extract sections from each line of files."""

    def __init__(self):
        super().__init__("cut", "Extract selected fields from each line of files")

    def _parse_field_spec(self, spec: str) -> Optional[List[int]]:
        fields = set()
        for chunk in spec.split(','):
            part = chunk.strip()
            if not part:
                return None

            if '-' in part:
                start_text, end_text = part.split('-', 1)
                if not start_text.isdigit() or not end_text.isdigit():
                    return None
                start = int(start_text)
                end = int(end_text)
                if start <= 0 or end <= 0 or start > end:
                    return None
                for idx in range(start, end + 1):
                    fields.add(idx)
            else:
                if not part.isdigit():
                    return None
                value = int(part)
                if value <= 0:
                    return None
                fields.add(value)

        return sorted(fields)

    def execute(self, args: List[str], shell) -> int:
        delimiter = '\t'
        field_spec = None
        filenames: List[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '-d':
                if i + 1 >= len(args):
                    print("cut: option requires an argument -- 'd'")
                    return 1
                delimiter = args[i + 1]
                if delimiter == "":
                    print("cut: the delimiter must be a single character")
                    return 1
                delimiter = delimiter[0]
                i += 2
            elif arg == '-f':
                if i + 1 >= len(args):
                    print("cut: option requires an argument -- 'f'")
                    return 1
                field_spec = args[i + 1]
                i += 2
            elif arg.startswith('-'):
                print(f"cut: invalid option -- '{arg}'")
                return 1
            else:
                filenames.append(arg)
                i += 1

        if field_spec is None:
            print("cut: you must specify a list of fields with -f")
            return 1

        if not filenames:
            print("cut: missing file operand")
            return 1

        fields = self._parse_field_spec(field_spec)
        if not fields:
            print(f"cut: invalid field list '{field_spec}'")
            return 1

        for filename in filenames:
            content = shell.fs.read_file(filename)
            if content is None:
                print(f"cut: {filename}: No such file or directory")
                return 1

            text = content.decode('utf-8', errors='replace')
            for line in text.splitlines():
                parts = line.split(delimiter)
                selected = []
                for field_number in fields:
                    index = field_number - 1
                    if 0 <= index < len(parts):
                        selected.append(parts[index])
                print(delimiter.join(selected))

        return 0


class SortCommand(ShellCommand):
    """Sort lines of text files."""

    def __init__(self):
        super().__init__("sort", "Sort lines of text files")

    def execute(self, args: List[str], shell) -> int:
        reverse = False
        unique = False
        filenames: List[str] = []

        for arg in args:
            if arg == '-r':
                reverse = True
            elif arg == '-u':
                unique = True
            elif arg.startswith('-'):
                print(f"sort: invalid option -- '{arg}'")
                return 1
            else:
                filenames.append(arg)

        all_lines: List[str] = []

        if not filenames:
            # Read from stdin
            all_lines = sys.stdin.read().splitlines()
        else:
            for filename in filenames:
                content = shell.fs.read_file(filename)
                if content is None:
                    print(f"sort: cannot read '{filename}': No such file or directory")
                    return 1
                lines = content.decode('utf-8', errors='replace').splitlines()
                all_lines.extend(lines)

        sorted_lines = sorted(all_lines, reverse=reverse)
        if unique:
            deduped: List[str] = []
            prev = None
            for line in sorted_lines:
                if line != prev:
                    deduped.append(line)
                    prev = line
            sorted_lines = deduped

        for line in sorted_lines:
            print(line)

        return 0


class UniqCommand(ShellCommand):
    """Report or omit repeated lines."""

    def __init__(self):
        super().__init__("uniq", "Filter adjacent matching lines from files")

    def execute(self, args: List[str], shell) -> int:
        count = False
        repeated_only = False
        unique_only = False
        filenames: List[str] = []

        for arg in args:
            if arg == '-c':
                count = True
            elif arg == '-d':
                repeated_only = True
            elif arg == '-u':
                unique_only = True
            elif arg.startswith('-'):
                print(f"uniq: invalid option -- '{arg}'")
                return 1
            else:
                filenames.append(arg)

        if repeated_only and unique_only:
            print("uniq: options '-d' and '-u' are mutually exclusive")
            return 1

        if len(filenames) > 1:
            print("uniq: extra operand")
            return 1

        if not filenames:
            # Read from stdin
            lines = sys.stdin.read().splitlines()
        else:
            content = shell.fs.read_file(filenames[0])
            if content is None:
                print(f"uniq: {filenames[0]}: No such file or directory")
                return 1
            lines = content.decode('utf-8', errors='replace').splitlines()
        groups: List[Tuple[str, int]] = []

        for line in lines:
            if groups and groups[-1][0] == line:
                groups[-1] = (line, groups[-1][1] + 1)
            else:
                groups.append((line, 1))

        for line, line_count in groups:
            if repeated_only and line_count < 2:
                continue
            if unique_only and line_count != 1:
                continue

            if count:
                print(f"{line_count} {line}")
            else:
                print(line)

        return 0


class FindCommand(ShellCommand):
    """Search for files and directories."""

    def __init__(self):
        super().__init__("find", "Search for files and directories")

    def execute(self, args: List[str], shell) -> int:
        start_path = "."
        name_pattern = None
        type_filter = None
        max_depth: Optional[int] = None
        min_depth = 0

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-name":
                if i + 1 >= len(args):
                    print("find: missing argument to '-name'")
                    return 1
                name_pattern = args[i + 1]
                i += 2
            elif arg == "-maxdepth":
                if i + 1 >= len(args):
                    print("find: missing argument to '-maxdepth'")
                    return 1
                try:
                    max_depth = int(args[i + 1])
                except ValueError:
                    print(f"find: invalid max depth '{args[i + 1]}'")
                    return 1
                if max_depth < 0:
                    print(f"find: invalid max depth '{args[i + 1]}'")
                    return 1
                i += 2
            elif arg == "-mindepth":
                if i + 1 >= len(args):
                    print("find: missing argument to '-mindepth'")
                    return 1
                try:
                    min_depth = int(args[i + 1])
                except ValueError:
                    print(f"find: invalid min depth '{args[i + 1]}'")
                    return 1
                if min_depth < 0:
                    print(f"find: invalid min depth '{args[i + 1]}'")
                    return 1
                i += 2
            elif arg == "-type":
                if i + 1 >= len(args):
                    print("find: missing argument to '-type'")
                    return 1
                type_filter = args[i + 1]
                if type_filter not in ("f", "d"):
                    print(f"find: unsupported type '{type_filter}' (use 'f' or 'd')")
                    return 1
                i += 2
            elif arg.startswith("-"):
                print(f"find: unknown option '{arg}'")
                return 1
            else:
                if start_path != ".":
                    print(f"find: unexpected argument '{arg}'")
                    return 1
                start_path = arg
                i += 1

        root = shell.fs._normalize_path(start_path)
        if not shell.fs.exists(root):
            print(f"find: '{start_path}': No such file or directory")
            return 1

        if max_depth is not None and min_depth > max_depth:
            print("find: min depth cannot be greater than max depth")
            return 1

        matches = []
        pending: List[Tuple[str, int]] = [(root, 0)]

        while pending:
            current_path, depth = pending.pop()
            inode = shell.fs.get_inode(current_path)
            if inode is None:
                continue

            is_match = True
            if depth < min_depth:
                is_match = False
            if max_depth is not None and depth > max_depth:
                is_match = False
            if name_pattern and not fnmatch.fnmatch(inode.name, name_pattern):
                is_match = False

            if type_filter == "f" and inode.type.value != "regular":
                is_match = False
            elif type_filter == "d" and inode.type.value != "directory":
                is_match = False

            if is_match:
                matches.append(current_path)

            should_descend = max_depth is None or depth < max_depth
            if should_descend and inode.type.value == "directory" and isinstance(inode.content, dict):
                for child_name in sorted(inode.content.keys(), reverse=True):
                    pending.append((inode.content[child_name], depth + 1))

        for path in sorted(matches):
            print(path)

        return 0


class SaveCommand(ShellCommand):
    """Save system state to disk."""

    def __init__(self):
        super().__init__("save", "Save system state")

    def execute(self, args: List[str], shell) -> int:
        try:
            from core.persistence import PersistenceManager
            pm = PersistenceManager()
            if pm.save_state(shell.fs, shell, shell.kernel):
                print("System state saved successfully")
                return 0
            else:
                print("Failed to save system state")
                return 1
        except Exception as e:
            print(f"save: {e}")
            return 1


class LoadCommand(ShellCommand):
    """Load system state from disk."""

    def __init__(self):
        super().__init__("load", "Load system state")

    def execute(self, args: List[str], shell) -> int:
        try:
            from core.persistence import PersistenceManager
            pm = PersistenceManager()

            if not pm.state_exists():
                print("No saved state found")
                return 1

            info = pm.get_state_info()
            if info:
                print(f"Found saved state:")
                print(f"  Files: {info['files']}")
                print(f"  Directories: {info['directories']}")
                print(f"  History: {info['history_count']} commands")
                print(f"  Directory: {info['current_directory']}")

            print("\nLoad this state? (y/n): ", end='')
            if input().lower() != 'y':
                print("Load cancelled")
                return 0

            if pm.load_state(shell.fs, shell, shell.kernel):
                print("System state loaded successfully")
                return 0
            else:
                print("Failed to load system state")
                return 1
        except Exception as e:
            print(f"load: {e}")
            return 1


class UseraddCommand(ShellCommand):
    """Create a new user account."""

    def __init__(self):
        super().__init__("useradd", "Create a new user account")

    def execute(self, args: List[str], shell) -> int:
        if not shell.um:
            print("useradd: user management not available")
            return 1

        # Check if running as root
        if shell.auth and shell.auth.get_current_uid() != 0:
            print("useradd: Permission denied (requires root)")
            return 1

        # Parse options
        create_home = False
        shell_path = "/bin/sh"
        username = None

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-m":
                create_home = True
                i += 1
            elif arg == "-s" and i + 1 < len(args):
                shell_path = args[i + 1]
                i += 2
            elif not arg.startswith("-"):
                username = arg
                i += 1
            else:
                print(f"useradd: invalid option -- '{arg}'")
                return 1

        if not username:
            print("Usage: useradd [-m] [-s shell] username")
            return 1

        # Create user
        success, msg = shell.um.create_user(
            username=username,
            password="",  # Empty password initially
            shell=shell_path,
            create_home=create_home
        )

        if success:
            print(msg)
            print(f"Set password with: passwd {username}")
            return 0
        else:
            print(f"useradd: {msg}")
            return 1


class UserdelCommand(ShellCommand):
    """Delete a user account."""

    def __init__(self):
        super().__init__("userdel", "Delete a user account")

    def execute(self, args: List[str], shell) -> int:
        if not shell.um:
            print("userdel: user management not available")
            return 1

        # Check if running as root
        if shell.auth and shell.auth.get_current_uid() != 0:
            print("userdel: Permission denied (requires root)")
            return 1

        remove_home = False
        username = None

        for arg in args:
            if arg == "-r":
                remove_home = True
            elif not arg.startswith("-"):
                username = arg
            else:
                print(f"userdel: invalid option -- '{arg}'")
                return 1

        if not username:
            print("Usage: userdel [-r] username")
            return 1

        success, msg = shell.um.delete_user(username, remove_home)

        if success:
            print(msg)
            return 0
        else:
            print(f"userdel: {msg}")
            return 1


class PasswdCommand(ShellCommand):
    """Change user password."""

    def __init__(self):
        super().__init__("passwd", "Change user password")

    def execute(self, args: List[str], shell) -> int:
        if not shell.um or not shell.auth:
            print("passwd: user management not available")
            return 1

        # Determine which user to change password for
        if args:
            target_user = args[0]
            # Only root can change other users' passwords
            if shell.auth.get_current_uid() != 0:
                print("passwd: Only root can change other users' passwords")
                return 1
        else:
            target_user = shell.auth.get_current_user()

        if not shell.um.user_exists(target_user):
            print(f"passwd: user '{target_user}' does not exist")
            return 1

        # Get new password
        import getpass
        try:
            new_pass = getpass.getpass(f"Enter new password for {target_user}: ")
            confirm_pass = getpass.getpass("Retype new password: ")

            if new_pass != confirm_pass:
                print("passwd: passwords do not match")
                return 1

            success, msg = shell.um.change_password(target_user, new_pass)

            if success:
                print(f"passwd: password updated successfully")
                return 0
            else:
                print(f"passwd: {msg}")
                return 1
        except (EOFError, KeyboardInterrupt):
            print("\npasswd: cancelled")
            return 1


class SuCommand(ShellCommand):
    """Switch user."""

    def __init__(self):
        super().__init__("su", "Switch user")

    def execute(self, args: List[str], shell) -> int:
        if not shell.auth or not shell.um:
            print("su: authentication not available")
            return 1

        # Default to root if no username given
        target_user = args[0] if args else "root"

        if not shell.um.user_exists(target_user):
            print(f"su: user '{target_user}' does not exist")
            return 1

        # Get password
        import getpass
        try:
            password = getpass.getpass(f"Password: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 1

        # Attempt authentication
        success, result = shell.auth.switch_user(target_user, password)

        if success:
            # Update environment
            user = shell.um.get_user(target_user)
            if user:
                shell.environment["USER"] = target_user
                shell.environment["HOME"] = user.home_dir
                # Change to user's home directory
                shell.fs.change_directory(user.home_dir)
            print(f"Switched to user '{target_user}'")
            return 0
        else:
            print(f"su: Authentication failure")
            return 1


class LoginCommand(ShellCommand):
    """Login as a user."""

    def __init__(self):
        super().__init__("login", "Login as a user")

    def execute(self, args: List[str], shell) -> int:
        if not shell.auth or not shell.um:
            print("login: authentication not available")
            return 1

        username = args[0] if args else None

        if not username:
            username = input("Username: ")

        if not username:
            print("login: no username specified")
            return 1

        if not shell.um.user_exists(username):
            print(f"login: user '{username}' does not exist")
            return 1

        # Get password
        import getpass
        try:
            password = getpass.getpass("Password: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 1

        # Attempt login
        success, result = shell.auth.login(username, password)

        if success:
            # Update environment
            user = shell.um.get_user(username)
            if user:
                shell.environment["USER"] = username
                shell.environment["HOME"] = user.home_dir
                # Change to user's home directory
                shell.fs.change_directory(user.home_dir)

            # Show login info
            import time
            print(f"\nWelcome to PureOS!")
            if user and user.last_login:
                print(f"Last login: {time.ctime(user.last_login)}")
            print()
            return 0
        else:
            print(f"login: {result}")
            return 1


class LogoutCommand(ShellCommand):
    """Logout current user."""

    def __init__(self):
        super().__init__("logout", "Logout current user")

    def execute(self, args: List[str], shell) -> int:
        if not shell.auth:
            print("logout: not logged in")
            return 1

        current_user = shell.auth.get_current_user()
        shell.auth.logout()

        print(f"User '{current_user}' logged out")

        # If we were root, stop the shell
        # Otherwise, we might want to switch back to a login prompt
        # For now, just return success
        return 0


class WhoCommand(ShellCommand):
    """Show who is logged in."""

    def __init__(self):
        super().__init__("who", "Show who is logged in")

    def execute(self, args: List[str], shell) -> int:
        if not shell.auth:
            print("who: authentication not available")
            return 1

        sessions = shell.auth.list_active_sessions()

        if not sessions:
            print("No active sessions")
            return 0

        print(f"{'USERNAME':<15} {'UID':<8} {'LOGIN TIME':<25}")
        print("-" * 50)

        import time
        for session in sessions:
            login_time = time.ctime(session["login_time"])
            print(f"{session['username']:<15} {session['uid']:<8} {login_time:<25}")

        return 0


class IdCommand(ShellCommand):
    """Print user identity."""

    def __init__(self):
        super().__init__("id", "Print user identity")

    def execute(self, args: List[str], shell) -> int:
        if not shell.auth or not shell.um:
            print("id: authentication not available")
            return 1

        # Determine which user to show
        if args:
            username = args[0]
            user = shell.um.get_user(username)
            if not user:
                print(f"id: '{username}': no such user")
                return 1
        else:
            username = shell.auth.get_current_user()
            user = shell.um.get_user(username)

        if not user:
            print("id: cannot determine user")
            return 1

        # Get user's groups
        groups = shell.um.get_user_groups(username)
        group_ids = []
        for group_name in groups:
            group = shell.um.get_group(group_name)
            if group:
                group_ids.append(f"{group_name}({group.gid})")

        print(f"uid={user.uid}({user.username}) gid={user.gid}({user.username})")
        if group_ids:
            print(f"groups={','.join(group_ids)}")

        return 0


class BashCommand(ShellCommand):
    """Execute shell scripts."""

    def __init__(self):
        super().__init__("bash", "Execute shell script")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: bash <script> [args...]")
            return 1

        script_file = args[0]
        script_args = args[1:]

        try:
            from shell.scripting import execute_script_file
            return execute_script_file(script_file, shell, shell.fs, shell.kernel, script_args)
        except ImportError as e:
            print(f"bash: scripting engine not available: {e}")
            return 1
        except Exception as e:
            print(f"bash: error executing script: {e}")
            return 1


class SourceCommand(ShellCommand):
    """Source a script (execute in current shell)."""

    def __init__(self):
        super().__init__("source", "Execute script in current shell")
        self.aliases = ["."]

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: source <script>")
            return 1

        script_file = args[0]

        try:
            from shell.scripting import execute_script_file
            return execute_script_file(script_file, shell, shell.fs, shell.kernel, args[1:])
        except Exception as e:
            print(f"source: {e}")
            return 1


class TestCommand(ShellCommand):
    """Evaluate conditional expressions."""

    def __init__(self):
        super().__init__("test", "Evaluate conditional expression")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            return 1  # False

        # Remove trailing ] if present (for [ command)
        if args[-1] == ']':
            args = args[:-1]

        # File tests
        if args[0].startswith('-') and len(args) >= 2:
            test = args[0]
            filename = args[1]

            if test == '-f':
                return 0 if shell.fs.is_file(filename) else 1
            elif test == '-d':
                return 0 if shell.fs.is_directory(filename) else 1
            elif test == '-e':
                return 0 if shell.fs.exists(filename) else 1
            elif test == '-s':
                inode = shell.fs.get_inode(filename)
                return 0 if (inode and inode.size > 0) else 1

        # String tests
        if len(args) == 3:
            left = args[0]
            op = args[1]
            right = args[2]

            if op == '=':
                return 0 if left == right else 1
            elif op == '!=':
                return 0 if left != right else 1

        # Numeric tests
        if len(args) == 3:
            try:
                left = int(args[0])
                op = args[1]
                right = int(args[2])

                if op == '-eq':
                    return 0 if left == right else 1
                elif op == '-ne':
                    return 0 if left != right else 1
                elif op == '-lt':
                    return 0 if left < right else 1
                elif op == '-le':
                    return 0 if left <= right else 1
                elif op == '-gt':
                    return 0 if left > right else 1
                elif op == '-ge':
                    return 0 if left >= right else 1
            except ValueError:
                pass

        # String unary tests
        if args[0] == '-z' and len(args) >= 2:
            return 0 if len(args[1]) == 0 else 1

        if args[0] == '-n' and len(args) >= 2:
            return 0 if len(args[1]) > 0 else 1

        return 1  # False


class AliasCommand(ShellCommand):
    """Define or display aliases."""

    def __init__(self):
        super().__init__("alias", "Define or display aliases")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            # Display all aliases
            for name, value in sorted(shell.aliases.items()):
                print(f"alias {name}='{value}'")
            return 0

        # Check if it's a definition or query
        arg = ' '.join(args)

        if '=' in arg:
            # Defining an alias: name='value' or name=value
            parts = arg.split('=', 1)
            name = parts[0].strip()
            value = parts[1].strip()

            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            shell.aliases[name] = value
            return 0
        else:
            # Querying specific alias
            name = arg.strip()
            if name in shell.aliases:
                print(f"alias {name}='{shell.aliases[name]}'")
                return 0
            else:
                print(f"alias: {name}: not found")
                return 1


class UnaliasCommand(ShellCommand):
    """Remove alias definitions."""

    def __init__(self):
        super().__init__("unalias", "Remove alias definitions")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: unalias [-a] name [name ...]")
            return 1

        if args[0] == '-a':
            # Remove all aliases
            shell.aliases.clear()
            return 0

        # Remove specific aliases
        exit_code = 0
        for name in args:
            if name in shell.aliases:
                del shell.aliases[name]
            else:
                print(f"unalias: {name}: not found")
                exit_code = 1

        return exit_code


class JobsCommand(ShellCommand):
    """List active jobs."""

    def __init__(self):
        super().__init__("jobs", "List active jobs")

    def execute(self, args: List[str], shell) -> int:
        if not shell.job_manager:
            print("jobs: job control not available")
            return 1

        show_pid = "-l" in args or "-p" in args

        jobs = shell.job_manager.list_jobs()
        if not jobs:
            return 0

        for line in shell.job_manager.format_jobs_list(show_pid):
            print(line)

        return 0


class FgCommand(ShellCommand):
    """Bring a job to the foreground."""

    def __init__(self):
        super().__init__("fg", "Bring job to foreground")

    def execute(self, args: List[str], shell) -> int:
        if not shell.job_manager:
            print("fg: job control not available")
            return 1

        job_spec = args[0] if args else None
        job = shell.job_manager.parse_job_spec(job_spec or '')

        if not job:
            if job_spec:
                print(f"fg: {job_spec}: no such job")
            else:
                print("fg: no current job")
            return 1

        if job.state.value == "Stopped":
            if shell.job_manager.continue_job(job.job_id, background=False):
                print(job.command)
            else:
                print(f"fg: {job.job_id}: could not continue job")
                return 1
        elif job.state.value == "Running":
            print(job.command)
        else:
            print(f"fg: {job.job_id}: job has terminated")
            return 1

        shell.foreground_job = job
        shell.foreground_job_id = job.job_id

        if job.thread and job.thread.is_alive():
            job.thread.join()

        shell.foreground_job = None
        shell.foreground_job_id = None

        if shell.job_manager.get_job(job.job_id):
            shell.job_manager.finish_job(job.job_id, job.exit_code or 0)

        return job.exit_code or 0


class BgCommand(ShellCommand):
    """Resume a stopped job in the background."""

    def __init__(self):
        super().__init__("bg", "Resume job in background")

    def execute(self, args: List[str], shell) -> int:
        if not shell.job_manager:
            print("bg: job control not available")
            return 1

        job_spec = args[0] if args else None
        job = shell.job_manager.parse_job_spec(job_spec or '')

        if not job:
            if job_spec:
                print(f"bg: {job_spec}: no such job")
            else:
                print("bg: no current job")
            return 1

        if job.state.value != "Stopped":
            print(f"bg: job {job.job_id} already in background")
            return 1

        if shell.job_manager.continue_job(job.job_id, background=True):
            print(f"[{job.job_id}] {job.command}")
            return 0
        else:
            print(f"bg: {job.job_id}: could not continue job")
            return 1


class WaitCommand(ShellCommand):
    """Wait for background jobs to complete."""

    def __init__(self):
        super().__init__("wait", "Wait for background jobs")

    def execute(self, args: List[str], shell) -> int:
        if not shell.job_manager:
            print("wait: job control not available")
            return 1

        if args:
            job = shell.job_manager.parse_job_spec(args[0])
            if not job:
                print(f"wait: {args[0]}: no such job")
                return 1

            if job.thread and job.thread.is_alive():
                job.thread.join()

            shell.job_manager.finish_job(job.job_id, job.exit_code or 0)
            return job.exit_code or 0
        else:
            jobs = shell.job_manager.list_jobs()
            for job in jobs:
                if job.thread and job.thread.is_alive():
                    job.thread.join()
                shell.job_manager.finish_job(job.job_id, job.exit_code or 0)

            return 0


class SleepCommand(ShellCommand):
    """Pause for a specified amount of time."""

    def __init__(self):
        super().__init__("sleep", "Pause for specified seconds")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("sleep: missing operand")
            return 1

        try:
            seconds = float(args[0])
            if seconds < 0:
                print("sleep: invalid time interval")
                return 1
            time.sleep(seconds)
            return 0
        except ValueError:
            print(f"sleep: invalid time interval '{args[0]}'")
            return 1


# =============================================================================
# v1.7 New Commands
# =============================================================================

class LnCommand(ShellCommand):
    """Create hard or symbolic links."""

    def __init__(self):
        super().__init__("ln", "Create links between files")

    def execute(self, args: List[str], shell) -> int:
        symbolic = "-s" in args
        paths = [a for a in args if not a.startswith("-")]

        if len(paths) < 2:
            print("ln: missing file operand")
            print("Usage: ln [-s] <target> <link_name>")
            return 1

        target = paths[0]
        link_name = paths[1]

        if symbolic:
            # Symlink: store target path in inode
            from core.filesystem import Inode, FileType
            import os as _os
            link_path = shell.fs._normalize_path(link_name)
            if shell.fs.exists(link_name):
                print(f"ln: failed to create symlink '{link_name}': File exists")
                return 1
            parent_path = shell.fs._get_parent(link_path)
            if parent_path not in shell.fs.inodes:
                print(f"ln: cannot create symlink '{link_name}': No such directory")
                return 1
            inode = Inode(
                name=_os.path.basename(link_path),
                type=FileType.SYMLINK,
                parent=parent_path,
                content=b"",
                permissions="rwxrwxrwx",
                target=shell.fs._normalize_path(target),
            )
            shell.fs.inodes[link_path] = inode
            shell.fs._add_to_parent(link_path, _os.path.basename(link_path))
            return 0
        else:
            # Hard link: copy content (simplified)
            content = shell.fs.read_file(target)
            if content is None:
                print(f"ln: failed to access '{target}': No such file or directory")
                return 1
            if not shell.fs.write_file(link_name, content):
                print(f"ln: failed to create hard link '{link_name}'")
                return 1
            return 0


class DiffCommand(ShellCommand):
    """Compare files line by line."""

    def __init__(self):
        super().__init__("diff", "Compare files line by line")

    def execute(self, args: List[str], shell) -> int:
        # Options
        unified = False
        context_lines = 3
        filtered = []
        i = 0
        while i < len(args):
            if args[i] in ("-u", "--unified"):
                unified = True
            elif args[i].startswith("-U") and len(args[i]) > 2:
                unified = True
                try:
                    context_lines = int(args[i][2:])
                except ValueError:
                    pass
            elif args[i] == "-u" and i + 1 < len(args) and args[i+1].isdigit():
                unified = True
                context_lines = int(args[i+1])
                i += 1
            else:
                filtered.append(args[i])
            i += 1

        if len(filtered) < 2:
            print("diff: missing operand")
            print("Usage: diff [-u] <file1> <file2>")
            return 1

        file1, file2 = filtered[0], filtered[1]
        c1 = shell.fs.read_file(file1)
        c2 = shell.fs.read_file(file2)

        if c1 is None:
            print(f"diff: {file1}: No such file or directory")
            return 1
        if c2 is None:
            print(f"diff: {file2}: No such file or directory")
            return 1

        lines1 = c1.decode('utf-8', errors='replace').splitlines()
        lines2 = c2.decode('utf-8', errors='replace').splitlines()

        if lines1 == lines2:
            return 0  # No differences

        # Simple LCS-based diff
        diff_lines = self._diff(lines1, lines2, file1, file2, unified, context_lines)
        for line in diff_lines:
            print(line)
        return 1  # Differences found

    def _diff(self, a, b, name_a, name_b, unified, ctx):
        """Produce unified or normal diff output."""
        import time as _time
        # Compute edit script using DP
        ops = self._edit_ops(a, b)

        if unified:
            stamp = _time.strftime('%Y-%m-%d %H:%M:%S')
            result = [f"--- {name_a}\t{stamp}", f"+++ {name_b}\t{stamp}"]
            # Build hunks
            hunks = []
            current_hunk = []
            old_ln = 0  # 1-based
            new_ln = 0
            hunk_old_start = 1
            hunk_new_start = 1
            i = 0
            while i < len(ops):
                op, line = ops[i]
                if op == '=':
                    old_ln += 1
                    new_ln += 1
                    current_hunk.append((' ', line))
                elif op == '-':
                    old_ln += 1
                    current_hunk.append(('-', line))
                elif op == '+':
                    new_ln += 1
                    current_hunk.append(('+', line))
                i += 1
            # Trim context and emit
            changes = [i for i, (t, _) in enumerate(current_hunk) if t != ' ']
            if not changes:
                return result
            groups = []
            g_start = max(0, changes[0] - ctx)
            g_end = min(len(current_hunk), changes[0] + 1 + ctx)
            for c in changes[1:]:
                if c - ctx <= g_end:
                    g_end = min(len(current_hunk), c + 1 + ctx)
                else:
                    groups.append((g_start, g_end))
                    g_start = max(0, c - ctx)
                    g_end = min(len(current_hunk), c + 1 + ctx)
            groups.append((g_start, g_end))
            # Compute line numbers per group
            for gs, ge in groups:
                old_s = 1 + sum(1 for t, _ in current_hunk[:gs] if t in ('=', '-', ' '))
                new_s = 1 + sum(1 for t, _ in current_hunk[:gs] if t in ('=', '+', ' '))
                old_count = sum(1 for t, _ in current_hunk[gs:ge] if t in (' ', '-'))
                new_count = sum(1 for t, _ in current_hunk[gs:ge] if t in (' ', '+'))
                result.append(f"@@ -{old_s},{old_count} +{new_s},{new_count} @@")
                for t, ln in current_hunk[gs:ge]:
                    prefix = ' ' if t == '=' else t
                    result.append(f"{prefix}{ln}")
            return result
        else:
            # Normal diff
            result = []
            ops = self._edit_ops(a, b)
            i = 0
            while i < len(ops):
                op, line = ops[i]
                if op == '-':
                    j = i
                    while j < len(ops) and ops[j][0] == '-':
                        j += 1
                    if j < len(ops) and ops[j][0] == '+':
                        k = j
                        while k < len(ops) and ops[k][0] == '+':
                            k += 1
                        result.append(f"{i+1}c{j+1}")
                        for _, l in ops[i:j]:
                            result.append(f"< {l}")
                        result.append("---")
                        for _, l in ops[j:k]:
                            result.append(f"> {l}")
                        i = k
                    else:
                        result.append(f"{i+1}d{i}")
                        for _, l in ops[i:j]:
                            result.append(f"< {l}")
                        i = j
                elif op == '+':
                    j = i
                    while j < len(ops) and ops[j][0] == '+':
                        j += 1
                    result.append(f"{i}a{i+1}")
                    for _, l in ops[i:j]:
                        result.append(f"> {l}")
                    i = j
                else:
                    i += 1
            return result

    def _edit_ops(self, a, b):
        """Compute edit operations using LCS."""
        m, n = len(a), len(b)
        # dp[i][j] = LCS length of a[:i] and b[:j]
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        # Backtrack
        ops = []
        i, j = m, n
        while i > 0 or j > 0:
            if i > 0 and j > 0 and a[i-1] == b[j-1]:
                ops.append(('=', a[i-1]))
                i -= 1; j -= 1
            elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
                ops.append(('+', b[j-1]))
                j -= 1
            else:
                ops.append(('-', a[i-1]))
                i -= 1
        ops.reverse()
        return ops


class TeeCommand(ShellCommand):
    """Read from stdin and write to both stdout and files."""

    def __init__(self):
        super().__init__("tee", "Read stdin and write to stdout and files")

    def execute(self, args: List[str], shell) -> int:
        append = "-a" in args
        files = [a for a in args if not a.startswith("-")]

        lines = []
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                lines.append(line)
                print(line, end='')
        except EOFError:
            pass

        data = ''.join(lines).encode('utf-8')
        for path in files:
            if append and shell.fs.exists(path):
                existing = shell.fs.read_file(path) or b""
                shell.fs.write_file(path, existing + data)
            else:
                shell.fs.write_file(path, data)

        return 0


class TarCommand(ShellCommand):
    """Archive files (virtual tar — stores in filesystem)."""

    def __init__(self):
        super().__init__("tar", "Create or extract file archives")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("tar: missing option")
            print("Usage: tar -cf <archive> <files...>  (create)")
            print("       tar -tf <archive>              (list)")
            print("       tar -xf <archive> [-C <dir>]  (extract)")
            return 1

        # Parse flags (may be combined like -czf or positional like cf)
        flags_raw = ""
        remaining = []
        for arg in args:
            if arg.startswith("-"):
                flags_raw += arg[1:]
            else:
                remaining.append(arg)

        # Also handle non-dash combined flags (e.g. "tar cf archive dir")
        if not flags_raw and remaining:
            first = remaining[0]
            if all(c in "cxtfvzC" for c in first):
                flags_raw = first
                remaining = remaining[1:]

        create  = 'c' in flags_raw
        extract = 'x' in flags_raw
        list_   = 't' in flags_raw
        verbose = 'v' in flags_raw

        # Find archive file (-f flag means next arg / remaining[0])
        archive = remaining[0] if remaining else None
        sources = remaining[1:]

        # -C <dir>
        dest_dir = "."
        if "-C" in args:
            idx = args.index("-C")
            if idx + 1 < len(args):
                dest_dir = args[idx + 1]
                sources = [s for s in sources if s != dest_dir]

        if not archive:
            print("tar: archive name required")
            return 1

        if create:
            return self._create(shell, archive, sources, verbose)
        elif list_:
            return self._list(shell, archive, verbose)
        elif extract:
            return self._extract(shell, archive, dest_dir, verbose)
        else:
            print("tar: you must specify one of -c, -t, or -x")
            return 1

    def _create(self, shell, archive, sources, verbose):
        """Create a simple tar-like archive stored as text in the VFS."""
        import json as _json
        members = {}

        def collect(path):
            norm = shell.fs._normalize_path(path)
            if shell.fs.is_directory(norm):
                entries = shell.fs.list_directory(norm)
                if entries:
                    for e in entries:
                        child = norm.rstrip('/') + '/' + e.name
                        collect(child)
            elif shell.fs.is_file(norm):
                data = shell.fs.read_file(norm)
                if data is not None:
                    import base64 as _b64
                    members[norm] = _b64.b64encode(data).decode('ascii')
                    if verbose:
                        print(norm)

        for src in sources:
            collect(src)

        payload = _json.dumps(members).encode('utf-8')
        if not shell.fs.write_file(archive, payload):
            print(f"tar: cannot create archive '{archive}'")
            return 1
        return 0

    def _list(self, shell, archive, verbose):
        import json as _json
        data = shell.fs.read_file(archive)
        if data is None:
            print(f"tar: {archive}: No such file or directory")
            return 1
        try:
            members = _json.loads(data.decode('utf-8'))
            for path in members:
                print(path)
            return 0
        except Exception:
            print(f"tar: {archive}: not a valid archive")
            return 1

    def _extract(self, shell, archive, dest_dir, verbose):
        import json as _json, base64 as _b64
        data = shell.fs.read_file(archive)
        if data is None:
            print(f"tar: {archive}: No such file or directory")
            return 1
        try:
            members = _json.loads(data.decode('utf-8'))
            for orig_path, b64data in members.items():
                # Rebase path under dest_dir
                rel = orig_path.lstrip('/')
                if dest_dir in ('.', '/'):
                    target = '/' + rel
                else:
                    target = shell.fs._normalize_path(dest_dir + '/' + rel)
                # Ensure parent dirs exist
                parent = shell.fs._get_parent(target)
                if parent and not shell.fs.exists(parent):
                    shell.fs.mkdir(parent, parents=True)
                content = _b64.b64decode(b64data)
                shell.fs.write_file(target, content)
                if verbose:
                    print(target)
            return 0
        except Exception as e:
            print(f"tar: extraction failed: {e}")
            return 1


class CronCommand(ShellCommand):
    """Manage scheduled cron jobs."""

    def __init__(self):
        super().__init__("cron", "Manage scheduled jobs")
        self._scheduler = None

    def _get_scheduler(self, shell):
        """Return the shared CronScheduler, creating it on first use."""
        if not hasattr(shell, '_cron_scheduler') or shell._cron_scheduler is None:
            from core.cron import CronScheduler
            shell._cron_scheduler = CronScheduler(shell)
            shell._cron_scheduler.start()
        return shell._cron_scheduler

    def execute(self, args: List[str], shell) -> int:
        sched = self._get_scheduler(shell)
        sub = args[0] if args else "list"

        if sub == "list":
            jobs = sched.list_jobs()
            if not jobs:
                print("No cron jobs scheduled.")
                return 0
            print(f"{'ID':<4} {'Name':<20} {'Interval':<10} {'Runs':<6} {'Last Run':<10} {'State'}")
            print("-" * 70)
            for job in jobs:
                from core.cron import _fmt_interval
                last = time.strftime('%H:%M:%S', time.localtime(job.last_run)) if job.last_run else "never"
                nxt  = time.strftime('%H:%M:%S', time.localtime(job.next_run))
                print(f"{job.job_id:<4} {job.name:<20} {_fmt_interval(job.interval):<10} "
                      f"{job.run_count:<6} {last:<10} {job.state.value}")
            return 0

        elif sub == "add":
            # cron add <name> <interval_seconds> <command...>
            if len(args) < 4:
                print("Usage: cron add <name> <interval_secs> <command>")
                return 1
            name = args[1]
            try:
                interval = float(args[2])
                if interval <= 0:
                    raise ValueError
            except ValueError:
                print("cron: interval must be a positive number (seconds)")
                return 1
            command = " ".join(args[3:])
            job = sched.add_job(name, command, interval)
            print(f"Cron job [{job.job_id}] '{name}' added (every {interval}s): {command}")
            return 0

        elif sub == "remove":
            if len(args) < 2:
                print("Usage: cron remove <job_id>")
                return 1
            try:
                jid = int(args[1])
            except ValueError:
                print("cron: job_id must be an integer")
                return 1
            if sched.remove_job(jid):
                print(f"Cron job [{jid}] removed.")
                return 0
            print(f"cron: no job with id {jid}")
            return 1

        elif sub == "pause":
            if len(args) < 2:
                print("Usage: cron pause <job_id>")
                return 1
            try:
                jid = int(args[1])
            except ValueError:
                print("cron: job_id must be an integer")
                return 1
            if sched.pause_job(jid):
                print(f"Cron job [{jid}] paused.")
                return 0
            print(f"cron: cannot pause job {jid}")
            return 1

        elif sub == "resume":
            if len(args) < 2:
                print("Usage: cron resume <job_id>")
                return 1
            try:
                jid = int(args[1])
            except ValueError:
                print("cron: job_id must be an integer")
                return 1
            if sched.resume_job(jid):
                print(f"Cron job [{jid}] resumed.")
                return 0
            print(f"cron: cannot resume job {jid}")
            return 1

        else:
            print("Usage: cron [list|add|remove|pause|resume] ...")
            print("  cron list")
            print("  cron add <name> <interval_secs> <command>")
            print("  cron remove <job_id>")
            print("  cron pause  <job_id>")
            print("  cron resume <job_id>")
            return 1


class TopCommand(ShellCommand):
    """Display a dynamic real-time view of running processes."""

    def __init__(self):
        super().__init__("top", "Display real-time process information")

    def execute(self, args: List[str], shell) -> int:
        # Non-interactive snapshot (suitable for both terminal and redirection)
        import time as _time

        info = shell.kernel.get_system_info()
        procs = shell.kernel.list_processes()

        total_mem = info["total_memory"]
        used_mem  = info["used_memory"]
        free_mem  = info["free_memory"]
        uptime    = shell.kernel.get_uptime()

        days, rem = divmod(int(uptime), 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        uptime_str = f"{days}d {hours:02d}:{mins:02d}:{secs:02d}" if days else f"{hours:02d}:{mins:02d}:{secs:02d}"

        now = _time.strftime('%H:%M:%S')

        print(f"top - {now} up {uptime_str},  {len(procs)} tasks")
        print(f"Mem:  {total_mem//1024//1024}MB total, {used_mem//1024//1024}MB used, {free_mem//1024//1024}MB free")
        print()
        print(f"{'PID':<8} {'NAME':<18} {'STATE':<12} {'CPU':>5} {'MEM':>8}")
        print("-" * 55)

        for proc in sorted(procs, key=lambda p: p.pid):
            mem_kb = proc.memory_usage // 1024
            mem_pct = (proc.memory_usage / total_mem * 100) if total_mem else 0
            print(f"{proc.pid:<8} {proc.name:<18} {proc.state.value:<12} {proc.cpu_time:>5.2f}s {mem_kb:>6}KB")

        return 0


# ─────────────────────────────────────────────────────────────────────────────
# v1.8 NEW COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

class SedCommand(ShellCommand):
    """Stream editor – substitute, delete, print lines."""

    def __init__(self):
        super().__init__("sed", "Stream editor for filtering and transforming text")

    def execute(self, args: List[str], shell) -> int:
        import re as _re

        if not args:
            print("Usage: sed [-n] SCRIPT [file...]")
            return 1

        silent = False
        scripts: List[str] = []
        filenames: List[str] = []

        i = 0
        while i < len(args):
            if args[i] == '-n':
                silent = True
            elif args[i] in ('-e', '--expression'):
                i += 1
                if i < len(args):
                    scripts.append(args[i])
            elif args[i].startswith('-e'):
                scripts.append(args[i][2:])
            elif not scripts:
                scripts.append(args[i])
            else:
                filenames.append(args[i])
            i += 1

        if not scripts:
            print("sed: no script command")
            return 1

        def read_source() -> Optional[str]:
            if not filenames:
                return sys.stdin.read()
            parts = []
            for fn in filenames:
                c = shell.fs.read_file(fn)
                if c is None:
                    print(f"sed: {fn}: No such file or directory", file=sys.stderr)
                    return None
                parts.append(c.decode('utf-8', errors='replace'))
            return ''.join(parts)

        source = read_source()
        if source is None:
            return 1

        lines = source.splitlines()
        commands = []
        for script in scripts:
            commands.extend([cmd.strip() for cmd in script.split(';') if cmd.strip()])

        # Range state keyed by command index
        range_active: Dict[int, bool] = {idx: False for idx in range(len(commands))}
        output_lines: List[str] = []

        def parse_address(address: str) -> Optional[Tuple[str, Optional[str]]]:
            if not address:
                return None
            if address.startswith('/') and address.endswith('/'):
                return ('regex', address[1:-1])
            if address.isdigit():
                return ('line', address)
            return None

        def parse_command(command: str) -> Tuple[Optional[Tuple[str, Optional[str]]], Optional[Tuple[str, Optional[str]]], str]:
            text = command.strip()
            if not text:
                return None, None, ''
            if text[0] == '/':
                end = text.find('/', 1)
                if end != -1:
                    first = text[1:end]
                    rest = text[end + 1:]
                    if rest.startswith(',/'):
                        end2 = rest.find('/', 2)
                        if end2 != -1:
                            second = rest[2:end2]
                            return ('regex', first), ('regex', second), rest[end2 + 1:].strip()
                    if rest.startswith(','):
                        tail = rest[1:].lstrip()
                        if tail and tail.split(None, 1)[0].isdigit():
                            second_num = tail.split(None, 1)[0]
                            return ('regex', first), ('line', second_num), tail[len(second_num):].strip()
                    return ('regex', first), None, rest.strip()
            if text[0].isdigit():
                num = ''
                idx = 0
                while idx < len(text) and text[idx].isdigit():
                    num += text[idx]
                    idx += 1
                rest = text[idx:].lstrip()
                if rest.startswith(','):
                    rest = rest[1:].lstrip()
                    if rest.startswith('/'):
                        end = rest.find('/', 1)
                        if end != -1:
                            second = rest[1:end]
                            return ('line', num), ('regex', second), rest[end + 1:].strip()
                    elif rest and rest.split(None, 1)[0].isdigit():
                        second_num = rest.split(None, 1)[0]
                        return ('line', num), ('line', second_num), rest[len(second_num):].strip()
                return ('line', num), None, rest.strip()
            return None, None, text

        def address_matches(addr: Tuple[str, Optional[str]], line_no: int, line: str) -> bool:
            kind, value = addr
            if kind == 'line':
                return line_no == int(value)
            if kind == 'regex':
                try:
                    return bool(_re.search(value or '', line))
                except _re.error as e:
                    print(f"sed: invalid regex: {e}", file=sys.stderr)
                    raise
            return False

        parsed_commands = []
        for cmd in commands:
            start, end, body = parse_command(cmd)
            parsed_commands.append((start, end, body))

        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx]
            lineno = line_idx + 1
            delete = False
            insert_before: List[str] = []
            append_after: List[str] = []
            force_print = False
            restart_cycle = False

            for idx, (start, end, body) in enumerate(parsed_commands):
                if not body:
                    continue

                in_range = True
                if start:
                    if end:
                        if not range_active[idx]:
                            if address_matches(start, lineno, line):
                                range_active[idx] = True
                            else:
                                in_range = False
                        if range_active[idx] and address_matches(end, lineno, line):
                            range_active[idx] = False
                    else:
                        in_range = address_matches(start, lineno, line)
                if not in_range:
                    continue

                op = body[0]
                payload = body[1:].lstrip() if len(body) > 1 else ''

                if op == 's':
                    # s/pattern/replacement/flags
                    delim = body[1]
                    parts = body[2:].split(delim)
                    if len(parts) >= 2:
                        pat_s = parts[0]
                        repl = parts[1]
                        flags_s = parts[2] if len(parts) > 2 else ''
                        flags_re = _re.IGNORECASE if 'i' in flags_s else 0
                        count = 0 if 'g' in flags_s else 1
                        try:
                            line = _re.sub(pat_s, repl, line, count=count, flags=flags_re)
                        except _re.error as e:
                            print(f"sed: invalid regex: {e}", file=sys.stderr)
                            return 1
                elif op == 'd':
                    delete = True
                    break
                elif op == 'p':
                    output_lines.append(line)
                elif op == 'q':
                    if not silent:
                        output_lines.append(line)
                    for ol in output_lines:
                        print(ol)
                    return 0
                elif op == 'y':
                    # y/src/dst/ – transliterate
                    delim = body[1]
                    parts = body[2:].split(delim)
                    if len(parts) >= 2:
                        src_chars, dst_chars = parts[0], parts[1]
                        table = str.maketrans(src_chars, dst_chars[:len(src_chars)])
                        line = line.translate(table)
                elif op == 'i':
                    insert_before.append(payload)
                elif op == 'a':
                    append_after.append(payload)
                elif op == 'c':
                    line = payload
                    force_print = True
                    append_after = []
                    insert_before = []
                    break
                elif op == 'n':
                    if not silent:
                        output_lines.append(line)
                    output_lines.extend(append_after)
                    append_after = []
                    line_idx += 1
                    if line_idx >= len(lines):
                        delete = True
                        break
                    line = lines[line_idx]
                    lineno = line_idx + 1
                    restart_cycle = True
                    break

            if restart_cycle:
                continue

            if not delete:
                output_lines.extend(insert_before)
                if not silent or force_print:
                    output_lines.append(line)
                output_lines.extend(append_after)

            line_idx += 1

        for ol in output_lines:
            print(ol)
        return 0


class AwkCommand(ShellCommand):
    """Pattern scanning and text processing (subset of awk)."""

    def __init__(self):
        super().__init__("awk", "Pattern scanning and processing language")

    def execute(self, args: List[str], shell) -> int:
        import re as _re

        if not args:
            print("Usage: awk [-F sep] 'program' [file...]")
            return 1

        sep = None
        program = None
        filenames: List[str] = []
        i = 0
        while i < len(args):
            if args[i] == '-F' and i + 1 < len(args):
                i += 1
                sep = args[i]
            elif args[i].startswith('-F'):
                sep = args[i][2:]
            elif program is None:
                program = args[i]
            else:
                filenames.append(args[i])
            i += 1

        if program is None:
            print("awk: no program given")
            return 1

        def parse_pattern(text: str) -> Optional[str]:
            if not text:
                return None
            token = text.strip()
            if token.startswith('/') and token.endswith('/'):
                return token[1:-1]
            return None

        # Parse BEGIN, END, and pattern-action blocks
        begin_block = ''
        end_block   = ''
        rules: List[tuple] = []   # (pattern_str, action_str)

        # Strip comments
        program = _re.sub(r'#[^\n]*', '', program)

        # Simple tokeniser: find BEGIN { }, END { }, /pat/ { }, { }
        remaining = program.strip()
        while remaining:
            remaining = remaining.strip()
            if not remaining:
                break
            m = _re.match(r'^BEGIN\s*\{([^}]*)\}', remaining, _re.DOTALL)
            if m:
                begin_block += m.group(1)
                remaining = remaining[m.end():]
                continue
            m = _re.match(r'^END\s*\{([^}]*)\}', remaining, _re.DOTALL)
            if m:
                end_block += m.group(1)
                remaining = remaining[m.end():]
                continue
            m = _re.match(r'^(/[^/]*/)?\s*\{([^}]*)\}', remaining, _re.DOTALL)
            if m:
                pat = m.group(1)[1:-1] if m.group(1) else None
                action = m.group(2)
                rules.append((pat, action))
                remaining = remaining[m.end():]
                continue
            # bare pattern without braces → print if matches
            m = _re.match(r'^(/[^/]*/)(?=\s*(?:\{|\s*$))', remaining, _re.DOTALL)
            if m:
                pat = parse_pattern(m.group(1))
                rules.append((pat, 'print'))
                remaining = remaining[m.end():]
                continue
            break

        # Awk variable environment
        env: Dict[str, Any] = {
            'NR': 0, 'NF': 0, 'FS': sep or ' ',
            'OFS': ' ', 'ORS': '\n', 'RS': '\n',
            'FILENAME': '', '$0': '', 'fields': [],
        }

        def set_record(line: str, filename: str):
            env['$0'] = line
            env['FILENAME'] = filename
            fs = env['FS']
            if fs == ' ':
                flds = line.split()
            else:
                flds = line.split(fs)
            env['fields'] = flds
            env['NF'] = len(flds)
            for idx, f in enumerate(flds, 1):
                env[f'${idx}'] = f

        def expand_vars(expr: str) -> str:
            """Replace $N, $NF, NR, NF, $0 etc. in an expression string."""
            expr = expr.replace('$NF', env['fields'][-1] if env['fields'] else '')
            expr = _re.sub(r'\$(\d+)', lambda m: env.get(f'${m.group(1)}', ''), expr)
            expr = expr.replace('NR', str(env['NR']))
            expr = expr.replace('NF', str(env['NF']))
            expr = expr.replace('$0', env['$0'])
            return expr

        def _coerce_number(value: str) -> Optional[float]:
            try:
                return float(value)
            except ValueError:
                return None

        def eval_condition(expr: str) -> bool:
            expr = expr.strip()
            if not expr:
                return False
            expr = expand_vars(expr)
            m = _re.match(r'^(.*?)\s*(==|!=|>=|<=|>|<)\s*(.*)$', expr)
            if m:
                left, op, right = m.group(1).strip(), m.group(2), m.group(3).strip()
                left_num = _coerce_number(left)
                right_num = _coerce_number(right)
                if left_num is not None and right_num is not None:
                    if op == '==':
                        return left_num == right_num
                    if op == '!=':
                        return left_num != right_num
                    if op == '>=':
                        return left_num >= right_num
                    if op == '<=':
                        return left_num <= right_num
                    if op == '>':
                        return left_num > right_num
                    if op == '<':
                        return left_num < right_num
                if op == '==':
                    return left == right
                if op == '!=':
                    return left != right
                if op == '>=':
                    return left >= right
                if op == '<=':
                    return left <= right
                if op == '>':
                    return left > right
                if op == '<':
                    return left < right
            return bool(expr)

        def run_action(action: str):
            for stmt in _re.split(r'[;\n]', action):
                stmt = stmt.strip()
                if not stmt:
                    continue
                # if (cond) { action }
                m = _re.match(r'^if\s*\(([^)]*)\)\s*\{([^}]*)\}$', stmt)
                if m:
                    if eval_condition(m.group(1)):
                        run_action(m.group(2))
                    continue
                # while (cond) { action }
                m = _re.match(r'^while\s*\(([^)]*)\)\s*\{([^}]*)\}$', stmt)
                if m:
                    guard = m.group(1)
                    body = m.group(2)
                    iterations = 0
                    while eval_condition(guard):
                        run_action(body)
                        iterations += 1
                        if iterations > 10000:
                            break
                    continue
                # print [expr, ...]
                m = _re.match(r'^print\b(.*)', stmt)
                if m:
                    expr = m.group(1).strip()
                    if not expr:
                        print(env['$0'] + env['ORS'], end='')
                    else:
                        parts = [p.strip() for p in expr.split(',')]
                        expanded = []
                        for p in parts:
                            token = p.strip()
                            if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
                                expanded.append(token[1:-1])
                            else:
                                expanded.append(expand_vars(token))
                        print(env['OFS'].join(expanded) + env['ORS'], end='')
                    continue
                # printf "fmt", args
                m = _re.match(r'^printf\s+"([^"]*)"(.*)', stmt)
                if m:
                    fmt = m.group(1).replace('\\n', '\n').replace('\\t', '\t')
                    rest = m.group(2).strip().lstrip(',')
                    vals = [expand_vars(p.strip().strip('"')) for p in rest.split(',') if p.strip()]
                    try:
                        sys.stdout.write(fmt % tuple(vals))
                    except Exception:
                        sys.stdout.write(fmt)
                    continue
                # var = expr (simple assignment)
                m = _re.match(r'^(\w+)\s*=\s*(.+)$', stmt)
                if m:
                    var, val = m.group(1), expand_vars(m.group(2).strip().strip('"'))
                    try:
                        env[var] = int(val)
                    except ValueError:
                        try:
                            env[var] = float(val)
                        except ValueError:
                            env[var] = val
                    continue
                # next
                if stmt == 'next':
                    raise StopIteration

        def run_block(block: str):
            if block.strip():
                run_action(block)

        # BEGIN
        if begin_block:
            run_block(begin_block)

        # Process input
        sources = []
        if not filenames:
            sources.append(('', sys.stdin.read()))
        else:
            for fn in filenames:
                c = shell.fs.read_file(fn)
                if c is None:
                    print(f"awk: {fn}: No such file or directory", file=sys.stderr)
                    return 1
                sources.append((fn, c.decode('utf-8', errors='replace')))

        for filename, text in sources:
            for line in text.splitlines():
                env['NR'] += 1
                set_record(line, filename)
                for pat, action in rules:
                    try:
                        if pat is None or _re.search(pat, line):
                            run_action(action)
                    except StopIteration:
                        break

        # END
        if end_block:
            run_block(end_block)

        return 0


class TrCommand(ShellCommand):
    """Translate or delete characters."""

    def __init__(self):
        super().__init__("tr", "Translate or delete characters")

    def _expand_set(self, s: str) -> str:
        """Expand character ranges like a-z."""
        import re as _re
        result = []
        i = 0
        while i < len(s):
            if i + 2 < len(s) and s[i + 1] == '-':
                start, end = ord(s[i]), ord(s[i + 2])
                if start <= end:
                    result.extend(chr(c) for c in range(start, end + 1))
                else:
                    result.extend([s[i], '-', s[i + 2]])
                i += 3
            elif s[i] == '\\' and i + 1 < len(s):
                esc = s[i + 1]
                result.append({'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}.get(esc, esc))
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)

    def execute(self, args: List[str], shell) -> int:
        delete = False
        squeeze = False
        complement = False
        sets: List[str] = []

        i = 0
        while i < len(args):
            if args[i] == '-d':
                delete = True
            elif args[i] == '-s':
                squeeze = True
            elif args[i] == '-c':
                complement = True
            elif args[i].startswith('-') and len(args[i]) > 1:
                for ch in args[i][1:]:
                    if ch == 'd': delete = True
                    elif ch == 's': squeeze = True
                    elif ch == 'c': complement = True
            else:
                sets.append(args[i])
            i += 1

        text = sys.stdin.read()

        if delete:
            if not sets:
                print("tr: missing operand")
                return 1
            del_set = set(self._expand_set(sets[0]))
            if complement:
                del_set = set(chr(c) for c in range(128)) - del_set
            result = ''.join(ch for ch in text if ch not in del_set)
        elif len(sets) >= 2:
            src = self._expand_set(sets[0])
            dst = self._expand_set(sets[1])
            if complement:
                all_chars = [chr(c) for c in range(128)]
                src = ''.join(c for c in all_chars if c not in src)
            # Pad dst with last char if shorter
            if len(dst) < len(src):
                dst = dst + dst[-1] * (len(src) - len(dst)) if dst else ''
            table = str.maketrans(src[:len(dst)], dst[:len(src)])
            result = text.translate(table)
        elif len(sets) == 1 and squeeze:
            # squeeze repeated chars in set1
            sq_set = set(self._expand_set(sets[0]))
            result = []
            prev = None
            for ch in text:
                if ch in sq_set and ch == prev:
                    continue
                result.append(ch)
                prev = ch
            result = ''.join(result)
        else:
            print("tr: missing operand")
            return 1

        if squeeze and not delete and len(sets) >= 2:
            sq_set = set(self._expand_set(sets[1]))
            squeezed = []
            prev = None
            for ch in result:
                if ch in sq_set and ch == prev:
                    continue
                squeezed.append(ch)
                prev = ch
            result = ''.join(squeezed)

        sys.stdout.write(result)
        return 0


class XargsCommand(ShellCommand):
    """Build and execute command lines from stdin."""

    def __init__(self):
        super().__init__("xargs", "Build and execute command lines from standard input")

    def execute(self, args: List[str], shell) -> int:
        cmd_args: List[str] = []
        max_args = None
        i = 0
        while i < len(args):
            if args[i] == '-n' and i + 1 < len(args):
                i += 1
                try:
                    max_args = int(args[i])
                except ValueError:
                    pass
            else:
                cmd_args.append(args[i])
            i += 1

        if not cmd_args:
            cmd_args = ['echo']

        # Read words from stdin
        words = sys.stdin.read().split()
        if not words:
            return 0

        rc = 0
        if max_args:
            for start in range(0, len(words), max_args):
                batch = words[start:start + max_args]
                full_cmd = ' '.join(cmd_args + batch)
                r = shell.execute(full_cmd)
                if r != 0:
                    rc = r
        else:
            full_cmd = ' '.join(cmd_args + words)
            rc = shell.execute(full_cmd)
        return rc


class MktempCommand(ShellCommand):
    """Create a temporary file or directory."""

    def __init__(self):
        super().__init__("mktemp", "Create a temporary file or directory")

    def execute(self, args: List[str], shell) -> int:
        import random, string
        is_dir = '-d' in args
        suffix = ''
        prefix = 'tmp.'
        # Look for template like /tmp/myXXXXXX
        template = None
        for a in args:
            if not a.startswith('-'):
                template = a
                break
        if template:
            # Replace trailing X's with random chars
            base = template.rstrip('X')
            n_x = len(template) - len(base)
            rand = ''.join(random.choices(string.ascii_letters + string.digits, k=max(n_x, 6)))
            path = base + rand
        else:
            rand = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            path = f"/tmp/tmp.{rand}"

        if is_dir:
            rc = shell.fs.mkdir(path)
            if rc:
                print(f"mktemp: cannot create dir '{path}'")
                return 1
        else:
            rc = shell.fs.write_file(path, b'')
            if rc is False:
                print(f"mktemp: cannot create file '{path}'")
                return 1
        print(path)
        return 0


class ReadlinkCommand(ShellCommand):
    """Print resolved symlink target."""

    def __init__(self):
        super().__init__("readlink", "Print resolved symbolic link or canonical file name")

    def execute(self, args: List[str], shell) -> int:
        canonical = '-f' in args or '-e' in args or '-m' in args
        paths = [a for a in args if not a.startswith('-')]
        if not paths:
            print("Usage: readlink [-f] file")
            return 1
        rc = 0
        for path in paths:
            inode = shell.fs.get_inode(path)
            if inode is None:
                print(f"readlink: {path}: No such file or directory", file=sys.stderr)
                rc = 1
                continue
            from core.filesystem import FileType
            if inode.type == FileType.SYMLINK:
                target = inode.content if isinstance(inode.content, str) else path
                print(target)
            elif canonical:
                print(shell.fs.resolve_path(path))
            else:
                print(f"readlink: {path}: not a symbolic link", file=sys.stderr)
                rc = 1
        return rc


class RealpathCommand(ShellCommand):
    """Print the resolved absolute file name."""

    def __init__(self):
        super().__init__("realpath", "Print the resolved absolute file name")

    def execute(self, args: List[str], shell) -> int:
        paths = [a for a in args if not a.startswith('-')]
        if not paths:
            print("Usage: realpath path [...]")
            return 1
        rc = 0
        for path in paths:
            resolved = shell.fs.resolve_path(path)
            if not shell.fs.exists(resolved):
                print(f"realpath: {path}: No such file or directory", file=sys.stderr)
                rc = 1
                continue
            print(resolved)
        return rc


class WatchCommand(ShellCommand):
    """Execute a command repeatedly, showing output."""

    def __init__(self):
        super().__init__("watch", "Execute a program periodically, showing output fullscreen")

    def execute(self, args: List[str], shell) -> int:
        import time as _time

        interval = 2.0
        count = None  # run forever unless -n count given
        cmd_parts: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-n', '--interval') and i + 1 < len(args):
                i += 1
                try:
                    interval = float(args[i])
                except ValueError:
                    pass
            elif args[i] == '-c' and i + 1 < len(args):
                i += 1
                try:
                    count = int(args[i])
                except ValueError:
                    pass
            else:
                cmd_parts.append(args[i])
            i += 1

        if not cmd_parts:
            print("Usage: watch [-n secs] [-c count] command")
            return 1

        cmd = ' '.join(cmd_parts)
        runs = 0
        try:
            while count is None or runs < count:
                print(f"\033[2J\033[H", end='')  # clear screen
                print(f"Every {interval:.1f}s: {cmd}   (Ctrl+C to stop)\n")
                shell.execute(cmd)
                runs += 1
                if count is None or runs < count:
                    _time.sleep(interval)
        except KeyboardInterrupt:
            print()
        return 0


class FetchCommand(ShellCommand):
    """Fetch content from a URL (like curl/wget, uses urllib)."""

    def __init__(self):
        super().__init__("fetch", "Fetch content from a URL")

    def execute(self, args: List[str], shell) -> int:
        try:
            from urllib.request import urlopen, Request
            from urllib.error import URLError, HTTPError
        except ImportError:
            print("fetch: urllib not available")
            return 1

        if not args:
            print("Usage: fetch [-o outfile] [-H 'Header: val'] url")
            return 1

        url = None
        outfile = None
        headers: Dict[str, str] = {}
        method = 'GET'
        i = 0
        while i < len(args):
            if args[i] in ('-o', '--output') and i + 1 < len(args):
                i += 1
                outfile = args[i]
            elif args[i] in ('-H', '--header') and i + 1 < len(args):
                i += 1
                if ':' in args[i]:
                    k, v = args[i].split(':', 1)
                    headers[k.strip()] = v.strip()
            elif args[i] in ('-X', '--method') and i + 1 < len(args):
                i += 1
                method = args[i].upper()
            else:
                url = args[i]
            i += 1

        if not url:
            print("fetch: no URL specified")
            return 1

        try:
            req = Request(url, headers=headers, method=method)
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
                if outfile:
                    shell.fs.write_file(outfile, data)
                    size = len(data)
                    print(f"fetch: saved {size} bytes to '{outfile}'")
                else:
                    try:
                        sys.stdout.write(data.decode('utf-8', errors='replace'))
                    except Exception:
                        sys.stdout.buffer.write(data)
        except HTTPError as e:
            print(f"fetch: HTTP error {e.code}: {e.reason}")
            return 1
        except URLError as e:
            print(f"fetch: connection error: {e.reason}")
            return 1
        except Exception as e:
            print(f"fetch: error: {e}")
            return 1
        return 0


class CalCommand(ShellCommand):
    """Display a calendar."""

    def __init__(self):
        super().__init__("cal", "Display a calendar")

    def execute(self, args: List[str], shell) -> int:
        import calendar as _cal
        import time as _time

        now = _time.localtime()
        year = now.tm_year
        month = now.tm_mon
        full_year = False

        non_flag = [a for a in args if not a.startswith('-')]
        if '-y' in args or '--year' in args:
            full_year = True
        if len(non_flag) == 2:
            try:
                month = int(non_flag[0])
                year  = int(non_flag[1])
            except ValueError:
                pass
        elif len(non_flag) == 1:
            try:
                year = int(non_flag[0])
                full_year = True
            except ValueError:
                pass

        if full_year:
            print(f"                   {year}")
            c = _cal.TextCalendar(_cal.SUNDAY)
            for m in range(1, 13):
                month_lines = c.formatmonth(year, m).splitlines()
                for line in month_lines:
                    print(line)
        else:
            print(_cal.month(year, month).rstrip())
        return 0


class BcCommand(ShellCommand):
    """An arbitrary-precision calculator (safe expression evaluator)."""

    def __init__(self):
        super().__init__("bc", "An arbitrary precision calculator language")

    def execute(self, args: List[str], shell) -> int:
        import math as _math

        # If args given treat as expression (join all args), else read from stdin
        non_flag_args = [a for a in args if not a.startswith('-')]
        if non_flag_args:
            lines = [' '.join(non_flag_args)]
        else:
            lines = sys.stdin.read().splitlines()

        safe_globals = {
            '__builtins__': {},
            'sqrt': _math.sqrt, 'sin': _math.sin, 'cos': _math.cos,
            'tan': _math.tan, 'log': _math.log, 'log10': _math.log10,
            'log2': _math.log2, 'exp': _math.exp, 'pi': _math.pi,
            'e': _math.e, 'abs': abs, 'round': round,
            'floor': _math.floor, 'ceil': _math.ceil,
            'pow': pow, 'factorial': _math.factorial,
        }
        local_vars: Dict[str, Any] = {}

        rc = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # allow assignments like x=5
            try:
                result = eval(line, safe_globals, local_vars)
                if result is not None:
                    # format nicely: integers without decimal
                    if isinstance(result, float) and result == int(result):
                        print(int(result))
                    else:
                        print(result)
                    local_vars['last'] = result
            except SyntaxError:
                try:
                    exec(line, safe_globals, local_vars)
                except Exception as e:
                    print(f"bc: {e}", file=sys.stderr)
                    rc = 1
            except Exception as e:
                print(f"bc: {e}", file=sys.stderr)
                rc = 1

        return rc


class PrintfCommand(ShellCommand):
    """Format and print data."""

    def __init__(self):
        super().__init__("printf", "Format and print data")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: printf FORMAT [ARGUMENT...]")
            return 1

        fmt = args[0]
        fmt_args = args[1:]

        # Handle escape sequences in format (shlex already strips outer quotes,
        # but \\n from single-quoted args arrives as literal \n two chars)
        def unescape(s: str) -> str:
            return s.replace('\\n', '\n').replace('\\t', '\t') \
                    .replace('\\r', '\r').replace('\\\\', '\\').replace('\\0', '\0')

        fmt = unescape(fmt)

        if not fmt_args:
            sys.stdout.write(fmt)
            return 0

        # Try Python %-formatting
        try:
            # Count format specifiers
            import re as _re
            specs = _re.findall(r'%[-+0-9.]*[diouxXeEfFgGsqcb%]', fmt)
            converted: List[Any] = []
            for i, spec in enumerate(specs):
                if spec == '%%':
                    continue
                val = fmt_args[i] if i < len(fmt_args) else ''
                if spec[-1] in 'diouxX':
                    try:
                        converted.append(int(val, 0))
                    except Exception:
                        converted.append(0)
                elif spec[-1] in 'eEfFgG':
                    try:
                        converted.append(float(val))
                    except Exception:
                        converted.append(0.0)
                else:
                    converted.append(val)
            sys.stdout.write(fmt % tuple(converted))
        except Exception:
            sys.stdout.write(fmt)
        return 0


class SeqCommand(ShellCommand):
    """Print a sequence of numbers."""

    def __init__(self):
        super().__init__("seq", "Print a sequence of numbers")

    def execute(self, args: List[str], shell) -> int:
        sep = '\n'
        fmt = None
        non_flag: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-s', '--separator') and i + 1 < len(args):
                i += 1
                sep = args[i].replace('\\n', '\n').replace('\\t', '\t')
            elif args[i] in ('-f', '--format') and i + 1 < len(args):
                i += 1
                fmt = args[i]
            elif args[i].startswith('-'):
                pass
            else:
                non_flag.append(args[i])
            i += 1

        try:
            if len(non_flag) == 1:
                first, step, last = 1, 1, int(non_flag[0])
            elif len(non_flag) == 2:
                first, step, last = int(non_flag[0]), 1, int(non_flag[1])
            elif len(non_flag) == 3:
                first, step, last = int(non_flag[0]), int(non_flag[1]), int(non_flag[2])
            else:
                print("Usage: seq [FIRST [STEP]] LAST")
                return 1
        except ValueError:
            print("seq: invalid argument")
            return 1

        nums = []
        n = first
        while (step > 0 and n <= last) or (step < 0 and n >= last):
            if fmt:
                try:
                    nums.append(fmt % n)
                except Exception:
                    nums.append(str(n))
            else:
                nums.append(str(n))
            n += step

        print(sep.join(nums))
        return 0


class YesCommand(ShellCommand):
    """Output a string repeatedly until killed."""

    def __init__(self):
        super().__init__("yes", "Output a string repeatedly until killed")

    def execute(self, args: List[str], shell) -> int:
        word = ' '.join(args) if args else 'y'
        try:
            # With a count limit to avoid infinite loops in tests
            count = 0
            while True:
                print(word)
                count += 1
                if count >= 10000:  # safety limit
                    break
        except (KeyboardInterrupt, BrokenPipeError):
            pass
        return 0


class StringsCommand(ShellCommand):
    """Print printable strings from files."""

    def __init__(self):
        super().__init__("strings", "Print the sequences of printable characters in files")

    def execute(self, args: List[str], shell) -> int:
        min_len = 4
        filenames: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-n', '--bytes') and i + 1 < len(args):
                i += 1
                try:
                    min_len = int(args[i])
                except ValueError:
                    pass
            elif not args[i].startswith('-'):
                filenames.append(args[i])
            i += 1

        if not filenames:
            print("Usage: strings [-n min] file [...]")
            return 1

        import re as _re
        for fn in filenames:
            data = shell.fs.read_file(fn)
            if data is None:
                print(f"strings: {fn}: No such file or directory", file=sys.stderr)
                continue
            text = data.decode('latin-1', errors='replace')
            pattern = _re.compile(r'[ -~]{%d,}' % min_len)
            for m in pattern.finditer(text):
                print(m.group())
        return 0


class ExprCommand(ShellCommand):
    """Evaluate expressions."""

    def __init__(self):
        super().__init__("expr", "Evaluate expressions")

    def execute(self, args: List[str], shell) -> int:
        import re as _re
        if not args:
            print("Usage: expr expression")
            return 1

        expr = ' '.join(args)

        # Handle string operations
        # expr string : regex  → match
        m = _re.match(r'^(.+)\s+:\s+(.+)$', expr)
        if m:
            s = m.group(1).strip().strip("'\"")
            pat = m.group(2).strip().strip("'\"")
            match = _re.match(pat, s)
            if match:
                if match.groups():
                    print(match.group(1))
                    return 0
                else:
                    print(len(match.group(0)))
                    return 0
            else:
                print(0)
                return 1

        # Arithmetic: expr num op num
        m = _re.match(r'^(-?\d+)\s*([+\-\*/%])\s*(-?\d+)$', expr)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            try:
                if op == '+':   result = a + b
                elif op == '-': result = a - b
                elif op == '*': result = a * b
                elif op == '/':
                    if b == 0:
                        print("expr: division by zero", file=sys.stderr)
                        return 2
                    result = a // b
                elif op == '%':
                    if b == 0:
                        print("expr: division by zero", file=sys.stderr)
                        return 2
                    result = a % b
                else:
                    result = 0
                print(result)
                return 0 if result != 0 else 1
            except Exception as e:
                print(f"expr: {e}", file=sys.stderr)
                return 2

        # Comparison: num cmp num
        m = _re.match(r'^(-?\d+)\s*(<=|>=|!=|=|<|>)\s*(-?\d+)$', expr)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            ops = {'=': lambda x,y: x==y, '!=': lambda x,y: x!=y,
                   '<': lambda x,y: x<y,  '>': lambda x,y: x>y,
                   '<=': lambda x,y: x<=y,'>=': lambda x,y: x>=y}
            result = 1 if ops.get(op, lambda x,y: False)(a, b) else 0
            print(result)
            return 0 if result else 1

        # length string
        m = _re.match(r'^length\s+"?([^"]*)"?$', expr)
        if m:
            print(len(m.group(1)))
            return 0

        # substr string pos len
        m = _re.match(r'^substr\s+"?([^"]*)"?\s+(\d+)\s+(\d+)$', expr)
        if m:
            s, pos, length = m.group(1), int(m.group(2)), int(m.group(3))
            print(s[pos-1:pos-1+length])
            return 0

        # index string chars
        m = _re.match(r'^index\s+"?([^"]*)"?\s+"?([^"]*)"?$', expr)
        if m:
            s, chars = m.group(1), m.group(2)
            for i, ch in enumerate(s, 1):
                if ch in chars:
                    print(i)
                    return 0
            print(0)
            return 1

        # Fallback: try safe eval
        try:
            result = eval(expr, {"__builtins__": {}}, {})
            print(result)
            return 0 if result else 1
        except Exception:
            print(f"expr: syntax error")
            return 2


class RevCommand(ShellCommand):
    """Reverse characters in each input line."""

    def __init__(self):
        super().__init__("rev", "Reverse characters in each input line")

    def execute(self, args: List[str], shell) -> int:
        lines: List[str] = []
        if args:
            for filename in args:
                data = shell.fs.read_file(filename)
                if data is None:
                    print(f"rev: {filename}: No such file or directory")
                    return 1
                lines.extend(data.decode('utf-8', errors='replace').splitlines())
        else:
            content = sys.stdin.read()
            lines = content.splitlines()

        for line in lines:
            print(line[::-1])
        return 0


# ── v1.9 New Commands ─────────────────────────────────────────────────────────

class GroupsCommand(ShellCommand):
    """Show group memberships for a user."""

    def __init__(self):
        super().__init__("groups", "Print group memberships for a user")

    def execute(self, args: List[str], shell) -> int:
        username = args[0] if args else shell.environment.get("USER", "root")
        if shell.um:
            grps = shell.um.get_user_groups(username)
            if not grps:
                print(f"groups: {username}: unknown user")
                return 1
            print(' '.join(grps))
        else:
            print(username)
        return 0


class PstreeCommand(ShellCommand):
    """Display process tree."""

    def __init__(self):
        super().__init__("pstree", "Display a tree of processes")

    def execute(self, args: List[str], shell) -> int:
        show_pids = '-p' in args
        processes = shell.kernel.list_processes()
        # Build parent->children map
        children: Dict[Optional[int], List] = {}
        for p in processes:
            parent = p.parent_pid
            children.setdefault(parent, []).append(p)

        def _print_tree(pid_or_none, prefix="", is_last=True):
            kids = children.get(pid_or_none, [])
            for i, proc in enumerate(kids):
                last = (i == len(kids) - 1)
                connector = "└── " if last else "├── "
                label = proc.name
                if show_pids:
                    label = f"{proc.name}({proc.pid})"
                print(f"{prefix}{connector}{label}")
                extension = "    " if last else "│   "
                _print_tree(proc.pid, prefix + extension, last)

        # Print init/root processes (no parent or parent not in process list)
        pids_in_table = {p.pid for p in processes}
        roots = [p for p in processes
                 if p.parent_pid is None or p.parent_pid not in pids_in_table]
        if not roots:
            roots = processes

        for proc in roots:
            label = proc.name
            if show_pids:
                label = f"{proc.name}({proc.pid})"
            print(label)
            _print_tree(proc.pid)
        return 0


class VmstatCommand(ShellCommand):
    """Report virtual memory statistics."""

    def __init__(self):
        super().__init__("vmstat", "Report virtual memory statistics")

    def execute(self, args: List[str], shell) -> int:
        info = shell.kernel.get_system_info()
        total  = info["total_memory"]
        used   = info["used_memory"]
        free   = info["free_memory"]
        procs  = info["process_count"]
        run    = info["running_processes"]
        # Convert to KB
        total_kb = total // 1024
        used_kb  = used  // 1024
        free_kb  = free  // 1024
        print("procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----")
        print(" r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st")
        print(f" {run}  0      0 {free_kb:6d}      0      0    0    0     0     0    0    0  0  0 100  0  0")
        print()
        print(f"Total memory : {total_kb:>10} KB")
        print(f"Used memory  : {used_kb:>10} KB")
        print(f"Free memory  : {free_kb:>10} KB")
        print(f"Processes    : {procs:>10}")
        return 0


class LsofCommand(ShellCommand):
    """List open files (virtual - shows filesystem inodes)."""

    def __init__(self):
        super().__init__("lsof", "List open files")

    def execute(self, args: List[str], shell) -> int:
        user_filter = None
        i = 0
        while i < len(args):
            if args[i] == '-u' and i + 1 < len(args):
                i += 1
                user_filter = args[i]
            i += 1

        print(f"{'COMMAND':<12} {'PID':>6}  {'USER':<10} {'TYPE':<8} {'NAME'}")
        print("-" * 60)
        processes = shell.kernel.list_processes()
        current_user = shell.environment.get("USER", "root")
        shown = 0
        for proc in processes:
            owner = current_user
            if user_filter and owner != user_filter:
                continue
            # Show the process's notional open files
            print(f"{'shell':<12} {proc.pid:>6}  {owner:<10} {'REG':<8} /dev/pts/0")
            shown += 1

        # Also show virtual fs files as open by shell
        for path, inode in list(shell.fs.inodes.items())[:20]:
            from core.filesystem import FileType
            if inode.type == FileType.REGULAR:
                owner = inode.owner
                if user_filter and owner != user_filter:
                    continue
                print(f"{'pureos':<12} {'1':>6}  {owner:<10} {'REG':<8} {path}")
                shown += 1
        if shown == 0:
            print("(no open files found)")
        return 0


class ZipCommand(ShellCommand):
    """Create a virtual zip archive."""

    def __init__(self):
        super().__init__("zip", "Create a virtual zip archive")

    def execute(self, args: List[str], shell) -> int:
        import json as _json
        if len(args) < 2:
            print("Usage: zip archive.zip file [file ...]")
            return 1
        archive_path = args[0]
        file_paths = args[1:]
        entries = {}
        for fp in file_paths:
            data = shell.fs.read_file(fp)
            if data is None:
                print(f"zip: {fp}: No such file or directory", file=sys.stderr)
                return 1
            entries[fp] = data.decode('latin-1', errors='replace')
        payload = _json.dumps({"format": "pureos-zip", "entries": entries}).encode()
        if not shell.fs.write_file(archive_path, payload):
            print(f"zip: cannot create {archive_path}", file=sys.stderr)
            return 1
        print(f"  adding: {', '.join(file_paths)}")
        print(f"Archive: {archive_path}  ({len(payload)} bytes)")
        return 0


class UnzipCommand(ShellCommand):
    """Extract a virtual zip archive."""

    def __init__(self):
        super().__init__("unzip", "Extract a virtual zip archive")

    def execute(self, args: List[str], shell) -> int:
        import json as _json
        dest_dir = "."
        archive_path = None
        i = 0
        while i < len(args):
            if args[i] == '-d' and i + 1 < len(args):
                i += 1
                dest_dir = args[i]
            elif not args[i].startswith('-'):
                archive_path = args[i]
            i += 1
        if not archive_path:
            print("Usage: unzip [-d destdir] archive.zip")
            return 1
        data = shell.fs.read_file(archive_path)
        if data is None:
            print(f"unzip: cannot find or open {archive_path}", file=sys.stderr)
            return 1
        try:
            payload = _json.loads(data.decode())
            if payload.get("format") != "pureos-zip":
                raise ValueError("not a pureos-zip")
            entries = payload["entries"]
        except Exception:
            print(f"unzip: {archive_path}: not a valid zip archive", file=sys.stderr)
            return 1
        if dest_dir != ".":
            shell.fs.mkdir(dest_dir, parents=True)
        for name, content in entries.items():
            import posixpath as _pp
            basename = _pp.basename(name)
            if dest_dir == ".":
                out_path = shell.fs._normalize_path(
                    shell.fs.current_directory + "/" + basename)
            else:
                out_path = shell.fs._normalize_path(dest_dir + "/" + basename)
            shell.fs.write_file(out_path, content.encode('latin-1', errors='replace'))
            print(f"  inflating: {out_path}")
        return 0


class DdCommand(ShellCommand):
    """Convert and copy a file."""

    def __init__(self):
        super().__init__("dd", "Convert and copy a file")

    def execute(self, args: List[str], shell) -> int:
        params: Dict[str, str] = {}
        for a in args:
            if '=' in a:
                k, v = a.split('=', 1)
                params[k.strip()] = v.strip()
        inf  = params.get('if')
        outf = params.get('of')
        bs   = int(params.get('bs', '512'))
        count = params.get('count')
        skip  = int(params.get('skip', '0'))

        if inf:
            data = shell.fs.read_file(inf)
            if data is None:
                print(f"dd: {inf}: No such file or directory", file=sys.stderr)
                return 1
        else:
            try:
                data = sys.stdin.read().encode()
            except Exception:
                data = b""

        # Apply skip (in blocks)
        data = data[skip * bs:]
        # Apply count
        if count is not None:
            data = data[:int(count) * bs]

        if outf:
            shell.fs.write_file(outf, data)
        else:
            sys.stdout.buffer.write(data) if hasattr(sys.stdout, 'buffer') else sys.stdout.write(data.decode('latin-1', errors='replace'))

        blocks = (len(data) + bs - 1) // bs if bs else 0
        print(f"{blocks}+0 records in", file=sys.stderr)
        print(f"{blocks}+0 records out", file=sys.stderr)
        print(f"{len(data)} bytes copied", file=sys.stderr)
        return 0


class NlCommand(ShellCommand):
    """Number lines of files."""

    def __init__(self):
        super().__init__("nl", "Number lines of files")

    def execute(self, args: List[str], shell) -> int:
        # Options
        body_numbering = 't'  # t=non-empty (default), a=all, n=none
        start = 1
        increment = 1
        filenames: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-b',) and i + 1 < len(args):
                i += 1
                body_numbering = args[i]
            elif args[i] in ('-v',) and i + 1 < len(args):
                i += 1
                try:
                    start = int(args[i])
                except ValueError:
                    pass
            elif args[i] in ('-i',) and i + 1 < len(args):
                i += 1
                try:
                    increment = int(args[i])
                except ValueError:
                    pass
            elif not args[i].startswith('-'):
                filenames.append(args[i])
            i += 1

        def _number_lines(lines: List[str]) -> None:
            n = start
            for line in lines:
                stripped = line.rstrip('\n')
                # Default body_numbering='t': number non-empty lines only
                if body_numbering == 'a' or (body_numbering == 't' and stripped) or (body_numbering not in ('a', 't', 'n') and stripped):
                    print(f"{n:>6}\t{stripped}")
                    n += increment
                elif body_numbering == 'n':
                    print(f"      \t{stripped}")
                else:
                    print(f"      \t{stripped}")

        if filenames:
            for fn in filenames:
                data = shell.fs.read_file(fn)
                if data is None:
                    print(f"nl: {fn}: No such file or directory", file=sys.stderr)
                    return 1
                _number_lines(data.decode(errors='replace').splitlines(keepends=True))
        else:
            lines = sys.stdin.readlines()
            _number_lines(lines)
        return 0


class OdCommand(ShellCommand):
    """Dump files in octal and other formats."""

    def __init__(self):
        super().__init__("od", "Dump files in octal and other formats")

    def execute(self, args: List[str], shell) -> int:
        fmt = 'o'   # o=octal, x=hex, d=decimal, c=char
        filenames: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-t',) and i + 1 < len(args):
                i += 1
                fmt = args[i][0] if args[i] else 'o'
            elif args[i] == '-x':
                fmt = 'x'
            elif args[i] == '-c':
                fmt = 'c'
            elif args[i] == '-d':
                fmt = 'd'
            elif not args[i].startswith('-'):
                filenames.append(args[i])
            i += 1

        if filenames:
            data = b""
            for fn in filenames:
                d = shell.fs.read_file(fn)
                if d is None:
                    print(f"od: {fn}: No such file or directory", file=sys.stderr)
                    return 1
                data += d
        else:
            data = sys.stdin.read().encode()

        offset = 0
        while offset < len(data):
            chunk = data[offset:offset+16]
            addr = f"{offset:07o}"
            if fmt == 'x':
                values = ' '.join(f"{b:02x}" for b in chunk)
            elif fmt == 'd':
                values = ' '.join(f"{b:3d}" for b in chunk)
            elif fmt == 'c':
                values = ' '.join(chr(b) if 32 <= b < 127 else f"\\{b:03o}" for b in chunk)
            else:  # octal default
                values = ' '.join(f"{b:03o}" for b in chunk)
            print(f"{addr}  {values}")
            offset += 16
        print(f"{offset:07o}")
        return 0


class XxdCommand(ShellCommand):
    """Make a hex dump or reverse."""

    def __init__(self):
        super().__init__("xxd", "Make a hexdump or do the reverse")

    def execute(self, args: List[str], shell) -> int:
        reverse = '-r' in args or '--reverse' in args
        cols = 16
        filenames = [a for a in args if not a.startswith('-')]

        if filenames:
            data = shell.fs.read_file(filenames[0])
            if data is None:
                print(f"xxd: {filenames[0]}: No such file or directory", file=sys.stderr)
                return 1
        else:
            data = sys.stdin.read().encode()

        if reverse:
            # reverse mode: parse hex dump back to binary
            import re as _re
            result = b""
            for line in data.decode(errors='replace').splitlines():
                m = _re.match(r'[0-9a-f]+:\s+((?:[0-9a-f]{2}\s*)+)', line)
                if m:
                    hex_part = m.group(1).replace(' ', '')
                    try:
                        result += bytes.fromhex(hex_part)
                    except Exception:
                        pass
            sys.stdout.write(result.decode('latin-1', errors='replace'))
        else:
            offset = 0
            while offset < len(data):
                chunk = data[offset:offset+cols]
                hex_part = ' '.join(f"{b:02x}" for b in chunk)
                # pad to fill cols * 3 - 1
                hex_part = hex_part.ljust(cols * 3 - 1)
                ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print(f"{offset:08x}: {hex_part}  {ascii_part}")
                offset += cols
        return 0


class NohupCommand(ShellCommand):
    """Run a command immune to hangups."""

    def __init__(self):
        super().__init__("nohup", "Run a command immune to hangups, with output to nohup.out")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: nohup command [args ...]")
            return 1
        cmd_line = ' '.join(args)
        # Redirect stdout to nohup.out
        nohup_path = shell.fs._normalize_path(
            shell.environment.get("HOME", "/root") + "/nohup.out")
        old_stdout = sys.stdout
        captured = StringIO()
        sys.stdout = captured
        rc = 0
        try:
            rc = shell.execute(cmd_line, save_to_history=False)
        except Exception:
            rc = 1
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        # Append to nohup.out
        existing = shell.fs.read_file(nohup_path) or b""
        shell.fs.write_file(nohup_path, existing + output.encode())
        print(f"nohup: appending output to '{nohup_path}'")
        return rc


class MountCommand(ShellCommand):
    """Mount a virtual filesystem."""

    _mount_table: Dict[str, str] = {}  # mountpoint -> device

    def __init__(self):
        super().__init__("mount", "Mount a filesystem")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            # List mounts
            default_mounts = [
                ("pureos-rootfs", "/",    "pureos", "rw"),
                ("tmpfs",         "/tmp", "tmpfs",  "rw"),
                ("proc",          "/proc","proc",   "ro"),
                ("devfs",         "/dev", "devfs",  "rw"),
            ]
            for dev, mp, fstype, opts in default_mounts:
                print(f"{dev} on {mp} type {fstype} ({opts})")
            for mp, dev in MountCommand._mount_table.items():
                print(f"{dev} on {mp} type virtualfs (rw)")
            return 0

        if len(args) < 2:
            print("Usage: mount <device> <mountpoint>")
            return 1

        device, mountpoint = args[0], args[1]
        # Create mountpoint directory if needed
        if not shell.fs.exists(mountpoint):
            shell.fs.mkdir(mountpoint, parents=True)
        MountCommand._mount_table[mountpoint] = device
        print(f"Mounted {device} on {mountpoint}")
        return 0


class UmountCommand(ShellCommand):
    """Unmount a virtual filesystem."""

    def __init__(self):
        super().__init__("umount", "Unmount a filesystem")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: umount <mountpoint>")
            return 1
        mountpoint = args[0]
        if mountpoint in MountCommand._mount_table:
            del MountCommand._mount_table[mountpoint]
            print(f"Unmounted {mountpoint}")
            return 0
        print(f"umount: {mountpoint}: not mounted", file=sys.stderr)
        return 1


class ColumnCommand(ShellCommand):
    """Format input into columns."""

    def __init__(self):
        super().__init__("column", "Format input into multiple columns")

    def execute(self, args: List[str], shell) -> int:
        separator = None
        table_mode = '-t' in args or '--table' in args
        filenames: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-s', '--separator') and i + 1 < len(args):
                i += 1
                separator = args[i]
            elif args[i] == '-t' or args[i] == '--table':
                pass
            elif not args[i].startswith('-'):
                filenames.append(args[i])
            i += 1

        lines: List[str] = []
        if filenames:
            for fn in filenames:
                data = shell.fs.read_file(fn)
                if data is None:
                    print(f"column: {fn}: No such file or directory", file=sys.stderr)
                    return 1
                lines.extend(data.decode(errors='replace').splitlines())
        else:
            lines = [l.rstrip('\n') for l in sys.stdin.readlines()]

        if not lines:
            return 0

        if table_mode:
            # Split each line into fields and align columns
            rows = []
            for line in lines:
                if separator:
                    fields = line.split(separator)
                else:
                    fields = line.split()
                rows.append(fields)
            if not rows:
                return 0
            ncols = max(len(r) for r in rows)
            widths = [0] * ncols
            for row in rows:
                for j, field in enumerate(row):
                    widths[j] = max(widths[j], len(field))
            for row in rows:
                parts = []
                for j in range(ncols):
                    val = row[j] if j < len(row) else ""
                    if j < ncols - 1:
                        parts.append(val.ljust(widths[j]))
                    else:
                        parts.append(val)
                print("  ".join(parts))
        else:
            # Multi-column output (like `ls` style)
            if not lines:
                return 0
            try:
                term_width = 80
            except Exception:
                term_width = 80
            max_len = max(len(l) for l in lines) + 2
            ncols = max(1, term_width // max_len)
            nrows = (len(lines) + ncols - 1) // ncols
            for r in range(nrows):
                row_parts = []
                for c in range(ncols):
                    idx = r + c * nrows
                    if idx < len(lines):
                        row_parts.append(lines[idx].ljust(max_len))
                print("".join(row_parts).rstrip())
        return 0


class StraceCommand(ShellCommand):
    """Trace system calls (simulated)."""

    def __init__(self):
        super().__init__("strace", "Trace system calls and signals (simulated)")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: strace command [args ...]")
            return 1

        # Filter out strace options
        cmd_args = []
        i = 0
        while i < len(args):
            if args[i] in ('-e', '-p', '-o', '-s') and i + 1 < len(args):
                i += 2
                continue
            if args[i].startswith('-'):
                i += 1
                continue
            cmd_args.append(args[i])
            i += 1

        if not cmd_args:
            print("strace: must specify a command to trace")
            return 1

        cmd_line = ' '.join(cmd_args)
        # Simulated syscall trace
        import time as _time
        simulated_calls = [
            'execve("{cmd}", ["{cmd}"], envp) = 0'.format(cmd=cmd_args[0]),
            'brk(NULL)                           = 0x55a000',
            'mmap(NULL, 4096, PROT_READ, MAP_PRIVATE, 3, 0) = 0x7f0000',
            'open("/etc/ld.so.cache", O_RDONLY)  = 3',
            'fstat(3, {st_mode=S_IFREG, st_size=128}) = 0',
            'mmap(NULL, 128, PROT_READ, MAP_PRIVATE, 3, 0) = 0x7f1000',
            'close(3)                            = 0',
            'open("/lib/libc.so.6", O_RDONLY)    = 3',
            'read(3, "\\x7fELF...", 832)           = 832',
            'close(3)                            = 0',
            'write(1, ..., ...) = ...',
        ]
        for call in simulated_calls:
            print(call, file=sys.stderr)
            _time.sleep(0.01)

        rc = shell.execute(cmd_line, save_to_history=False)
        import os as _os
        print(f"+++ exited with {rc} +++", file=sys.stderr)
        return rc


class InstallCommand(ShellCommand):
    """Copy files and set attributes (like GNU install)."""

    def __init__(self):
        super().__init__("install", "Copy files and set attributes")

    def execute(self, args: List[str], shell) -> int:
        mode = "755"
        owner = None
        group = None
        make_dir = False
        filenames: List[str] = []
        i = 0
        while i < len(args):
            if args[i] in ('-m', '--mode') and i + 1 < len(args):
                i += 1
                mode = args[i]
            elif args[i].startswith('-m'):
                mode = args[i][2:]
            elif args[i] in ('-o', '--owner') and i + 1 < len(args):
                i += 1
                owner = args[i]
            elif args[i] in ('-g', '--group') and i + 1 < len(args):
                i += 1
                group = args[i]
            elif args[i] in ('-d', '--directory'):
                make_dir = True
            elif not args[i].startswith('-'):
                filenames.append(args[i])
            i += 1

        if make_dir:
            for d in filenames:
                shell.fs.mkdir(d, parents=True)
                if owner:
                    shell.fs.chown(d, owner, group)
                print(f"install: created directory '{d}'")
            return 0

        if len(filenames) < 2:
            print("Usage: install [options] source dest")
            return 1

        sources = filenames[:-1]
        dest = filenames[-1]

        for src in sources:
            data = shell.fs.read_file(src)
            if data is None:
                print(f"install: cannot stat '{src}': No such file or directory", file=sys.stderr)
                return 1
            import posixpath as _pp
            # Treat dest as a directory if it ends with '/' or is an existing dir
            dest_norm = shell.fs._normalize_path(dest)
            if dest.endswith('/') or shell.fs.is_directory(dest_norm):
                if not shell.fs.is_directory(dest_norm):
                    shell.fs.mkdir(dest_norm, parents=True)
                target = shell.fs._normalize_path(dest_norm + "/" + _pp.basename(src))
            else:
                target = dest_norm
            shell.fs.write_file(target, data)
            # Apply mode
            try:
                octal_val = int(mode, 8)
                perm_map = {4: 'r', 2: 'w', 1: 'x'}
                perm_str = ""
                for shift in (6, 3, 0):
                    bits = (octal_val >> shift) & 0o7
                    perm_str += perm_map.get(4 if bits & 4 else 0, '-')
                    perm_str += perm_map.get(2 if bits & 2 else 0, '-')
                    perm_str += perm_map.get(1 if bits & 1 else 0, '-')
                # Fix: rebuild properly
                perm_str = ""
                for shift in (6, 3, 0):
                    bits = (octal_val >> shift) & 0o7
                    perm_str += ('r' if bits & 4 else '-')
                    perm_str += ('w' if bits & 2 else '-')
                    perm_str += ('x' if bits & 1 else '-')
                shell.fs.chmod(target, perm_str)
            except ValueError:
                shell.fs.chmod(target, "rwxr-xr-x")
            if owner:
                shell.fs.chown(target, owner, group)
            print(f"install: '{src}' -> '{target}'")
        return 0
