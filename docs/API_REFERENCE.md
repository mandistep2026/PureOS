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


---

### core.ipc — IPCManager

```python
class core.ipc.IPCManager
```

Manages all IPC mechanisms: pipes, POSIX-style message queues, shared memory segments, and counting semaphores. All operations are thread-safe.

**Methods**

---

#### `IPCManager.create_pipe() -> tuple[int, int]`

Create a unidirectional pipe. Returns `(read_fd, write_fd)` — integer file descriptors.

```python
read_fd, write_fd = ipc.create_pipe()
pipe, end = ipc.get_pipe_by_fd(write_fd)
pipe.write(b"hello")
```

---

#### `IPCManager.get_pipe_by_fd(fd) -> tuple[Pipe, str] | None`

Look up a pipe by file descriptor. Returns `(Pipe, end_type)` where `end_type` is `"read"` or `"write"`.

---

#### `IPCManager.close_pipe_fd(fd) -> bool`

Close one end of a pipe. When both ends are closed, the pipe is destroyed.

---

#### `IPCManager.create_message_queue(name, max_messages=10, max_msg_size=8192) -> str | None`

Create a named message queue. Returns a UUID queue ID, or `None` if name already exists.

```python
qid = ipc.create_message_queue("myqueue", max_messages=100)
mq  = ipc.get_message_queue("myqueue")
mq.send(b"payload", priority=1)
priority, data = mq.receive(timeout=5.0)
```

---

#### `IPCManager.get_message_queue(name) -> MessageQueue | None`

Retrieve a message queue by name.

---

#### `IPCManager.remove_message_queue(name) -> bool`

Destroy a message queue.

---

#### `IPCManager.create_shared_memory(name, size) -> str | None`

Create a named shared memory segment of `size` bytes. Returns a UUID shm ID, or `None` if name exists.

```python
shm_id = ipc.create_shared_memory("myshm", 4096)
shm = ipc.get_shared_memory("myshm")
shm.attach(pid)
shm.write(0, b"data")
chunk = shm.read(0, 4)
```

---

#### `IPCManager.get_shared_memory(name) -> SharedMemory | None`

Retrieve a shared memory segment by name.

---

#### `IPCManager.remove_shared_memory(name) -> bool`

Destroy shared memory segment. Fails if any PIDs are still attached.

---

#### `IPCManager.create_semaphore(name, initial_value=1, max_value=1) -> str | None`

Create a named counting semaphore. Returns a UUID semaphore ID, or `None` if name exists.

```python
sem_id = ipc.create_semaphore("mysem", initial_value=1)
sem = ipc.get_semaphore("mysem")
sem.wait()      # P — decrement (blocks if 0)
sem.post()      # V — increment
```

---

#### `IPCManager.get_semaphore(name) -> Semaphore | None`

Retrieve a semaphore by name.

---

#### `IPCManager.remove_semaphore(name) -> bool`

Destroy a semaphore.

---

#### `IPCManager.list_all() -> Dict[str, List[str]]`

Return a dict with keys `"pipes"`, `"message_queues"`, `"shared_memory"`, `"semaphores"`, each containing a list of IDs/names.

**Related types:**

| Class | Key methods |
|---|---|
| `Pipe` | `write(data)`, `read(size=-1)`, `available()`, `close_read()`, `close_write()` |
| `MessageQueue` | `send(message, priority, timeout)`, `receive(timeout)`, `size()` |
| `SharedMemory` | `attach(pid)`, `detach(pid)`, `write(offset, data)`, `read(offset, size)` |
| `Semaphore` | `wait(timeout)`, `post()`, `get_value()` |

---

### core.init — InitSystem

```python
class core.init.InitSystem
```

systemd-inspired service manager. Supports service lifecycle (start, stop, restart, reload), boot targets, enable/disable on boot, and dependency ordering.

**Constructor**

```python
InitSystem(kernel: Kernel, logger: SystemLogger = None)
```

**Default services:** `syslog.service`, `network.service`, `cron.service`  
**Default targets:** `rescue.target`, `multi-user.target`, `graphical.target`

**Service states:** `inactive`, `activating`, `active`, `deactivating`, `failed`, `reloading`

