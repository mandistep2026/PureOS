"""
PureOS System Logging
Centralized logging system similar to syslog/journald.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TextIO
from enum import Enum
import sys


class LogLevel(Enum):
    """System log levels (compatible with syslog)."""
    EMERG = 0    # System is unusable
    ALERT = 1    # Action must be taken immediately
    CRIT = 2     # Critical conditions
    ERR = 3      # Error conditions
    WARNING = 4  # Warning conditions
    NOTICE = 5   # Normal but significant
    INFO = 6     # Informational
    DEBUG = 7    # Debug-level messages


class LogFacility(Enum):
    """Log facilities (syslog-style)."""
    KERN = 0      # Kernel messages
    USER = 1      # User-level messages
    MAIL = 2      # Mail system
    DAEMON = 3    # System daemons
    AUTH = 4      # Security/authorization
    SYSLOG = 5    # Syslog internal
    LPR = 6       # Line printer subsystem
    NEWS = 7      # Network news
    UUCP = 8      # UUCP subsystem
    CRON = 9      # Cron/at
    AUTHPRIV = 10 # Private auth messages
    LOCAL0 = 16   # Local use 0-7
    LOCAL1 = 17
    LOCAL2 = 18
    LOCAL3 = 19
    LOCAL4 = 20
    LOCAL5 = 21
    LOCAL6 = 22
    LOCAL7 = 23


@dataclass
class LogEntry:
    """Represents a single log entry."""
    timestamp: float
    level: LogLevel
    facility: LogFacility
    pid: Optional[int]
    process_name: str
    message: str
    hostname: str = "pureos"
    
    def to_syslog_format(self) -> str:
        """Format as traditional syslog message."""
        timestr = time.strftime("%b %d %H:%M:%S", time.localtime(self.timestamp))
        priority = self.facility.value * 8 + self.level.value
        pid_str = f"[{self.pid}]" if self.pid else ""
        return f"<{priority}>{timestr} {self.hostname} {self.process_name}{pid_str}: {self.message}"
    
    def to_readable_format(self) -> str:
        """Format as human-readable message."""
        timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        pid_str = f"[{self.pid}]" if self.pid else ""
        return f"{timestr} {self.level.name:8} {self.process_name}{pid_str}: {self.message}"


class SystemLogger:
    """Central system logging service."""
    
    def __init__(self, max_entries: int = 10000):
        self.entries: List[LogEntry] = []
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self.log_level = LogLevel.INFO
        self.output_streams: List[TextIO] = []
        self.kernel_buffer: List[str] = []  # Ring buffer for kernel messages
        self.max_kernel_messages = 1000
    
    def log(self, level: LogLevel, facility: LogFacility, message: str, 
            process_name: str = "system", pid: Optional[int] = None) -> None:
        """Add a log entry."""
        if level.value > self.log_level.value:
            return  # Skip messages below current log level
        
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            facility=facility,
            pid=pid,
            process_name=process_name,
            message=message
        )
        
        with self._lock:
            self.entries.append(entry)
            
            # Maintain max size
            if len(self.entries) > self.max_entries:
                self.entries.pop(0)
            
            # Kernel messages go to kernel buffer too
            if facility == LogFacility.KERN:
                self.kernel_buffer.append(f"[{time.time():.6f}] {message}")
                if len(self.kernel_buffer) > self.max_kernel_messages:
                    self.kernel_buffer.pop(0)
            
            # Write to output streams
            formatted = entry.to_readable_format()
            for stream in self.output_streams:
                try:
                    stream.write(formatted + "\n")
                    stream.flush()
                except:
                    pass
    
    def add_output(self, stream: TextIO) -> None:
        """Add an output stream for real-time logging."""
        with self._lock:
            if stream not in self.output_streams:
                self.output_streams.append(stream)
    
    def remove_output(self, stream: TextIO) -> None:
        """Remove an output stream."""
        with self._lock:
            if stream in self.output_streams:
                self.output_streams.remove(stream)
    
    def query(self, level: Optional[LogLevel] = None,
              facility: Optional[LogFacility] = None,
              process_name: Optional[str] = None,
              since: Optional[float] = None,
              limit: Optional[int] = None) -> List[LogEntry]:
        """Query log entries with filters."""
        with self._lock:
            results = list(self.entries)
        
        # Apply filters
        if level is not None:
            results = [e for e in results if e.level.value <= level.value]
        if facility is not None:
            results = [e for e in results if e.facility == facility]
        if process_name is not None:
            results = [e for e in results if e.process_name == process_name]
        if since is not None:
            results = [e for e in results if e.timestamp >= since]
        
        # Apply limit
        if limit is not None:
            results = results[-limit:]
        
        return results
    
    def get_kernel_log(self) -> List[str]:
        """Get kernel message buffer (like dmesg)."""
        with self._lock:
            return list(self.kernel_buffer)
    
    def clear(self) -> None:
        """Clear all log entries."""
        with self._lock:
            self.entries.clear()
            self.kernel_buffer.clear()
    
    def set_log_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self.log_level = level
    
    def export_to_file(self, filepath: str, filesystem) -> bool:
        """Export logs to a file in the virtual filesystem."""
        try:
            with self._lock:
                lines = [entry.to_readable_format() for entry in self.entries]
            content = "\n".join(lines).encode('utf-8')
            return filesystem.write_file(filepath, content)
        except:
            return False


# Convenience logging functions
def log_kernel(logger: SystemLogger, level: LogLevel, message: str) -> None:
    """Log a kernel message."""
    logger.log(level, LogFacility.KERN, message, "kernel", pid=0)


def log_daemon(logger: SystemLogger, level: LogLevel, message: str, daemon_name: str, pid: Optional[int] = None) -> None:
    """Log a daemon message."""
    logger.log(level, LogFacility.DAEMON, message, daemon_name, pid=pid)


def log_auth(logger: SystemLogger, level: LogLevel, message: str, process: str = "auth", pid: Optional[int] = None) -> None:
    """Log an authentication/security message."""
    logger.log(level, LogFacility.AUTH, message, process, pid=pid)


def log_cron(logger: SystemLogger, level: LogLevel, message: str, pid: Optional[int] = None) -> None:
    """Log a cron message."""
    logger.log(level, LogFacility.CRON, message, "cron", pid=pid)
