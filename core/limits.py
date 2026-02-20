"""
PureOS Resource Limits
Resource control and limits for processes (ulimit, cgroups-like functionality).
"""

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class ResourceType(Enum):
    """Types of resources that can be limited."""
    CPU_TIME = "cpu_time"              # Max CPU time in seconds
    FILE_SIZE = "file_size"            # Max file size in bytes
    DATA_SIZE = "data_size"            # Max data segment size
    STACK_SIZE = "stack_size"          # Max stack size
    CORE_SIZE = "core_size"            # Max core file size
    RSS_SIZE = "rss_size"              # Max resident set size
    NPROC = "nproc"                    # Max number of processes
    NOFILE = "nofile"                  # Max number of open files
    MEMLOCK = "memlock"                # Max locked memory
    AS_SIZE = "as_size"                # Max address space size
    LOCKS = "locks"                    # Max file locks
    SIGPENDING = "sigpending"          # Max pending signals
    MSGQUEUE = "msgqueue"              # Max bytes in POSIX message queues
    NICE = "nice"                      # Max nice priority
    RTPRIO = "rtprio"                  # Max real-time priority
    RTTIME = "rttime"                  # Max real-time timeout


# Default limits (soft, hard)
DEFAULT_LIMITS = {
    ResourceType.CPU_TIME: (None, None),         # Unlimited
    ResourceType.FILE_SIZE: (None, None),        # Unlimited
    ResourceType.DATA_SIZE: (None, None),        # Unlimited
    ResourceType.STACK_SIZE: (8388608, None),    # 8MB soft, unlimited hard
    ResourceType.CORE_SIZE: (0, None),           # No core dumps by default
    ResourceType.RSS_SIZE: (None, None),         # Unlimited
    ResourceType.NPROC: (1024, 2048),           # 1024 soft, 2048 hard
    ResourceType.NOFILE: (1024, 4096),          # 1024 soft, 4096 hard
    ResourceType.MEMLOCK: (65536, 65536),       # 64KB
    ResourceType.AS_SIZE: (None, None),         # Unlimited
    ResourceType.LOCKS: (None, None),           # Unlimited
    ResourceType.SIGPENDING: (1024, 1024),
    ResourceType.MSGQUEUE: (819200, 819200),    # 800KB
    ResourceType.NICE: (0, 0),
    ResourceType.RTPRIO: (0, 0),
    ResourceType.RTTIME: (None, None),
}


@dataclass
class ResourceLimit:
    """Resource limit for a process or group."""
    soft: Optional[int]  # Soft limit (can be increased up to hard limit)
    hard: Optional[int]  # Hard limit (absolute maximum)
    
    def check(self, value: int) -> bool:
        """Check if value is within limits."""
        if self.soft is not None and value > self.soft:
            return False
        return True
    
    def check_hard(self, value: int) -> bool:
        """Check against hard limit."""
        if self.hard is not None and value > self.hard:
            return False
        return True