**Methods**

---

#### `InitSystem.register_service(service) -> bool`

Register a `Service` object. Returns `False` if a service with the same name already exists.

```python
from core.init import Service, ServiceType
svc = Service(name="myapp.service", description="My App",
              exec_start=lambda: my_main())
init.register_service(svc)
```

---

#### `InitSystem.start_service(name) -> bool`

Start a service. Resolves `dependencies` and `after` ordering. Runs `exec_start` in a background thread. Returns `False` if the service is unknown or dependencies fail.

---

#### `InitSystem.stop_service(name) -> bool`

Stop an active service. Calls `exec_stop` if defined, then joins the service thread (5s timeout).

---

#### `InitSystem.restart_service(name) -> bool`

Stop then start a service (100ms gap).

---

#### `InitSystem.reload_service(name) -> bool`

Call `exec_reload` on an active service without stopping it.

---

#### `InitSystem.enable_service(name) -> bool` / `disable_service(name) -> bool`

Mark a service to start (or not start) automatically at boot.

---

#### `InitSystem.get_service_status(name) -> Dict | None`

Return a status dict: `name`, `description`, `state`, `enabled`, `pid`, `uptime`, `restart_count`, `last_exit_code`.

---

#### `InitSystem.list_services() -> List[Dict]`

Return a list of service summary dicts: `name`, `state`, `enabled`, `description`.

---

#### `InitSystem.switch_target(target_name) -> bool`

Transition to a system target. Stops services not wanted by the target; starts required and wanted services.

---

#### `InitSystem.set_default_target(target_name) -> bool`

Set the target that will be activated at next boot.

**Related:** `Service`, `ServiceState`, `ServiceType`, `Target`

---

### core.limits — ResourceManager

```python
class core.limits.ResourceManager
```

Manages per-process resource limits (ulimit-style) and a cgroup hierarchy for group resource control.

**Constructor**

```python
ResourceManager(kernel: Kernel = None)
```

**Default cgroups:** `/` (root), `/system` (50 MB limit), `/user`

**Resource types** (`ResourceType` enum):

| Value | Description |
|---|---|
| `CPU_TIME` | Max CPU time (seconds) |
| `FILE_SIZE` | Max file size (bytes) |
| `STACK_SIZE` | Max stack size (default soft: 8 MB) |
| `NPROC` | Max processes (default soft: 1024, hard: 2048) |
| `NOFILE` | Max open files (default soft: 1024, hard: 4096) |
| `MEMLOCK` | Max locked memory (default: 64 KB) |
| `SIGPENDING` | Max pending signals (default: 1024) |
| `MSGQUEUE` | Max bytes in POSIX queues (default: 800 KB) |

**Methods**

---

#### `ResourceManager.set_process_limit(pid, resource, soft, hard=None) -> bool`

Set a resource limit for a process. Soft limit cannot exceed hard limit.

```python
from core.limits import ResourceType
rm.set_process_limit(42, ResourceType.NOFILE, soft=2048, hard=4096)
```

---

#### `ResourceManager.get_process_limits(pid) -> ProcessLimits | None`

Return the `ProcessLimits` object for a process.

---

#### `ResourceManager.create_process_limits(pid) -> ProcessLimits`

Initialize default limits for a process.

---

#### `ResourceManager.check_limit(pid, resource, value) -> bool`

Check whether `value` is within the soft limit for a resource. Returns `True` if no limits are set.

---

#### `ResourceManager.remove_process_limits(pid) -> None`

Remove all limit entries for a terminated process.

---

#### `ResourceManager.create_cgroup(name, parent="/") -> CGroup | None`

Create a new control group. Returns `None` if `name` already exists or `parent` is unknown.

```python
cg = rm.create_cgroup("/user/alice", parent="/user")
cg.memory_limit = 100 * 1024 * 1024  # 100 MB
```

---

#### `ResourceManager.get_cgroup(name) -> CGroup | None`

Retrieve a cgroup by path name.

---

#### `ResourceManager.delete_cgroup(name) -> bool`

Delete a cgroup. Fails if it contains processes or is root `/`.

