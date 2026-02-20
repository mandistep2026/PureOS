"""
PureOS Kernel
Core operating system functionality using only Python standard library.
"""

import threading
import queue
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    STOPPED = "stopped"
    TERMINATED = "terminated"


class Signal(Enum):
    SIGHUP  = 1   # Hangup
    SIGINT  = 2   # Interrupt
    SIGQUIT = 3   # Quit
    SIGKILL = 9   # Kill (cannot be caught)
    SIGUSR1 = 10  # User-defined 1
    SIGUSR2 = 12  # User-defined 2
    SIGTERM = 15  # Termination
    SIGCONT = 18  # Continue
    SIGSTOP = 19  # Stop (cannot be caught)
    SIGTSTP = 20  # Terminal stop


@dataclass
class Process:
    """Represents a process in the system."""
    pid: int
    name: str
    state: ProcessState = ProcessState.NEW
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    cpu_time: float = 0.0
    memory_usage: int = 0
    parent_pid: Optional[int] = None
    code: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    # Signal handling
    pending_signals: List[int] = field(default_factory=list)
    signal_handlers: Dict[int, Optional[Callable]] = field(default_factory=dict)


class MemoryManager:
    """Manages virtual memory allocation."""
    
    def __init__(self, total_memory: int = 1024 * 1024 * 100):  # 100MB default
        self.total_memory = total_memory
        self.used_memory = 0
        self.allocations: Dict[int, int] = {}  # pid -> bytes allocated
        self._lock = threading.Lock()
    
    def allocate(self, pid: int, bytes_needed: int) -> bool:
        """Allocate memory to a process."""
        with self._lock:
            if self.used_memory + bytes_needed > self.total_memory:
                return False
            self.allocations[pid] = self.allocations.get(pid, 0) + bytes_needed
            self.used_memory += bytes_needed
            return True
    
    def free(self, pid: int) -> int:
        """Free all memory allocated to a process."""
        with self._lock:
            freed = self.allocations.pop(pid, 0)
            self.used_memory -= freed
            return freed
    
    def get_free_memory(self) -> int:
        """Get available memory."""
        with self._lock:
            return self.total_memory - self.used_memory
    
    def get_process_memory(self, pid: int) -> int:
        """Get memory used by a specific process."""
        return self.allocations.get(pid, 0)


class Scheduler:
    """Round-robin process scheduler."""
    
    def __init__(self, time_quantum: float = 0.1):
        self.time_quantum = time_quantum
        self.ready_queue: queue.Queue = queue.Queue()
        self.current_process: Optional[Process] = None
        self._lock = threading.Lock()
        self._running = False
    
    def add_process(self, process: Process) -> None:
        """Add a process to the ready queue."""
        process.state = ProcessState.READY
        self.ready_queue.put(process)
    
    def get_next_process(self) -> Optional[Process]:
        """Get the next process to run."""
        try:
            return self.ready_queue.get(timeout=0.1)
        except queue.Empty:
            return None
    
    def schedule(self) -> Optional[Process]:
        """Perform context switch."""
        with self._lock:
            if self.current_process:
                if self.current_process.state != ProcessState.TERMINATED:
                    self.current_process.state = ProcessState.READY
                    self.ready_queue.put(self.current_process)
            
            next_process = self.get_next_process()
            if next_process:
                next_process.state = ProcessState.RUNNING
                self.current_process = next_process
            else:
                self.current_process = None
            
            return self.current_process


