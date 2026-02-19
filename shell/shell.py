"""
PureOS Shell
Command interpreter for the operating system.
"""

import sys
import shlex
import time
from io import StringIO
from typing import List, Dict, Callable, Optional, Tuple
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
    
    def __init__(self, kernel, filesystem, authenticator=None, user_manager=None):
        self.kernel = kernel
        self.fs = filesystem
        self.auth = authenticator
        self.um = user_manager
        self.commands: Dict[str, ShellCommand] = {}
        self.running = False
        self.last_exit_code = 0
        self.aliases: Dict[str, str] = {}
        self.environment: Dict[str, str] = {
            "PATH": "/bin",
            "HOME": "/root",
            "USER": "root",
            "SHELL": "/bin/sh",
            "TERM": "xterm",
        }
        # Command history
        self.history: List[str] = []
        self.history_position = 0
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
        self.register_command(NanoCommand())
        self.register_command(GrepCommand())
        self.register_command(HeadCommand())
        self.register_command(TailCommand())
        
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
        
        # Utilities
        self.register_command(EchoCommand())
        self.register_command(HelpCommand())
        self.register_command(ClearCommand())
        self.register_command(DateCommand())
        self.register_command(WhoamiCommand())
        self.register_command(EnvCommand())
        self.register_command(ExportCommand())
        self.register_command(HistoryCommand())
        
        # System
        self.register_command(RebootCommand())
        self.register_command(ShutdownCommand())
        self.register_command(ExitCommand())
    
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
        for key, value in self.environment.items():
            line = line.replace(f"${key}", value)
        
        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()
        
        if not parts:
            return "", []
        
        return parts[0], parts[1:]
    
    def execute(self, line: str, save_to_history: bool = True) -> int:
        """Execute a command line."""
        stripped = line.strip()

        # Handle history commands
        if stripped == "!!":
            # Repeat last command
            if not self.history:
                print("!!: event not found")
                return 1
            line = self.history[-1]
            print(f"{line}")
            return self.execute(line, save_to_history=False)

        if stripped.startswith("!") and stripped[1:].isdigit():
            # Execute command by history number
            n = int(stripped[1:])
            if n < 1 or n > len(self.history):
                print(f"{stripped}: event not found")
                return 1
            line = self.history[n - 1]
            print(f"{line}")
            return self.execute(line, save_to_history=False)

        # Save to history (except for history commands themselves)
        if save_to_history and stripped and not stripped.startswith("!"):
            self.history.append(stripped)
            self.history_position = len(self.history)

        # Parse redirection
        output_file = None
        append_mode = False

        # Check for output redirection
        if ' >> ' in line:
            parts = line.split(' >> ', 1)
            line = parts[0].strip()
            output_file = parts[1].strip()
            append_mode = True
        elif ' > ' in line:
            parts = line.split(' > ', 1)
            line = parts[0].strip()
            output_file = parts[1].strip()
            append_mode = False

        command_name, args = self.parse_input(line)

        if not command_name:
            return 0

        # Capture output if redirecting
        old_stdout = sys.stdout
        output_buffer = None

        if output_file and command_name in self.commands:
            output_buffer = StringIO()
            sys.stdout = output_buffer

        try:
            if command_name in self.commands:
                try:
                    self.last_exit_code = self.commands[command_name].execute(args, self)
                except Exception as e:
                    if output_buffer:
                        sys.stdout = old_stdout
                    print(f"Error: {e}")
                    self.last_exit_code = 1
            else:
                if output_buffer:
                    sys.stdout = old_stdout
                print(f"{command_name}: command not found")
                self.last_exit_code = 127

            # Handle output redirection
            if output_file and output_buffer:
                sys.stdout = old_stdout
                output_content = output_buffer.getvalue()

                # Get existing content if appending
                existing_content = b""
                if append_mode and self.fs.exists(output_file):
                    existing = self.fs.read_file(output_file)
                    if existing:
                        existing_content = existing

                # Write to file
                new_content = existing_content + output_content.encode('utf-8')
                if not self.fs.write_file(output_file, new_content):
                    print(f"Cannot write to '{output_file}'")
                    self.last_exit_code = 1

        finally:
            # Always restore stdout
            sys.stdout = old_stdout
            if output_buffer:
                output_buffer.close()

        return self.last_exit_code
    
    def get_prompt(self) -> str:
        """Generate shell prompt based on current user."""
        if self.auth and self.auth.is_authenticated():
            username = self.auth.get_current_user()
        else:
            username = self.environment.get('USER', 'user')
        
        cwd = self.fs.get_current_directory()
        # Replace home directory with ~
        if self.auth:
            home = self.auth.get_user_home()
            if cwd.startswith(home):
                cwd = "~" + cwd[len(home):]
        
        return f"{username}@pureos:{cwd}$ "
    
    def run(self) -> None:
        """Run the shell interactively."""
        self.running = True

        print("PureOS Shell v1.0")
        print("Type 'help' for available commands")
        print("Use '!!' to repeat last command, '!n' to run command #n")
        print()

        while self.running:
            try:
                prompt = self.get_prompt()
                line = input(prompt)
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
            # Read from stdin
            try:
                while True:
                    line = input()
                    print(line)
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
        
        recursive = "-r" in args or "-rf" in args
        force = "-f" in args or "-rf" in args
        paths = [a for a in args if not a.startswith("-")]
        
        for path in paths:
            if shell.fs.is_directory(path):
                if not recursive:
                    if not force:
                        print(f"rm: cannot remove '{path}': Is a directory")
                    return 1
                # TODO: Implement recursive deletion
                print(f"rm: recursive deletion not yet implemented")
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
                "File Operations": ["ls", "cd", "pwd", "cat", "mkdir", "rmdir", "rm", "touch", "cp", "mv"],
                "System Info": ["ps", "kill", "uname", "free", "df"],
                "Utilities": ["echo", "help", "clear", "date", "whoami", "env", "export", "history"],
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
        
        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                shell.environment[key] = value
            elif arg in shell.environment:
                # Mark as exported (already in environment)
                pass
        
        return 0


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
        if len(args) < 2:
            print("Usage: grep <pattern> <file>")
            return 1

        pattern = args[0]
        filename = args[1]

        content = shell.fs.read_file(filename)
        if content is None:
            print(f"grep: {filename}: No such file or directory")
            return 1

        lines = content.decode('utf-8', errors='replace').split('\n')
        found = False

        for i, line in enumerate(lines, 1):
            if pattern in line:
                print(f"{filename}:{i}:{line}")
                found = True

        return 0 if found else 1