---

#### `ResourceManager.move_process_to_cgroup(pid, cgroup_name) -> bool`

Move a process from its current cgroup to a different one.

---

#### `ResourceManager.get_process_cgroup(pid) -> str | None`

Return the cgroup path that contains the given PID.

---

#### `ResourceManager.list_cgroups() -> List[Dict]`

Return a list of dicts: `name`, `parent`, `pids`, `cpu_shares`, `memory_limit`, `memory_usage`.

---

#### `ResourceManager.get_ulimit_info(pid) -> Dict`

Return a `ulimit -a`-style dict mapping resource names to `{soft, hard}` string values.

**Related:** `ProcessLimits`, `CGroup`, `ResourceLimit`, `ResourceType`

---

### core.network — NetworkManager

```python
class core.network.NetworkManager
```

Simulated TCP/IP network stack with two default interfaces (`lo` at `127.0.0.1`, `eth0` at `192.168.1.100`), routing table, socket tables, and simulated ICMP/DNS.

**Methods**

---

#### `NetworkManager.get_interface(name) -> NetworkInterface | None`

Return a `NetworkInterface` by name (e.g. `"eth0"`).

---

#### `NetworkManager.list_interfaces() -> List[NetworkInterface]`

Return all network interfaces.

---

#### `NetworkManager.set_interface_state(name, state) -> bool`

Bring an interface up or down. `state` is `NetworkState.UP` or `NetworkState.DOWN`.

---

#### `NetworkManager.set_interface_ip(name, ip, netmask=None) -> bool`

Assign an IP address. Supports CIDR notation (`"192.168.1.5/24"`).

---

#### `NetworkManager.add_route(destination, gateway, genmask, interface, metric=0) -> None`

Add a static routing entry to the routing table.

---

#### `NetworkManager.list_routes() -> List[RoutingEntry]`

Return the current routing table.

---

#### `NetworkManager.ping(target, count=4, timeout=2.0) -> tuple[bool, List[Dict], str]`

Simulate ICMP echo. Returns `(all_success, results, hostname)`. Each result dict: `seq`, `ttl`, `time`, `success`.

```python
ok, results, host = nm.ping("8.8.8.8", count=3)
for r in results:
    print(f"seq={r['seq']} time={r['time']:.1f}ms")
```

---

#### `NetworkManager.traceroute(target, max_hops=30) -> List[Dict]`

Simulate traceroute. Returns list of hop dicts: `hop`, `ip`, `name`, `rtt`.

---

#### `NetworkManager.netstat(show_all=False) -> Dict`

Return active connections: `{"tcp": [...], "udp": [...], "unix": []}`.

---

#### `NetworkManager.get_hostname() -> str` / `set_hostname(hostname) -> bool`

Get or set the system hostname (max 64 characters).

---

#### `NetworkManager.resolve_hostname(hostname) -> str | None`

Simulate DNS resolution. Knows common hostnames (`google.com`, `cloudflare.com`, `github.com`, `python.org`).

**Simulated hosts include:** `8.8.8.8`, `1.1.1.1`, `9.9.9.9`, `192.168.1.1`, `127.0.0.1`

**Related:** `NetworkInterface`, `NetworkState`, `RoutingEntry`, `Socket`

---

### core.package — PackageManager

```python
class core.package.PackageManager
```

Package lifecycle management with an in-memory database of 27+ available packages. Handles dependency resolution on install and reverse-dependency checking on remove.

**Constructor**

```python
PackageManager(filesystem: FileSystem = None)
```

**Available packages include:** `vim`, `nano`, `curl`, `wget`, `git`, `python3`, `node`, `gcc`, `make`, `bash`, `zsh`, `tmux`, `htop`, `tree`, `jq`, `zip`, `tar`, `gzip`, `openssh`, `nginx`, `sqlite`, `redis`, `iperf3`, `netcat`, `tcpdump`, `mtr`, `wireshark`

**Methods**

---

#### `PackageManager.install(package_name) -> tuple[bool, str]`

Install a package and its dependencies recursively.

```python
ok, msg = pm.install("git")   # also installs "curl" dependency
```

---

