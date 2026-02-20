"""
PureOS System Commands
Commands for system logging, IPC, service management, and resource control.
"""

import sys
from typing import List
from shell.shell import ShellCommand


class DmesgCommand(ShellCommand):
    """Display kernel ring buffer (system log)."""
    
    def __init__(self):
        super().__init__("dmesg", "Print kernel ring buffer")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'logger') or not shell.kernel.logger:
            print("dmesg: system logger not available")
            return 1
        
        clear = '-c' in args or '--clear' in args
        level = None
        
        # Parse log level filter
        for arg in args:
            if arg.startswith('-l') or arg.startswith('--level='):
                try:
                    if '=' in arg:
                        level_str = arg.split('=')[1]
                    else:
                        level_str = arg[2:]
                    from core.logging import LogLevel
                    level = LogLevel[level_str.upper()]
                except:
                    pass
        
        kernel_log = shell.kernel.logger.get_kernel_log()
        for line in kernel_log:
            print(line)
        
        if clear:
            shell.kernel.logger.kernel_buffer.clear()
        
        return 0


class LoggerCommand(ShellCommand):
    """Add entries to system log."""
    
    def __init__(self):
        super().__init__("logger", "Make entries in the system log")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'logger') or not shell.kernel.logger:
            print("logger: system logger not available")
            return 1
        
        from core.logging import LogLevel, LogFacility
        
        priority = LogLevel.INFO
        facility = LogFacility.USER
        tag = "user"
        message_parts = []
        
        i = 0
        while i < len(args):
            if args[i] in ('-p', '--priority') and i + 1 < len(args):
                i += 1
                # Parse facility.level format
                if '.' in args[i]:
                    fac_str, lev_str = args[i].split('.', 1)
                    try:
                        facility = LogFacility[fac_str.upper()]
                    except:
                        pass
                    try:
                        priority = LogLevel[lev_str.upper()]
                    except:
                        pass
            elif args[i] in ('-t', '--tag') and i + 1 < len(args):
                i += 1
                tag = args[i]
            elif not args[i].startswith('-'):
                message_parts.append(args[i])
            i += 1
        
        if not message_parts:
            print("logger: no message specified")
            return 1
        
        message = ' '.join(message_parts)
        shell.kernel.logger.log(priority, facility, message, tag)
        return 0


class JournalctlCommand(ShellCommand):
    """Query the system journal."""
    
    def __init__(self):
        super().__init__("journalctl", "Query the system journal")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'logger') or not shell.kernel.logger:
            print("journalctl: system logger not available")
            return 1
        
        from core.logging import LogLevel, LogFacility
        
        follow = '-f' in args or '--follow' in args
        lines = None
        since = None
        unit = None
        priority = None
        
        i = 0
        while i < len(args):
            if args[i] in ('-n', '--lines') and i + 1 < len(args):
                i += 1
                try:
                    lines = int(args[i])
                except:
                    pass
            elif args[i] in ('-u', '--unit') and i + 1 < len(args):
                i += 1
                unit = args[i]
            elif args[i] in ('-p', '--priority') and i + 1 < len(args):
                i += 1
                try:
                    priority = LogLevel[args[i].upper()]
                except:
                    pass
            i += 1
        
        entries = shell.kernel.logger.query(
            level=priority,
            process_name=unit,
            limit=lines
        )
        
        for entry in entries:
            print(entry.to_readable_format())
        
        return 0


