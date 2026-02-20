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
- `find` - Search for files and directories (supports `-name`, `-type`, `-mindepth`, and `-maxdepth`)
- `sort` - Sort lines in text files (supports `-r` reverse and `-u` unique)
- `uniq` - Filter adjacent duplicate lines (supports `-c` counts, `-d` duplicates only, `-u` unique only)
- `cut` - Extract selected fields from delimited text (supports `-d` delimiter and `-f` field list/ranges)
- `chmod` - Change file permissions (symbolic mode like `rwxr-xr-x` or octal mode like `755`)
- `chown` - Change file owner/group (format: `owner[:group]`)
- `stat` - Display file or directory metadata (type, size, owner, permissions, timestamps)

#### System Information
- `ps` - List running processes
- `kill` - Terminate processes
- `uname` - System information
- `free` - Memory usage display
- `df` - Disk space usage
- `uptime` - Show system uptime

#### Utilities
- `echo` - Display text
- `help` - Show available commands
- `clear` - Clear screen
- `date` - Show date and time
- `whoami` - Current user
- `env` - Environment variables
- `export` - Set environment variables
- `unset` - Remove environment variables
- `which` - Locate a command (supports `-a` to show all matches)
- `type` - Describe command type (supports `-a` to show alias/builtin/path matches)
- `basename` - Print path base name (optionally removing a suffix)
- `dirname` - Print path directory name

#### Text Editing
- `nano <file>` - Edit files with built-in text editor

#### System Control
- `reboot` - Restart system
- `shutdown` - Power off
- `exit` - Exit shell

#### Package Manager
- `pkg install <package>` - Install a package
- `pkg remove <package>` - Remove a package
- `pkg list` - List installed packages
- `pkg list -a` - List all available packages
- `pkg search <query>` - Search for packages
- `pkg info <package>` - Show package information
- `pkg update` - Update package database
- `pkg depends <package>` - Show package dependencies

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
PureOS now automatically saves your filesystem state, command history, environment variables, and shell aliases to `~/.pureos/state.json`. On startup, you'll be prompted to restore your previous session.

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

## What's New in v1.4

### Job Control
Unix-style job control for managing background and foreground processes:

```bash
# Run command in background
sleep 10 &

# List all jobs
jobs

# Job listing output:
[1]+  Running      sleep 10 &
[2]-  Stopped      nano myfile.txt

# Bring job to foreground
fg %1

# Resume stopped job in background
bg %2

# Wait for all background jobs
wait

# Wait for specific job
wait %1
```

### Job Control Commands
- **`command &`**: Execute command in background
- **`jobs`**: List all active jobs with their status
- **`jobs -l`**: List jobs with process IDs
- **`fg [%job]`**: Bring job to foreground (default: current job)
- **`bg [%job]`**: Resume stopped job in background
- **`wait [%job]`**: Wait for background job(s) to complete
- **`sleep N`**: Pause for N seconds (useful for testing)

### Job Specifications
Jobs can be referenced by:
- **`%n`**: Job number n
- **`%%`** or **`%+`**: Current job
- **`%-`**: Previous job

### Background Job Notifications
When a background job completes, you'll see:
```
[1]+  Done                    sleep 10
```

## Future Enhancements

## v1.8 Changelog

