#!/usr/bin/env python3
"""
PureOS - An operating system written entirely in Python
No external dependencies - uses only Python standard library

Usage:
    python main.py [options]

Options:
    --help, -h      Show this help message
    --version, -v   Show version information
    --test          Run system tests
    --batch FILE    Execute commands from file and exit
"""

import sys
import os

# Ensure we're using only standard library
if __name__ == "__main__":
    # Check for external dependencies
    try:
        import importlib
        # Only allow standard library modules
        forbidden_modules = ['requests', 'numpy', 'pandas', 'django', 'flask', 
                           'pytest', 'unittest.mock', 'pip', 'setuptools',
                           'wheel', 'twine', 'build', 'virtualenv', 'venv']
        for module in forbidden_modules:
            if module in sys.modules:
                print(f"Error: External dependency '{module}' detected!")
                print("PureOS only uses Python standard library.")
                sys.exit(1)
    except Exception:
        pass

from core.kernel import Kernel
from core.filesystem import FileSystem
from core.persistence import PersistenceManager
from core.user import UserManager
from core.auth import Authenticator
from shell.shell import Shell


__version__ = "1.6.0"
__author__ = "PureOS Team"


class PureOS:
    """Main PureOS operating system class."""

    def __init__(self):
        self.kernel = None
        self.filesystem = None
        self.shell = None
        self.user_manager = None
        self.authenticator = None
        self.running = False
        self.persistence = PersistenceManager()
        self.auto_save = True
        self.state_loaded = False
        self.require_login = True  # Enable login system

    def initialize(self) -> bool:
        """Initialize the operating system."""
        print("Initializing PureOS...")

        try:
            # Initialize kernel
            print("  [1/5] Starting kernel...")
            self.kernel = Kernel()
            self.kernel.start()

            # Initialize filesystem
            print("  [2/5] Mounting filesystem...")
            self.filesystem = FileSystem()

            # Initialize user management
            print("  [3/5] Initializing user management...")
            self.user_manager = UserManager(self.filesystem)
            self.authenticator = Authenticator(self.user_manager)

            # Initialize shell with auth and user manager
            print("  [4/5] Loading shell...")
            self.shell = Shell(self.kernel, self.filesystem, 
                             self.authenticator, self.user_manager)

            # Try to load saved state
            print("  [5/5] Checking for saved state...")
            if self.persistence.state_exists():
                info = self.persistence.get_state_info()
                if info:
                    print(f"\n  Found saved state:")
                    print(f"    Files: {info['files']}")
                    print(f"    Directories: {info['directories']}")
                    print(f"    History: {info['history_count']} commands")
                    print(f"    Working directory: {info['current_directory']}")
                    print(f"\n  Load saved state? (y/n): ", end='', flush=True)

                    try:
                        response = input().lower().strip()
                        if response == 'y':
                            if self.persistence.load_state(self.filesystem, self.shell, self.kernel):
                                print("  State loaded successfully!")
                                self.state_loaded = True
                            else:
                                print("  Failed to load state, starting fresh.")
                    except (EOFError, KeyboardInterrupt):
                        print("\n  Skipping state load.")

            print("\nPureOS initialized successfully!")
            return True

        except Exception as e:
            print(f"\nError initializing PureOS: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the operating system."""
        print("\nShutting down PureOS...")

        # Auto-save state if enabled
        if self.auto_save and self.filesystem and self.shell:
            print("  Saving system state...")
            if self.persistence.save_state(self.filesystem, self.shell, self.kernel):
                print("  State saved to ~/.pureos/state.json")
            else:
                print("  Warning: Failed to save state")

        if self.kernel:
            self.kernel.stop()

        print("System halted.")
    
    def _login_prompt(self) -> bool:
        """Display login prompt and authenticate user.
        
        Returns:
            True if login successful, False otherwise
        """
        print("\n" + "=" * 50)
        print("PureOS v1.2 - Login")
        print("=" * 50)
        print()
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                username = input("Username: ").strip()
                if not username:
                    print("Error: Username required")
                    continue
                
                if not self.user_manager.user_exists(username):
                    print("Error: Invalid username or password")
                    continue
                
                # Get password
                import getpass
                password = getpass.getpass("Password: ")
                
                # Attempt authentication
                success, result = self.authenticator.login(username, password)
                
                if success:
                    print(f"\nWelcome, {username}!")
                    if username == "alice":
                        print("Default password is: password123")
                        print("Change it with: passwd")
                    print()
                    
                    # Set up user environment
                    user = self.user_manager.get_user(username)
                    if user:
                        self.shell.environment["USER"] = username
                        self.shell.environment["HOME"] = user.home_dir
                        self.filesystem.change_directory(user.home_dir)
                    
                    return True
                else:
                    print(f"Error: {result}")
                    
            except (EOFError, KeyboardInterrupt):
                print("\n")
                return False
        
        print("\nMaximum login attempts exceeded")
        return False
    
    def run(self) -> int:
        """Run the operating system."""
        if not self.initialize():
            return 1
        
        # Show login prompt if enabled
        if self.require_login and self.authenticator:
            if not self._login_prompt():
                print("Login failed, shutting down...")
                self.shutdown()
                return 1
        
        try:
            if self.shell is not None:
                self.shell.run()
        except KeyboardInterrupt:
            print("\n")
        finally:
            self.shutdown()
        
        return 0
    
    def run_batch(self, filename: str) -> int:
        """Execute commands from a file."""
        if not self.initialize():
            return 1
        
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and self.shell is not None:
                    print(f"$ {line}")
                    self.shell.execute(line)
        
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
        finally:
            self.shutdown()
        
        return 0
    
    def run_tests(self) -> int:
        """Run system tests."""
        print("Running PureOS system tests...\n")
        
        passed = 0
        failed = 0
        
        # Test 1: Kernel initialization
        print("Test 1: Kernel initialization...")
        try:
            kernel = Kernel()
            kernel.start()
            assert kernel is not None
            kernel.stop()
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 2: Filesystem operations
        print("Test 2: Filesystem operations...")
        try:
            fs = FileSystem()
            assert fs.exists("/")
            assert fs.mkdir("/test_dir")
            assert fs.exists("/test_dir")
            assert fs.create_file("/test_dir/file.txt", b"Hello, PureOS!")
            content = fs.read_file("/test_dir/file.txt")
            assert content == b"Hello, PureOS!"
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 3: Process creation
        print("Test 3: Process creation...")
        try:
            kernel = Kernel()
            kernel.start()
            
            def test_process():
                return "Process executed successfully"
            
            pid = kernel.create_process("test", test_process)
            assert pid > 0
            import time
            time.sleep(0.2)  # Let process execute
            kernel.stop()
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 4: Shell commands
        print("Test 4: Shell commands...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert "ls" in shell.commands
            assert "cd" in shell.commands
            assert "pwd" in shell.commands
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 5: Standard directories
        print("Test 5: Standard directories...")
        try:
            fs = FileSystem()
            assert fs.exists("/bin")
            assert fs.exists("/etc")
            assert fs.exists("/home")
            assert fs.exists("/tmp")
            assert fs.exists("/var")
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 6: Recursive deletion
        print("Test 6: Recursive deletion...")
        try:
            fs = FileSystem()
            assert fs.mkdir("/tmp/tree")
            assert fs.mkdir("/tmp/tree/branch")
            assert fs.create_file("/tmp/tree/branch/leaf.txt", b"leaf")
            assert fs.exists("/tmp/tree/branch/leaf.txt")
            assert fs.remove_tree("/tmp/tree")
            assert not fs.exists("/tmp/tree")
            assert not fs.exists("/tmp/tree/branch")
            assert not fs.exists("/tmp/tree/branch/leaf.txt")
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 7: Package manager
        print("Test 7: Package manager...")
        try:
            from core.package import PackageManager
            pm = PackageManager()
            packages = pm.list_available()
            assert len(packages) > 0
            assert pm.is_installed("vim") == False
            success, msg = pm.install("vim")
            assert success
            assert pm.is_installed("vim") == True
            success, msg = pm.remove("vim")
            assert success
            assert pm.is_installed("vim") == False
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 8: Network manager
        print("Test 8: Network manager...")
        try:
            from core.network import NetworkManager, NetworkInterface, NetworkState
            nm = NetworkManager()
            assert nm.get_hostname() == "pureos"
            nm.set_hostname("testhost")
            assert nm.get_hostname() == "testhost"
            iface = nm.get_interface("eth0")
            assert iface is not None
            assert iface.ip_address == "192.168.1.100"
            success, results, hostname = nm.ping("8.8.8.8", 2)
            assert success == True
            assert len(results) == 2
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 9: Uptime tracking
        print("Test 9: Uptime tracking...")
        try:
            import time
            kernel = Kernel()
            kernel.start()
            time.sleep(0.05)
            assert kernel.get_uptime() > 0
            info = kernel.get_system_info()
            assert info["uptime_seconds"] > 0
            kernel.stop()
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 10: Command discovery tools
        print("Test 10: Command discovery tools...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert "which" in shell.commands
            assert "type" in shell.commands
            assert shell.execute("type ls") == 0
            assert shell.execute("type definitely_missing_cmd") == 1
            assert shell.execute("which -a ls") == 0
            assert shell.execute("type -a ls") == 0
            assert shell.execute("which -a definitely_missing_cmd") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
        
        # Test 11: Alias persistence
        print("Test 11: Alias persistence...")
        try:
            import tempfile
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            shell.execute("alias gs='echo status'")
            shell.execute("unalias ll")

            with tempfile.TemporaryDirectory() as state_dir:
                pm = PersistenceManager(state_dir=state_dir)
                assert pm.save_state(fs, shell, kernel)

                reloaded_fs = FileSystem()
                reloaded_shell = Shell(kernel, reloaded_fs)
                assert pm.load_state(reloaded_fs, reloaded_shell, kernel)
                assert reloaded_shell.aliases.get("gs") == "echo status"
                assert "ll" not in reloaded_shell.aliases
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 12: File metadata commands
        print("Test 12: File metadata commands...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("touch /tmp/meta.txt") == 0
            assert shell.execute("chmod rwxr----- /tmp/meta.txt") == 0
            inode = fs.get_inode("/tmp/meta.txt")
            assert inode is not None
            assert inode.permissions == "rwxr-----"
            assert shell.execute("chown alice:staff /tmp/meta.txt") == 0
            inode = fs.get_inode("/tmp/meta.txt")
            assert inode.owner == "alice"
            assert inode.group == "staff"
            assert shell.execute("chmod 755 /tmp/meta.txt") == 0
            inode = fs.get_inode("/tmp/meta.txt")
            assert inode.permissions == "rwxr-xr-x"
            assert shell.execute("stat /tmp/meta.txt") == 0
            assert shell.execute("stat /tmp/does-not-exist") == 1
            assert shell.execute("chmod 999 /tmp/meta.txt") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 13: Find command
        print("Test 13: Find command...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("mkdir -p /tmp/find_demo/sub") == 0
            assert shell.execute("touch /tmp/find_demo/readme.txt") == 0
            assert shell.execute("touch /tmp/find_demo/sub/notes.log") == 0
            assert shell.execute("find /tmp/find_demo") == 0
            assert shell.execute("find /tmp/find_demo -name '*.txt'") == 0
            assert shell.execute("find /tmp/find_demo -type d") == 0
            assert shell.execute("find /tmp/find_demo -type f") == 0
            assert shell.execute("find /tmp/find_demo -maxdepth 1 > /tmp/find_maxdepth.txt") == 0
            assert fs.read_file("/tmp/find_maxdepth.txt") == b"/tmp/find_demo\n/tmp/find_demo/readme.txt\n/tmp/find_demo/sub\n"
            assert shell.execute("find /tmp/find_demo -mindepth 1 -type f > /tmp/find_mindepth.txt") == 0
            assert fs.read_file("/tmp/find_mindepth.txt") == b"/tmp/find_demo/readme.txt\n/tmp/find_demo/sub/notes.log\n"
            assert shell.execute("find /tmp/find_demo -mindepth 2 -maxdepth 1") == 1
            assert shell.execute("find /tmp/find_demo -maxdepth nope") == 1
            assert shell.execute("find /tmp/find_demo -type x") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 14: Redirection parsing variants
        print("Test 14: Redirection parsing variants...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("echo alpha>/tmp/redir.txt") == 0
            assert fs.read_file("/tmp/redir.txt") == b"alpha\n"
            assert shell.execute("echo beta>>/tmp/redir.txt") == 0
            assert fs.read_file("/tmp/redir.txt") == b"alpha\nbeta\n"
            assert shell.execute("echo gamma > /tmp/redir2.txt") == 0
            assert fs.read_file("/tmp/redir2.txt") == b"gamma\n"
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1


        # Test 15: Environment variable expansion
        print("Test 15: Environment variable expansion...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            shell.environment["PROJECT"] = "PureOS"
            command, args = shell.parse_input("echo ${PROJECT} $HOME")
            assert command == "echo"
            assert args == ["PureOS", "/root"]
            assert shell.execute("which definitely_missing_cmd") == 1
            command, args = shell.parse_input("echo $?")
            assert command == "echo"
            assert args == ["1"]

            # Quote-aware expansion behavior
            command, args = shell.parse_input("echo '$PROJECT' \"$PROJECT\"")
            assert command == "echo"
            assert args == ["$PROJECT", "PureOS"]
            command, args = shell.parse_input(r"echo \$PROJECT")
            assert command == "echo"
            assert args == ["$PROJECT"]
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 16: Environment variable mutation commands
        print("Test 16: Environment variable mutation commands...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("export PROJECT=PureOS") == 0
            assert shell.environment.get("PROJECT") == "PureOS"
            assert shell.execute("unset PROJECT") == 0
            assert "PROJECT" not in shell.environment
            assert shell.execute("export 1INVALID=bad") == 1
            assert shell.execute("unset 1INVALID") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 17: rm option parsing
        print("Test 17: rm option parsing...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("mkdir -p /tmp/rm_opts/sub") == 0
            assert shell.execute("touch /tmp/rm_opts/sub/file.txt") == 0
            assert shell.execute("rm -rf /tmp/rm_opts") == 0
            assert not fs.exists("/tmp/rm_opts")

            assert shell.execute("mkdir -p /tmp/rm_long/sub") == 0
            assert shell.execute("touch /tmp/rm_long/sub/file.txt") == 0
            assert shell.execute("rm --recursive --force /tmp/rm_long") == 0
            assert not fs.exists("/tmp/rm_long")

            assert shell.execute("touch /tmp/rm_dash_file") == 0
            assert shell.execute("rm -- /tmp/rm_dash_file") == 0
            assert not fs.exists("/tmp/rm_dash_file")

            assert shell.execute("rm -z /tmp/nowhere") == 1
            assert shell.execute("rm --bad-option /tmp/nowhere") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 18: Sort command
        print("Test 18: Sort command...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("echo banana > /tmp/sort.txt") == 0
            assert shell.execute("echo apple >> /tmp/sort.txt") == 0
            assert shell.execute("echo banana >> /tmp/sort.txt") == 0
            assert shell.execute("sort /tmp/sort.txt > /tmp/sort_out.txt") == 0
            assert fs.read_file("/tmp/sort_out.txt") == b"apple\nbanana\nbanana\n"
            assert shell.execute("sort -u /tmp/sort.txt > /tmp/sort_unique.txt") == 0
            assert fs.read_file("/tmp/sort_unique.txt") == b"apple\nbanana\n"
            assert shell.execute("sort -r /tmp/sort.txt > /tmp/sort_reverse.txt") == 0
            assert fs.read_file("/tmp/sort_reverse.txt") == b"banana\nbanana\napple\n"
            assert shell.execute("sort -z /tmp/sort.txt") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 19: Head/Tail command option parsing
        print("Test 19: Head/Tail command option parsing...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("echo one > /tmp/ht1.txt") == 0
            assert shell.execute("echo two >> /tmp/ht1.txt") == 0
            assert shell.execute("echo three >> /tmp/ht1.txt") == 0
            assert shell.execute("echo alpha > /tmp/ht2.txt") == 0
            assert shell.execute("echo beta >> /tmp/ht2.txt") == 0

            assert shell.execute("head -n 2 /tmp/ht1.txt > /tmp/head_n.txt") == 0
            assert fs.read_file("/tmp/head_n.txt") == b"one\ntwo\n"
            assert shell.execute("tail -n2 /tmp/ht1.txt > /tmp/tail_n.txt") == 0
            assert fs.read_file("/tmp/tail_n.txt") == b"two\nthree\n"
            assert shell.execute("head -n two /tmp/ht1.txt") == 1
            assert shell.execute("tail -n -1 /tmp/ht1.txt") == 1
            assert shell.execute("head -z /tmp/ht1.txt") == 1
            assert shell.execute("tail -z /tmp/ht1.txt") == 1

            assert shell.execute("head -n 1 /tmp/ht1.txt /tmp/ht2.txt > /tmp/head_multi.txt") == 0
            assert b"==> /tmp/ht1.txt <==" in fs.read_file("/tmp/head_multi.txt")
            assert b"==> /tmp/ht2.txt <==" in fs.read_file("/tmp/head_multi.txt")

            assert shell.execute("tail -n 1 /tmp/ht1.txt /tmp/ht2.txt > /tmp/tail_multi.txt") == 0
            assert b"==> /tmp/ht1.txt <==" in fs.read_file("/tmp/tail_multi.txt")
            assert b"==> /tmp/ht2.txt <==" in fs.read_file("/tmp/tail_multi.txt")

            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # Test 20: Grep command options
        print("Test 20: Grep command options...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("echo Alpha > /tmp/grep_a.txt") == 0
            assert shell.execute("echo beta >> /tmp/grep_a.txt") == 0
            assert shell.execute("echo ALPHA >> /tmp/grep_a.txt") == 0
            assert shell.execute("echo gamma > /tmp/grep_b.txt") == 0
            assert shell.execute("echo alpha >> /tmp/grep_b.txt") == 0

            assert shell.execute("grep Alpha /tmp/grep_a.txt > /tmp/grep_plain.txt") == 0
            assert fs.read_file("/tmp/grep_plain.txt") == b"Alpha\n"

            assert shell.execute("grep -i alpha /tmp/grep_a.txt > /tmp/grep_i.txt") == 0
            assert fs.read_file("/tmp/grep_i.txt") == b"Alpha\nALPHA\n"

            assert shell.execute("grep -n alpha /tmp/grep_b.txt > /tmp/grep_n.txt") == 0
            assert fs.read_file("/tmp/grep_n.txt") == b"2:alpha\n"

            assert shell.execute("grep -v alpha /tmp/grep_b.txt > /tmp/grep_v.txt") == 0
            assert fs.read_file("/tmp/grep_v.txt") == b"gamma\n"

            assert shell.execute("grep -n alpha /tmp/grep_a.txt /tmp/grep_b.txt > /tmp/grep_multi.txt") == 0
            multi = fs.read_file("/tmp/grep_multi.txt")
            assert b"/tmp/grep_b.txt:2:alpha\n" in multi

            assert shell.execute("grep -z alpha /tmp/grep_a.txt") == 1
            assert shell.execute("grep alpha /tmp/does-not-exist") == 1
            assert shell.execute("grep missing /tmp/grep_a.txt") == 1

            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1


        # Test 21: Uniq command
        print("Test 21: Uniq command...")
        try:
            kernel = Kernel()
            fs = FileSystem()
            shell = Shell(kernel, fs)
            assert shell.execute("echo apple > /tmp/uniq.txt") == 0
            assert shell.execute("echo apple >> /tmp/uniq.txt") == 0
            assert shell.execute("echo banana >> /tmp/uniq.txt") == 0
            assert shell.execute("echo banana >> /tmp/uniq.txt") == 0
            assert shell.execute("echo carrot >> /tmp/uniq.txt") == 0

            assert shell.execute("uniq /tmp/uniq.txt > /tmp/uniq_out.txt") == 0
            assert fs.read_file("/tmp/uniq_out.txt") == b"apple\nbanana\ncarrot\n"

            assert shell.execute("uniq -c /tmp/uniq.txt > /tmp/uniq_count.txt") == 0
            assert fs.read_file("/tmp/uniq_count.txt") == b"2 apple\n2 banana\n1 carrot\n"

            assert shell.execute("uniq -d /tmp/uniq.txt > /tmp/uniq_dup.txt") == 0
            assert fs.read_file("/tmp/uniq_dup.txt") == b"apple\nbanana\n"

            assert shell.execute("uniq -u /tmp/uniq.txt > /tmp/uniq_unique.txt") == 0
            assert fs.read_file("/tmp/uniq_unique.txt") == b"carrot\n"

            assert shell.execute("uniq -x /tmp/uniq.txt") == 1
            assert shell.execute("uniq -d -u /tmp/uniq.txt") == 1
            print("  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        print(f"\n{'='*50}")
        print(f"Test Results: {passed} passed, {failed} failed")
        
        return 0 if failed == 0 else 1


def show_help():
    """Show help message."""
    print(__doc__)
    print("\nAvailable commands:")
    print("  ls        List directory contents")
    print("  cd        Change directory")
    print("  pwd       Print working directory")
    print("  cat       Display file contents")
    print("  mkdir     Create directory")
    print("  rmdir     Remove directory")
    print("  rm        Remove file")
    print("  touch     Create empty file")
    print("  cp        Copy file")
    print("  mv        Move/rename file")
    print("  find      Search for files and directories")
    print("  chmod     Change file permissions")
    print("  chown     Change file owner/group")
    print("  ps        List processes")
    print("  kill      Terminate process")
    print("  uname     System information")
    print("  free      Memory usage")
    print("  df        Disk usage")
    print("  uptime    System uptime")
    print("  echo      Print text")
    print("  help      Show help")
    print("  clear     Clear screen")
    print("  date      Show date/time")
    print("  whoami    Current user")
    print("  env       Environment variables")
    print("  export    Set environment variable")
    print("  unset     Remove environment variable")
    print("  which     Locate a command")
    print("  type      Describe command type")
    print("  sort      Sort lines in text files")
    print("  uniq      Filter adjacent duplicate lines")
    print("  reboot    Reboot system")
    print("  shutdown  Power off")
    print("  exit      Exit shell")
    print("  pkg       Package manager")
    print("  ifconfig  Configure network interface")
    print("  ping      Send ICMP echo requests")
    print("  netstat   Show network connections")
    print("  ip        Show/manipulate routing")
    print("  hostname  Show/set hostname")
    print("  traceroute Trace network path")
    print("  dig       DNS lookup")
    print("  nslookup  Query DNS")


def show_version():
    """Show version information."""
    print(f"PureOS version {__version__}")
    print(f"Running on Python {sys.version}")
    print("Standard library only - no external dependencies")


def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        show_help()
        return 0
    
    if "--version" in args or "-v" in args:
        show_version()
        return 0
    
    if "--test" in args:
        os_obj = PureOS()
        return os_obj.run_tests()
    
    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 < len(args):
            filename = args[idx + 1]
            os_obj = PureOS()
            return os_obj.run_batch(filename)
        else:
            print("Error: --batch requires a filename")
            return 1
    
    # Run interactive shell
    os_obj = PureOS()
    return os_obj.run()


if __name__ == "__main__":
    sys.exit(main())