@dataclass
class ProcessLimits:
    """Resource limits for a single process."""
    pid: int
    limits: Dict[ResourceType, ResourceLimit] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize with default limits."""
        if not self.limits:
            for resource, (soft, hard) in DEFAULT_LIMITS.items():
                self.limits[resource] = ResourceLimit(soft=soft, hard=hard)
    
    def get_limit(self, resource: ResourceType) -> ResourceLimit:
        """Get limit for a resource."""
        return self.limits.get(resource, ResourceLimit(None, None))
    
    def set_limit(self, resource: ResourceType, soft: Optional[int], 
                  hard: Optional[int] = None) -> bool:
        """Set resource limit. Returns True if successful."""
        current = self.limits.get(resource, ResourceLimit(None, None))
        
        # Can't set soft limit above hard limit
        if hard is None:
            hard = current.hard
        if soft is not None and hard is not None and soft > hard:
            return False
        
        # Can't increase hard limit (unless root)
        # For now, we'll allow it in our simulation
        
        self.limits[resource] = ResourceLimit(soft=soft, hard=hard)
        return True


@dataclass
class CGroup:
    """Control group for resource management."""
    name: str
    parent: Optional[str] = None
    pids: List[int] = field(default_factory=list)
    
    # CPU limits
    cpu_shares: int = 1024              # Relative CPU weight
    cpu_quota: Optional[int] = None     # CPU time quota (microseconds per period)
    cpu_period: int = 100000            # CPU period (microseconds)
    
    # Memory limits
    memory_limit: Optional[int] = None  # Memory limit in bytes
    memory_soft_limit: Optional[int] = None
    swap_limit: Optional[int] = None
    
    # I/O limits
    io_weight: int = 500                # I/O weight (100-1000)
    
    # Process limits
    pids_max: Optional[int] = None      # Max number of processes
    
    # Statistics
    cpu_usage: float = 0.0              # Total CPU usage
    memory_usage: int = 0               # Current memory usage
    
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def add_process(self, pid: int) -> bool:
        """Add a process to this cgroup."""
        with self.lock:
            if pid not in self.pids:
                # Check pids_max limit
                if self.pids_max is not None and len(self.pids) >= self.pids_max:
                    return False
                self.pids.append(pid)
                return True
            return False
    
    def remove_process(self, pid: int) -> bool:
        """Remove a process from this cgroup."""
        with self.lock:
            if pid in self.pids:
                self.pids.remove(pid)
                return True
            return False
    
    def check_memory_limit(self, requested: int) -> bool:
        """Check if memory allocation is allowed."""
        with self.lock:
            if self.memory_limit is None:
                return True
            return self.memory_usage + requested <= self.memory_limit
    
    def update_memory_usage(self, delta: int) -> None:
        """Update memory usage statistics."""
        with self.lock:
            self.memory_usage = max(0, self.memory_usage + delta)
    
    def get_cpu_quota_ratio(self) -> Optional[float]:
        """Get CPU quota as a ratio (0.0-1.0+)."""
        if self.cpu_quota is None:
            return None
        return self.cpu_quota / self.cpu_period


class ResourceManager:
    """Manages resource limits and control groups."""
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.process_limits: Dict[int, ProcessLimits] = {}
        self.cgroups: Dict[str, CGroup] = {}
        self._lock = threading.Lock()
        
        # Create default cgroups
        self._initialize_cgroups()
    
    def _initialize_cgroups(self):
        """Initialize default cgroup hierarchy."""
        # Root cgroup
        self.cgroups["/"] = CGroup(name="/", parent=None)
        
        # System services cgroup
        self.cgroups["/system"] = CGroup(
            name="/system",
            parent="/",
            cpu_shares=2048,
            memory_limit=50 * 1024 * 1024  # 50MB
        )
        
        # User sessions cgroup
        self.cgroups["/user"] = CGroup(
            name="/user",
            parent="/",
            cpu_shares=1024,
            memory_limit=None
        )
    
    def create_process_limits(self, pid: int) -> ProcessLimits:
        """Create limits for a new process."""
        with self._lock:
            if pid in self.process_limits:
                return self.process_limits[pid]
            
            limits = ProcessLimits(pid=pid)
            self.process_limits[pid] = limits
            return limits
    
    def get_process_limits(self, pid: int) -> Optional[ProcessLimits]:
        """Get limits for a process."""
        with self._lock:
            return self.process_limits.get(pid)
    
    def set_process_limit(self, pid: int, resource: ResourceType,
                         soft: Optional[int], hard: Optional[int] = None) -> bool:
        """Set a resource limit for a process."""
        limits = self.get_process_limits(pid)
        if not limits:
            limits = self.create_process_limits(pid)
        return limits.set_limit(resource, soft, hard)
    
    def check_limit(self, pid: int, resource: ResourceType, value: int) -> bool:
        """Check if a process can use a resource."""
        limits = self.get_process_limits(pid)
        if not limits:
            return True  # No limits set
        
        limit = limits.get_limit(resource)
        return limit.check(value)
    
    def remove_process_limits(self, pid: int) -> None:
        """Remove limits for a terminated process."""
        with self._lock:
            self.process_limits.pop(pid, None)
    
    def create_cgroup(self, name: str, parent: str = "/") -> Optional[CGroup]:
        """Create a new cgroup."""
        with self._lock:
            if name in self.cgroups:
                return None
            
            if parent not in self.cgroups:
                return None
            
            cgroup = CGroup(name=name, parent=parent)
            self.cgroups[name] = cgroup
            return cgroup
    
    def get_cgroup(self, name: str) -> Optional[CGroup]:
        """Get a cgroup by name."""
        with self._lock:
            return self.cgroups.get(name)
    
    def delete_cgroup(self, name: str) -> bool:
        """Delete a cgroup (must be empty)."""
        with self._lock:
            cgroup = self.cgroups.get(name)
            if not cgroup or len(cgroup.pids) > 0 or name == "/":
                return False
            del self.cgroups[name]
            return True
    
    def move_process_to_cgroup(self, pid: int, cgroup_name: str) -> bool:
        """Move a process to a different cgroup."""
        with self._lock:
            target = self.cgroups.get(cgroup_name)
            if not target:
                return False
            
            # Remove from current cgroups
            for cgroup in self.cgroups.values():
                cgroup.remove_process(pid)
            
            # Add to target
            return target.add_process(pid)
    
    def get_process_cgroup(self, pid: int) -> Optional[str]:
        """Get the cgroup a process belongs to."""
        with self._lock:
            for name, cgroup in self.cgroups.items():
                if pid in cgroup.pids:
                    return name
            return None
    
    def list_cgroups(self) -> List[Dict]:
        """List all cgroups."""
        with self._lock:
            return [
                {
                    "name": name,
                    "parent": cg.parent,
                    "pids": list(cg.pids),
                    "cpu_shares": cg.cpu_shares,
                    "memory_limit": cg.memory_limit,
                    "memory_usage": cg.memory_usage,
                }
                for name, cg in self.cgroups.items()
            ]
    
    def get_ulimit_info(self, pid: int) -> Dict:
        """Get ulimit-style information for a process."""
        limits = self.get_process_limits(pid)
        if not limits:
            limits = self.create_process_limits(pid)
        
        info = {}
        for resource, limit in limits.limits.items():
            soft_str = "unlimited" if limit.soft is None else str(limit.soft)
            hard_str = "unlimited" if limit.hard is None else str(limit.hard)
            info[resource.value] = {"soft": soft_str, "hard": hard_str}
        
        return info