### New Commands (13)
| Command | Description |
|---------|-------------|
| `sed` | Stream editor — `s/pat/repl/flags`, `d` delete, `p` print, `y` transliterate, address ranges |
| `awk` | Pattern scanning — field splitting, `BEGIN`/`END`, pattern matching, `print`/`printf` |
| `tr` | Translate/delete characters, character ranges, squeeze repeats (`-s`) |
| `xargs` | Build and execute commands from stdin, `-n` max-args batching |
| `seq` | Print number sequences — `seq N`, `seq FIRST LAST`, `seq FIRST STEP LAST` |
| `bc` | Arbitrary-precision calculator — stdin or inline expressions, math functions |
| `expr` | Evaluate arithmetic, string length/index/substr, regex match |
| `printf` | C-style formatted output with `%s`, `%d`, `%f` specifiers |
| `cal` | Display a calendar — current month, specific month/year, full year (`-y`) |
| `mktemp` | Create unique temp file or directory (`-d`) |
| `readlink` | Print symlink target or canonical path (`-f`) |
| `realpath` | Resolve and print absolute file path |
| `fetch` | HTTP/HTTPS client using `urllib` — `-o outfile`, `-H headers`, `-X method` |
| `watch` | Run a command repeatedly every N seconds (`-n`, `-c count`) |
| `strings` | Extract printable strings from binary files |
| `yes` | Repeatedly output a string |

### Shell Engine Upgrades
- **Arithmetic expansion** `$(( expr ))` — full arithmetic with `+`, `-`, `*`, `/`, `**`, `%`
- **Command substitution** `$( cmd )` — capture command output into arguments
- **Parameter expansion** — `${var:-default}`, `${var:=default}`, `${var:?error}`, `${var:+alt}`, `${#var}`
- **Here-doc** `cmd <<EOF … EOF` — redirect multi-line inline text as stdin
- **Quote-aware output redirect** — `>` and `>>` parsing no longer strips single-quoted awk/sed programs
- **`#` not treated as comment** in command arguments (fixes `${#var}` and awk/sed programs)

### Scripting Engine Upgrades
- **`case..esac`** — fully implemented with multi-line block collection, `|` pattern alternation, `*` wildcard, fnmatch patterns
- **Multi-line block collection** — `if`/`fi`, `while`/`done`, `for`/`done`, `case`/`esac` now correctly span multiple lines in scripts

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
- [x] Job control - Background processes (`&`, `fg`, `bg`, `jobs`) ✓ **v1.4**
- [x] Package manager - Install/remove software packages ✓ **v1.5**
- [x] Network stack simulation - Virtual networking ✓ **v1.6**
- [x] Pipe support (`cmd1 | cmd2 | cmd3`) ✓ **v1.7**
- [x] Stdin redirection (`cmd < file`) ✓ **v1.7**
- [x] `ln` - Symbolic and hard links ✓ **v1.7**
- [x] `diff` - File comparison (unified and normal output) ✓ **v1.7**
- [x] `tee` - Read stdin, write to stdout and files ✓ **v1.7**
- [x] `tar` - Virtual archive creation and extraction ✓ **v1.7**
- [x] `cron` - Job scheduler (add/remove/pause/resume) ✓ **v1.7**
- [x] `top` - Process monitor snapshot ✓ **v1.7**
- [x] System files (`/etc/motd`, `/etc/hostname`, `/proc/version`) ✓ **v1.7**

### Planned Features
- [ ] Graphical interface (using curses)
- [ ] `awk` / `sed` stream editors

## What's New in v1.5

### Package Manager
PureOS now includes a full-featured package manager for installing and managing software packages:

```bash
# Install a package
pkg install vim
pkg install git

# Remove a package
pkg remove vim

# List installed packages
pkg list

# List all available packages
pkg list -a

# Search for packages
pkg search editor
pkg search network

# Get package information
pkg info git
pkg depends git
```

### Available Packages
PureOS includes 25 pre-built packages across categories:
- **Editors**: vim, nano
- **Network**: curl, wget, openssh, nginx, wireshark
- **Development**: git, gcc, make
- **Languages**: python3, node
- **Shells**: bash, zsh
- **Terminal**: tmux, screen
- **System**: htop, tree, jq
- **Archive**: zip, unzip, tar, gzip
- **Database**: sqlite, redis

### Dependency Management
The package manager automatically handles dependencies:
```bash
# Installing git will also install its dependency (curl)
pkg install git
```

### Package Categories
Packages are organized by category: editors, network, devel, lang, shells, terminal, system, utils, archive, database

## About

