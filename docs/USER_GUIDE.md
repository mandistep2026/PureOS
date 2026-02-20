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

## 3. Advanced Features

### 3.1 System Logging

PureOS includes a full syslog-compatible logging infrastructure with 8 log levels (EMERG, ALERT, CRIT, ERR, WARNING, NOTICE, INFO, DEBUG) and 24 facilities.

#### Viewing Kernel Messages

```bash
dmesg                             # Show all kernel ring buffer messages
dmesg -n 20                       # Show last 20 messages
dmesg -l WARNING                  # Filter by log level (WARNING and above)
dmesg -l ERR                      # Show only errors
dmesg -c                          # Show messages then clear the buffer
```

#### Adding Log Entries

```bash
logger "Backup completed"         # Log a message (default: INFO, USER facility)
logger -p warning "Disk nearing capacity"   # Log with WARNING priority
logger -p err "Service failed to start"     # Log as error
```

#### Querying the System Journal

```bash
journalctl                        # Show all journal entries
journalctl -n 50                  # Show last 50 entries
journalctl -p err                 # Show only errors and above
journalctl -u syslog.service      # Filter by service unit
journalctl -f                     # Follow (stream) new log entries
```

### 3.2 Service Management

PureOS includes a systemd-style init system with service lifecycle management.

#### systemctl Commands

```bash
systemctl status                  # Show status of all services
systemctl status syslog.service   # Status of a specific service
systemctl start network.service   # Start a service
systemctl stop network.service    # Stop a service
systemctl restart cron.service    # Restart a service
systemctl enable syslog.service   # Enable service to start automatically
systemctl disable cron.service    # Disable automatic start
```

**Default services:**

| Service           | Description                     |
|-------------------|---------------------------------|
| `syslog.service`  | System logging daemon           |
| `network.service` | Virtual network stack           |
| `cron.service`    | Job scheduler                   |

**Service states:** `inactive`, `activating`, `active`, `deactivating`, `failed`, `reloading`

Example output:

```
● syslog.service - System Logging Service
   Loaded: enabled
   Active: active (running)
```

### 3.3 Resource Management

#### User Limits (ulimit)

```bash
ulimit                            # Show all current resource limits
ulimit -n                         # Show max number of open files
ulimit -u                         # Show max number of user processes
ulimit -s                         # Show stack size limit
ulimit -n 2048                    # Set max open files to 2048
ulimit -v 524288                  # Set virtual memory limit (KB)
```

Resource types include: CPU time, file size, data size, stack size, open files (`NOFILE`), processes (`NPROC`), locked memory, and address space.

#### Control Groups (cgctl)

Control groups allow you to organize processes into hierarchies with resource limits.

```bash
cgctl list                        # List all cgroups
cgctl show /system                # Show details of a cgroup
cgctl create /user/alice          # Create a new cgroup
cgctl delete /user/alice          # Remove a cgroup
cgctl move 42 /system             # Move PID 42 into the /system cgroup
```

**Default cgroups:**

| Cgroup    | CPU Shares | Memory Limit | Purpose             |
|-----------|------------|--------------|---------------------|
| `/`       | —          | —            | Root cgroup         |
| `/system` | 2048       | 50 MB        | System services     |
| `/user`   | 1024       | —            | User sessions       |

### 3.4 IPC Facilities

Inter-process communication tools for inspecting shared resources.

```bash
ipcs                              # Show all IPC facilities
```

Output includes:
- **Pipes** — unidirectional byte streams (64 KB buffers)
- **Message Queues** — POSIX-style priority queues
- **Shared Memory** — process-shared memory segments
- **Semaphores** — counting semaphores for synchronization

### 3.5 Package Management

```bash
pkg install vim                   # Install a package
pkg remove vim                    # Remove a package
pkg list                          # List installed packages
pkg list -a                       # List all available packages
pkg search editor                 # Search packages by keyword
pkg info git                      # Show package information
pkg depends git                   # Show package dependencies
pkg update                        # Refresh package database
```

Example:

```
alice@pureos:~$ pkg search network
Available packages matching 'network':
  iperf3       Network bandwidth measurement tool
  netcat       Network utility for connections
  tcpdump      Packet analyzer
  mtr          Combined traceroute and ping
```

### 3.6 Cron Jobs (Scheduled Tasks)