class SystemctlCommand(ShellCommand):
    """Control the init system and service manager."""
    
    def __init__(self):
        super().__init__("systemctl", "Control system services")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'init_system') or not shell.kernel.init_system:
            print("systemctl: init system not available")
            return 1
        
        init = shell.kernel.init_system
        
        if not args:
            # List services
            services = init.list_services()
            print(f"{'SERVICE':<30} {'STATE':<12} {'ENABLED':<8}")
            print("-" * 52)
            for svc in services:
                enabled = "enabled" if svc['enabled'] else "disabled"
                print(f"{svc['name']:<30} {svc['state']:<12} {enabled:<8}")
            return 0
        
        command = args[0]
        
        if command == "start" and len(args) > 1:
            service = args[1]
            if init.start_service(service):
                print(f"Started {service}")
                return 0
            else:
                print(f"Failed to start {service}")
                return 1
        
        elif command == "stop" and len(args) > 1:
            service = args[1]
            if init.stop_service(service):
                print(f"Stopped {service}")
                return 0
            else:
                print(f"Failed to stop {service}")
                return 1
        
        elif command == "restart" and len(args) > 1:
            service = args[1]
            if init.restart_service(service):
                print(f"Restarted {service}")
                return 0
            else:
                print(f"Failed to restart {service}")
                return 1
        
        elif command == "status" and len(args) > 1:
            service = args[1]
            status = init.get_service_status(service)
            if status:
                print(f"● {status['name']} - {status.get('description', '')}")
                print(f"   Loaded: {'enabled' if status['enabled'] else 'disabled'}")
                print(f"   Active: {status['state']}")
                if status['pid']:
                    print(f"   PID: {status['pid']}")
                if status['uptime'] > 0:
                    print(f"   Uptime: {status['uptime']:.1f}s")
                return 0
            else:
                print(f"Unit {service} could not be found")
                return 1
        
        elif command == "enable" and len(args) > 1:
            service = args[1]
            if init.enable_service(service):
                print(f"Enabled {service}")
                return 0
            else:
                print(f"Failed to enable {service}")
                return 1
        
        elif command == "disable" and len(args) > 1:
            service = args[1]
            if init.disable_service(service):
                print(f"Disabled {service}")
                return 0
            else:
                print(f"Failed to disable {service}")
                return 1
        
        elif command == "list-units":
            services = init.list_services()
            print(f"{'UNIT':<30} {'LOAD':<8} {'ACTIVE':<12} {'SUB':<12} {'DESCRIPTION'}")
            print("-" * 80)
            for svc in services:
                load = "loaded" if svc['enabled'] else "masked"
                print(f"{svc['name']:<30} {load:<8} {svc['state']:<12} {'running':<12} {svc['description']}")
            return 0
        
        else:
            print(f"systemctl: unknown command '{command}'")
            print("Usage: systemctl [start|stop|restart|status|enable|disable|list-units] [service]")
            return 1


class UlimitCommand(ShellCommand):
    """Get and set user limits."""
    
    def __init__(self):
        super().__init__("ulimit", "Get and set user limits")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'resource_manager') or not shell.kernel.resource_manager:
            print("ulimit: resource manager not available")
            return 1
        
        from core.limits import ResourceType
        
        # Get current shell PID (simulated)
        pid = 1  # Shell process
        
        if not args or '-a' in args:
            # Show all limits
            info = shell.kernel.resource_manager.get_ulimit_info(pid)
            print(f"{'Resource':<20} {'Soft Limit':<15} {'Hard Limit':<15}")
            print("-" * 50)
            for resource, limits in info.items():
                print(f"{resource:<20} {limits['soft']:<15} {limits['hard']:<15}")
            return 0
        
        # Parse specific limit options
        resource_map = {
            '-c': ResourceType.CORE_SIZE,
            '-d': ResourceType.DATA_SIZE,
            '-f': ResourceType.FILE_SIZE,
            '-n': ResourceType.NOFILE,
            '-s': ResourceType.STACK_SIZE,
            '-t': ResourceType.CPU_TIME,
            '-u': ResourceType.NPROC,
            '-v': ResourceType.AS_SIZE,
        }
        
        resource = None
        value = None
        
        for i, arg in enumerate(args):
            if arg in resource_map:
                resource = resource_map[arg]
                # Next arg might be the value
                if i + 1 < len(args) and not args[i + 1].startswith('-'):
                    try:
                        value = int(args[i + 1]) if args[i + 1] != 'unlimited' else None
                    except:
                        pass
                break
        
        if resource:
            limits = shell.kernel.resource_manager.get_process_limits(pid)
            if not limits:
                limits = shell.kernel.resource_manager.create_process_limits(pid)
            
            limit = limits.get_limit(resource)
            
            if value is None and len(args) == 1:
                # Show current value
                soft_str = "unlimited" if limit.soft is None else str(limit.soft)
                print(soft_str)
            elif value is not None:
                # Set new value
                if shell.kernel.resource_manager.set_process_limit(pid, resource, value, limit.hard):
                    return 0
                else:
                    print("ulimit: cannot modify limit")
                    return 1
        
        return 0


