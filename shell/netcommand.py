"""
PureOS Network Shell Commands
"""

import time
import random
from typing import List
from shell.shell import ShellCommand


class IfconfigCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("ifconfig", "Configure network interface")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            return self.show_all_interfaces(shell)

        iface_name = args[0]

        if len(args) == 1:
            return self.show_interface(shell, iface_name)

        if args[1] == "up":
            return self.bring_up(shell, iface_name)
        elif args[1] == "down":
            return self.bring_down(shell, iface_name)
        elif "." in args[1]:
            return self.set_ip(shell, iface_name, args[1])
        else:
            shell.print(f"ifconfig: unknown option {args[1]}")
            return 1

    def show_all_interfaces(self, shell) -> int:
        for iface in self.nm.list_interfaces():
            self._print_interface(shell, iface)
        return 0

    def show_interface(self, shell, name: str) -> int:
        iface = self.nm.get_interface(name)
        if not iface:
            shell.print(f"ifconfig: {name}: No such device")
            return 1
        self._print_interface(shell, iface)
        return 0

    def _print_interface(self, shell, iface):
        state_str = "UP" if iface.state.value == "up" else "DOWN"
        shell.print(f"{iface.name}    Link encap:{'Ethernet' if iface.name != 'lo' else 'Local Loopback'}  HWaddr {iface.mac_address}")
        shell.print(f"          inet addr:{iface.ip_address}  Bcast:{iface.get_broadcast()}  Mask:{iface.netmask}")
        shell.print(f"          {state_str} MTU:{iface.mtu}  Metric:1")
        shell.print(f"          RX packets:{iface.rx_packets} bytes:{iface.rx_bytes}")
        shell.print(f"          TX packets:{iface.tx_packets} bytes:{iface.tx_bytes}")
        shell.print("")

    def bring_up(self, shell, name: str) -> int:
        if self.nm.set_interface_state(name, self.nm.interfaces[name].state.__class__.UP):
            shell.print(f"{name}: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu {self.nm.get_interface(name).mtu}")
            return 0
        shell.print(f"ifconfig: {name}: No such device")
        return 1

    def bring_down(self, shell, name: str) -> int:
        if self.nm.set_interface_state(name, self.nm.interfaces[name].state.__class__.DOWN):
            shell.print(f"{name}: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu {self.nm.get_interface(name).mtu}")
            return 0
        shell.print(f"ifconfig: {name}: No such device")
        return 1

    def set_ip(self, shell, name: str, ip: str) -> int:
        if self.nm.set_interface_ip(name, ip):
            shell.print(f"{name}: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu {self.nm.get_interface(name).mtu}")
            return 0
        shell.print(f"ifconfig: {name}: No such device")
        return 1


class PingCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("ping", "Send ICMP echo requests")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            shell.print("ping: usage: ping [-c count] [-t timeout] destination")
            return 1

        count = 4
        timeout = 2.0

        if "-c" in args:
            try:
                idx = args.index("-c")
                count = int(args[idx + 1])
            except (ValueError, IndexError):
                shell.print("ping: invalid count")
                return 1

        if "-t" in args:
            try:
                idx = args.index("-t")
                timeout = float(args[idx + 1])
                if timeout <= 0:
                    raise ValueError
            except (ValueError, IndexError):
                shell.print("ping: invalid timeout")
                return 1

        # Collect indices consumed by flags so the target can be identified
        # as the last argument not consumed by a flag pair.
        flag_indices = set()
        for flag in ("-c", "-t"):
            if flag in args:
                fi = args.index(flag)
                flag_indices.update((fi, fi + 1))

        positional = [a for i, a in enumerate(args) if i not in flag_indices]
        if not positional or positional[-1].startswith("-"):
            shell.print("ping: usage: ping [-c count] [-t timeout] destination")
            return 1
        target = positional[-1]

        target = self._resolve_target(target, shell)

        shell.print(f"PING {target} ({target}): 56 data bytes")

        success, results, hostname = self.nm.ping(target, count, timeout)

        for r in results:
            status = "OK" if r["success"] else "FAILED"
            shell.print(f"64 bytes from {target}: icmp_seq={r['seq']} ttl={r['ttl']} time={r['time']:.3f} ms {status}")

        stats = f"\n--- {target} ping statistics ---"
        shell.print(stats)
        transmitted = len(results)
        received = sum(1 for r in results if r["success"])
        loss = ((transmitted - received) / transmitted * 100) if transmitted > 0 else 0
        shell.print(f"{transmitted} packets transmitted, {received} packets received, {loss:.0f}% packet loss")

        return 0 if success else 1

    def _resolve_target(self, target: str, shell) -> str:
        if "." in target and not target[0].isdigit():
            resolved = self.nm.resolve_hostname(target)
            if resolved:
                return resolved
        return target


class NetstatCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("netstat", "Show network connections")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        show_all = "-a" in args or "--all" in args
        tcp_only = "-t" in args
        udp_only = "-u" in args
        numeric = "-n" in args

        conns = self.nm.netstat(show_all)

        shell.print("Active Internet connections (servers and established)")

        if not tcp_only and not udp_only:
            self._print_tcp(shell, conns["tcp"], numeric)
            self._print_udp(shell, conns["udp"], numeric)
        elif tcp_only:
            self._print_tcp(shell, conns["tcp"], numeric)
        elif udp_only:
            self._print_udp(shell, conns["udp"], numeric)

        return 0

    def _print_tcp(self, shell, connections: List, numeric: bool):
        shell.print("Proto Recv-Q Send-Q Local Address           Foreign Address         State")
        if not connections:
            shell.print("tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN")
            shell.print("tcp        0      0 127.0.0.1:631           0.0.0.0:*               LISTEN")
            return
        for conn in connections:
            local = f"{conn['local_addr'][0]}:{conn['local_addr'][1]}" if conn['local_addr'] else "0.0.0.0:0"
            remote = f"{conn['remote_addr'][0]}:{conn['remote_addr'][1]}" if conn['remote_addr'] else "0.0.0.0:0"
            shell.print(f"tcp        0      0 {local:21} {remote:21} {conn['state']}")

    def _print_udp(self, shell, connections: List, numeric: bool):
        shell.print("Proto Recv-Q Send-Q Local Address           Foreign Address         State")
        if not connections:
            shell.print("udp        0      0 0.0.0.0:68              0.0.0.0:*")
            shell.print("udp        0      0 0.0.0.0:5353            0.0.0.0:*")
            shell.print("udp        0      0 127.0.0.1:323          0.0.0.0:*")
            return
        for conn in connections:
            local = f"{conn['local_addr'][0]}:{conn['local_addr'][1]}" if conn['local_addr'] else "0.0.0.0:0"
            remote = f"{conn['remote_addr'][0]}:{conn['remote_addr'][1]}" if conn['remote_addr'] else "0.0.0.0:*"
            shell.print(f"udp        0      0 {local:21} {remote:21}")


class IpCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("ip", "Show/manipulate routing, devices, tunnels")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            shell.print("Usage: ip [ OPTIONS ] OBJECT { COMMAND }")
            shell.print("Options: -4, -6, -s, -r")
            shell.print("Objects: addr, link, route, neigh")
            return 1

        if args[0] == "addr" or args[0] == "address":
            return self.show_addresses(shell, args[1:])
        elif args[0] == "link":
            return self.show_links(shell, args[1:])
        elif args[0] == "route":
            return self.show_routes(shell, args[1:])
        elif args[0] == "neigh":
            return self.show_neigh(shell, args[1:])
        elif args[0] == "help":
            return self.show_help(shell)
        else:
            shell.print(f"ip: unknown object '{args[0]}'")
            return 1

    def show_addresses(self, shell, args: List) -> int:
        if "show" in args or not args:
            for idx, iface in enumerate(self.nm.list_interfaces(), start=1):
                state = "UP" if iface.state.value == "up" else "DOWN"
                shell.print(f"{idx}: {iface.name} <{state},LOOPBACK,RUNNING,MULTICAST> mtu {iface.mtu} qdisc pfifo_fast state UNKNOWN mode DEFAULT")
                shell.print(f"    link/{'ether' if iface.name != 'loopback' else 'loopback'} {iface.mac_address} brd ff:ff:ff:ff:ff:ff")
                shell.print(f"    inet {iface.ip_address}/{iface._netmask_to_prefix(iface.netmask)} brd {iface.get_broadcast()} scope global {iface.name}")
                shell.print(f"    inet6 {self._generate_ipv6(iface.ip_address)} scope global")
                shell.print("")
        return 0

    def _generate_ipv6(self, ipv4: str) -> str:
        parts = [f"{int(p):02x}" for p in ipv4.split(".")]
        return f"fe80::{parts[2]}:{parts[3]}ff:fe00:0000/64"

    def show_links(self, shell, args: List) -> int:
        for idx, iface in enumerate(self.nm.list_interfaces(), start=1):
            state = "UP" if iface.state.value == "up" else "DOWN"
            shell.print(f"{idx}: {iface.name} <{state},BROADCAST,MULTICAST,UP,LOWER_UP> mtu {iface.mtu} qdisc pfifo_fast state {state} mode DEFAULT")
            shell.print(f"    link/{'ether' if iface.name != 'lo' else 'loopback'} {iface.mac_address} brd ff:ff:ff:ff:ff:ff")
        return 0

    def show_routes(self, shell, args: List) -> int:
        shell.print("default via 192.168.1.1 dev eth0")
        for route in self.nm.list_routes():
            if route.destination != "0.0.0.0":
                shell.print(f"{route.destination}/{route.genmask} dev {route.interface} scope link")
        return 0

    def show_neigh(self, shell, args: List) -> int:
        shell.print("192.168.1.1 dev eth0 lladdr 52:54:00:12:35:01 REACHABLE")
        shell.print("192.168.1.254 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE")
        return 0

    def show_help(self, shell) -> int:
        shell.print("Usage: ip [ OPTIONS ] OBJECT { COMMAND }")
        shell.print("  ip addr show")
        shell.print("  ip link set eth0 up/down")
        shell.print("  ip addr add 192.168.1.1/24 dev eth0")
        shell.print("  ip route show")
        return 0


class HostnameCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("hostname", "Show or set the hostname")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            shell.print(self.nm.get_hostname())
            return 0

        if args[0] == "-i" or args[0] == "--ip-address":
            iface = self.nm.get_interface("eth0")
            if iface:
                shell.print(iface.ip_address)
            return 0

        if args[0] == "-s" or args[0] == "--short":
            shell.print(self.nm.get_hostname().split(".")[0])
            return 0

        new_hostname = args[0]
        if self.nm.set_hostname(new_hostname):
            shell.environment["HOSTNAME"] = new_hostname
            return 0
        else:
            shell.print("hostname: name too long")
            return 1


class TracerouteCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("traceroute", "Trace the route to a host")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            shell.print("traceroute: usage: traceroute [-m max_ttl] host")
            return 1

        max_hops = 30
        target = args[-1]

        if "-m" in args:
            try:
                idx = args.index("-m")
                max_hops = int(args[idx + 1])
                target = args[idx + 2] if idx + 2 < len(args) else args[-1]
            except (ValueError, IndexError):
                shell.print("traceroute: invalid max_ttl")
                return 1

        shell.print(f"traceroute to {target}, {max_hops} hops max")

        hops = self.nm.traceroute(target, max_hops)

        for hop in hops:
            rtt_str = f"{hop['rtt']:.3f} ms" if hop['rtt'] > 0 else "*"
            shell.print(f" {hop['hop']:2d}  {hop['ip']:18s} ({hop['name']})  {rtt_str}")

        return 0


class DigCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("dig", "DNS lookup utility")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            shell.print("dig: usage: dig [@server] host [query-type]")
            return 1

        target = args[-1]

        if "@" in args[0]:
            server = args[0][1:]
        else:
            server = None

        ip = self.nm.resolve_hostname(target)

        rc = self.nm.get_resolver_config()
        ns = rc.nameservers[0] if rc.nameservers else "127.0.0.1"

        shell.print("; <<>> DiG 9.18.1 <<>> " + target)
        shell.print(";; global options: +cmd")
        shell.print(";; Got answer:")
        shell.print(";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345")
        shell.print(";; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1")
        shell.print("")
        shell.print(f";; OPT pseudo-section:")
        shell.print(";; EDNS: version: 0, flags:; udp: 4096")
        shell.print(";; QUESTION SECTION:")
        shell.print(f";{target}.          IN      A")
        shell.print(";; ANSWER SECTION:")
        if ip:
            shell.print(f"{target}.         86400   IN      A       {ip}")
        else:
            shell.print(f"{target}.         86400   IN      A       192.0.2.1")
        shell.print(";; Query time: 5 msec")
        shell.print(f";; SERVER: {ns}#53({ns})")
        shell.print(";; WHEN: " + time.strftime("%a %b %d %H:%M:%S %Z %Y"))
        shell.print(";; MSG SIZE  rcvd: 56")

        return 0


class NslookupCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("nslookup", "Query DNS for domain names")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            shell.print("nslookup: usage: nslookup [host] [server]")
            return 1

        target = args[0]
        ip = self.nm.resolve_hostname(target)

        rc = self.nm.get_resolver_config()
        ns = rc.nameservers[0] if rc.nameservers else "127.0.0.1"

        shell.print(f"Server:     {ns}")
        shell.print(f"Address:    {ns}#53")
        shell.print("")
        if ip:
            shell.print(f"Name:   {target}")
            shell.print(f"Address: {ip}")
        else:
            shell.print(f"** server can't find {target}: NXDOMAIN")

        return 0


class RouteCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("route", "Show/manipulate the IP routing table")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        shell.print("Kernel IP routing table")
        shell.print("Destination     Gateway         Genmask         Flags Metric Ref  Use Iface")
        shell.print("0.0.0.0         192.168.1.1    0.0.0.0         UG    100    0      0 eth0")
        shell.print("192.168.1.0     0.0.0.0        255.255.255.0   U     0      0      0 eth0")
        shell.print("127.0.0.0       0.0.0.0        255.0.0.0       U     0      0      0 lo")

        return 0


class ArpCommand(ShellCommand):
    def __init__(self, network_manager=None):
        super().__init__("arp", "Manipulate the ARP cache")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        shell.print("Address                  HWtype  HWaddress           Flags Mask            Iface")
        shell.print("192.168.1.1             ether   52:54:00:12:35:01   C                     eth0")
        shell.print("192.168.1.254           ether   00:11:22:33:44:55   C                     eth0")
        shell.print("192.168.1.10            ether   aa:bb:cc:dd:ee:ff   C                     eth0")

        return 0


