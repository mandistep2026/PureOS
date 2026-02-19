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
from shell.shell import Shell


__version__ = "1.0.0"
__author__ = "PureOS Team"


class PureOS:
    """Main PureOS operating system class."""
    
    def __init__(self):
        self.kernel = None
        self.filesystem = None
        self.shell = None
        self.running = False
    
    def initialize(self) -> bool:
        """Initialize the operating system."""
        print("Initializing PureOS...")
        
        try:
            # Initialize kernel
            print("  [1/3] Starting kernel...")
            self.kernel = Kernel()
            self.kernel.start()
            
            # Initialize filesystem
            print("  [2/3] Mounting filesystem...")
            self.filesystem = FileSystem()
            
            # Initialize shell
            print("  [3/3] Loading shell...")
            self.shell = Shell(self.kernel, self.filesystem)
            
            print("\nPureOS initialized successfully!")
            return True
            
        except Exception as e:
            print(f"\nError initializing PureOS: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the operating system."""
        print("\nShutting down PureOS...")
        
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
