# PureOS User Guide

> **Version 2.0.0** | Python 3.7+ | No external dependencies required

Welcome to PureOS — an educational operating system written entirely in Python using only the standard library. This guide will walk you through everything from first boot to advanced shell scripting.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Core Commands Tutorial](#2-core-commands-tutorial)
3. [Advanced Features](#3-advanced-features)
4. [Shell Scripting](#4-shell-scripting)
5. [Text Editor](#5-text-editor)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Getting Started

### 1.1 Requirements

PureOS requires **Python 3.7 or higher** and uses only the Python standard library — no `pip install` needed.

Verify your Python version:

```bash
python3 --version
# Python 3.7.x or higher required
```

### 1.2 Running PureOS

```bash
# Start the interactive shell
python main.py

# Run a batch script and exit
python main.py --batch commands.txt

# Run all tests (527 tests)
python main.py --test

# Show version
python main.py --version

# Show help
python main.py --help
```

### 1.3 Boot Sequence

When you start PureOS you will see the initialization sequence:

```
Initializing PureOS...
  [1/5] Starting kernel...
  [2/5] Mounting filesystem...
  [3/5] Initializing user management...
  [4/5] Loading shell...
  [5/5] Checking for saved state...

PureOS initialized successfully!
```

If a saved session exists from a previous run, you will be prompted to restore it. Type `y` to restore or `n` to start fresh.

### 1.4 Logging In

PureOS includes a multi-user login system. After boot you will see a login prompt:

```
==================================================
PureOS v2.0 - Login
==================================================

Username: alice
Password:
```

**Default accounts:**

| Username | Password     | Home Directory | Notes                  |
|----------|--------------|----------------|------------------------|
| `root`   | *(empty)*    | `/root`        | Superuser — all access |
| `alice`  | `password123`| `/home/alice`  | Default regular user   |

> **Tip:** To log in as `root`, simply press Enter when prompted for the password (root has no password by default). After first login, set a root password with `passwd`.

You can also create additional users — see [User Management](#user-management) below.

### 1.5 The Shell Prompt

After login the shell prompt follows the standard `user@host:directory$` format:

```
alice@pureos:~$          # Regular user in home directory
root@pureos:/etc#        # Root user in /etc
alice@pureos:/home/alice/projects$   # User in a subdirectory
```

The `~` is shorthand for the current user's home directory. Root's prompt ends with `#`; all other users see `$`.

### 1.6 Basic Navigation

```bash
pwd                  # Print current directory
ls                   # List directory contents
ls -l                # Long format with permissions, size, date
ls -a                # Show hidden files (starting with .)
ls -la               # Combine long format and show hidden files
cd /etc              # Change to /etc directory
cd ~                 # Go to your home directory
cd ..                # Go up one level
cd -                 # Return to previous directory
```

### 1.7 Getting Help

```bash
help                 # List all available commands with descriptions
help ls              # Show help for a specific command
type ls              # Show whether a command is a builtin, alias, or file
which grep           # Find where a command is located
```

### 1.8 The Filesystem Layout

PureOS uses a standard Unix-like hierarchy:

```
/
├── bin/         Binaries and scripts
├── etc/         Configuration files (passwd, group, hostname, motd)
├── home/        User home directories
│   └── alice/
├── proc/        Kernel information (version, net/dev)
├── root/        Root user's home directory
├── tmp/         Temporary files (cleared on reboot)
├── usr/         User programs and local installs
│   ├── bin/
│   └── local/
└── var/
    └── log/     System log files
```

### 1.9 Saving and Restoring Sessions

PureOS automatically offers to save your session on shutdown. You can also save and load manually:

```bash
save                 # Save filesystem state, history, and environment
load                 # Restore a previously saved state
```

State is stored in `~/.pureos/state.json` on your real machine.

---

## 2. Core Commands Tutorial

### 2.1 File Management

#### Listing Files

```bash
ls                        # List current directory
ls /etc                   # List a specific directory
ls -l /home               # Long listing: permissions, owner, size, date
ls -la                    # Include hidden files in long format
```

Long format columns: `permissions  links  owner  group  size  date  name`

```
drwxr-xr-x 1 alice alice     0 Jan 15 10:23 projects/
-rw-r--r-- 1 alice alice   512 Jan 15 10:24 notes.txt
```

#### Creating Files and Directories

```bash
touch notes.txt            # Create an empty file (or update timestamp)
mkdir projects             # Create a directory
mkdir -p a/b/c             # Create nested directories (no error if they exist)
```

#### Viewing File Contents

```bash
cat notes.txt              # Print entire file
cat file1.txt file2.txt    # Print multiple files in sequence
head notes.txt             # Show first 10 lines
head -n 5 notes.txt        # Show first 5 lines
tail notes.txt             # Show last 10 lines
tail -n 20 log.txt         # Show last 20 lines
```

#### Copying, Moving, and Renaming

```bash
cp source.txt dest.txt     # Copy a file
cp report.txt backup/      # Copy into a directory
mv old.txt new.txt         # Rename a file
mv file.txt /tmp/          # Move to another directory
```

#### Removing Files and Directories

```bash
rm file.txt                # Remove a file
rm -f file.txt             # Force removal (no error if missing)
rm -r mydir/               # Recursively remove a directory and its contents
rm -rf oldproject/         # Force recursive removal (use with care!)
rmdir emptydir/            # Remove an empty directory
```

#### File Information

```bash
stat notes.txt             # Detailed metadata: size, permissions, timestamps
du -h notes.txt            # Disk usage for a file (human-readable)
du -sh projects/           # Total size of a directory
df                         # Filesystem disk space usage
```

Example `stat` output:

```
  File: /home/alice/notes.txt
  Type: regular
  Size: 512 bytes
Access: (rw-r--r--)
Owner: alice:alice
Modify: 2025-01-15 10:24:00
Create: 2025-01-15 09:00:00
```

#### Searching for Files

```bash
find / -name "*.txt"              # Find all .txt files from root
find /home -type f                # Find only regular files
find /tmp -type d                 # Find only directories
find . -name "report*"            # Find files starting with "report"
find / -maxdepth 2 -name config   # Limit search depth to 2 levels
```

#### Symbolic and Hard Links

```bash
ln -s /etc/hostname myhost        # Create a symbolic link
ln original.txt hardlink.txt      # Create a hard link
readlink myhost                   # Show symlink target
realpath myhost                   # Show resolved absolute path
```

#### Permissions and Ownership

File permissions use the format `rwxrwxrwx` — three triplets for owner, group, and others.

```bash
chmod 755 script.sh               # Octal: rwxr-xr-x
chmod 644 notes.txt               # Octal: rw-r--r--
chmod +x script.sh                # Add execute for all
chmod u+x script.sh               # Add execute for owner only
chmod go-w notes.txt              # Remove write for group and others
chmod a=r readme.txt              # Set read-only for everyone

chown alice notes.txt             # Change owner
chown alice:alice notes.txt       # Change owner and group
```

Permission meaning per triplet:

| Symbol | Meaning for files | Meaning for directories |
|--------|-------------------|------------------------|
| `r`    | Read content      | List contents           |
| `w`    | Write/modify      | Create/delete files     |
| `x`    | Execute           | Enter the directory     |

### 2.2 Text Processing

These commands are designed to work together using pipes (`|`).

#### Searching with grep

```bash
grep "error" logfile.txt          # Find lines containing "error"
grep -i "error" logfile.txt       # Case-insensitive search
grep -n "error" logfile.txt       # Show line numbers
grep -v "debug" logfile.txt       # Show lines NOT containing "debug"

# With pipes
cat /var/log/syslog | grep error
ls -la | grep "\.txt"
```

#### Sorting

```bash
sort names.txt                    # Alphabetical sort
sort -r names.txt                 # Reverse sort
sort -n numbers.txt               # Numeric sort
sort -u names.txt                 # Sort and remove duplicates
sort -ru numbers.txt              # Reverse numeric sort, unique
```

#### Filtering Duplicates with uniq

`uniq` works on **adjacent** lines, so sort first:

```bash
sort names.txt | uniq             # Remove duplicate lines
sort names.txt | uniq -c          # Count occurrences of each line
sort names.txt | uniq -d          # Show only lines that appear more than once
sort names.txt | uniq -u          # Show only lines that appear exactly once
```

#### Extracting Fields with cut

```bash
cut -d: -f1 /etc/passwd           # Extract first field (username) from passwd
cut -d, -f2,3 data.csv            # Extract fields 2 and 3 from CSV
cut -d: -f1-3 /etc/passwd         # Extract fields 1 through 3
echo "a:b:c:d" | cut -d: -f2     # Outputs: b
```

#### Counting with wc

```bash
wc notes.txt                      # Lines, words, bytes
wc -l notes.txt                   # Count lines only
wc -w notes.txt                   # Count words only
wc -c notes.txt                   # Count bytes only
ls | wc -l                        # Count number of files in directory
```

#### Stream Editing with sed

```bash
sed 's/old/new/' file.txt         # Replace first occurrence per line
sed 's/old/new/g' file.txt        # Replace all occurrences (global)
sed 's/error/ERROR/gi' file.txt   # Replace, case-insensitive
sed '/^#/d' config.txt            # Delete comment lines
sed -n '5,10p' file.txt           # Print lines 5 to 10
sed '3i\New line here' file.txt   # Insert text before line 3
```

#### Pattern Processing with awk

```bash
awk '{print $1}' file.txt         # Print first field of each line
awk '{print $NF}' file.txt        # Print last field
awk -F: '{print $1}' /etc/passwd  # Use : as delimiter, print usernames
awk '{print $1, $3}' file.txt     # Print fields 1 and 3
awk 'NR > 5' file.txt             # Print lines after line 5
awk '/error/ {print}' log.txt     # Print lines matching a pattern
awk '{sum += $1} END {print sum}' numbers.txt   # Sum a column
```

#### Translating Characters with tr

```bash
echo "hello" | tr 'a-z' 'A-Z'    # Convert to uppercase
echo "hello world" | tr -d 'l'   # Delete character 'l'
echo "aabbcc" | tr -s 'a-z'      # Squeeze repeated characters
cat file.txt | tr '\n' ' '        # Replace newlines with spaces
```

#### Pipes and Pipeline Examples

Real-world pipeline combinations:

```bash
# Count unique IPs in a log file
cat access.log | cut -d' ' -f1 | sort | uniq -c | sort -rn

# Find the 5 largest files
find / -type f | xargs wc -c | sort -n | tail -5

# Search for errors, show unique messages
grep -i error app.log | sort | uniq -c | sort -rn

# Extract usernames from passwd sorted alphabetically
cat /etc/passwd | cut -d: -f1 | sort
```

### 2.3 Process Management

#### Viewing Processes

```bash
ps                                # List all running processes
top                               # Snapshot of processes with CPU/memory stats
htop                              # Interactive real-time process viewer
pstree                            # Display processes as a tree
pstree -p                         # Include PIDs in the tree
```

Example `ps` output:

```
PID      NAME            STATE        CPU TIME     MEMORY
1        init            running      0.00s        1024KB
2        kernel_worker   ready        0.00s        512KB
```

#### Background Jobs

```bash
sleep 60 &                        # Run command in background
jobs                              # List background jobs
jobs -l                           # List with PIDs
fg                                # Bring most recent job to foreground
fg %1                             # Bring job #1 to foreground
bg %1                             # Resume stopped job in background
wait                              # Wait for all background jobs to finish
wait %1                           # Wait for specific job
```

When a background job starts, you see:

```
[1] 12345
```

When it completes:

```
[1]+  Done                    sleep 60
```

#### Killing Processes

```bash
kill 42                           # Terminate process with PID 42
```

#### nohup — Immune to Hangup

```bash
nohup long-running-command &      # Run immune to hangup signals
                                  # Output appended to ~/nohup.out
cat ~/nohup.out                   # View captured output
```

#### Monitoring System Resources

```bash
free                              # Memory usage summary
free -h                           # Human-readable (KB, MB, GB)
df                                # Disk space (virtual 100MB filesystem)
uptime                            # How long the system has been running
vmstat                            # Virtual memory statistics
```

### 2.4 User Management

#### Checking Your Identity

```bash
whoami                            # Print current username
id                                # Print UID, GID, and group memberships
id alice                          # Show identity for another user
groups                            # List your group memberships
groups alice                      # List groups for a specific user
who                               # Show all logged-in users and session times
```

#### Switching Users

```bash
su alice                          # Switch to user alice (prompts for password)
su                                # Switch to root (prompts for root password)
su root                           # Equivalent to `su` with no argument
logout                            # Log out current user
```

#### Managing Users (requires root)

```bash
useradd bob                       # Create user bob (no home directory)
useradd -m charlie                # Create user charlie with home directory
useradd -m -s /bin/sh diana       # Create with specific shell
passwd bob                        # Set or change bob's password
passwd                            # Change your own password
userdel bob                       # Delete user bob
userdel -r charlie                # Delete user and remove home directory
```

Example session — creating a new user:

```
root@pureos:~# useradd -m bob
User 'bob' created successfully
Set password with: passwd bob

root@pureos:~# passwd bob
Enter new password for bob:
Retype new password:
passwd: password updated successfully

root@pureos:~# su bob
Password:
Switched to user 'bob'
bob@pureos:/root$
```

---
