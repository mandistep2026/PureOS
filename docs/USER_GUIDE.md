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
