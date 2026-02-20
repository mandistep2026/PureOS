"""
PureOS Metrics
Metrics collection, health checking, and performance profiling.
"""

import time
import random
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict


class MetricsCollector:
    """Collects system metrics from kernel, filesystem, and network subsystems."""

    def __init__(self, kernel, filesystem, network_manager=None, init_system=None):
        self.kernel = kernel
        self.filesystem = filesystem
        self.network_manager = network_manager
        self.init_system = init_system

        # CPU tick tracking for delta-based percentage calculations
        self._last_cpu_sample_time: float = time.time()
        self._last_cpu_ticks: Dict[str, float] = {
            "user": 0.0,
            "sys": 0.0,
            "idle": 0.0,
            "iowait": 0.0,
        }
        self._context_switches: int = 0
        self._interrupts: int = 0

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------

    def get_cpu_snapshot(self) -> Dict:
        """Return a snapshot of CPU utilisation metrics.

        Percentages are calculated from kernel._cpu_ticks when available,
        otherwise realistic simulated values are used.
        """
        now = time.time()
        elapsed = max(now - self._last_cpu_sample_time, 0.001)

        # Try to read real tick data from the kernel attribute
        if hasattr(self.kernel, "_cpu_ticks") and isinstance(self.kernel._cpu_ticks, dict):
            ticks = self.kernel._cpu_ticks
            delta_user   = max(ticks.get("user",   0.0) - self._last_cpu_ticks["user"],   0.0)
            delta_sys    = max(ticks.get("sys",     0.0) - self._last_cpu_ticks["sys"],    0.0)
            delta_idle   = max(ticks.get("idle",    0.0) - self._last_cpu_ticks["idle"],   0.0)
            delta_iowait = max(ticks.get("iowait",  0.0) - self._last_cpu_ticks["iowait"], 0.0)

            total = delta_user + delta_sys + delta_idle + delta_iowait
            if total > 0:
                user_pct    = (delta_user   / total) * 100.0
                sys_pct     = (delta_sys    / total) * 100.0
                idle_pct    = (delta_idle   / total) * 100.0
                iowait_pct  = (delta_iowait / total) * 100.0
            else:
                user_pct = sys_pct = iowait_pct = 0.0
                idle_pct = 100.0

            # Update saved state
            self._last_cpu_ticks = {
                "user":   ticks.get("user",   0.0),
                "sys":    ticks.get("sys",    0.0),
                "idle":   ticks.get("idle",   0.0),
                "iowait": ticks.get("iowait", 0.0),
            }
        else:
            # Simulate realistic CPU usage with small random jitter
            user_pct   = round(random.uniform(5.0,  25.0) + random.uniform(-2.0, 2.0), 2)
            sys_pct    = round(random.uniform(1.0,  10.0) + random.uniform(-1.0, 1.0), 2)
            iowait_pct = round(random.uniform(0.0,   5.0) + random.uniform(-0.5, 0.5), 2)
            idle_pct   = round(max(100.0 - user_pct - sys_pct - iowait_pct, 0.0), 2)

        # Accumulate simulated context-switch / interrupt counters
        self._context_switches += int(elapsed * random.uniform(200, 800))
        self._interrupts        += int(elapsed * random.uniform(100, 400))

        self._last_cpu_sample_time = now

        return {
            "user_pct":        round(user_pct,   2),
            "sys_pct":         round(sys_pct,    2),
            "idle_pct":        round(idle_pct,   2),
            "iowait_pct":      round(iowait_pct, 2),
            "context_switches": self._context_switches,
            "interrupts":       self._interrupts,
        }

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def get_memory_snapshot(self) -> Dict:
        """Return a snapshot of memory utilisation metrics (bytes)."""
        mm = self.kernel.memory_manager
        total    = mm.total_memory
        used     = mm.used_memory
        free     = mm.get_free_memory()

        # Simulate cached / buffer / swap figures
        cached  = int(total * random.uniform(0.05, 0.15))
        buffers = int(total * random.uniform(0.01, 0.05))
        available = free + cached

        swap_total = int(total * 0.5)            # 50 % of RAM as swap
        swap_used  = int(swap_total * random.uniform(0.0, 0.2))
        swap_free  = swap_total - swap_used

        # Shared memory from IPC if present
        shared = 0
        if self.kernel.ipc_manager is not None:
            ipc = self.kernel.ipc_manager
            for shm in ipc.shared_memory.values():
                shared += getattr(shm, "size", 0)

        return {
            "total":      total,
            "used":       used,
            "free":       free,
            "cached":     cached,
            "buffers":    buffers,
            "available":  available,
            "swap_total": swap_total,
            "swap_used":  swap_used,
            "swap_free":  swap_free,
            "shared":     shared,
        }

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def get_io_snapshot(self) -> Dict:
        """Return a snapshot of block I/O metrics."""
        # Prefer real rates from filesystem if available
        if hasattr(self.filesystem, "get_io_rates") and callable(self.filesystem.get_io_rates):
            try:
                rates = self.filesystem.get_io_rates()
                return {
                    "reads_per_sec":    rates.get("reads_per_sec",    0.0),
                    "writes_per_sec":   rates.get("writes_per_sec",   0.0),
                    "read_kb_per_sec":  rates.get("read_kb_per_sec",  0.0),
                    "write_kb_per_sec": rates.get("write_kb_per_sec", 0.0),
                    "util_pct":         rates.get("util_pct",         0.0),
                }
            except Exception:
                pass

        # Simulated values with jitter
        reads_per_sec    = round(random.uniform(0.0,  50.0)  + random.uniform(-2.0, 2.0), 2)
        writes_per_sec   = round(random.uniform(0.0,  30.0)  + random.uniform(-2.0, 2.0), 2)
        read_kb_per_sec  = round(random.uniform(0.0, 500.0)  + random.uniform(-10,  10),  2)
        write_kb_per_sec = round(random.uniform(0.0, 200.0)  + random.uniform(-5,    5),  2)
        util_pct         = round(random.uniform(0.0,  40.0)  + random.uniform(-5.0,  5.0), 2)

        return {
            "reads_per_sec":    max(reads_per_sec,    0.0),
            "writes_per_sec":   max(writes_per_sec,   0.0),
            "read_kb_per_sec":  max(read_kb_per_sec,  0.0),
            "write_kb_per_sec": max(write_kb_per_sec, 0.0),
            "util_pct":         max(min(util_pct, 100.0), 0.0),
        }

    def get_process_io(self, pid: int) -> Dict:
        """Return per-process I/O statistics for the given PID."""
        process = self.kernel.get_process(pid)
        if process is None:
            return {}

        # If the process has an io_stats attribute, use it
        if hasattr(process, "io_stats") and isinstance(process.io_stats, dict):
            return dict(process.io_stats)

        # Simulate per-process I/O based on memory usage as a proxy for activity
        mem = getattr(process, "memory_usage", 0)
        scale = mem / max(self.kernel.memory_manager.total_memory, 1)

        read_bytes  = int(scale * random.uniform(1024, 1024 * 1024))
        write_bytes = int(scale * random.uniform(512,  512  * 1024))

        return {
            "pid":         pid,
            "read_bytes":  read_bytes,
            "write_bytes": write_bytes,
            "read_kb_per_sec":  round(random.uniform(0.0, 50.0), 2),
            "write_kb_per_sec": round(random.uniform(0.0, 20.0), 2),
        }

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------

    def get_network_snapshot(self) -> Dict:
        """Return a snapshot of network interface statistics."""
        if self.network_manager is None:
            return {"interfaces": [], "total_rx_bytes": 0, "total_tx_bytes": 0}

        interfaces = []
        total_rx = 0
        total_tx = 0

        for iface in self.network_manager.list_interfaces():
            # Simulate traffic accumulation with jitter
            jitter_rx = int(random.uniform(0, 8192))
            jitter_tx = int(random.uniform(0, 4096))
            iface.rx_bytes += jitter_rx
            iface.tx_bytes += jitter_tx

            total_rx += iface.rx_bytes
            total_tx += iface.tx_bytes

            interfaces.append({
                "name":       iface.name,
                "state":      iface.state.value,
                "ip_address": iface.ip_address,
                "rx_bytes":   iface.rx_bytes,
                "tx_bytes":   iface.tx_bytes,
                "rx_packets": iface.rx_packets,
                "tx_packets": iface.tx_packets,
                "rx_kb_per_sec": round(jitter_rx / 1024.0, 2),
                "tx_kb_per_sec": round(jitter_tx / 1024.0, 2),
            })

        return {
            "interfaces":     interfaces,
            "total_rx_bytes": total_rx,
            "total_tx_bytes": total_tx,
        }

    # ------------------------------------------------------------------
    # Disk / Filesystem
    # ------------------------------------------------------------------

    def get_disk_snapshot(self) -> Dict:
        """Return a snapshot of filesystem usage statistics."""
        total_inodes = len(self.filesystem.inodes)
        total_size   = self.filesystem.get_size()

        # Simulated capacity figures
        capacity_bytes = 1024 * 1024 * 1024  # 1 GiB virtual disk
        free_bytes     = max(capacity_bytes - total_size, 0)
        used_pct       = round((total_size / capacity_bytes) * 100.0, 2)

        return {
            "total_bytes":  capacity_bytes,
            "used_bytes":   total_size,
            "free_bytes":   free_bytes,
            "used_pct":     used_pct,
            "total_inodes": total_inodes,
            "inode_used_pct": round((total_inodes / max(total_inodes + 1000, 1)) * 100.0, 2),
        }

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    def get_service_snapshot(self) -> List[Dict]:
        """Return health information for all registered services."""
        if self.init_system is None:
            return []

        snapshots = []
        for svc_info in self.init_system.list_services():
            name   = svc_info["name"]
            status = self.init_system.get_service_status(name)
            if status:
                snapshots.append({
                    "name":          status["name"],
                    "state":         status["state"],
                    "enabled":       status["enabled"],
                    "uptime":        status.get("uptime", 0.0),
                    "restart_count": status.get("restart_count", 0),
                    "pid":           status.get("pid"),
                })
        return snapshots

    # ------------------------------------------------------------------
    # Aggregated health
    # ------------------------------------------------------------------

    def get_system_health(self) -> Dict:
        """Return an aggregated health score and summary metrics."""
        mem  = self.get_memory_snapshot()
        cpu  = self.get_cpu_snapshot()
        disk = self.get_disk_snapshot()
        svcs = self.get_service_snapshot()

        mem_used_pct  = ((mem["total"] - mem["free"]) / max(mem["total"], 1)) * 100.0
        swap_used_pct = (mem["swap_used"] / max(mem["swap_total"], 1)) * 100.0
        failed_svcs   = [s for s in svcs if s["state"] == "failed"]
        process_count = len(self.kernel.processes)

        # Simple 0-100 health score; deductions for pressure indicators
        score = 100.0
        score -= min(mem_used_pct * 0.3, 30.0)          # Up to -30 for memory pressure
        score -= min(cpu["user_pct"] * 0.2, 20.0)       # Up to -20 for CPU usage
        score -= min(disk["used_pct"] * 0.1, 10.0)      # Up to -10 for disk usage
        score -= min(len(failed_svcs) * 5.0, 20.0)      # Up to -20 for failed services
        score -= min(max(process_count - 50, 0) * 0.5, 20.0)  # Up to -20 for process count
        score  = max(round(score, 1), 0.0)

        return {
            "health_score":    score,
            "mem_used_pct":    round(mem_used_pct, 2),
            "swap_used_pct":   round(swap_used_pct, 2),
            "cpu_user_pct":    cpu["user_pct"],
            "cpu_idle_pct":    cpu["idle_pct"],
            "disk_used_pct":   disk["used_pct"],
            "process_count":   process_count,
            "failed_services": len(failed_svcs),
            "uptime_seconds":  self.kernel.get_uptime(),
        }