class HeadCommand(ShellCommand):
    """Output the first part of files."""

    def __init__(self):
        super().__init__("head", "Output the first part of files")

    def execute(self, args: List[str], shell) -> int:
        lines_count = 10
        filename = None

        # Parse arguments
        for i, arg in enumerate(args):
            if arg.startswith('-n'):
                if len(arg) > 2:
                    lines_count = int(arg[2:])
                elif i + 1 < len(args):
                    lines_count = int(args[i + 1])
            elif not arg.startswith('-'):
                filename = arg

        if not filename:
            print("head: missing file operand")
            return 1

        content = shell.fs.read_file(filename)
        if content is None:
            print(f"head: cannot open '{filename}' for reading: No such file or directory")
            return 1

        lines = content.decode('utf-8', errors='replace').split('\n')
        for line in lines[:lines_count]:
            print(line)

        return 0


class TailCommand(ShellCommand):
    """Output the last part of files."""

    def __init__(self):
        super().__init__("tail", "Output the last part of files")

    def execute(self, args: List[str], shell) -> int:
        lines_count = 10
        filename = None

        # Parse arguments
        for i, arg in enumerate(args):
            if arg.startswith('-n'):
                if len(arg) > 2:
                    lines_count = int(arg[2:])
                elif i + 1 < len(args):
                    lines_count = int(args[i + 1])
            elif not arg.startswith('-'):
                filename = arg

        if not filename:
            print("tail: missing file operand")
            return 1

        content = shell.fs.read_file(filename)
        if content is None:
            print(f"tail: cannot open '{filename}' for reading: No such file or directory")
            return 1

        lines = content.decode('utf-8', errors='replace').split('\n')
        start = max(0, len(lines) - lines_count)
        for line in lines[start:]:
            print(line)

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