class ResolvectlCommand(ShellCommand):
    """Show DNS resolver status (resolvectl status)."""

    USAGE = (
        "Usage: resolvectl [status]\n"
        "  (no args)   Show DNS resolver status\n"
        "  status      Same as no args\n"
    )

    def __init__(self, network_manager=None):
        super().__init__("resolvectl", "Show DNS resolver status")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args or args[0] == "status":
            return self._show_status(shell)

        if args[0] in ("-h", "--help"):
            shell.print(self.USAGE)
            return 0

        shell.print(f"resolvectl: unknown option '{args[0]}'")
        shell.print(self.USAGE)
        return 1

    def _show_status(self, shell) -> int:
        rc = self.nm.get_resolver_config()
        nameservers = rc.nameservers or []
        search = rc.search or []

        shell.print("Global")
        shell.print(f"  Hostname: {self.nm.get_hostname()}")
        if nameservers:
            shell.print(f"  DNS Servers: {' '.join(nameservers)}")
            shell.print(f"  Current DNS Server: {nameservers[0]}")
        else:
            shell.print("  DNS Servers: (none)")

        domain_label = "DNS Domain" if len(search) == 1 else "DNS Domains"
        if search:
            shell.print(f"  {domain_label}: {' '.join(search)}")
        else:
            shell.print(f"  {domain_label}: (none)")

        for iface in self.nm.list_interfaces():
            shell.print("")
            shell.print(f"Link {iface.name} ({iface.state.value})")
            shell.print(f"  Addresses: {iface.get_cidr()}")
            if nameservers:
                shell.print(f"  DNS Servers: {' '.join(nameservers)}")
            if search:
                shell.print(f"  Search Domains: {' '.join(search)}")
        return 0


class ResolvconfCommand(ShellCommand):
    """View or set DNS resolver configuration (/etc/resolv.conf)."""

    USAGE = (
        "Usage: resolvconf [OPTIONS]\n"
        "  (no args)            Show current DNS configuration\n"
        "  -n <ns> [<ns2> ...]  Set nameserver(s)\n"
        "  -s <dom> [<dom2> ...]  Set search domain(s)\n"
        "  --set <key>=<value>  Set a single key (nameserver|search)\n"
    )

    def __init__(self, network_manager=None):
        super().__init__("resolvconf", "View or set DNS resolver configuration")
        self.nm = network_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.nm:
            self.nm = shell.network_manager

        if not args:
            return self._show(shell)

        if args[0] in ("-h", "--help"):
            shell.print(self.USAGE)
            return 0

        if args[0] == "-n":
            # Set nameservers
            servers = args[1:]
            if not servers:
                shell.print("resolvconf: -n requires at least one nameserver")
                return 1
            return self._set_nameservers(shell, servers)

        if args[0] == "-s":
            # Set search domains
            domains = args[1:]
            if not domains:
                shell.print("resolvconf: -s requires at least one search domain")
                return 1
            return self._set_search(shell, domains)

        if args[0] == "--set":
            # --set key=value
            for token in args[1:]:
                if "=" not in token:
                    shell.print(f"resolvconf: invalid --set token '{token}' (expect key=value)")
                    return 1
                key, _, value = token.partition("=")
                if key == "nameserver":
                    self.nm.set_nameservers([v.strip() for v in value.split(",")])
                elif key == "search":
                    self.nm.set_search_domains([v.strip() for v in value.split(",")])
                else:
                    shell.print(f"resolvconf: unknown key '{key}'")
                    return 1
            self._sync_fs(shell)
            return 0

        shell.print(f"resolvconf: unknown option '{args[0]}'")
        shell.print(self.USAGE)
        return 1

    def _show(self, shell) -> int:
        rc = self.nm.get_resolver_config()
        content = rc.to_resolv_conf()
        if content:
            shell.print(content.rstrip())
        else:
            shell.print("# /etc/resolv.conf is empty")
        return 0

    def _set_nameservers(self, shell, servers: List[str]) -> int:
        self.nm.set_nameservers(servers)
        self._sync_fs(shell)
        shell.print(f"DNS nameservers set to: {', '.join(servers)}")
        return 0

    def _set_search(self, shell, domains: List[str]) -> int:
        self.nm.set_search_domains(domains)
        self._sync_fs(shell)
        shell.print(f"DNS search domains set to: {', '.join(domains)}")
        return 0

    def _sync_fs(self, shell) -> None:
        """Write the current resolver config to /etc/resolv.conf in the VFS."""
        rc = self.nm.get_resolver_config()
        content = rc.to_resolv_conf().encode("utf-8")
        fs = getattr(shell, 'fs', None) or getattr(shell, 'filesystem', None)
        if fs is not None:
            fs.write_file("/etc/resolv.conf", content)
