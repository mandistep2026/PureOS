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
            collector = MetricsCollector(shell.kernel)
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
            collector = MetricsCollector(shell.kernel)
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