PureOS includes a cron scheduler that runs commands on a timer (interval-based).

```bash
cron list                         # List all scheduled jobs
cron add backup 3600 tar -cf /tmp/backup.tar /home
                                  # Schedule "backup" to run every 3600 seconds
cron add monitor 60 ps            # Run `ps` every 60 seconds
cron pause 1                      # Pause job with ID 1
cron resume 1                     # Resume job with ID 1
cron remove 1                     # Remove job with ID 1
```

The `cron add` syntax is: `cron add <name> <interval_seconds> <command>`

Example output of `cron list`:

```
ID   Name                 Interval   Runs   Last Run   State
--------------------------------------------------------------------
1    backup               1h         3      10:30:00   active
2    monitor              60s        45     10:31:00   active
```

### 3.7 Networking

PureOS simulates a virtual network stack with two interfaces:

| Interface | Address        | Type      |
|-----------|----------------|-----------|
| `lo`      | 127.0.0.1/8    | Loopback  |
| `eth0`    | 192.168.1.100/24 | Ethernet |

```bash
ifconfig                          # Show network interface configuration
ifconfig eth0                     # Show specific interface
ping 8.8.8.8                      # Ping a host (simulated, works with well-known IPs)
ping google.com                   # Ping by hostname (DNS resolution simulated)
netstat                           # Show network connections and statistics
route                             # Show routing table
arp                               # Show ARP cache
ip addr                           # Modern interface info (like ifconfig)
hostname                          # Show or set the system hostname
traceroute 8.8.8.8                # Trace route to host
dig google.com                    # DNS lookup
nslookup cloudflare.com           # DNS name resolution
resolvectl                         # Show DNS resolver status
```

#### Fetching URLs

```bash
fetch https://example.com                    # Download and print a URL
fetch -o page.html https://example.com       # Save to a file
fetch -H 'Accept: application/json' https://api.example.com
fetch -X POST https://api.example.com/data   # HTTP POST request
```

### 3.8 System Monitoring (v2.1 Features)

#### Memory Statistics

```bash
free -h                           # Human-readable memory breakdown
free -m                           # In megabytes
free -h -t                        # Include totals row
free -h -s 5                      # Refresh every 5 seconds
```

#### I/O Statistics

```bash
iostat                            # CPU and I/O statistics
iostat -x                         # Extended statistics per device
iostat -d                         # Device I/O only
iostat -x 2 5                     # Extended stats, every 2s, 5 times
```

#### CPU Statistics

```bash
mpstat                            # Per-CPU statistics
mpstat -P ALL                     # Stats for all CPUs
mpstat -A 1                       # All stats, refresh every second
```

#### System Diagnostics

```bash
sysdiag                           # Run comprehensive system checks
sysdiag -v                        # Verbose output
sysdiag -q                        # Quiet mode (exit code only)
sysdiag --category SYSTEM         # Filter by category
sysdiag --fix                     # Attempt automatic fixes
```

Checks performed: memory pressure, process count, zombie processes, filesystem health, service status, swap usage, and I/O load. Returns exit code `1` if any CRITICAL issue is found.

```bash
sysdiag && echo "All systems OK" || echo "Issues detected"
```

#### System Health Dashboard

```bash
syshealth                         # Full health dashboard
syshealth --brief                 # One-line summary
syshealth --watch                 # Live updating dashboard
syshealth --json                  # JSON output for scripting
syshealth --cpu --mem             # Show only CPU and memory sections
```

#### Performance Profiling

```bash
perf stat                         # Collect syscall statistics
perf stat -e read                 # Filter by event type
perf top                          # Live syscall monitoring
perf record                       # Record performance data
perf report                       # Display aggregated performance report
```

#### Interactive Process Viewer (htop)

```bash
htop                              # Full-screen interactive process viewer
htop -d 20                        # Update every 2 seconds (tenths of seconds)
htop -u alice                     # Filter to show only alice's processes
htop -s mem                       # Sort by memory usage
htop -p 1,2,3                     # Filter to specific PIDs
```

Interactive keys while in `htop`: `q` or `F10` to quit, `k` to kill selected process, `s` to cycle sort column.

### 3.9 Archive Tools

#### tar

