"""
PureOS Inter-Process Communication (IPC)
Provides pipes, message queues, and shared memory for process communication.
"""

import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any, Tuple
from enum import Enum
import uuid


class IPCType(Enum):
    """Types of IPC mechanisms."""
    PIPE = "pipe"
    MESSAGE_QUEUE = "message_queue"
    SHARED_MEMORY = "shared_memory"
    SEMAPHORE = "semaphore"


@dataclass
class Pipe:
    """Unidirectional pipe for byte stream communication."""
    pipe_id: str
    read_end: int  # File descriptor
    write_end: int  # File descriptor
    buffer: bytearray = field(default_factory=bytearray)
    max_size: int = 65536  # 64KB default
    closed_read: bool = False
    closed_write: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def write(self, data: bytes) -> int:
        """Write data to pipe. Returns number of bytes written."""
        if self.closed_write:
            raise BrokenPipeError("Write end of pipe is closed")
        
        with self.lock:
            available = self.max_size - len(self.buffer)
            to_write = min(len(data), available)
            self.buffer.extend(data[:to_write])
            return to_write
    
    def read(self, size: int = -1) -> bytes:
        """Read data from pipe. Returns bytes read."""
        if self.closed_read:
            raise ValueError("Read end of pipe is closed")
        
        with self.lock:
            if size == -1 or size >= len(self.buffer):
                data = bytes(self.buffer)
                self.buffer.clear()
            else:
                data = bytes(self.buffer[:size])
                self.buffer = self.buffer[size:]
            return data
    
    def available(self) -> int:
        """Return number of bytes available to read."""
        with self.lock:
            return len(self.buffer)
    
    def close_read(self) -> None:
        """Close read end."""
        self.closed_read = True
    
    def close_write(self) -> None:
        """Close write end."""
        self.closed_write = True


@dataclass
class MessageQueue:
    """POSIX-style message queue."""
    queue_id: str
    name: str
    max_messages: int = 10
    max_msg_size: int = 8192
    messages: queue.Queue = field(default_factory=queue.Queue)
    current_messages: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def send(self, message: bytes, priority: int = 0, timeout: Optional[float] = None) -> bool:
        """Send a message to the queue."""
        if len(message) > self.max_msg_size:
            raise ValueError(f"Message size {len(message)} exceeds maximum {self.max_msg_size}")
        
        with self.lock:
            if self.current_messages >= self.max_messages:
                return False  # Queue full
            
            try:
                self.messages.put((priority, time.time(), message), timeout=timeout)
                self.current_messages += 1
                return True
            except queue.Full:
                return False
    
    def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[int, bytes]]:
        """Receive a message from the queue. Returns (priority, message)."""
        try:
            priority, timestamp, message = self.messages.get(timeout=timeout)
            with self.lock:
                self.current_messages -= 1
            return (priority, message)
        except queue.Empty:
            return None
    
    def size(self) -> int:
        """Return number of messages in queue."""
        with self.lock:
            return self.current_messages


@dataclass
class SharedMemory:
    """Shared memory segment."""
    shm_id: str
    name: str
    size: int
    data: bytearray = field(default_factory=bytearray)
    attached_pids: List[int] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def __post_init__(self):
        """Initialize data buffer."""
        if not self.data:
            self.data = bytearray(self.size)
    
    def attach(self, pid: int) -> bool:
        """Attach process to shared memory."""
        with self.lock:
            if pid not in self.attached_pids:
                self.attached_pids.append(pid)
                return True
            return False
    
    def detach(self, pid: int) -> bool:
        """Detach process from shared memory."""
        with self.lock:
            if pid in self.attached_pids:
                self.attached_pids.remove(pid)
                return True
            return False
    
    def write(self, offset: int, data: bytes) -> int:
        """Write data at offset. Returns bytes written."""
        with self.lock:
            if offset < 0 or offset >= self.size:
                raise ValueError("Offset out of bounds")
            
            end = min(offset + len(data), self.size)
            bytes_to_write = end - offset
            self.data[offset:end] = data[:bytes_to_write]
            return bytes_to_write
    
    def read(self, offset: int, size: int) -> bytes:
        """Read data from offset."""
        with self.lock:
            if offset < 0 or offset >= self.size:
                raise ValueError("Offset out of bounds")
            
            end = min(offset + size, self.size)
            return bytes(self.data[offset:end])