# ---------------------------------------------------------------------------
# Health Checker
# ---------------------------------------------------------------------------

class HealthChecker:
    """Runs named health checks against the system and returns structured results."""

    def __init__(self, metrics_collector: MetricsCollector, kernel,
                 filesystem, init_system=None):
        self.metrics   = metrics_collector
        self.kernel    = kernel
        self.filesystem = filesystem
        self.init_system = init_system

    # ------------------------------------------------------------------
    # Individual checks — each returns (status, message)
    # ------------------------------------------------------------------

    def check_memory_pressure(self) -> Tuple[str, str]:
        """WARN if memory usage >80 %, CRIT if >95 %."""
        mem = self.metrics.get_memory_snapshot()
        used_pct = ((mem["total"] - mem["free"]) / max(mem["total"], 1)) * 100.0
        used_mb  = (mem["total"] - mem["free"]) // (1024 * 1024)
        total_mb = mem["total"] // (1024 * 1024)

        if used_pct >= 95.0:
            return ("CRIT",
                    f"Memory critically high: {used_pct:.1f}% used ({used_mb}/{total_mb} MB)")
        if used_pct >= 80.0:
            return ("WARN",
                    f"Memory pressure elevated: {used_pct:.1f}% used ({used_mb}/{total_mb} MB)")
        return ("OK", f"Memory usage normal: {used_pct:.1f}% ({used_mb}/{total_mb} MB)")

    def check_process_count(self) -> Tuple[str, str]:
        """WARN if process count >50, CRIT if >100."""
        count = len(self.kernel.processes)
        if count > 100:
            return ("CRIT", f"Process count critically high: {count} processes")
        if count > 50:
            return ("WARN", f"Process count elevated: {count} processes")
        return ("OK", f"Process count normal: {count} processes")

    def check_zombie_processes(self) -> Tuple[str, str]:
        """WARN if any TERMINATED processes remain in the process table."""
        from core.kernel import ProcessState
        zombies = [p for p in self.kernel.processes.values()
                   if p.state == ProcessState.TERMINATED]
        if zombies:
            names = ", ".join(p.name for p in zombies[:5])
            suffix = f" (+{len(zombies)-5} more)" if len(zombies) > 5 else ""
            return ("WARN",
                    f"{len(zombies)} zombie process(es) detected: {names}{suffix}")
        return ("OK", "No zombie processes")

    def check_filesystem_usage(self) -> Tuple[str, str]:
        """WARN if inode count >500, CRIT if >1000."""
        inode_count = len(self.filesystem.inodes)
        if inode_count > 1000:
            return ("CRIT",
                    f"Filesystem inode count critically high: {inode_count} inodes")
        if inode_count > 500:
            return ("WARN",
                    f"Filesystem inode count elevated: {inode_count} inodes")
        return ("OK", f"Filesystem usage normal: {inode_count} inodes")

    def check_service_health(self) -> Tuple[str, str]:
        """WARN if any services are in a FAILED state."""
        if self.init_system is None:
            return ("INFO", "Init system not available; service check skipped")

        failed = [s for s in self.init_system.list_services()
                  if s["state"] == "failed"]
        if failed:
            names = ", ".join(s["name"] for s in failed[:5])
            suffix = f" (+{len(failed)-5} more)" if len(failed) > 5 else ""
            return ("WARN", f"{len(failed)} failed service(s): {names}{suffix}")
        return ("OK", "All services healthy")

    def check_uptime(self) -> Tuple[str, str]:
        """INFO-only: reports system uptime."""
        uptime_s = self.kernel.get_uptime()
        hours    = int(uptime_s // 3600)
        minutes  = int((uptime_s % 3600) // 60)
        seconds  = int(uptime_s % 60)
        return ("INFO",
                f"System uptime: {hours}h {minutes}m {seconds}s ({uptime_s:.1f}s total)")

    def check_swap_usage(self) -> Tuple[str, str]:
        """WARN if swap usage >50 %."""
        mem = self.metrics.get_memory_snapshot()
        swap_pct = (mem["swap_used"] / max(mem["swap_total"], 1)) * 100.0
        swap_used_mb  = mem["swap_used"]  // (1024 * 1024)
        swap_total_mb = mem["swap_total"] // (1024 * 1024)

        if swap_pct >= 50.0:
            return ("WARN",
                    f"Swap usage elevated: {swap_pct:.1f}% ({swap_used_mb}/{swap_total_mb} MB)")
        return ("OK",
                f"Swap usage normal: {swap_pct:.1f}% ({swap_used_mb}/{swap_total_mb} MB)")

    def check_io_pressure(self) -> Tuple[str, str]:
        """WARN if write throughput exceeds 10,000 KB/s."""
        io = self.metrics.get_io_snapshot()
        write_kb = io.get("write_kb_per_sec", 0.0)

        if write_kb > 10000.0:
            return ("WARN",
                    f"I/O write pressure elevated: {write_kb:.1f} KB/s")
        return ("OK", f"I/O write throughput normal: {write_kb:.1f} KB/s")

    # ------------------------------------------------------------------
    # Run all checks
    # ------------------------------------------------------------------

    def run_all_checks(self) -> List[Tuple[str, str, str]]:
        """Run every health check and return a list of (check_name, status, message)."""
        checks = [
            ("memory_pressure",   self.check_memory_pressure),
            ("process_count",     self.check_process_count),
            ("zombie_processes",  self.check_zombie_processes),
            ("filesystem_usage",  self.check_filesystem_usage),
            ("service_health",    self.check_service_health),
            ("uptime",            self.check_uptime),
            ("swap_usage",        self.check_swap_usage),
            ("io_pressure",       self.check_io_pressure),
        ]

        results: List[Tuple[str, str, str]] = []
        for check_name, check_fn in checks:
            try:
                status, message = check_fn()
            except Exception as exc:
                status  = "CRIT"
                message = f"Check raised exception: {exc}"
            results.append((check_name, status, message))

        return results


# ---------------------------------------------------------------------------
# Performance Profiler
# ---------------------------------------------------------------------------

class PerfProfiler:
    """Extracts and summarises syscall performance data from processes."""

    def __init__(self, kernel):
        self.kernel = kernel

    def get_profile(self, pid: Optional[int] = None) -> Dict:
        """Return syscall statistics for one process or all processes.

        Reads ``Process.syscall_log`` when it exists (list of dicts with at
        minimum ``name`` and optionally ``duration`` keys).  Falls back to
        simulated data for processes that have no log.
        """
        if pid is not None:
            process = self.kernel.get_process(pid)
            if process is None:
                return {}
            return self._profile_one(process)

        # Aggregate across all processes
        all_calls: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_duration": 0.0, "min_duration": float("inf"),
                     "max_duration": 0.0}
        )

        for process in self.kernel.list_processes():
            single = self._profile_one(process)
            for syscall, stats in single.get("syscalls", {}).items():
                agg = all_calls[syscall]
                agg["count"]          += stats["count"]
                agg["total_duration"] += stats["total_duration"]
                agg["min_duration"]    = min(agg["min_duration"], stats["min_duration"])
                agg["max_duration"]    = max(agg["max_duration"], stats["max_duration"])

        # Replace inf for calls with no duration data
        for stats in all_calls.values():
            if stats["min_duration"] == float("inf"):
                stats["min_duration"] = 0.0
            if stats["count"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["count"]
            else:
                stats["avg_duration"] = 0.0

        return {
            "scope":    "system",
            "syscalls": dict(all_calls),
        }

    def _profile_one(self, process) -> Dict:
        """Build a profile dict for a single Process object."""
        syscall_log = getattr(process, "syscall_log", None)

        if syscall_log and isinstance(syscall_log, list) and len(syscall_log) > 0:
            # Real data path
            aggregated: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "total_duration": 0.0,
                         "min_duration": float("inf"), "max_duration": 0.0}
            )
            for entry in syscall_log:
                if not isinstance(entry, dict):
                    continue
                name     = entry.get("name", "unknown")
                duration = float(entry.get("duration", 0.0))
                agg = aggregated[name]
                agg["count"]          += 1
                agg["total_duration"] += duration
                agg["min_duration"]    = min(agg["min_duration"], duration)
                agg["max_duration"]    = max(agg["max_duration"], duration)

            for stats in aggregated.values():
                if stats["min_duration"] == float("inf"):
                    stats["min_duration"] = 0.0
                stats["avg_duration"] = (stats["total_duration"] /
                                         max(stats["count"], 1))

            return {
                "pid":      process.pid,
                "name":     process.name,
                "syscalls": dict(aggregated),
            }

        # Simulated data path — generate plausible syscall mix
        common_syscalls = ["read", "write", "open", "close", "stat",
                           "mmap", "brk", "futex", "poll", "ioctl"]
        syscalls: Dict[str, Dict[str, Any]] = {}
        cpu_time = max(getattr(process, "cpu_time", 0.0), 0.0)

        for syscall in random.sample(common_syscalls,
                                     k=random.randint(3, len(common_syscalls))):
            count          = random.randint(1, 200)
            avg_us         = random.uniform(0.001, 2.0)          # milliseconds
            total_duration = avg_us * count
            jitter         = random.uniform(0.8, 1.2)
            syscalls[syscall] = {
                "count":          count,
                "total_duration": round(total_duration * jitter,   4),
                "avg_duration":   round(avg_us,                     4),
                "min_duration":   round(avg_us * random.uniform(0.1, 0.5), 4),
                "max_duration":   round(avg_us * random.uniform(1.5, 5.0), 4),
            }

        return {
            "pid":      process.pid,
            "name":     process.name,
            "cpu_time": cpu_time,
            "syscalls": syscalls,
        }

    def summarize_syscalls(self, pid: int) -> List[Dict]:
        """Return the top syscalls for a process, sorted by call frequency.

        Each entry in the returned list contains:
        ``name``, ``count``, ``total_duration``, ``avg_duration``,
        ``min_duration``, ``max_duration``.
        """
        profile = self.get_profile(pid)
        if not profile:
            return []

        rows = []
        for name, stats in profile.get("syscalls", {}).items():
            rows.append({
                "name":           name,
                "count":          stats["count"],
                "total_duration": stats["total_duration"],
                "avg_duration":   stats["avg_duration"],
                "min_duration":   stats["min_duration"],
                "max_duration":   stats["max_duration"],
            })

        # Sort by frequency descending, then by total duration descending
        rows.sort(key=lambda r: (r["count"], r["total_duration"]), reverse=True)
        return rows
