# PureOS API Reference

This document is the comprehensive public API reference for PureOS. APIs are organized by module. All classes and functions listed here are part of the public interface.

---

## Table of Contents

1. [Core Module APIs](#core-module-apis)
   - [core.kernel — Kernel](#corekernelkernel)
   - [core.filesystem — FileSystem](#corefilesystemfilesystem)
   - [core.auth — Authenticator](#coreauthenticator)
   - [core.user — UserManager](#coreusermanager)
   - [core.logging — SystemLogger](#coreloggingsystemlogger)
   - [core.ipc — IPCManager](#coreipc-ipcmanager)
   - [core.init — InitSystem](#coreinit-initsystem)
   - [core.limits — ResourceManager](#corelimits-resourcemanager)
   - [core.network — NetworkManager](#corenetwork-networkmanager)
   - [core.package — PackageManager](#corepackage-packagemanager)
   - [core.cron — CronScheduler](#corecron-cronscheduler)
   - [core.persistence — PersistenceManager](#corepersistence-persistencemanager)
2. [Shell Module APIs](#shell-module-apis)
   - [shell.shell — Shell](#shellshell-shell)
   - [shell.shell — ShellCommand (Base Class)](#shellshell-shellcommand)
   - [Command Reference](#command-reference)
3. [Data Classes & Enums](#data-classes--enums)

---

## Core Module APIs

### core.kernel — Kernel

```python
class core.kernel.Kernel
```

The main kernel class that coordinates all OS subsystems. Manages processes, memory, scheduling, signals, and I/O statistics. Instantiated once at startup; subsystems (logger, ipc_manager, init_system, resource_manager) are attached during `__init__`.

**Properties**

| Property | Type | Description |
|---|---|---|
| `logger` | `SystemLogger \| None` | System-wide logger (core.logging). |
| `ipc_manager` | `IPCManager \| None` | IPC facility manager (core.ipc). |
| `init_system` | `InitSystem \| None` | Service/daemon manager (core.init). |
| `resource_manager` | `ResourceManager \| None` | Resource limits and cgroups (core.limits). |
| `memory_manager` | `MemoryManager` | Virtual memory allocator. |
| `scheduler` | `Scheduler` | Round-robin process scheduler. |
| `processes` | `Dict[int, Process]` | Active process table (PID → Process). |

**Methods**

---

#### `Kernel.start() -> None`

Start the kernel scheduler background thread.

```python
kernel = Kernel()
kernel.start()
```

---

#### `Kernel.stop() -> None`

Stop the kernel scheduler. Joins the kernel thread with a 2-second timeout.

---

#### `Kernel.create_process(name, code, priority=5, memory=1048576, *args, **kwargs) -> int`

Create and schedule a new process.

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable process name. |
| `code` | `Callable` | Function to execute as the process body. |
| `priority` | `int` | Scheduler priority (default 5). |
| `memory` | `int` | Memory to allocate in bytes (default 1 MB). |
| `*args, **kwargs` | | Passed to `code` at execution time. |

**Returns** `int` — the new process PID.  
**Raises** `RuntimeError` if process limit (512) is reached.  
**Raises** `MemoryError` if memory allocation fails.

```python
pid = kernel.create_process("worker", my_func, priority=3, memory=2*1024*1024)
```

---

#### `Kernel.terminate_process(pid) -> bool`

Terminate a process and free its memory. Returns `True` on success.

---

#### `Kernel.suspend_process(pid) -> bool`

Suspend a running or ready process (SIGSTOP equivalent). Returns `True` on success.

---

#### `Kernel.resume_process(pid) -> bool`

Resume a stopped process. Returns `True` on success.

---

#### `Kernel.get_process(pid) -> Process | None`

Return the `Process` object for the given PID, or `None` if not found.

```python
proc = kernel.get_process(42)
if proc:
    print(proc.name, proc.state)
```

---

#### `Kernel.list_processes() -> List[Process]`

Return a list of all current `Process` objects.

---

#### `Kernel.send_signal(pid, signal) -> bool`

Send a `Signal` enum value to a process.

| Signal | Effect |
|---|---|
| `SIGKILL`, `SIGTERM` | Terminate immediately |
| `SIGSTOP`, `SIGTSTP` | Suspend |
| `SIGCONT` | Resume |
| Others | Queued or dispatched to handler |

```python
from core.kernel import Signal
kernel.send_signal(42, Signal.SIGTERM)
```

---

#### `Kernel.register_signal_handler(pid, signal, handler) -> bool`

Register a callable as the handler for a signal on the given PID. Pass `None` to clear.

---

#### `Kernel.get_pending_signals(pid) -> List[int]`

Return and clear the list of pending (unhandled) signal numbers for a process.

---

#### `Kernel.get_uptime() -> float`

Return system uptime in seconds since `start()` was called.

---

#### `Kernel.get_system_info() -> Dict[str, Any]`

Return a snapshot dictionary with keys:
`total_memory`, `free_memory`, `used_memory`, `process_count`, `uptime_seconds`, `running_processes`, `context_switches`, `interrupts`, `io_stats`, `cpu_ticks`.

---

#### `Kernel.get_cpu_stats() -> dict`

Return CPU tick counters: `user`, `system`, `idle`, `iowait`, `context_switches`, `interrupts`.

---

#### `Kernel.get_io_stats() -> dict`

Return I/O counters: `reads`, `writes`, `read_bytes`, `write_bytes`.

---

#### `Kernel.record_io(pid, op, bytes_count) -> None`

Record an I/O operation for process and system stats. `op` is `"read"` or `"write"`.

---

#### `Kernel.record_syscall(pid, name, duration=0.001) -> None`

Record a system call for performance profiling. Stores up to 200 entries per process.

**Related:** `Process`, `Signal`, `MemoryManager`, `Scheduler`

---

### core.filesystem — FileSystem

```python
class core.filesystem.FileSystem
```

In-memory virtual filesystem backed by an inode dictionary. Supports files, directories, and symlinks. Initialized with standard UNIX directory tree (`/bin`, `/etc`, `/home`, `/tmp`, `/var`, `/proc`, `/dev`, `/root`, `/usr`).

**Properties**

| Property | Type | Description |
|---|---|---|
| `inodes` | `Dict[str, Inode]` | Map of absolute path → Inode. |
| `current_directory` | `str` | Current working directory path. |
| `total_reads` | `int` | Cumulative read operation count. |
| `total_writes` | `int` | Cumulative write operation count. |

**Methods**

---

#### `FileSystem.create_file(path, content=b"") -> bool`

Create a new regular file. Returns `False` if the path already exists or parent directory is missing.

```python
fs.create_file("/etc/myapp.conf", b"[settings]\nkey=value\n")
```

---

#### `FileSystem.write_file(path, content) -> bool`

Write bytes to a file, creating it if it does not exist. Returns `False` if path is a directory.

```python
fs.write_file("/tmp/output.txt", b"hello world\n")
```

---

#### `FileSystem.read_file(path) -> bytes | None`

Read and return file contents as bytes. Follows symlinks. Returns `None` if path does not exist or is a directory.

```python
data = fs.read_file("/etc/hostname")  # b"pureos\n"
```

---

#### `FileSystem.delete_file(path) -> bool`

Delete a regular file. Returns `False` if path does not exist or is not a regular file.

---

#### `FileSystem.mkdir(path, parents=False) -> bool`

Create a directory. If `parents=True`, creates intermediate directories. Returns `False` if path already exists.

```python
fs.mkdir("/home/bob/projects", parents=True)
```

---

#### `FileSystem.rmdir(path) -> bool`

Remove an empty directory. Returns `False` if non-empty or not a directory.

---

#### `FileSystem.remove_tree(path) -> bool`

Recursively remove a file or directory tree. Returns `False` for root `/`.

---

#### `FileSystem.change_directory(path) -> bool`

Set the current working directory. Returns `False` if path does not exist or is not a directory.

---

#### `FileSystem.get_current_directory() -> str`

Return the current working directory as an absolute path string.

---

#### `FileSystem.list_directory(path=None) -> List[Inode] | None`

List inodes in a directory. Uses `current_directory` when `path` is `None`. Returns `None` if not a directory.

---

#### `FileSystem.stat(path) -> Dict | None`

Return a metadata dictionary for a path:

```python
{"name": str, "type": str, "size": int, "created": float,
 "modified": float, "permissions": str, "owner": str, "group": str}
```

---

#### `FileSystem.chmod(path, permissions) -> bool`

Set the permission string on an inode (e.g. `"rwxr-xr-x"`). Returns `False` if path not found.

---

#### `FileSystem.chown(path, owner, group=None) -> bool`

Change the owner (and optionally group) of a path. Returns `False` if path not found.

---

#### `FileSystem.exists(path) -> bool`

Return `True` if the path exists in the inode table.

---

#### `FileSystem.is_directory(path) -> bool` / `FileSystem.is_file(path) -> bool`

Type-check helpers. Return `False` if path does not exist.

---

#### `FileSystem.get_inode(path) -> Inode | None`

Return the raw `Inode` object for a path.

---

#### `FileSystem.get_io_rates() -> dict`

Return I/O rates since the last call: `read_bytes_per_sec`, `write_bytes_per_sec`, `total_reads`, `total_writes`, `read_bytes_total`, `written_bytes_total`.

---

#### `FileSystem.export_to_json() -> str` / `FileSystem.import_from_json(json_data) -> bool`

Serialize or restore the entire filesystem state as a JSON string.

**Related:** `Inode`, `FileType`, `core.persistence.PersistenceManager`

---

### core.auth — Authenticator

```python
class core.auth.Authenticator
```

Handles user authentication and session management. Wraps `UserManager` for credential verification. Passwords are validated via PBKDF2-HMAC-SHA256.

**Constructor**

```python
Authenticator(user_manager: UserManager)
```

**Properties**

| Property | Type | Description |
|---|---|---|
| `current_session` | `Session \| None` | The active session, if any. |
| `sessions` | `List[Session]` | All active sessions. |

**Methods**

---

#### `Authenticator.login(username, password) -> tuple[bool, Session | str]`

Authenticate a user and create a session.

```python
ok, result = auth.login("alice", "password123")
if ok:
    session = result   # Session object
else:
    print(result)      # Error message string
```

---

#### `Authenticator.logout() -> bool`

Invalidate and remove the current session. Returns `False` if no session is active.

---

#### `Authenticator.switch_user(username, password) -> tuple[bool, Session | str]`

Switch to a different user account (equivalent to `su`). Delegates to `login()`.

---

#### `Authenticator.is_authenticated() -> bool`

Return `True` if there is an active, authenticated session.

---

#### `Authenticator.get_current_user() -> str | None`

Return the username of the current session, or `None`.

---

#### `Authenticator.get_current_uid() -> int | None` / `get_current_gid() -> int | None`

Return the UID or GID of the current session.

---

#### `Authenticator.get_session_info() -> Dict`

Return a dict with `username`, `uid`, `gid`, `login_time`, `is_authenticated`.

---

#### `Authenticator.list_active_sessions() -> List[Dict]`

Return a list of dicts (username, uid, login_time) for all authenticated sessions.

---

#### `Authenticator.check_permission(required_uid=None, required_gid=None) -> bool`

Check if the current user satisfies UID/GID requirements. UID 0 (root) always passes.

---

#### `Authenticator.can_read_file(file_owner, file_group, permissions) -> bool`

#### `Authenticator.can_write_file(file_owner, file_group, permissions) -> bool`

#### `Authenticator.can_execute_file(file_owner, file_group, permissions) -> bool`

Unix-style permission checks against the current session. Root always returns `True`.

```python
ok = auth.can_read_file("root", "root", "rw-r--r--")
```

**Related:** `Session`, `UserManager`

---

### core.user — UserManager

```python
class core.user.UserManager
```

Manages user accounts and groups. Initializes with system accounts: `root` (UID 0) and `alice` (UID 1000, password `password123`). Persists state to `/etc/passwd` and `/etc/group` in the virtual filesystem.

**Constructor**

```python
UserManager(filesystem: FileSystem)
```

**Default users:** `root` (no password), `alice` (password: `password123`)  
**Default groups:** `root` (GID 0), `users` (GID 100), `sudo` (GID 27), `disk` (GID 6), `wheel` (GID 10)

**Methods**

---

#### `UserManager.create_user(username, password="", home_dir=None, shell="/bin/sh", create_home=True) -> tuple[bool, str]`

Create a new user account. Username must match `^[a-zA-Z_][a-zA-Z0-9_-]*$`.

```python
ok, msg = um.create_user("bob", "secret", create_home=True)
```

**Returns** `(True, "User 'bob' created successfully")` or `(False, error_message)`.

---

#### `UserManager.delete_user(username, remove_home=False) -> tuple[bool, str]`

Delete a user account. Cannot delete `root`. Removes user from all groups.

---

#### `UserManager.change_password(username, new_password) -> tuple[bool, str]`

Change a user's password. Generates a new PBKDF2 salt and hash.

---

#### `UserManager.verify_password(username, password) -> bool`

Verify a plaintext password against the stored PBKDF2-HMAC-SHA256 hash (200,000 iterations).

---

#### `UserManager.get_user(username) -> User | None`

Return the `User` object for the given username.

---

#### `UserManager.get_user_by_uid(uid) -> User | None`

Look up a user by numeric UID.

---

#### `UserManager.user_exists(username) -> bool`

Return `True` if the username is registered.

---

#### `UserManager.list_users() -> List[User]`

Return all `User` objects.

---

#### `UserManager.get_group(name) -> Group | None`

Return the `Group` object for the given group name.

---

#### `UserManager.get_group_by_gid(gid) -> Group | None`

Look up a group by numeric GID.

---

#### `UserManager.list_groups() -> List[Group]`

Return all `Group` objects.

---

#### `UserManager.get_user_groups(username) -> List[str]`

Return a list of group names the user belongs to.

---

#### `UserManager.is_user_in_group(username, groupname) -> bool`

Return `True` if the user is a member of the group.

---

#### `UserManager.export_passwd() -> str` / `export_group() -> str`

Export user/group data in `/etc/passwd` and `/etc/group` format.

---

#### `UserManager.to_dict() -> dict` / `from_dict(data) -> None`

Serialize/deserialize all user and group state for persistence.

**Related:** `User`, `Group`, `Authenticator`

---

### core.logging — SystemLogger

```python
class core.logging.SystemLogger
```

Centralized syslog-compatible logging service. Stores up to 10,000 log entries in memory. Kernel messages are also kept in a separate ring buffer (up to 1,000 entries).

**Enums**

```python
class LogLevel(Enum):
    EMERG = 0    # System unusable
    ALERT = 1    # Immediate action required
    CRIT  = 2    # Critical condition
    ERR   = 3    # Error
    WARNING = 4  # Warning
    NOTICE  = 5  # Significant normal condition
    INFO    = 6  # Informational
    DEBUG   = 7  # Debug

class LogFacility(Enum):
    KERN = 0    # Kernel
    USER = 1    # User-level
    DAEMON = 3  # System daemons
    AUTH = 4    # Authentication
    CRON = 9    # Cron scheduler
    # ... LOCAL0–LOCAL7 (16–23)
```

**Constructor**

```python
SystemLogger(max_entries: int = 10000)
```

**Methods**

---

#### `SystemLogger.log(level, facility, message, process_name="system", pid=None) -> None`

Add a log entry. Entries below the current `log_level` threshold are silently dropped.

```python
from core.logging import LogLevel, LogFacility
logger.log(LogLevel.ERR, LogFacility.KERN, "Page fault at 0x0", "kernel", pid=0)
```

---

#### `SystemLogger.query(level=None, facility=None, process_name=None, since=None, limit=None) -> List[LogEntry]`

Query log entries with optional filters. All filters are ANDed.

| Parameter | Type | Description |
|---|---|---|
| `level` | `LogLevel` | Return entries at or above this severity. |
| `facility` | `LogFacility` | Filter by facility. |
| `process_name` | `str` | Filter by process name. |
| `since` | `float` | Unix timestamp lower bound. |
| `limit` | `int` | Return only the last N entries. |

```python
errors = logger.query(level=LogLevel.ERR, limit=50)
```

---

#### `SystemLogger.get_kernel_log() -> List[str]`

Return the kernel ring buffer (equivalent to `dmesg`). Each entry is formatted as `[timestamp] message`.

---

#### `SystemLogger.set_log_level(level) -> None`

Set the minimum level for recorded entries.

---

#### `SystemLogger.add_output(stream) / remove_output(stream) -> None`

Attach/detach a `TextIO` stream for real-time log output.

---

#### `SystemLogger.clear() -> None`

Clear all entries and the kernel ring buffer.

---

#### `SystemLogger.export_to_file(filepath, filesystem) -> bool`

Write all entries to a file in the virtual filesystem.

**Convenience functions** (module-level):

```python
log_kernel(logger, level, message)          # facility=KERN, process="kernel", pid=0
log_daemon(logger, level, message, name)    # facility=DAEMON
log_auth(logger, level, message)            # facility=AUTH
log_cron(logger, level, message)            # facility=CRON
```

**Related:** `LogEntry`, `LogLevel`, `LogFacility`

