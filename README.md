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

## New Features in v1.2

### Multi-User System
PureOS now supports multiple users with authentication:

```bash
# Login
PureOS v1.2 - Login
Username: alice
Password: *****

# Create new users (requires root)
useradd -m newuser
passwd newuser

# Switch users
su username

# Show current user
whoami
id

# List active sessions
who
```

### Shell Scripting
Full scripting support with variables, conditionals, and loops:

```bash
#!/bin/sh
# Example script

NAME="PureOS"
if [ -f "/etc/config" ]; then
    echo "Config exists"
else
    echo "Creating config..."
fi

for user in root alice bob; do
    echo "User: $user"
done

# Execute script
bash script.sh
source script.sh
```

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

## What's New in v1.2

### Multi-User System
- **Login system** with password authentication
- **User management**: `useradd`, `userdel`, `passwd`
- **User switching**: `su`, `login`, `logout`
- **Permission system** with root/non-root users
- **Default users**: `root` (password: empty) and `alice` (password: password123)

### Shell Scripting Engine
- **Script execution**: `bash script.sh`
- **Variables**: Local and environment variables with expansion
- **Control flow**: `if/then/else`, `for` loops, `while` loops
- **Conditionals**: File tests (`-f`, `-d`, `-e`), string/numeric comparisons
- **Functions**: Define and call shell functions
- **Test command**: `[ expression ]` for conditions

## What's New in v1.3

### Tab Completion
- **Command completion**: Type `ec<TAB>` to complete to `echo`
- **Filename completion**: Type `/ho<TAB>` to complete to `/home/`
- **Username completion**: Type `su ro<TAB>` to complete to `su root`
- **Variable completion**: Type `echo $HO<TAB>` to complete to `echo $HOME`
- **Multiple matches**: Double-tap Tab to see all matching options

### Advanced Line Editing
- **Cursor movement**: `Ctrl+A` (beginning), `Ctrl+E` (end), arrow keys
- **Line editing**: `Ctrl+K` (kill to end), `Ctrl+U` (kill to start), `Ctrl+W` (delete word)
- **Kill and yank**: `Ctrl+K` to cut, `Ctrl+Y` to paste
- **History search**: `Ctrl+R` to search command history
- **Clear screen**: `Ctrl+L` clears the screen

### Aliases
- **Built-in aliases**: `ll` = `ls -la`, `la` = `ls -a`, `l` = `ls -CF`
- **Custom aliases**: `alias name='command'`
- **List aliases**: `alias` shows all defined aliases
- **Remove aliases**: `unalias name` or `unalias -a` (remove all)

### Prompt Customization
- **PS1 variable**: Customize primary prompt
  - `\u` - Username
  - `\h` - Hostname
  - `\w` - Current working directory
  - `\W` - Basename of current directory
  - `\$` - `#` for root, `$` for others
  - `\t` - Current time (24-hour)
- **PS2 variable**: Customize continuation prompt (for multi-line input)
- **Example**: `export PS1="[\t] \u@\h:\W\$ "`

### Wildcards (Globbing)
- **Asterisk (`*`)**: Match any characters - `rm *.txt`
- **Question mark (`?`)**: Match single character - `ls file?.txt`
- **Character class (`[abc]`)**: Match any character in brackets
- **Examples**:
  - `ls *.sh` - List all .sh files
  - `rm *.tmp` - Remove all .tmp files
  - `cat file?.txt` - Match file1.txt, file2.txt, etc.

### Multi-line Input
- **Line continuation**: End line with `\` to continue on next line
- **PS2 prompt**: Shows continuation prompt (default: `>`)

## Future Enhancements

### Completed Features ✓
- [x] Persistent storage (JSON or pickle) ✓ **v1.1**
- [x] Text editor (vim-like) ✓ **v1.1**
- [x] Command history ✓ **v1.1**
- [x] User authentication system ✓ **v1.2**
- [x] Scripting language ✓ **v1.2**
- [x] Multi-user support ✓ **v1.2**
- [x] Tab completion ✓ **v1.3**
- [x] Line editing with key bindings ✓ **v1.3**
- [x] Command aliases ✓ **v1.3**
- [x] Prompt customization ✓ **v1.3**
- [x] Wildcards/globbing ✓ **v1.3**

### Planned Features
- [ ] Package manager - Install/remove software packages
- [ ] Network stack simulation - Virtual networking
- [ ] Job control - Background processes (`&`, `fg`, `bg`)
- [ ] Graphical interface (using curses)
- [ ] More utilities: `find`, `tar`, `gzip`

## About

PureOS demonstrates how operating system concepts can be implemented using only Python's standard library. It's perfect for:
- Learning OS concepts
- Teaching systems programming
- Prototyping OS features
- Understanding process management

---

**PureOS** - Pure Python, Pure Power!
