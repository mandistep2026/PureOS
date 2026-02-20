"""
PureOS Monitor Commands
Commands for system monitoring: memory, I/O, CPU statistics, and diagnostics.
"""

import time
import sys
import json
from typing import List
from core.metrics import MetricsCollector, HealthChecker, PerfProfiler

from shell.shell import ShellCommand


class FreeEnhancedCommand(ShellCommand):
    """Display amount of free and used memory with full swap and buffer/cache support."""

    def __init__(self):
        super().__init__("free", "Display amount of free and used memory in the system")

    def execute(self, args: List[str], shell) -> int:
        # Parse flags
        show_bytes    = '-b' in args
        show_kilobytes = '-k' in args
        show_megabytes = '-m' in args
        show_gigabytes = '-g' in args
        human_readable = '-h' in args
        show_totals    = '-t' in args
        wide           = '-w' in args

        # Repeating interval support: -s <sec>
        interval = None
        i = 0
        while i < len(args):
            if args[i] == '-s' and i + 1 < len(args):
                try:
                    interval = float(args[i + 1])
                except ValueError:
                    print("free: invalid argument for -s")
                    return 1
                i += 2
                continue
            i += 1

        def _print_once():
            info = shell.kernel.get_system_info()
            total = info["total_memory"]
            used  = info["used_memory"]
            free  = info["free_memory"]

            # Simulated values
            buff_cache = used // 4          # 25% of used
            available  = free + buff_cache
            shared     = max(1024, used // 100)  # small simulated value

            # Swap: fixed simulated values (512 MB total, mostly free)
            swap_total = 512 * 1024 * 1024
            swap_used  = 2 * 1024 * 1024
            swap_free  = swap_total - swap_used

            def fmt(b: int) -> str:
                if human_readable:
                    for unit in ['B', 'K', 'M', 'G', 'T']:
                        if abs(b) < 1024:
                            return f"{b:.1f}{unit}"
                        b /= 1024
                    return f"{b:.1f}P"
                elif show_bytes:
                    return str(int(b * 1))          # already bytes
                elif show_megabytes:
                    return str(b // (1024 * 1024))
                elif show_gigabytes:
                    return str(b // (1024 * 1024 * 1024))
                else:
                    # Default: kilobytes
                    return str(b // 1024)

            if wide:
                # Wide format: separate buffers and cache columns
                header = f"{'':>14} {'total':>12} {'used':>12} {'free':>12} {'shared':>12} {'buffers':>12} {'cache':>12} {'available':>12}"
                mem_line = (
                    f"{'Mem:':>14}"
                    f" {fmt(total):>12}"
                    f" {fmt(used):>12}"
                    f" {fmt(free):>12}"
                    f" {fmt(shared):>12}"
                    f" {fmt(buff_cache // 2):>12}"
                    f" {fmt(buff_cache // 2):>12}"
                    f" {fmt(available):>12}"
                )
            else:
                header = f"{'':>14} {'total':>12} {'used':>12} {'free':>12} {'shared':>12} {'buff/cache':>12} {'available':>12}"
                mem_line = (
                    f"{'Mem:':>14}"
                    f" {fmt(total):>12}"
                    f" {fmt(used):>12}"
                    f" {fmt(free):>12}"
                    f" {fmt(shared):>12}"
                    f" {fmt(buff_cache):>12}"
                    f" {fmt(available):>12}"
                )

            swap_line = (
                f"{'Swap:':>14}"
                f" {fmt(swap_total):>12}"
                f" {fmt(swap_used):>12}"
                f" {fmt(swap_free):>12}"
            )

            print(header)
            print(mem_line)
            print(swap_line)

            if show_totals:
                total_total = total + swap_total
                total_used  = used  + swap_used
                total_free  = free  + swap_free
                total_line = (
                    f"{'Total:':>14}"
                    f" {fmt(total_total):>12}"
                    f" {fmt(total_used):>12}"
                    f" {fmt(total_free):>12}"
                )
                print(total_line)

        if interval is not None:
            try:
                while True:
                    _print_once()
                    print()
                    time.sleep(interval)
            except KeyboardInterrupt:
                print()
        else:
            _print_once()

        return 0


class IostatCommand(ShellCommand):
    """Display I/O statistics."""

    def __init__(self):
        super().__init__("iostat", "Report CPU and I/O statistics")

    def execute(self, args: List[str], shell) -> int:
        cpu_only    = '-c' in args
        device_only = '-d' in args
        extended    = '-x' in args
        use_kb      = '-k' in args
        use_mb      = '-m' in args

        # Parse positional: [interval [count]]
        positional = [a for a in args if not a.startswith('-')]
        interval = None
        count    = None
        if positional:
            try:
                interval = float(positional[0])
            except ValueError:
                pass
        if len(positional) >= 2:
            try:
                count = int(positional[1])
            except ValueError:
                pass

        try:
            collector = MetricsCollector(shell.kernel, shell.fs)
        except Exception as e:
            print(f"iostat: metrics collector unavailable: {e}")
            return 1

        def _print_once(iteration: int):
            try:
                cpu_snap = collector.get_cpu_snapshot()
            except Exception:
                cpu_snap = {}

            try:
                io_stats = collector.get_io_stats()
            except Exception:
                io_stats = {}

            # --- CPU section ---
            if not device_only:
                usr    = cpu_snap.get('user',    12.50)
                nice   = cpu_snap.get('nice',     0.00)
                system = cpu_snap.get('system',   3.20)
                iowait = cpu_snap.get('iowait',   1.10)
                steal  = cpu_snap.get('steal',    0.00)
                idle   = cpu_snap.get('idle',    83.20)

                print("avg-cpu:  %user   %nice %system %iowait  %steal   %idle")
                print(f"          {usr:6.2f}  {nice:6.2f}  {system:6.2f}  {iowait:6.2f}  {steal:6.2f}  {idle:6.2f}")
                print()

            # --- Device section ---
            if not cpu_only:
                unit_label = "MB" if use_mb else "kB"
                divisor    = 1024 if use_mb else 1

                if extended:
                    print(f"{'Device':<12} {'r/s':>8} {'w/s':>8} {'rkB/s':>10} {'wkB/s':>10} {'await':>8} {'%util':>8}")
                    print("-" * 70)
                else:
                    print(f"{'Device':<12} {'tps':>8} {f'{unit_label}_read/s':>12} {f'{unit_label}_wrtn/s':>12} {f'{unit_label}_read':>12} {f'{unit_label}_wrtn':>12}")
                    print("-" * 70)

                devices = io_stats.get('devices', {}) if io_stats else {}

                if not devices:
                    # Simulated default device
                    devices = {
                        'vda': {
                            'tps':       5.23,
                            'read_s':  128.40,
                            'write_s':  64.20,
                            'read_kb':  2048,
                            'write_kb': 1024,
                            'await':     4.20,
                            'util':      2.10,
                        }
                    }

                for dev_name, stats in devices.items():
                    if extended:
                        r_s   = stats.get('tps',       0) / 2
                        w_s   = stats.get('tps',       0) / 2
                        rkb_s = stats.get('read_s',    0)
                        wkb_s = stats.get('write_s',   0)
                        await_ = stats.get('await',    0.0)
                        util  = stats.get('util',      0.0)
                        print(f"{dev_name:<12} {r_s:>8.2f} {w_s:>8.2f} {rkb_s:>10.2f} {wkb_s:>10.2f} {await_:>8.2f} {util:>8.2f}")
                    else:
                        tps     = stats.get('tps',      0)
                        read_s  = stats.get('read_s',   0) / divisor
                        write_s = stats.get('write_s',  0) / divisor
                        read_kb = stats.get('read_kb',  0) // divisor
                        write_kb = stats.get('write_kb', 0) // divisor
                        print(f"{dev_name:<12} {tps:>8.2f} {read_s:>12.2f} {write_s:>12.2f} {read_kb:>12} {write_kb:>12}")

        if interval is not None:
            iterations = 0
            try:
                while count is None or iterations < count:
                    _print_once(iterations)
                    iterations += 1
                    if count is None or iterations < count:
                        print()
                        time.sleep(interval)
            except KeyboardInterrupt:
                print()
        else:
            _print_once(0)

        return 0


class MpstatCommand(ShellCommand):
    """Display per-CPU statistics."""

    def __init__(self):
        super().__init__("mpstat", "Report processors related statistics")

    def execute(self, args: List[str], shell) -> int:
        show_util   = '-u' in args
        show_irq    = '-I' in args
        show_all    = '-A' in args
        cpu_filter  = None  # which CPU(s) to show

        # Parse -P <num|ALL>
        i = 0
        while i < len(args):
            if args[i] == '-P' and i + 1 < len(args):
                cpu_filter = args[i + 1].upper()
                i += 2
                continue
            i += 1

        # Parse positional: [interval [count]]
        positional = [a for a in args if not a.startswith('-') and a != (cpu_filter or '')]
        interval = None
        count    = None
        if positional:
            try:
                interval = float(positional[0])
            except ValueError:
                pass
        if len(positional) >= 2:
            try:
                count = int(positional[1])
            except ValueError:
                pass

        try:
            collector = MetricsCollector(shell.kernel, shell.fs)
        except Exception as e:
            print(f"mpstat: metrics collector unavailable: {e}")
            return 1

        # PureOS system identification header
        hostname  = shell.environment.get('HOSTNAME', 'pureos')
        kern_ver  = "1.0"
        arch      = "x86_64"
        num_cpu   = 1  # PureOS has 1 CPU

        def _print_once():
            date_str = time.strftime('%m/%d/%Y')
            print(f"Linux {kern_ver} ({hostname})   {date_str}   _{arch}_   ({num_cpu} CPU)")
            print()

            try:
                cpu_snap = collector.get_cpu_snapshot()
            except Exception:
                cpu_snap = {}

            usr    = cpu_snap.get('user',     12.50)
            nice   = cpu_snap.get('nice',      0.00)
            sys_   = cpu_snap.get('system',    3.20)
            iowait = cpu_snap.get('iowait',    1.10)
            irq    = cpu_snap.get('irq',       0.50)
            soft   = cpu_snap.get('softirq',   0.20)
            steal  = cpu_snap.get('steal',     0.00)
            idle   = cpu_snap.get('idle',     82.50)

            time_str = time.strftime('%H:%M:%S')

            print(f"{'Time':>10}  {'CPU':>4}  {'%usr':>6}  {'%nice':>6}  {'%sys':>6}  {'%iowait':>8}  {'%irq':>6}  {'%soft':>6}  {'%steal':>6}  {'%idle':>6}")

            # Determine which CPUs to show
            show_all_cpus = (cpu_filter == 'ALL' or show_all)

            # Always show aggregate 'all' row unless a specific CPU is requested
            if cpu_filter is None or cpu_filter == 'ALL' or show_all:
                print(f"{time_str:>10}  {'all':>4}  {usr:>6.2f}  {nice:>6.2f}  {sys_:>6.2f}  {iowait:>8.2f}  {irq:>6.2f}  {soft:>6.2f}  {steal:>6.2f}  {idle:>6.2f}")

            if show_all_cpus:
                # PureOS only has CPU 0
                print(f"{time_str:>10}  {'0':>4}  {usr:>6.2f}  {nice:>6.2f}  {sys_:>6.2f}  {iowait:>8.2f}  {irq:>6.2f}  {soft:>6.2f}  {steal:>6.2f}  {idle:>6.2f}")
            elif cpu_filter is not None and cpu_filter not in ('ALL',):
                # Specific CPU requested
                try:
                    cpu_num = int(cpu_filter)
                    if cpu_num == 0:
                        print(f"{time_str:>10}  {cpu_num:>4}  {usr:>6.2f}  {nice:>6.2f}  {sys_:>6.2f}  {iowait:>8.2f}  {irq:>6.2f}  {soft:>6.2f}  {steal:>6.2f}  {idle:>6.2f}")
                    else:
                        print(f"mpstat: CPU {cpu_num} not available (system has {num_cpu} CPU)")
                        return
                except ValueError:
                    pass

            if show_irq or show_all:
                print()
                print(f"{'Time':>10}  {'CPU':>4}  {'intr/s':>10}")
                simulated_intr = 250.0
                print(f"{time_str:>10}  {'all':>4}  {simulated_intr:>10.2f}")
                if show_all_cpus:
                    print(f"{time_str:>10}  {'0':>4}  {simulated_intr:>10.2f}")

        if interval is not None:
            iterations = 0
            try:
                while count is None or iterations < count:
                    _print_once()
                    iterations += 1
                    if count is None or iterations < count:
                        print()
                        time.sleep(interval)
            except KeyboardInterrupt:
                print()
        else:
            _print_once()

        return 0


class SysdiagCommand(ShellCommand):
    """Run system diagnostics."""

    def __init__(self):
        super().__init__("sysdiag", "Run PureOS system diagnostics")

    def execute(self, args: List[str], shell) -> int:
        quiet   = '-q' in args
        verbose = '-v' in args
        fix     = '--fix' in args

        # Parse --category <name>
        category_filter = None
        i = 0
        while i < len(args):
            if args[i] == '--category' and i + 1 < len(args):
                category_filter = args[i + 1].upper()
                i += 2
                continue
            i += 1

        try:
            checker = HealthChecker(shell.kernel)
        except Exception as e:
            print(f"sysdiag: health checker unavailable: {e}")
            return 1

        if not quiet:
            print("PureOS System Diagnostics Report")
            print(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

        # Run all checks
        try:
            results = checker.run_all_checks()
        except Exception as e:
            print(f"sysdiag: error running checks: {e}")
            return 1

        crit_count = 0
        warn_count = 0
        ok_count   = 0

        # Group results by category
        categories: dict = {}
        for result in results:
            cat = result.get('category', 'GENERAL').upper()
            categories.setdefault(cat, []).append(result)

        # If filtering by category, restrict output
        if category_filter:
            filtered = {k: v for k, v in categories.items() if k == category_filter}
            if not filtered:
                print(f"sysdiag: no checks found for category '{category_filter}'")
                return 1
            categories = filtered

        for cat_name in sorted(categories.keys()):
            checks = categories[cat_name]

            if not quiet:
                print(f"[{cat_name}]")

            for check in checks:
                status  = check.get('status', 'OK').upper()
                message = check.get('message', '')
                detail  = check.get('detail', '')

                if status == 'CRIT' or status == 'CRITICAL':
                    status = 'CRIT'
                    crit_count += 1
                    symbol = '✗ CRIT'
                elif status == 'WARN' or status == 'WARNING':
                    status = 'WARN'
                    warn_count += 1
                    symbol = '⚠ WARN'
                else:
                    ok_count += 1
                    symbol = '✓ OK  '

                if not quiet:
                    print(f"  {symbol} {message}")
                    if verbose and detail:
                        print(f"         Detail: {detail}")

                # Attempt fix if requested and check provides a fix action
                if fix and status in ('CRIT', 'WARN'):
                    fix_fn = check.get('fix')
                    if callable(fix_fn):
                        try:
                            fix_fn()
                            if not quiet:
                                print(f"         [FIX] Applied fix for: {message}")
                        except Exception as fix_err:
                            if not quiet:
                                print(f"         [FIX] Failed: {fix_err}")

            if not quiet:
                print()

        if not quiet:
            print(f"Summary: {crit_count} CRIT, {warn_count} WARN, {ok_count} OK")

        # Return 1 if any CRIT, 0 otherwise
        return 1 if crit_count > 0 else 0


class SyshealthCommand(ShellCommand):
    """System health dashboard."""

    def __init__(self):
        super().__init__("syshealth", "Display PureOS system health dashboard")

    def execute(self, args: List[str], shell) -> int:
        brief    = '--brief' in args
        as_json  = '--json'  in args
        watch    = '--watch' in args
        show_cpu = '--cpu'   in args
        show_mem = '--mem'   in args
        show_disk = '--disk' in args
        show_net = '--net'   in args
        show_svc = '--svc'   in args

        # If no section flags given, show all sections
        any_section = show_cpu or show_mem or show_disk or show_net or show_svc
        if not any_section:
            show_cpu = show_mem = show_disk = show_net = show_svc = True

        # Build subsystem objects
        try:
            init_sys = getattr(shell.kernel, 'init_system', None)
            net_mgr  = getattr(shell, 'network_manager', None)
            collector = MetricsCollector(
                shell.kernel, shell.fs,
                network_manager=net_mgr,
                init_system=init_sys,
            )
            checker = HealthChecker(
                collector, shell.kernel, shell.fs,
                init_system=init_sys,
            )
        except Exception as e:
            print(f"syshealth: unable to initialise metrics: {e}")
            return 1

        def _progress_bar(pct: float, width: int = 20) -> str:
            filled = int(round(pct / 100.0 * width))
            filled = max(0, min(width, filled))
            return '█' * filled + '░' * (width - filled)

        def _status_tag(status: str) -> str:
            s = status.upper()
            if s == 'CRIT':
                return '[CRIT]'
            if s == 'WARN':
                return '[WARN]'
            return '[OK]'

        def _collect_data():
            hostname = shell.environment.get('HOSTNAME', 'pureos')
            uptime_s = shell.kernel.get_uptime()
            h = int(uptime_s // 3600)
            m = int((uptime_s % 3600) // 60)
            s = int(uptime_s % 60)
            uptime_str = f"{h}h {m}m {s}s"
            now_str = time.strftime('%Y-%m-%d %H:%M:%S')

            mem_snap  = collector.get_memory_snapshot()
            cpu_snap  = collector.get_cpu_snapshot()
            disk_snap = collector.get_disk_snapshot()
            net_snap  = collector.get_network_snapshot()
            svc_snap  = collector.get_service_snapshot()

            cpu_pct  = cpu_snap.get('user_pct', 0.0) + cpu_snap.get('sys_pct', 0.0)
            mem_total = mem_snap['total']
            mem_used  = mem_snap['used']
            mem_pct   = (mem_used / max(mem_total, 1)) * 100.0
            swap_total = mem_snap['swap_total']
            swap_used  = mem_snap['swap_used']
            swap_pct   = (swap_used / max(swap_total, 1)) * 100.0
            disk_pct   = disk_snap['used_pct']

            # Network: first interface, or zeros
            net_ifaces = net_snap.get('interfaces', [])
            if net_ifaces:
                iface = net_ifaces[0]
                net_name = iface['name']
                net_tx   = iface.get('tx_kb_per_sec', 0.0)
                net_rx   = iface.get('rx_kb_per_sec', 0.0)
            else:
                net_name, net_tx, net_rx = 'eth0', 0.0, 0.0

            active_svcs = sum(1 for s in svc_snap if s.get('state') == 'running')
            failed_svcs = sum(1 for s in svc_snap if s.get('state') == 'failed')

            # Health statuses
            _, cpu_msg  = checker.check_memory_pressure()   # proxy
            cpu_status  = 'OK' if cpu_pct < 80 else ('WARN' if cpu_pct < 95 else 'CRIT')
            mem_st, _   = checker.check_memory_pressure()
            swap_st, _  = checker.check_swap_usage()
            disk_st, _  = checker.check_filesystem_usage()
            svc_st, _   = checker.check_service_health()
            net_status  = 'OK'

            return {
                'hostname': hostname,
                'uptime': uptime_str,
                'now': now_str,
                'cpu_pct': round(cpu_pct, 1),
                'cpu_status': cpu_status,
                'mem_pct': round(mem_pct, 1),
                'mem_status': mem_st,
                'swap_pct': round(swap_pct, 1),
                'swap_status': swap_st,
                'disk_pct': round(disk_pct, 1),
                'disk_status': disk_st,
                'net_name': net_name,
                'net_tx': net_tx,
                'net_rx': net_rx,
                'net_status': net_status,
                'active_svcs': active_svcs,
                'failed_svcs': failed_svcs,
                'svc_status': svc_st,
            }

        def _print_dashboard(d):
            W = 54  # inner width
            border_top    = '╔' + '═' * W + '╗'
            border_mid    = '╠' + '═' * W + '╣'
            border_bottom = '╚' + '═' * W + '╝'

            def row(text):
                # Pad/truncate to exactly W chars
                text = text[:W]
                print('║' + text.ljust(W) + '║')

            print(border_top)
            row('         PureOS System Health Dashboard               ')
            row(f"  {d['hostname']} | uptime: {d['uptime']} | {d['now']}  ")
            print(border_mid)

            if show_cpu:
                bar = _progress_bar(d['cpu_pct'])
                tag = _status_tag(d['cpu_status'])
                row(f" CPU      {bar}  {d['cpu_pct']:5.1f}%  {tag}          ")

            if show_mem:
                bar = _progress_bar(d['mem_pct'])
                tag = _status_tag(d['mem_status'])
                row(f" Memory   {bar}  {d['mem_pct']:5.1f}%  {tag}          ")
                bar = _progress_bar(d['swap_pct'])
                tag = _status_tag(d['swap_status'])
                row(f" Swap     {bar}  {d['swap_pct']:5.1f}%  {tag}          ")

            if show_disk:
                bar = _progress_bar(d['disk_pct'])
                tag = _status_tag(d['disk_status'])
                row(f" Disk     {bar}  {d['disk_pct']:5.1f}%  {tag}          ")

            if show_net:
                tag = _status_tag(d['net_status'])
                net_str = (f" Network  {d['net_name']} "
                           f"\u2191{d['net_tx']:.1f}KB/s "
                           f"\u2193{d['net_rx']:.1f}KB/s      {tag}          ")
                row(net_str)

            if show_svc:
                tag = _status_tag(d['svc_status'])
                svc_str = (f" Services {d['active_svcs']} active, "
                           f"{d['failed_svcs']} failed           {tag}          ")
                row(svc_str)

            print(border_bottom)

        def _print_brief(d):
            lines = []
            if show_cpu:
                lines.append(f"CPU: {d['cpu_pct']}% {_status_tag(d['cpu_status'])}")
            if show_mem:
                lines.append(f"Mem: {d['mem_pct']}% {_status_tag(d['mem_status'])}")
                lines.append(f"Swap: {d['swap_pct']}% {_status_tag(d['swap_status'])}")
            if show_disk:
                lines.append(f"Disk: {d['disk_pct']}% {_status_tag(d['disk_status'])}")
            if show_net:
                lines.append(
                    f"Net: {d['net_name']} "
                    f"\u2191{d['net_tx']:.1f}KB/s \u2193{d['net_rx']:.1f}KB/s "
                    f"{_status_tag(d['net_status'])}"
                )
            if show_svc:
                lines.append(
                    f"Svc: {d['active_svcs']} active, "
                    f"{d['failed_svcs']} failed {_status_tag(d['svc_status'])}"
                )
            print('  '.join(lines))

        def _print_json(d):
            print(json.dumps(d, indent=2))

        def _render(d):
            if as_json:
                _print_json(d)
            elif brief:
                _print_brief(d)
            else:
                _print_dashboard(d)

        def _any_crit(d):
            for key in ('cpu_status', 'mem_status', 'swap_status',
                        'disk_status', 'net_status', 'svc_status'):
                if d.get(key, '').upper() == 'CRIT':
                    return True
            return False

        if watch:
            try:
                while True:
                    print("\033[2J\033[H", end="")
                    d = _collect_data()
                    _render(d)
                    time.sleep(3)
            except KeyboardInterrupt:
                print()
            return 0
        else:
            d = _collect_data()
            _render(d)
            return 1 if _any_crit(d) else 0


class PerfCommand(ShellCommand):
    """Performance profiler."""

    def __init__(self):
        super().__init__("perf", "Performance analysis tool")

    def execute(self, args: List[str], shell) -> int:
        if not args:
            print("Usage: perf {stat|top|record|report} [pid] [-e <event>] [-n <count>]")
            return 1

        subcommand = args[0]
        rest = args[1:]

        try:
            profiler = PerfProfiler(shell.kernel)
        except Exception as e:
            print(f"perf: profiler unavailable: {e}")
            return 1

        # ----------------------------------------------------------------
        # perf stat [pid] [-e <event>] [-n <count>]
        # ----------------------------------------------------------------
        if subcommand == 'stat':
            pid = None
            event_filter = None
            duration = 5.0

            i = 0
            while i < len(rest):
                if rest[i] == '-e' and i + 1 < len(rest):
                    event_filter = rest[i + 1]
                    i += 2
                    continue
                if rest[i] == '-n' and i + 1 < len(rest):
                    try:
                        duration = float(rest[i + 1])
                    except ValueError:
                        pass
                    i += 2
                    continue
                # Positional: PID
                try:
                    pid = int(rest[i])
                except ValueError:
                    pass
                i += 1

            # Resolve process name
            proc_name = 'system'
            if pid is not None:
                proc = shell.kernel.get_process(pid)
                if proc is None:
                    print(f"perf stat: no process with PID {pid}")
                    return 1
                proc_name = proc.name

            # Collect profile
            try:
                profile = profiler.get_profile(pid)
            except Exception as e:
                print(f"perf stat: error collecting profile: {e}")
                return 1

            syscalls = profile.get('syscalls', {})

            # Apply event filter
            if event_filter:
                syscalls = {k: v for k, v in syscalls.items()
                            if event_filter.lower() in k.lower()}

            # Sort by count descending
            sorted_calls = sorted(syscalls.items(),
                                  key=lambda kv: kv[1]['count'], reverse=True)

            if pid is not None:
                print(f"\nPerformance counter stats for PID {pid} ({proc_name}):\n")
            else:
                print(f"\nPerformance counter stats for {proc_name}:\n")

            total_count = sum(v['count'] for _, v in sorted_calls)
            for name, stats in sorted_calls:
                count = stats['count']
                rate  = count / max(duration, 0.001)
                count_fmt = f"{count:,}"
                print(f"  {count_fmt:>12}  {name:<24}  #  {rate:>8.1f} /sec")

            print(f"\n       {duration:.3f} seconds time elapsed\n")
            return 0

        # ----------------------------------------------------------------
        # perf top
        # ----------------------------------------------------------------
        elif subcommand == 'top':
            print(f"{'PID':<8} {'COMM':<14} {'SYSCALL':<17} {'COUNT':>8}    {'%TIME':>6}")

            try:
                while True:
                    # Collect fresh snapshot across all processes
                    all_rows = []
                    for proc in shell.kernel.list_processes():
                        try:
                            profile = profiler.get_profile(proc.pid)
                        except Exception:
                            continue
                        for sc_name, stats in profile.get('syscalls', {}).items():
                            all_rows.append({
                                'pid':   proc.pid,
                                'comm':  proc.name,
                                'syscall': sc_name,
                                'count': stats['count'],
                                'total_duration': stats['total_duration'],
                            })

                    # Compute %TIME from total_duration shares
                    total_dur = sum(r['total_duration'] for r in all_rows) or 1.0
                    all_rows.sort(key=lambda r: r['total_duration'], reverse=True)

                    # Print top rows (overwrite previous output)
                    for row in all_rows[:20]:
                        pct = (row['total_duration'] / total_dur) * 100.0
                        print(f"  {row['pid']:<6} {row['comm']:<14} {row['syscall']:<17} "
                              f"{row['count']:>8}    {pct:>5.1f}%")

                    time.sleep(2)

            except KeyboardInterrupt:
                print()
            return 0

        # ----------------------------------------------------------------
        # perf record [pid]
        # ----------------------------------------------------------------
        elif subcommand == 'record':
            pid = None
            i = 0
            while i < len(rest):
                try:
                    pid = int(rest[i])
                except ValueError:
                    pass
                i += 1

            if pid is not None:
                proc = shell.kernel.get_process(pid)
                if proc is None:
                    print(f"perf record: no process with PID {pid}")
                    return 1
                print(f"[ perf record: Woken up 1 times to write data ]")
                print(f"[ perf record: Captured and wrote 0.024 MB perf.data "
                      f"({profiler.get_profile(pid).get('syscalls', {}).__len__()} samples) ]")
            else:
                total_procs = len(list(shell.kernel.list_processes()))
                print(f"[ perf record: Woken up 1 times to write data ]")
                print(f"[ perf record: Captured and wrote 0.048 MB perf.data "
                      f"({total_procs * 10} samples) ]")
            return 0

        # ----------------------------------------------------------------
        # perf report
        # ----------------------------------------------------------------
        elif subcommand == 'report':
            print("# ========================================")
            print("# captured on: " + time.strftime('%a %b %d %H:%M:%S %Y'))
            print("# hostname   : " + shell.environment.get('HOSTNAME', 'pureos'))
            print("# ========================================")
            print("#")
            print(f"# {'Overhead':>8}  {'Command':<16}  {'Shared Object':<20}  Symbol")
            print("# ........  ................  ....................  .........")

            # Aggregate across all processes
            try:
                profile = profiler.get_profile(None)
            except Exception as e:
                print(f"perf report: error: {e}")
                return 1

            syscalls = profile.get('syscalls', {})
            total_dur = sum(v['total_duration'] for v in syscalls.values()) or 1.0
            sorted_calls = sorted(syscalls.items(),
                                  key=lambda kv: kv[1]['total_duration'], reverse=True)

            for name, stats in sorted_calls:
                overhead = (stats['total_duration'] / total_dur) * 100.0
                print(f"  {overhead:>7.2f}%  {'[kernel]':<16}  {'[vdso]':<20}  [k] {name}")

            print()
            return 0

        else:
            print(f"perf: unknown subcommand '{subcommand}'")
            print("Usage: perf {stat|top|record|report} [pid] [-e <event>] [-n <count>]")
            return 1


class HtopCommand(ShellCommand):
    """Interactive real-time process monitor."""

    def __init__(self):
        super().__init__("htop", "Interactive process viewer")

    def execute(self, args: List[str], shell) -> int:
        # ----------------------------------------------------------------
        # Parse arguments
        # ----------------------------------------------------------------
        delay    = 10          # tenths of a second (default 1.0 s)
        pid_filter: List[int] = []
        sort_col = 'cpu'       # default sort column
        user_filter = None
        no_color = '--no-color' in args

        i = 0
        while i < len(args):
            if args[i] == '-d' and i + 1 < len(args):
                try:
                    delay = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
                continue
            if args[i] == '-p' and i + 1 < len(args):
                for part in args[i + 1].split(','):
                    try:
                        pid_filter.append(int(part.strip()))
                    except ValueError:
                        pass
                i += 2
                continue
            if args[i] == '-s' and i + 1 < len(args):
                sort_col = args[i + 1].lower()
                i += 2
                continue
            if args[i] == '-u' and i + 1 < len(args):
                user_filter = args[i + 1]
                i += 2
                continue
            i += 1

        # ANSI colour helpers
        def _c(code: str, text: str) -> str:
            if no_color:
                return text
            return f"\033[{code}m{text}\033[0m"

        def _progress_bar(pct: float, width: int = 20) -> str:
            filled = int(round(pct / 100.0 * width))
            filled = max(0, min(width, filled))
            bar = '█' * filled + '░' * (width - filled)
            if no_color:
                return bar
            colour = '32' if pct < 60 else ('33' if pct < 85 else '31')
            return f"\033[{colour}m{bar}\033[0m"

        # Build collector once
        try:
            init_sys  = getattr(shell.kernel, 'init_system', None)
            net_mgr   = getattr(shell, 'network_manager', None)
            collector = MetricsCollector(
                shell.kernel, shell.fs,
                network_manager=net_mgr,
                init_system=init_sys,
            )
        except Exception as e:
            print(f"htop: metrics unavailable: {e}")
            return 1

        # Sort-column cycling order (used by 's' keypress)
        sort_cols = ['pid', 'cpu', 'mem', 'time', 'command']

        def _fmt_mem(bytes_val: int) -> str:
            """Format bytes as K/M string."""
            kb = bytes_val // 1024
            if kb >= 1024:
                return f"{kb // 1024}M"
            return f"{kb}K"

        def _fmt_time(secs: float) -> str:
            cs = int(secs * 100) % 100
            s  = int(secs) % 60
            m  = int(secs) // 60
            return f"{m}:{s:02d}.{cs:02d}"

        def _render_screen():
            cpu_snap  = collector.get_cpu_snapshot()
            mem_snap  = collector.get_memory_snapshot()

            cpu_pct   = cpu_snap.get('user_pct', 0.0) + cpu_snap.get('sys_pct', 0.0)
            mem_total = mem_snap['total']
            mem_used  = mem_snap['used']
            mem_pct   = (mem_used / max(mem_total, 1)) * 100.0
            swap_total = mem_snap['swap_total']
            swap_used  = mem_snap['swap_used']
            swap_pct   = (swap_used / max(swap_total, 1)) * 100.0

            uptime_s  = shell.kernel.get_uptime()
            h = int(uptime_s // 3600)
            m = int((uptime_s % 3600) // 60)
            s = int(uptime_s % 60)
            uptime_str = f"{h}:{m:02d}:{s:02d}"

            # Gather processes
            all_procs = list(shell.kernel.list_processes())

            # Apply filters
            if pid_filter:
                all_procs = [p for p in all_procs if p.pid in pid_filter]
            if user_filter:
                all_procs = [p for p in all_procs
                             if getattr(p, 'owner', 'root') == user_filter]

            running_count = sum(
                1 for p in all_procs
                if str(getattr(p, 'state', '')).upper() in ('RUNNING', 'PROCESSSTATE.RUNNING')
            )
            load_avg = f"{cpu_pct/100*0.8:.2f} {cpu_pct/100*0.6:.2f} {cpu_pct/100*0.4:.2f}"

            # Header
            cpu_bar = _progress_bar(cpu_pct)
            mem_bar = _progress_bar(mem_pct)
            swp_bar = _progress_bar(swap_pct)

            print(f" {_c('1', 'CPU')}[{cpu_bar} {cpu_pct:5.1f}%]"
                  f"     Tasks: {len(all_procs)}, {running_count} running")
            print(f" {_c('1', 'Mem')}[{mem_bar} {mem_pct:5.1f}%]"
                  f"     Load average: {load_avg}")
            print(f" {_c('1', 'Swp')}[{swp_bar} {swap_pct:5.1f}%]"
                  f"     Uptime: {uptime_str}")
            print()

            # Column header
            hdr = (f"  {'PID':>5} {'USER':<9} {'PRI':>4} {'NI':>3}"
                   f"  {'VIRT':>6} {'RES':>6} {'%CPU':>5} {'%MEM':>5}"
                   f" {'TIME+':>9}  {'COMMAND'}")
            print(_c('7', hdr))

            # Sort processes
            mem_total_safe = max(mem_total, 1)
            for p in all_procs:
                mem_usage = getattr(p, 'memory_usage', 0)
                cpu_time  = getattr(p, 'cpu_time', 0.0)
                p._sort_cpu  = cpu_time
                p._sort_mem  = mem_usage
                p._sort_pid  = p.pid
                p._sort_time = cpu_time
                p._sort_cmd  = p.name

            sort_key_map = {
                'cpu':     lambda p: p._sort_cpu,
                'mem':     lambda p: p._sort_mem,
                'pid':     lambda p: p._sort_pid,
                'time':    lambda p: p._sort_time,
                'command': lambda p: p._sort_cmd,
            }
            key_fn = sort_key_map.get(sort_col, sort_key_map['cpu'])
            all_procs.sort(key=key_fn, reverse=(sort_col != 'command'))

            for p in all_procs:
                mem_usage = getattr(p, 'memory_usage', 0)
                cpu_time  = getattr(p, 'cpu_time', 0.0)
                owner     = getattr(p, 'owner', 'root')
                priority  = getattr(p, 'priority', 5)
                nice      = getattr(p, 'nice', 0)
                virt      = _fmt_mem(mem_usage * 2)
                res       = _fmt_mem(mem_usage)
                cpu_p     = min((cpu_time / max(uptime_s, 1)) * 100.0, 99.9)
                mem_p     = (mem_usage / mem_total_safe) * 100.0
                time_str  = _fmt_time(cpu_time)

                line = (f"  {p.pid:>5} {owner:<9} {priority:>4} {nice:>3}"
                        f"  {virt:>6} {res:>6} {cpu_p:>5.1f} {mem_p:>5.1f}"
                        f" {time_str:>9}  {p.name}")
                print(line)

            # Function-key bar
            fkey_bar = (_c('44;37', 'F1') + _c('0', 'Help ') +
                        _c('44;37', 'F2') + _c('0', 'Setup') +
                        _c('44;37', 'F3') + _c('0', 'Search') +
                        _c('44;37', 'F4') + _c('0', 'Filter') +
                        _c('44;37', 'F5') + _c('0', 'Sort') +
                        _c('44;37', 'F6') + _c('0', 'Cols') +
                        _c('44;37', 'F9') + _c('0', 'Kill') +
                        _c('44;37', 'F10') + _c('0', 'Quit'))
            print()
            print(fkey_bar)

        # ----------------------------------------------------------------
        # Non-interactive fallback (not a TTY)
        # ----------------------------------------------------------------
        if not sys.stdout.isatty():
            _render_screen()
            return 0

        # ----------------------------------------------------------------
        # Interactive loop
        # ----------------------------------------------------------------
        import select

        def _keypress_available() -> bool:
            """Return True if a key is waiting on stdin."""
            try:
                return bool(select.select([sys.stdin], [], [], 0)[0])
            except Exception:
                return False

        def _read_key() -> str:
            try:
                return sys.stdin.read(1)
            except Exception:
                return ''

        try:
            while True:
                print("\033[2J\033[H", end="")
                _render_screen()

                sleep_secs = delay / 10.0
                time.sleep(sleep_secs)

                if _keypress_available():
                    key = _read_key()
                    if key in ('q', 'Q'):
                        break
                    elif key == '\x1b':
                        # Possible F10: ESC [ 2 1 ~
                        rest_key = ''
                        if _keypress_available():
                            rest_key = sys.stdin.read(4)
                        if '21' in rest_key:
                            break
                    elif key == 'k':
                        # Kill: prompt for PID then signal
                        print("PID to kill: ", end='', flush=True)
                        try:
                            kill_pid = int(input())
                            shell.kernel.kill_process(kill_pid)
                        except Exception:
                            pass
                    elif key == 's':
                        # Cycle sort column
                        try:
                            idx = sort_cols.index(sort_col)
                        except ValueError:
                            idx = 0
                        sort_col = sort_cols[(idx + 1) % len(sort_cols)]

        except KeyboardInterrupt:
            pass

        print()
        return 0
