"""
PureOS Init System
Service management and daemon control similar to systemd/init.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class ServiceState(Enum):
    """Service states."""
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    FAILED = "failed"
    RELOADING = "reloading"


class ServiceType(Enum):
    """Service types."""
    SIMPLE = "simple"      # Main process is started
    FORKING = "forking"    # Service forks and parent exits
    ONESHOT = "oneshot"    # Process exits after start
    NOTIFY = "notify"      # Service sends readiness notification
    IDLE = "idle"          # Delays execution until other jobs finish


@dataclass
class Service:
    """Represents a system service/daemon."""
    name: str
    description: str
    service_type: ServiceType = ServiceType.SIMPLE
    exec_start: Optional[Callable] = None
    exec_stop: Optional[Callable] = None
    exec_reload: Optional[Callable] = None
    restart_policy: str = "on-failure"  # no, always, on-success, on-failure
    restart_delay: float = 1.0
    pid: Optional[int] = None
    state: ServiceState = ServiceState.INACTIVE
    enabled: bool = False
    dependencies: List[str] = field(default_factory=list)
    after: List[str] = field(default_factory=list)  # Start after these services
    before: List[str] = field(default_factory=list)  # Start before these
    wanted_by: List[str] = field(default_factory=list)  # Targets that want this
    environment: Dict[str, str] = field(default_factory=dict)
    working_directory: str = "/"
    user: str = "root"
    restart_count: int = 0
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    last_exit_code: Optional[int] = None
    
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        if self.start_time and self.state == ServiceState.ACTIVE:
            return time.time() - self.start_time
        return 0.0


@dataclass
class Target:
    """Represents a system target (like runlevels)."""
    name: str
    description: str
    wants: List[str] = field(default_factory=list)  # Services this target wants
    requires: List[str] = field(default_factory=list)  # Services this target requires
    conflicts: List[str] = field(default_factory=list)  # Conflicting targets


class InitSystem:
    """System initialization and service management."""
    
    def __init__(self, kernel, logger=None):
        self.kernel = kernel
        self.logger = logger
        self.services: Dict[str, Service] = {}
        self.targets: Dict[str, Target] = {}
        self._lock = threading.Lock()
        self.default_target = "multi-user.target"
        self.current_target: Optional[str] = None
        self._service_threads: Dict[str, threading.Thread] = {}
        
        # Initialize default targets
        self._initialize_targets()
        
        # Initialize default services
        self._initialize_services()
    
    def _initialize_targets(self):
        """Create default system targets."""
        self.targets["rescue.target"] = Target(
            name="rescue.target",
            description="Rescue Mode",
            wants=[]
        )
        
        self.targets["multi-user.target"] = Target(
            name="multi-user.target",
            description="Multi-User System",
            wants=["network.service", "cron.service", "syslog.service"]
        )
        
        self.targets["graphical.target"] = Target(
            name="graphical.target",
            description="Graphical Interface",
            wants=["multi-user.target"]
        )
    
    def _initialize_services(self):
        """Create default system services."""
        # Syslog service
        self.services["syslog.service"] = Service(
            name="syslog.service",
            description="System Logging Service",
            service_type=ServiceType.SIMPLE,
            wanted_by=["multi-user.target"],
            enabled=True
        )
        
        # Network service
        self.services["network.service"] = Service(
            name="network.service",
            description="Network Configuration",
            service_type=ServiceType.ONESHOT,
            wanted_by=["multi-user.target"],
            enabled=True
        )
        
        # Cron service
        self.services["cron.service"] = Service(
            name="cron.service",
            description="Regular Background Program Processing",
            service_type=ServiceType.SIMPLE,
            after=["syslog.service"],
            wanted_by=["multi-user.target"],
            enabled=True
        )
    
    def register_service(self, service: Service) -> bool:
        """Register a new service."""
        with self._lock:
            if service.name in self.services:
                return False
            self.services[service.name] = service
            if self.logger:
                from core.logging import LogLevel, LogFacility
                self.logger.log(LogLevel.INFO, LogFacility.DAEMON, 
                              f"Registered service: {service.name}", "init", 1)
            return True
    
    def unregister_service(self, name: str) -> bool:
        """Unregister a service."""
        with self._lock:
            if name not in self.services:
                return False
            service = self.services[name]
            if service.state == ServiceState.ACTIVE:
                return False  # Can't unregister active service
            del self.services[name]
            return True
    
    def start_service(self, name: str) -> bool:
        """Start a service."""
        with self._lock:
            if name not in self.services:
                return False
            service = self.services[name]
            
            if service.state == ServiceState.ACTIVE:
                return True  # Already running
            
            if service.state == ServiceState.ACTIVATING:
                return False  # Already starting
            
            service.state = ServiceState.ACTIVATING
        
        # Start dependencies first
        for dep in service.dependencies:
            if not self.start_service(dep):
                service.state = ServiceState.FAILED
                return False
        
        # Start services in 'after' list
        for after_svc in service.after:
            if after_svc in self.services:
                self.start_service(after_svc)
        
        # Execute start command
        try:
            if service.exec_start:
                def run_service():
                    try:
                        exit_code = service.exec_start()
                        service.last_exit_code = exit_code
                        
                        if service.service_type == ServiceType.ONESHOT:
                            service.state = ServiceState.INACTIVE
                        elif exit_code != 0:
                            service.state = ServiceState.FAILED
                            if service.restart_policy in ("always", "on-failure"):
                                time.sleep(service.restart_delay)
                                service.restart_count += 1
                                self.start_service(service.name)
                        else:
                            service.state = ServiceState.INACTIVE
                    except Exception as e:
                        service.state = ServiceState.FAILED
                        service.last_exit_code = 1
                        if self.logger:
                            from core.logging import LogLevel, LogFacility
                            self.logger.log(LogLevel.ERR, LogFacility.DAEMON,
                                          f"Service {service.name} failed: {e}", "init", 1)
                
                thread = threading.Thread(target=run_service, daemon=True)
                self._service_threads[name] = thread
                thread.start()
            
            service.state = ServiceState.ACTIVE
            service.start_time = time.time()
            
            if self.logger:
                from core.logging import LogLevel, LogFacility
                self.logger.log(LogLevel.INFO, LogFacility.DAEMON,
                              f"Started service: {service.name}", "init", 1)
            
            return True
        except Exception as e:
            service.state = ServiceState.FAILED
            if self.logger:
                from core.logging import LogLevel, LogFacility
                self.logger.log(LogLevel.ERR, LogFacility.DAEMON,
                              f"Failed to start service {service.name}: {e}", "init", 1)
            return False
    
    def stop_service(self, name: str) -> bool:
        """Stop a service."""
        with self._lock:
            if name not in self.services:
                return False
            service = self.services[name]
            
            if service.state != ServiceState.ACTIVE:
                return True  # Already stopped
            
            service.state = ServiceState.DEACTIVATING
        
        try:
            if service.exec_stop:
                service.exec_stop()
            
            # Wait for thread to finish
            if name in self._service_threads:
                thread = self._service_threads[name]
                thread.join(timeout=5.0)
                del self._service_threads[name]
            
            service.state = ServiceState.INACTIVE
            service.stop_time = time.time()
            
            if self.logger:
                from core.logging import LogLevel, LogFacility
                self.logger.log(LogLevel.INFO, LogFacility.DAEMON,
                              f"Stopped service: {service.name}", "init", 1)
            
            return True
        except Exception as e:
            service.state = ServiceState.FAILED
            if self.logger:
                from core.logging import LogLevel, LogFacility
                self.logger.log(LogLevel.ERR, LogFacility.DAEMON,
                              f"Failed to stop service {service.name}: {e}", "init", 1)
            return False
    
    def restart_service(self, name: str) -> bool:
        """Restart a service."""
        if self.stop_service(name):
            time.sleep(0.1)
            return self.start_service(name)
        return False
    
    def reload_service(self, name: str) -> bool:
        """Reload service configuration."""
        with self._lock:
            if name not in self.services:
                return False
            service = self.services[name]
            
            if service.state != ServiceState.ACTIVE:
                return False
            
            service.state = ServiceState.RELOADING
        
        try:
            if service.exec_reload:
                service.exec_reload()
            service.state = ServiceState.ACTIVE
            return True
        except:
            service.state = ServiceState.ACTIVE  # Return to previous state
            return False
    
    def enable_service(self, name: str) -> bool:
        """Enable a service to start on boot."""
        with self._lock:
            if name not in self.services:
                return False
            self.services[name].enabled = True
            return True
    
    def disable_service(self, name: str) -> bool:
        """Disable a service from starting on boot."""
        with self._lock:
            if name not in self.services:
                return False
            self.services[name].enabled = False
            return True
    
    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service status information."""
        with self._lock:
            if name not in self.services:
                return None
            service = self.services[name]
            return {
                "name": service.name,
                "description": service.description,
                "state": service.state.value,
                "enabled": service.enabled,
                "pid": service.pid,
                "uptime": service.uptime(),
                "restart_count": service.restart_count,
                "last_exit_code": service.last_exit_code,
            }
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all services."""
        with self._lock:
            return [
                {
                    "name": svc.name,
                    "state": svc.state.value,
                    "enabled": svc.enabled,
                    "description": svc.description,
                }
                for svc in self.services.values()
            ]
    
    def switch_target(self, target_name: str) -> bool:
        """Switch to a different system target."""
        if target_name not in self.targets:
            return False
        
        target = self.targets[target_name]
        
        # Stop services not wanted by new target
        for service_name in list(self.services.keys()):
            service = self.services[service_name]
            if service.state == ServiceState.ACTIVE:
                if service_name not in target.wants and service_name not in target.requires:
                    self.stop_service(service_name)
        
        # Start required services
        for service_name in target.requires:
            if service_name in self.services:
                if not self.start_service(service_name):
                    return False
        
        # Start wanted services
        for service_name in target.wants:
            if service_name in self.services:
                self.start_service(service_name)
        
        self.current_target = target_name
        
        if self.logger:
            from core.logging import LogLevel, LogFacility
            self.logger.log(LogLevel.INFO, LogFacility.DAEMON,
                          f"Switched to target: {target_name}", "init", 1)
        
        return True
    
    def isolate_target(self, target_name: str) -> bool:
        """Switch to target and stop all other services."""
        return self.switch_target(target_name)
    
    def get_default_target(self) -> str:
        """Get the default target."""
        return self.default_target
    
    def set_default_target(self, target_name: str) -> bool:
        """Set the default target."""
        if target_name not in self.targets:
            return False
        self.default_target = target_name
        return True