#### `PackageManager.remove(package_name) -> tuple[bool, str]`

Remove an installed package. Fails if another installed package depends on it.

---

#### `PackageManager.list_installed() -> List[Package]`

Return all installed `Package` objects.

---

#### `PackageManager.list_available() -> List[Package]`

Return all packages in the repository (installed and available).

---

#### `PackageManager.search(query) -> List[Package]`

Case-insensitive search across `name`, `description`, and `category`.

```python
results = pm.search("network")
```

---

#### `PackageManager.info(package_name) -> Package | None`

Return the `Package` object (installed or available), or `None`.

---

#### `PackageManager.is_installed(package_name) -> bool`

Return `True` if the package is currently installed.

---

#### `PackageManager.get_dependencies(package_name) -> List[str]`

Return the list of declared dependency names for a package.

---

#### `PackageManager.total_installed_size() -> int`

Return the total installed size in bytes across all installed packages.

**`Package` fields:** `name`, `version`, `description`, `size`, `installed_size`, `dependencies`, `status`, `author`, `category`, `installed_time`

---

### core.cron — CronScheduler

```python
class core.cron.CronScheduler
```

Interval-based job scheduler. Executes shell commands in background threads on a configurable interval. The scheduler runs a 1-second polling loop in a daemon thread.

**Constructor**

```python
CronScheduler(shell=None)
```

**Methods**

---

#### `CronScheduler.start() -> None`

Start the background scheduler thread.

---

#### `CronScheduler.stop() -> None`

Stop the scheduler loop.

---

#### `CronScheduler.add_job(name, command, interval, max_runs=None, delay=0.0) -> CronJob`

Schedule a new job.

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable job name. |
| `command` | `str` | Shell command string to execute. |
| `interval` | `float` | Seconds between executions. |
| `max_runs` | `int \| None` | Maximum executions before expiring (None = unlimited). |
| `delay` | `float` | Initial delay before first run (0 = run after first interval). |

```python
job = cron.add_job("backup", "tar /home/alice", interval=3600)
```

---

#### `CronScheduler.remove_job(job_id) -> bool`

Remove a job by its integer ID.

---

#### `CronScheduler.pause_job(job_id) -> bool` / `resume_job(job_id) -> bool`

Pause or resume an active job. Resuming reschedules the next run from the current time.

---

#### `CronScheduler.list_jobs() -> List[CronJob]`

Return all registered `CronJob` objects.

---

#### `CronScheduler.get_job(job_id) -> CronJob | None`

Return a specific job by ID.

**`CronJob` fields:** `job_id`, `name`, `command`, `interval`, `next_run`, `state`, `run_count`, `last_run`, `last_exit_code`, `max_runs`

**`CronJobState` enum:** `ACTIVE`, `PAUSED`, `EXPIRED`

---

### core.persistence — PersistenceManager

```python
class core.persistence.PersistenceManager
```

Serializes and restores complete system state (filesystem, shell environment, aliases, command history) to a JSON file on the host disk. Default state directory: `~/.pureos/state.json`.

**Constructor**

```python
PersistenceManager(state_dir: str = None)
# Default: ~/.pureos
```

**Methods**

---

#### `PersistenceManager.save_state(filesystem, shell, kernel) -> bool`

Persist the system state to disk. Serializes:
- All filesystem inodes (binary content encoded as base64)
- Shell environment variables
- Shell aliases
- Command history
- Current working directory

Returns `True` on success.

```python
ok = pm.save_state(fs, shell, kernel)
```

---

#### `PersistenceManager.load_state(filesystem, shell, kernel) -> bool`

Restore a previously saved state. Returns `False` if no state file exists.

```python
if pm.state_exists():
    pm.load_state(fs, shell, kernel)
```

---

#### `PersistenceManager.state_exists() -> bool`

Return `True` if a saved state file is present.

---

#### `PersistenceManager.get_state_info() -> Dict | None`

Return metadata about the saved state without loading it: `version`, `files`, `directories`, `total_items`, `current_directory`, `history_count`. Returns `None` if no state exists.

---

#### `PersistenceManager.delete_state() -> bool`

Delete the saved state file from the host disk.

