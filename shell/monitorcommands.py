"""
PureOS Monitor Commands
Commands for system monitoring: memory, I/O, CPU statistics, and diagnostics.
"""

import time
import sys
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