```bash
tar -cf archive.tar file1 file2   # Create an archive
tar -cf backup.tar /home/alice    # Archive a directory
tar -tf archive.tar               # List archive contents
tar -xf archive.tar               # Extract archive (current directory)
tar -xf archive.tar -C /tmp       # Extract to /tmp
tar -cvf archive.tar dir/         # Verbose creation
```

#### zip / unzip

```bash
zip archive.zip file1.txt file2.txt   # Create a zip archive
unzip archive.zip                     # Extract to current directory
unzip -d /tmp/extracted archive.zip   # Extract to specific directory
```

### 3.10 Advanced File Utilities

```bash
diff file1.txt file2.txt          # Compare two files
diff -u file1.txt file2.txt       # Unified diff format

dd if=source.img of=dest.img bs=512   # Block-level copy
dd if=source of=dest count=100        # Copy first 100 blocks

nl file.txt                       # Number lines (non-empty by default)
nl -b a file.txt                  # Number all lines including empty

od file.bin                       # Octal dump
od -x file.bin                    # Hex dump
od -c file.bin                    # Character dump

xxd file.bin                      # Hex dump with ASCII sidebar
xxd -r hexdump.txt binary.bin     # Reverse: hex dump back to binary

column -t data.txt                # Align data into table columns
column -s: -t /etc/passwd         # Use : as separator

strings binary.bin                # Extract printable strings from binary
strace ls                         # Trace system calls (simulated)
mount                             # List mounted filesystems
mount /dev/sdb /mnt               # Mount a virtual device
umount /mnt                       # Unmount
```

### 3.11 Miscellaneous Utilities

```bash
bc                                # Calculator (supports +, -, *, /, sqrt, etc.)
echo "2 + 2" | bc                 # Pipe expression to calculator
bc <<< "sqrt(144)"                # Inline calculation

seq 10                            # Print 1 through 10
seq 5 10                          # Print 5 through 10
seq 0 2 20                        # Print 0, 2, 4, ... 20 (step 2)

cal                               # Display current month calendar
cal 3 2025                        # Calendar for March 2025
cal -y                            # Full year calendar

date                              # Show current date and time
sleep 5                           # Pause for 5 seconds
watch -n 2 date                   # Run `date` every 2 seconds
watch -n 1 -c 10 ps               # Run `ps` every second, 10 times

expr 5 + 3                        # Evaluate arithmetic expression
expr length "hello"               # String length
printf "%-10s %5d\n" alice 42     # Formatted output

tee output.txt                    # Write stdin to both stdout and a file
tee -a output.txt                 # Append mode

rev                               # Reverse characters in each line
echo "hello" | rev                # Outputs: olleh

basename /home/alice/notes.txt    # Outputs: notes.txt
dirname /home/alice/notes.txt     # Outputs: /home/alice
realpath ./notes.txt              # Resolve to absolute path

mktemp                            # Create a unique temp file in /tmp
mktemp -d                         # Create a unique temp directory
mktemp /tmp/myapp.XXXXXX          # Custom template (X's replaced)

lsof                              # List open files
lsof -u alice                     # Open files for user alice

vmstat                            # Virtual memory statistics
```

---

## 4. Shell Scripting

PureOS includes a full shell scripting engine. Scripts use standard Bourne-shell syntax and are executed with the `bash` command.

### 4.1 Running Scripts

```bash
bash myscript.sh                  # Execute a script file
bash myscript.sh arg1 arg2        # Pass arguments to a script
source myscript.sh                # Run script in the current shell context
. myscript.sh                     # Shorthand for source
```

Script files should be stored in the virtual filesystem. Start every script with a comment header:

```bash
#!/bin/sh
# My first PureOS script
echo "Hello from PureOS!"
```

Create and run a script:

```bash
nano hello.sh                     # Open editor to create the file
bash hello.sh                     # Run it
```

### 4.2 Variables

```bash
# Assign a variable (no spaces around =)
name="alice"
count=42
greeting="Hello, World"

# Use a variable with $
echo $name
echo "Welcome, $name!"
echo "Count is: $count"

# Brace syntax (recommended for clarity and adjacent text)
echo "${name}'s home directory"
prefix="file"
echo "${prefix}_001.txt"

# Export to make available to child processes
export PATH="/usr/local/bin:$PATH"
export MY_VAR="value"

# Unset a variable
unset count
```

#### Special Variables