@dataclass
class Semaphore:
    """Counting semaphore for synchronization."""
    sem_id: str
    name: str
    value: int
    max_value: int = 1
    lock: threading.Lock = field(default_factory=threading.Lock)
    condition: threading.Condition = field(default_factory=threading.Condition)
    
    def __post_init__(self):
        """Initialize condition with lock."""
        self.condition = threading.Condition(self.lock)
    
    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait (P operation) on semaphore."""
        with self.condition:
            start = time.time()
            while self.value <= 0:
                if timeout is not None:
                    elapsed = time.time() - start
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        return False
                    if not self.condition.wait(timeout=remaining):
                        return False
                else:
                    self.condition.wait()
            
            self.value -= 1
            return True
    
    def post(self) -> bool:
        """Post (V operation) on semaphore."""
        with self.condition:
            if self.value >= self.max_value:
                return False
            self.value += 1
            self.condition.notify()
            return True
    
    def get_value(self) -> int:
        """Get current semaphore value."""
        with self.lock:
            return self.value


class IPCManager:
    """Manages all IPC mechanisms in the system."""
    
    def __init__(self):
        self.pipes: Dict[str, Pipe] = {}
        self.message_queues: Dict[str, MessageQueue] = {}
        self.shared_memory: Dict[str, SharedMemory] = {}
        self.semaphores: Dict[str, Semaphore] = {}
        self.fd_to_pipe: Dict[int, Tuple[str, str]] = {}  # fd -> (pipe_id, end_type)
        self.next_fd = 100
        self._lock = threading.Lock()
    
    def create_pipe(self) -> Tuple[int, int]:
        """Create a pipe. Returns (read_fd, write_fd)."""
        pipe_id = str(uuid.uuid4())
        
        with self._lock:
            read_fd = self.next_fd
            self.next_fd += 1
            write_fd = self.next_fd
            self.next_fd += 1
        
        pipe = Pipe(pipe_id=pipe_id, read_end=read_fd, write_end=write_fd)
        
        with self._lock:
            self.pipes[pipe_id] = pipe
            self.fd_to_pipe[read_fd] = (pipe_id, "read")
            self.fd_to_pipe[write_fd] = (pipe_id, "write")
        
        return read_fd, write_fd
    
    def get_pipe_by_fd(self, fd: int) -> Optional[Tuple[Pipe, str]]:
        """Get pipe and end type by file descriptor."""
        with self._lock:
            mapping = self.fd_to_pipe.get(fd)
            if not mapping:
                return None
            pipe_id, end_type = mapping
            pipe = self.pipes.get(pipe_id)
            return (pipe, end_type) if pipe else None
    
    def close_pipe_fd(self, fd: int) -> bool:
        """Close a pipe file descriptor."""
        result = self.get_pipe_by_fd(fd)
        if not result:
            return False
        
        pipe, end_type = result
        if end_type == "read":
            pipe.close_read()
        else:
            pipe.close_write()
        
        with self._lock:
            del self.fd_to_pipe[fd]
            
            # If both ends closed, remove pipe
            if pipe.closed_read and pipe.closed_write:
                self.pipes.pop(pipe.pipe_id, None)
        
        return True
    
    def create_message_queue(self, name: str, max_messages: int = 10, 
                           max_msg_size: int = 8192) -> Optional[str]:
        """Create a message queue. Returns queue ID."""
        with self._lock:
            if name in self.message_queues:
                return None  # Already exists
            
            queue_id = str(uuid.uuid4())
            mq = MessageQueue(
                queue_id=queue_id,
                name=name,
                max_messages=max_messages,
                max_msg_size=max_msg_size
            )
            self.message_queues[name] = mq
            return queue_id
    
    def get_message_queue(self, name: str) -> Optional[MessageQueue]:
        """Get message queue by name."""
        with self._lock:
            return self.message_queues.get(name)
    
    def remove_message_queue(self, name: str) -> bool:
        """Remove a message queue."""
        with self._lock:
            if name in self.message_queues:
                del self.message_queues[name]
                return True
            return False
    
    def create_shared_memory(self, name: str, size: int) -> Optional[str]:
        """Create shared memory segment. Returns shm ID."""
        with self._lock:
            if name in self.shared_memory:
                return None
            
            shm_id = str(uuid.uuid4())
            shm = SharedMemory(shm_id=shm_id, name=name, size=size)
            self.shared_memory[name] = shm
            return shm_id
    
    def get_shared_memory(self, name: str) -> Optional[SharedMemory]:
        """Get shared memory by name."""
        with self._lock:
            return self.shared_memory.get(name)
    
    def remove_shared_memory(self, name: str) -> bool:
        """Remove shared memory segment."""
        with self._lock:
            shm = self.shared_memory.get(name)
            if shm and len(shm.attached_pids) == 0:
                del self.shared_memory[name]
                return True
            return False
    
    def create_semaphore(self, name: str, initial_value: int = 1, 
                        max_value: int = 1) -> Optional[str]:
        """Create a semaphore. Returns semaphore ID."""
        with self._lock:
            if name in self.semaphores:
                return None
            
            sem_id = str(uuid.uuid4())
            sem = Semaphore(
                sem_id=sem_id,
                name=name,
                value=initial_value,
                max_value=max_value
            )
            self.semaphores[name] = sem
            return sem_id
    
    def get_semaphore(self, name: str) -> Optional[Semaphore]:
        """Get semaphore by name."""
        with self._lock:
            return self.semaphores.get(name)
    
    def remove_semaphore(self, name: str) -> bool:
        """Remove a semaphore."""
        with self._lock:
            if name in self.semaphores:
                del self.semaphores[name]
                return True
            return False
    
    def list_all(self) -> Dict[str, List[str]]:
        """List all IPC objects."""
        with self._lock:
            return {
                "pipes": list(self.pipes.keys()),
                "message_queues": list(self.message_queues.keys()),
                "shared_memory": list(self.shared_memory.keys()),
                "semaphores": list(self.semaphores.keys()),
            }
