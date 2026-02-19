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


__version__ = "1.2.0"
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
    
    def run(self) -> int:
        """Run the operating system."""
        if not self.initialize():
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
    print("  ps        List processes")
    print("  kill      Terminate process")
    print("  uname     System information")
    print("  free      Memory usage")
    print("  df        Disk usage")
    print("  echo      Print text")
    print("  help      Show help")
    print("  clear     Clear screen")
    print("  date      Show date/time")
    print("  whoami    Current user")
    print("  env       Environment variables")
    print("  export    Set environment variable")
    print("  reboot    Reboot system")
    print("  shutdown  Power off")
    print("  exit      Exit shell")


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