| Variable | Meaning                                  |
|----------|------------------------------------------|
| `$?`     | Exit code of the last command            |
| `$$`     | PID of the current shell process         |
| `$0`     | Name of the script                       |
| `$1`–`$9`| Positional arguments passed to script    |
| `$#`     | Number of arguments                      |
| `$@`     | All arguments as separate words          |
| `$HOME`  | Current user's home directory            |
| `$USER`  | Current username                         |
| `$PATH`  | Command search path                      |

#### Parameter Expansion

```bash
echo ${name:-"default"}           # Use "default" if name is unset or empty
echo ${name:="fallback"}          # Assign "fallback" if name is unset
echo ${name:?"Error: name required"}  # Error if name is unset
echo ${name:+"set"}               # Output "set" only if name is defined
echo ${#name}                     # Length of $name
```

#### Arithmetic Expansion

```bash
result=$((5 + 3))
echo $result                      # 8

x=10
y=3
echo $((x * y))                   # 30
echo $((x / y))                   # 3  (integer division)
echo $((x % y))                   # 1  (remainder)
echo $((x ** 2))                  # 100 (exponentiation)
echo $((x + y * 2))               # 16  (standard precedence)
```

#### Command Substitution

Capture the output of a command into a variable:

```bash
today=$(date)
echo "Today is: $today"

num_files=$(ls | wc -l)
echo "There are $num_files files here"

current_dir=$(pwd)
echo "Working in: $current_dir"
```

### 4.3 Input and Output Redirection

```bash
echo "Hello" > file.txt           # Write stdout to file (overwrite)
echo "World" >> file.txt          # Append stdout to file
sort < unsorted.txt               # Read stdin from file
sort < unsorted.txt > sorted.txt  # Redirect both stdin and stdout
grep error app.log 2> errors.txt  # Redirect stderr to file
grep error app.log 2>> errors.txt # Append stderr to file
grep error app.log &> all.txt     # Redirect both stdout and stderr
grep error app.log 2>&1           # Merge stderr into stdout

# Here-document: feed multi-line text as stdin
cat << EOF
Line one
Line two
Line three
EOF

# Tee: write to both stdout and a file simultaneously
ps | tee process_list.txt
```

### 4.4 Conditionals

#### if / elif / else

```bash
#!/bin/sh

# Basic if
if [ "$name" = "root" ]; then
    echo "Welcome, administrator!"
fi

# if/else
if [ $count -gt 10 ]; then
    echo "Count is large"
else
    echo "Count is small"
fi

# if/elif/else
score=75
if [ $score -ge 90 ]; then
    echo "Grade: A"
elif [ $score -ge 80 ]; then
    echo "Grade: B"
elif [ $score -ge 70 ]; then
    echo "Grade: C"
else
    echo "Grade: F"
fi
```

#### Test Expressions

**File tests:**

| Expression      | True if...                        |
|-----------------|-----------------------------------|
| `[ -f file ]`   | file exists and is a regular file |
| `[ -d dir ]`    | dir exists and is a directory     |
| `[ -e path ]`   | path exists (any type)            |
| `[ -s file ]`   | file exists and is non-empty      |

**String comparisons:**

| Expression          | True if...              |
|---------------------|-------------------------|
| `[ "$a" = "$b" ]`   | strings are equal       |
| `[ "$a" != "$b" ]`  | strings are not equal   |
| `[ -z "$a" ]`       | string is empty         |
| `[ -n "$a" ]`       | string is non-empty     |

**Numeric comparisons:**

| Expression       | True if...              |
|------------------|-------------------------|
| `[ $a -eq $b ]`  | a equals b              |
| `[ $a -ne $b ]`  | a not equal to b        |
| `[ $a -lt $b ]`  | a less than b           |
| `[ $a -le $b ]`  | a less than or equal b  |
| `[ $a -gt $b ]`  | a greater than b        |
| `[ $a -ge $b ]`  | a greater than or equal |

#### Boolean Chains

```bash
# && runs the second command only if the first succeeds
mkdir /tmp/mydir && echo "Directory created"

# || runs the second command only if the first fails
rm oldfile.txt || echo "File not found"

# Combine checks
[ -f config.txt ] && [ -s config.txt ] && echo "Config file ready"
```

#### case / esac

Use `case` for matching a value against multiple patterns:

```bash
#!/bin/sh

day="Monday"

case $day in
    Monday|Tuesday|Wednesday|Thursday|Friday)
        echo "$day is a weekday"
        ;;
    Saturday|Sunday)
        echo "$day is the weekend"
        ;;
    *)
        echo "Unknown day: $day"
        ;;
esac
```

```bash
#!/bin/sh

# Matching command-line arguments
command=$1

case $command in
    start)
        echo "Starting service..."
        ;;
    stop)
        echo "Stopping service..."
        ;;
    restart)
        echo "Restarting service..."
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        ;;
esac
```

### 4.5 Loops

#### for Loop

```bash
# Iterate over a list of words
for fruit in apple banana cherry; do
    echo "Fruit: $fruit"
done

# Iterate over files
for file in *.txt; do
    echo "Processing: $file"
    wc -l $file
done

# Iterate over a numeric range using seq
for i in $(seq 1 5); do
    echo "Step $i"
done

# C-style arithmetic loop
for i in $(seq 0 2 10); do
    echo "Even number: $i"
done
```

#### while Loop

```bash
# Count down
count=5
while [ $count -gt 0 ]; do
    echo "Countdown: $count"
    count=$((count - 1))
done
echo "Liftoff!"

# Read lines from a file
while read line; do
    echo "Line: $line"
done < myfile.txt

# Process with a counter
i=1
while [ $i -le 10 ]; do
    echo "Iteration $i"
    i=$((i + 1))
done
```

### 4.6 Functions

```bash
#!/bin/sh

# Define a function
greet() {
    name=$1
    echo "Hello, $name!"
}

# Call the function
greet "alice"
greet "bob"

# Function with return value (via exit code)
is_even() {
    number=$1
    if [ $((number % 2)) -eq 0 ]; then
        return 0   # 0 = true/success
    else
        return 1   # non-zero = false/failure
    fi
}

if is_even 4; then
    echo "4 is even"
fi

# Function capturing output
get_username() {
    echo "$(whoami)"
}

user=$(get_username)
echo "Current user: $user"
```

### 4.7 A Complete Script Example

Here is a practical script that backs up a directory and logs results:

```bash
#!/bin/sh
# backup.sh — Back up a directory with timestamp

TARGET_DIR=$1
BACKUP_DIR="/tmp/backups"
LOG_FILE="/tmp/backup.log"

# Validate argument
if [ -z "$TARGET_DIR" ]; then
    echo "Usage: bash backup.sh <directory>"
    exit 1
fi

# Check directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: '$TARGET_DIR' is not a directory"
    exit 1
fi

# Create backup directory if needed
mkdir -p $BACKUP_DIR

# Generate archive name
timestamp=$(date)
archive="$BACKUP_DIR/backup_$timestamp.tar"

# Create the archive
tar -cf $archive $TARGET_DIR
exit_code=$?

if [ $exit_code -eq 0 ]; then
    msg="Backup of $TARGET_DIR completed: $archive"
    echo $msg
    logger "$msg"
else
    msg="Backup of $TARGET_DIR FAILED"
    echo $msg
    logger -p err "$msg"
    exit 1
fi
```

Run it with:

```bash
bash backup.sh /home/alice
```

### 4.8 Command History

```bash
history                           # Show all commands in history
history 20                        # Show last 20 commands
!!                                # Repeat the last command
!5                                # Repeat command number 5 from history
```

### 4.9 Aliases

```bash
alias                             # List all current aliases
alias ll='ls -la'                 # Define an alias
alias cls='clear'
alias grep='grep -n'              # Always show line numbers

# Built-in aliases available by default:
ll                                # Expands to: ls -la
la                                # Expands to: ls -a
l                                 # Expands to: ls -CF

unalias ll                        # Remove a specific alias
unalias -a                        # Remove all aliases
```

### 4.10 Tab Completion and Line Editing

**Tab completion:**

| Context                 | What completes              |
|-------------------------|-----------------------------|
| `ec<TAB>`               | `echo`                      |
| `/ho<TAB>`              | `/home/`                    |
| `su ro<TAB>`            | `su root`                   |
| `echo $HO<TAB>`         | `echo $HOME`                |
| Double-`<TAB>`          | Show all matching options   |

**Line editing shortcuts:**

