# PureOS

An operating system written entirely in Python using only the standard library. No external dependencies, no pip install required!

## Features

### Core System
- **Virtual Kernel**: Process management, memory allocation, and scheduling
- **Virtual File System**: In-memory filesystem with standard Unix-like hierarchy
- **Shell**: Interactive command interpreter with 30+ built-in commands
- **Process Management**: Create, monitor, and terminate processes
- **Memory Management**: Virtual memory allocation and tracking

### File System
- Hierarchical directory structure (`/bin`, `/etc`, `/home`, `/tmp`, `/var`, etc.)
- File operations: create, read, write, delete, copy, move
- Directory operations: create, remove, navigate
- File permissions and ownership
- Path normalization and resolution

### Shell Commands

#### File Operations
- `ls` - List directory contents (supports `-l`, `-a`, `-la` flags)
- `cd` - Change directory
- `pwd` - Print working directory
- `cat` - Display file contents
- `mkdir` - Create directories (supports `-p` for parents)
- `rmdir` - Remove empty directories
- `rm` - Remove files
- `touch` - Create empty files
- `cp` - Copy files
- `mv` - Move/rename files

#### System Information
- `ps` - List running processes
- `kill` - Terminate processes
- `uname` - System information
- `free` - Memory usage display
- `df` - Disk space usage

#### Utilities
- `echo` - Display text
- `help` - Show available commands
- `clear` - Clear screen
- `date` - Show date and time
- `whoami` - Current user
- `env` - Environment variables
- `export` - Set environment variables

#### Text Editing
- `nano <file>` - Edit files with built-in text editor

#### System Control
- `reboot` - Restart system
- `shutdown` - Power off
- `exit` - Exit shell

#### Persistence
- `save` - Manually save system state
- `load` - Load previously saved state

## Quick Start

### Run Interactive Shell
```bash
python main.py
```

### Run Tests
```bash
python main.py --test
```

### Execute Batch File
```bash
python main.py --batch commands.txt
```

### Show Help
```bash
python main.py --help
```

### Show Version
```bash
python main.py --version
```

## New Features in v1.1

### Persistent Storage
PureOS now automatically saves your filesystem state, command history, and environment variables to `~/.pureos/state.json`. On startup, you'll be prompted to restore your previous session.

### Command History
- Press `!!` to repeat the last command
- Press `!n` to execute the nth command from history
- Use `history` command to view all previous commands

### Text Editor
Built-in nano-like editor for creating and editing files:
```bash
nano filename.txt
```
Editor controls:
- `Ctrl+S` - Save file
- `Ctrl+Q` - Quit editor
- `Ctrl+N` - New line
- `Ctrl+D` - Delete line
- Arrow keys - Navigate

## Example Session

```
$ python main.py
Initializing PureOS...
  [1/4] Starting kernel...
  [2/4] Mounting filesystem...
  [3/4] Loading shell...
  [4/4] Checking for saved state...

  Found saved state:
    Files: 5
    Directories: 3
    History: 12 commands
    Working directory: /home/user

  Load saved state? (y/n): y
  State loaded successfully!

PureOS initialized successfully!

PureOS Shell v1.0
Type 'help' for available commands
Use '!!' to repeat last command, '!n' to run command #n

root@pureos:/home/user$ pwd
/home/user
root@pureos:/home/user$ ls
bin/  dev/  etc/  home/  proc/  root/  tmp/  var/
root@pureos:/home/user$ cd home
root@pureos:/home/user$ mkdir test
root@pureos:/home/user$ cd test
root@pureos:/home/user/test$ echo "Hello, PureOS!" > hello.txt
root@pureos:/home/user/test$ cat hello.txt
Hello, PureOS!
root@pureos:/home/user/test$ ls -l
total 1
drwxr-xr-x 1 root root        0 Feb 19 14:33 .
drwxr-xr-x 1 root root        0 Feb 19 14:33 ..
-rw-r--r-- 1 root root       17 Feb 19 14:33 hello.txt
root@pureos:/home/test$ ps
PID      NAME            STATE        CPU TIME     MEMORY
-----------------------------------------------------------------
1        init            running      0.00s        1024KB
2        shell           running      0.05s        512KB
root@pureos:/home/test$ free
           total        used        free
Mem:       104857600   2048000    102809600
root@pureos:/home/test$ uname -a
PureOS pureos 1.0.0 python_vm PureOS
root@pureos:/home/test$ exit
Shutting down PureOS...
System halted.
```

## Architecture

```
PureOS/
├── core/
│   ├── __init__.py
│   ├── kernel.py        # Process & memory management
│   └── filesystem.py    # Virtual file system
├── shell/
│   ├── __init__.py
│   └── shell.py         # Shell interpreter & commands
├── main.py              # Entry point
└── README.md            # This file
```

## Technical Details

### Kernel
- **Scheduler**: Round-robin with configurable time quantum
- **Memory Manager**: Virtual memory with allocation tracking
- **Process States**: NEW, READY, RUNNING, WAITING, TERMINATED
- **Threading**: Uses Python's threading for process simulation

### File System
- **Storage**: In-memory (volatile)
- **Inodes**: Track metadata (permissions, timestamps, ownership)
- **Paths**: Absolute and relative path support
- **Types**: Regular files, directories, symlinks

### Shell
- **Parser**: Supports quoted arguments and environment variables
- **Commands**: 30+ built-in commands
- **Environment**: Configurable PATH, HOME, USER, etc.
- **Aliases**: Support for command aliases (extensible)

## Design Principles

1. **Zero Dependencies**: Uses only Python standard library
2. **Modular**: Clear separation between kernel, filesystem, and shell
3. **Educational**: Clean, well-documented code
4. **Extensible**: Easy to add new commands and features

## Python Version

Requires Python 3.8 or higher

## License

This project is open source. Feel free to use, modify, and distribute.

## Contributing

PureOS is designed to be simple and educational. Contributions should maintain:
- No external dependencies
- Clear, readable code
- Comprehensive documentation
- Backward compatibility

## Future Enhancements

- [ ] Persistent storage (JSON or pickle)
- [ ] User authentication system
- [ ] Network stack simulation
- [ ] Package manager
- [ ] Text editor (vim-like)
- [ ] Scripting language
- [ ] Graphical interface (using curses)
- [ ] Multi-user support

## About

PureOS demonstrates how operating system concepts can be implemented using only Python's standard library. It's perfect for:
- Learning OS concepts
- Teaching systems programming
- Prototyping OS features
- Understanding process management

---

**PureOS** - Pure Python, Pure Power!