class IpcsCommand(ShellCommand):
    """Show IPC status."""
    
    def __init__(self):
        super().__init__("ipcs", "Show IPC facility status")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'ipc_manager') or not shell.kernel.ipc_manager:
            print("ipcs: IPC manager not available")
            return 1
        
        ipc = shell.kernel.ipc_manager
        all_ipc = ipc.list_all()
        
        show_all = '-a' in args
        show_queues = '-q' in args or show_all or not args
        show_shm = '-m' in args or show_all or not args
        show_sem = '-s' in args or show_all or not args
        
        if show_queues and all_ipc['message_queues']:
            print("------ Message Queues --------")
            print(f"{'key':<15} {'msqid':<10} {'owner':<10} {'perms':<8} {'used-bytes':<12}")
            for name in all_ipc['message_queues']:
                mq = ipc.get_message_queue(name)
                if mq:
                    print(f"{name:<15} {'0x' + mq.queue_id[:8]:<10} {'root':<10} {'660':<8} {mq.size():<12}")
            print()
        
        if show_shm and all_ipc['shared_memory']:
            print("------ Shared Memory Segments --------")
            print(f"{'key':<15} {'shmid':<10} {'owner':<10} {'perms':<8} {'bytes':<12} {'nattch':<8}")
            for name in all_ipc['shared_memory']:
                shm = ipc.get_shared_memory(name)
                if shm:
                    print(f"{name:<15} {'0x' + shm.shm_id[:8]:<10} {'root':<10} {'660':<8} {shm.size:<12} {len(shm.attached_pids):<8}")
            print()
        
        if show_sem and all_ipc['semaphores']:
            print("------ Semaphore Arrays --------")
            print(f"{'key':<15} {'semid':<10} {'owner':<10} {'perms':<8} {'nsems':<8}")
            for name in all_ipc['semaphores']:
                sem = ipc.get_semaphore(name)
                if sem:
                    print(f"{name:<15} {'0x' + sem.sem_id[:8]:<10} {'root':<10} {'660':<8} {'1':<8}")
            print()
        
        return 0


class CgroupCommand(ShellCommand):
    """Manage control groups."""
    
    def __init__(self):
        super().__init__("cgctl", "Control group management")
    
    def execute(self, args: List[str], shell) -> int:
        if not hasattr(shell.kernel, 'resource_manager') or not shell.kernel.resource_manager:
            print("cgctl: resource manager not available")
            return 1
        
        rm = shell.kernel.resource_manager
        
        if not args or args[0] == "list":
            cgroups = rm.list_cgroups()
            print(f"{'CGROUP':<30} {'PIDS':<8} {'CPU':<10} {'MEMORY':<15}")
            print("-" * 65)
            for cg in cgroups:
                mem_limit = "unlimited" if cg['memory_limit'] is None else f"{cg['memory_limit'] // 1024}K"
                print(f"{cg['name']:<30} {len(cg['pids']):<8} {cg['cpu_shares']:<10} {mem_limit:<15}")
            return 0
        
        command = args[0]
        
        if command == "create" and len(args) > 1:
            name = args[1]
            parent = args[2] if len(args) > 2 else "/"
            if rm.create_cgroup(name, parent):
                print(f"Created cgroup: {name}")
                return 0
            else:
                print(f"Failed to create cgroup: {name}")
                return 1
        
        elif command == "delete" and len(args) > 1:
            name = args[1]
            if rm.delete_cgroup(name):
                print(f"Deleted cgroup: {name}")
                return 0
            else:
                print(f"Failed to delete cgroup: {name}")
                return 1
        
        elif command == "move" and len(args) > 2:
            pid = int(args[1])
            cgroup = args[2]
            if rm.move_process_to_cgroup(pid, cgroup):
                print(f"Moved process {pid} to {cgroup}")
                return 0
            else:
                print(f"Failed to move process")
                return 1
        
        elif command == "show" and len(args) > 1:
            name = args[1]
            cg = rm.get_cgroup(name)
            if cg:
                print(f"Name: {cg.name}")
                print(f"Parent: {cg.parent}")
                print(f"PIDs: {', '.join(map(str, cg.pids)) if cg.pids else 'none'}")
                print(f"CPU shares: {cg.cpu_shares}")
                mem_limit = "unlimited" if cg.memory_limit is None else f"{cg.memory_limit} bytes"
                print(f"Memory limit: {mem_limit}")
                print(f"Memory usage: {cg.memory_usage} bytes")
                return 0
            else:
                print(f"Cgroup not found: {name}")
                return 1
        
        else:
            print("Usage: cgctl [list|create|delete|move|show]")
            return 1