| Key         | Action                               |
|-------------|--------------------------------------|
| `Ctrl+A`    | Move cursor to beginning of line     |
| `Ctrl+E`    | Move cursor to end of line           |
| `Ctrl+K`    | Cut from cursor to end of line       |
| `Ctrl+U`    | Cut from cursor to start of line     |
| `Ctrl+W`    | Delete previous word                 |
| `Ctrl+Y`    | Paste (yank) cut text                |
| `Ctrl+R`    | Search command history               |
| `Ctrl+L`    | Clear the screen                     |
| `↑` / `↓`  | Navigate command history             |

**Multi-line input:** End a line with `\` to continue on the next line:

```bash
echo "This is a very long \
command that spans \
multiple lines"
```

### 4.11 Prompt Customization

The prompt is controlled by the `PS1` environment variable. Escape sequences:

| Sequence | Meaning                        |
|----------|--------------------------------|
| `\u`     | Current username               |
| `\h`     | Hostname                       |
| `\w`     | Full current working directory |
| `\W`     | Basename of current directory  |
| `\$`     | `$` for users, `#` for root    |
| `\t`     | Current time (24h HH:MM:SS)    |
| `\d`     | Current date (Day Mon DD)      |

```bash
# Set a custom prompt
export PS1="\u@\h [\t] \w\$ "

# Minimal prompt
export PS1="\$ "

# Show only current directory name
export PS1="[\W]\$ "
```

---

## 5. Text Editor

PureOS includes a built-in nano-like text editor invoked with `nano`.

### 5.1 Opening the Editor

```bash
nano                              # Open editor with no file (unsaved buffer)
nano notes.txt                    # Open or create notes.txt
nano /etc/motd                    # Edit a system file (requires root)
```

When you open the editor, you see:

```
┌──────────────────────────── PureOS Editor 1.0 - notes.txt ────────────────────────────┐
│                                                                                         │
│   1  First line of text                                                                 │
│>  2  Second line (cursor here, highlighted)                                             │
│   3  Third line                                                                         │
│                                                                                         │
│─────────────────────────────────────────────────────────────────────────────────────────│
│ Ctrl+S: Save | Ctrl+Q: Quit | Ctrl+N: New Line | Ctrl+D: Delete Line | Arrows: Move   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

The `>` marker shows the currently selected line.

### 5.2 Editor Commands

| Key         | Action                                  |
|-------------|-----------------------------------------|
| `Ctrl+S`    | Save the file                           |
| `Ctrl+Q`    | Quit the editor                         |
| `Ctrl+N`    | Insert a new line at cursor position    |
| `Ctrl+D`    | Delete the current line                 |
| `↑`         | Move cursor up one line                 |
| `↓`         | Move cursor down one line               |
| `←`         | Move cursor left                        |
| `→`         | Move cursor right                       |

The status bar at the top shows `[Modified]` when there are unsaved changes.

### 5.3 Typical Editing Workflow

```bash
# Create and edit a script
nano myscript.sh

# Edit the file in the editor using the controls above,
# then save with Ctrl+S, quit with Ctrl+Q.

# Verify your changes
cat myscript.sh

# Run the script
bash myscript.sh
```

### 5.4 Creating Configuration Files

The editor is useful for creating configuration and data files:

```bash
# Create an /etc/motd (message of the day)
nano /etc/motd

# Create a crontab-style schedule description
nano /home/alice/tasks.txt

# Write a shell script
nano /home/alice/cleanup.sh
```

---

## 6. Troubleshooting

### 6.1 Common Issues

#### "command not found"

```
alice@pureos:~$ myscript
myscript: command not found
```

**Solutions:**
- Use `bash myscript.sh` instead of just `myscript`
- Check spelling: `which ls`, `type grep`
- Verify the command exists: `help` lists all available commands

#### "No such file or directory"

```
cat: notes.txt: No such file or directory
```

**Solutions:**
- Check your current directory: `pwd`
- List files to confirm: `ls -la`
- Use the full path: `cat /home/alice/notes.txt`
- Check for typos in the filename

#### "Permission denied"

```
rm: cannot remove '/etc/passwd': Permission denied
```

**Solutions:**
- Switch to root: `su` (password is empty by default)
- Check file permissions: `ls -l /etc/passwd`
- Check your own permissions: `id`

#### Login fails with "Invalid username or password"

- **root**: password is empty — just press Enter at the password prompt
- **alice**: default password is `password123`
- If you changed a password and forgot it, start PureOS fresh (state not loaded) to reset to defaults

#### Script runs but produces unexpected output

```bash
# Debug a script by adding echo statements
echo "DEBUG: value of x is $x"