PureOS demonstrates how operating system concepts can be implemented using only Python's standard library. It's perfect for:
- Learning OS concepts
- Teaching systems programming
- Prototyping OS features
- Understanding process management

## What's New in v1.6

### Network Stack Simulation
PureOS now includes a full virtual network stack with realistic simulation:

```bash
# Show network interfaces
ifconfig
ifconfig eth0 up
ifconfig eth0 192.168.1.50

# Ping hosts
ping 8.8.8.8
ping -c 4 google.com

# Show network connections
netstat
netstat -an

# Modern ip utility
ip addr show
ip route show

# Hostname
hostname
hostname myserver

# Trace route
traceroute google.com

# DNS lookup
dig google.com
nslookup google.com
```

### Network Interfaces
- **lo** (loopback): 127.0.0.1/8
- **eth0** (ethernet): 192.168.1.100/24 (configurable)

### Simulated Network
- Ping works to local addresses, 8.8.8.8, 1.1.1.1, etc.
- DNS resolution for popular domains (google.com, cloudflare.com, etc.)
- Realistic RTT times for different hosts
- Full routing table simulation
- Traceroute shows path through simulated network

### New Network Packages
- **iperf3**: Network bandwidth measurement
- **netcat**: Network utility for connections
- **tcpdump**: Packet analyzer
- **mtr**: Combined traceroute + ping

## What's New in v1.7

### Pipe Support
Connect commands with Unix-style pipes:

```bash
cat file.txt | grep error | sort | uniq -c
echo "hello world" | wc -w
ls | grep .txt | sort -r
cat /etc/os-release | grep NAME
```

Multi-stage pipes are fully supported. All text-processing commands (`grep`, `sort`, `uniq`, `cut`, `wc`, `head`, `tail`) now read from stdin when no file is given, making them proper pipe-friendly filters.

### Stdin Redirection
Redirect file content to a command's standard input:

```bash
sort < unsorted.txt
grep error < logfile.txt > errors.txt
cat < input.txt > output.txt
wc -l < myfile.txt
```

### New Commands

#### ln — Create links
```bash
ln -s /etc/hostname /tmp/host_link    # symbolic link
ln /tmp/orig.txt /tmp/hard.txt         # hard link
```

#### diff — Compare files
```bash
diff file1.txt file2.txt               # normal diff
diff -u file1.txt file2.txt            # unified diff
diff -u file1.txt file2.txt > patch.diff
```

#### tee — Pipe and save simultaneously
```bash
cat log.txt | tee backup.txt           # write to file AND stdout
echo data | tee -a log.txt             # append mode
echo result | tee out.txt | grep ok   # chain in pipeline
```

#### tar — Virtual archives
```bash
tar -cf archive.tar file1.txt dir/    # create archive
tar -tf archive.tar                   # list contents
tar -xf archive.tar -C /tmp/dest/     # extract to directory
tar -cf backup.tar /home/alice        # archive a directory
```

#### cron — Job scheduler
```bash
# List scheduled jobs
cron list

# Schedule a job (runs every 60 seconds)
cron add backup "tar -cf /tmp/backup.tar /home" 60

# Schedule a one-shot job (5-second interval, 1 run)
cron add ping-check "ping -c 1 8.8.8.8" 5

# Pause and resume
cron pause 1
cron resume 1

# Remove a job
cron remove 1
```

#### top — Process monitor
```bash
top                        # snapshot of all processes
top > /tmp/procs.txt      # save process list
```

### System Files
Standard Unix-like system files are now populated on boot:
- `/etc/hostname` — system hostname
- `/etc/motd` — message of the day (shown on login)
- `/etc/os-release` — OS identification
- `/etc/shells` — list of available shells
- `/proc/version` — kernel version string
- `/proc/net/dev` — network interface stats
- `/var/log/` — log directory
- `/usr/bin/`, `/usr/local/` — standard directories

---

**PureOS** - Pure Python, Pure Power!