class Kernel:
    """Main kernel class that coordinates all OS functions."""
    
    def __init__(self):
        self.next_pid = 1
        self.processes: Dict[int, Process] = {}
        self.process_table_lock = threading.Lock()
        self.memory_manager = MemoryManager()
        self.scheduler = Scheduler()
        self._shutdown = False
        self._kernel_thread: Optional[threading.Thread] = None
        self._boot_time: Optional[float] = None
    
    def create_process(self, name: str, code: Callable, 
                      priority: int = 5, 
                      memory: int = 1024 * 1024,  # 1MB default
                      *args, **kwargs) -> int:
        """Create a new process."""
        with self.process_table_lock:
            pid = self.next_pid
            self.next_pid += 1
        
        process = Process(
            pid=pid,
            name=name,
            priority=priority,
            code=code,
            args=args,
            kwargs=kwargs
        )
        
        # Allocate memory
        if not self.memory_manager.allocate(pid, memory):
            raise MemoryError(f"Failed to allocate {memory} bytes for process {name}")
        
        process.memory_usage = memory
        
        with self.process_table_lock:
            self.processes[pid] = process
        
        self.scheduler.add_process(process)
        return pid
    
    def terminate_process(self, pid: int) -> bool:
        """Terminate a process."""
        with self.process_table_lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            process.state = ProcessState.TERMINATED
            
            # Free memory
            self.memory_manager.free(pid)
            
            return True
    
    def suspend_process(self, pid: int) -> bool:
        """Suspend (stop) a running process."""
        with self.process_table_lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            if process.state not in (ProcessState.RUNNING, ProcessState.READY):
                return False
            
            process.state = ProcessState.STOPPED
            return True
    
    def resume_process(self, pid: int) -> bool:
        """Resume a stopped process."""
        with self.process_table_lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            if process.state != ProcessState.STOPPED:
                return False
            
            process.state = ProcessState.READY
            self.scheduler.add_process(process)
            return True
    
    def get_process(self, pid: int) -> Optional[Process]:
        """Get process by PID."""
        return self.processes.get(pid)
    
    def list_processes(self) -> List[Process]:
        """List all processes."""
        return list(self.processes.values())
    
    def _execute_process(self, process: Process) -> None:
        """Execute a process's code."""
        start_time = time.time()
        try:
            if process.code:
                process.result = process.code(*process.args, **process.kwargs)
        except Exception as e:
            process.error = str(e)
        finally:
            process.cpu_time = time.time() - start_time
            process.state = ProcessState.TERMINATED
            self.memory_manager.free(process.pid)
    
    def start(self) -> None:
        """Start the kernel scheduler."""
        self._shutdown = False
        self._boot_time = time.time()
        self._kernel_thread = threading.Thread(target=self._kernel_loop, daemon=True)
        self._kernel_thread.start()
    
    def stop(self) -> None:
        """Stop the kernel."""
        self._shutdown = True
        if self._kernel_thread:
            self._kernel_thread.join(timeout=2.0)
    
    def _kernel_loop(self) -> None:
        """Main kernel loop."""
        while not self._shutdown:
            process = self.scheduler.schedule()
            if process:
                # Execute for time quantum
                thread = threading.Thread(
                    target=self._execute_process,
                    args=(process,),
                    daemon=True
                )
                thread.start()
                thread.join(timeout=self.scheduler.time_quantum)
                
                if thread.is_alive():
                    # Process still running, will be rescheduled
                    pass
            else:
                # No processes, sleep briefly
                time.sleep(0.01)

    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        if self._boot_time is None:
            return 0.0
        return max(0.0, time.time() - self._boot_time)
    
    def send_signal(self, pid: int, signal: "Signal") -> bool:
        """Send a signal to a process.

        SIGKILL and SIGTERM terminate the process immediately.
        SIGSTOP suspends it; SIGCONT resumes it.
        All other signals are queued as pending.
        """
        with self.process_table_lock:
            if pid not in self.processes:
                return False
            process = self.processes[pid]

            if signal in (Signal.SIGKILL, Signal.SIGTERM):
                process.state = ProcessState.TERMINATED
                self.memory_manager.free(pid)
            elif signal == Signal.SIGSTOP or signal == Signal.SIGTSTP:
                if process.state in (ProcessState.RUNNING, ProcessState.READY):
                    process.state = ProcessState.STOPPED
            elif signal == Signal.SIGCONT:
                if process.state == ProcessState.STOPPED:
                    process.state = ProcessState.READY
                    self.scheduler.add_process(process)
            else:
                # Queue signal; custom handler can be checked later
                handler = process.signal_handlers.get(signal.value)
                if handler is not None:
                    try:
                        handler(signal.value)
                    except Exception:
                        pass
                else:
                    process.pending_signals.append(signal.value)
            return True

    def register_signal_handler(self, pid: int, signal: "Signal",
                                handler: Optional[Callable]) -> bool:
        """Register a custom signal handler for a process."""
        with self.process_table_lock:
            if pid not in self.processes:
                return False
            self.processes[pid].signal_handlers[signal.value] = handler
            return True

    def get_pending_signals(self, pid: int) -> List[int]:
        """Return and clear the list of pending signals for a process."""
        with self.process_table_lock:
            if pid not in self.processes:
                return []
            signals = list(self.processes[pid].pending_signals)
            self.processes[pid].pending_signals.clear()
            return signals

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            "total_memory": self.memory_manager.total_memory,
            "free_memory": self.memory_manager.get_free_memory(),
            "used_memory": self.memory_manager.used_memory,
            "process_count": len(self.processes),
            "uptime_seconds": self.get_uptime(),
            "running_processes": len([p for p in self.processes.values() 
                                     if p.state == ProcessState.RUNNING]),
        }