# Check exit codes
mycommand
echo "Exit code: $?"

# Trace execution (print each command before running)
bash -x myscript.sh        # Note: -x flag is printed but script still runs normally
```

#### Background job output appears at wrong time

Background job output can appear mixed with your prompt. This is normal behavior. Use `wait` to pause until all jobs complete:

```bash
long_command &
wait
echo "All done"
```

#### Filesystem seems full

```bash
df                            # Check overall disk usage (virtual 100MB limit)
du -sh /home/alice            # Check a directory's size
du -sh /tmp                   # Temporary files can accumulate
rm /tmp/*.tar                 # Clean up temp files
```

#### Saved state causes issues on startup

If a previously saved state is causing problems, choose **not** to load it at startup (answer `n` when prompted). The system will start with a fresh filesystem.

To delete saved state from your real machine:
```bash
# On your real system (not inside PureOS)
rm ~/.pureos/state.json
```

### 6.2 Checking System Status

When something seems wrong, these commands give you a system overview:

```bash
uname -a                          # OS and kernel version
uptime                            # How long the system has been running
free -h                           # Memory usage
df                                # Disk usage
ps                                # Running processes
who                               # Logged-in users
dmesg | tail -20                  # Recent kernel messages
journalctl -n 20                  # Recent journal entries
sysdiag                           # Comprehensive health check
```

### 6.3 Understanding Exit Codes

Every command returns an exit code. `0` means success; anything else means failure.

```bash
ls /tmp
echo $?        # Outputs 0 (success)

ls /nonexistent
echo $?        # Outputs 1 (failure)

grep pattern file_that_exists.txt
# Returns 0 if pattern found, 1 if not found

# Use in scripts
if grep -q "error" logfile.txt; then
    echo "Errors found in log"
fi
```

### 6.4 Getting Help Inside PureOS

```bash
help                              # List all commands with one-line descriptions
help <command>                    # Detailed help for a specific command
type <command>                    # Show if it's a builtin, alias, or file
which <command>                   # Find where a command lives
```

### 6.5 Running Tests

If you suspect something is broken, run the test suite:

```bash
# From your real terminal (not inside PureOS):
python main.py --test
```

A healthy system shows all 527 tests passing.

---

## Appendix: Quick Reference Card

### Essential Daily Commands

```bash
pwd          ls           cd ~         cat
mkdir -p     touch        cp           mv
rm -rf       find         grep -in     sort | uniq
wc -l        head -n 10   tail -n 10   echo
ps           kill         top          jobs
whoami       id           su           passwd
history      !!           help         exit
```

### Redirection Cheatsheet

| Syntax          | Effect                                 |
|-----------------|----------------------------------------|
| `cmd > file`    | Write stdout to file (overwrite)       |
| `cmd >> file`   | Append stdout to file                  |
| `cmd < file`    | Read stdin from file                   |
| `cmd 2> file`   | Write stderr to file                   |
| `cmd 2>&1`      | Merge stderr into stdout               |
| `cmd &> file`   | Write both stdout and stderr to file   |
| `cmd1 | cmd2`   | Pipe stdout of cmd1 to stdin of cmd2   |
| `cmd << EOF`    | Here-document: inline stdin text       |

### Default Users Reference

| User    | Password      | UID | Home         |
|---------|---------------|-----|--------------|
| `root`  | *(empty)*     | 0   | `/root`      |
| `alice` | `password123` | 1000| `/home/alice`|

### Filesystem Hierarchy

| Path         | Purpose                                  |
|--------------|------------------------------------------|
| `/`          | Root of the filesystem                   |
| `/bin`       | Command scripts and binaries             |
| `/etc`       | Configuration files                      |
| `/etc/passwd`| User account database                    |
| `/etc/group` | Group database                           |
| `/home`      | User home directories                    |
| `/proc`      | Kernel and process information           |
| `/root`      | Root user's home directory               |
| `/tmp`       | Temporary files                          |
| `/var/log`   | Log files                                |

---

*PureOS v2.0.0 — Pure Python, Pure Power!*
*Preparing for v2.1 release with enhanced monitoring and diagnostics.*
