"""
PureOS Network Stack
Virtual network simulation with interfaces, sockets, and routing.
"""

import time
import random
import secrets
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import socket as sys_socket


class NetworkState(Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class NetworkInterface:
    name: str
    ip_address: str = "0.0.0.0"
    netmask: str = "0.0.0.0"
    mac_address: str = "00:00:00:00:00:00"
    state: NetworkState = NetworkState.DOWN
    mtu: int = 1500
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0

    def get_cidr(self) -> str:
        if self.ip_address == "0.0.0.0":
            return "0.0.0.0/0"
        prefix = self._netmask_to_prefix(self.netmask)
        return f"{self.ip_address}/{prefix}"

    def _netmask_to_prefix(self, netmask: str) -> int:
        parts = netmask.split(".")
        prefix = 0
        for part in parts:
            prefix += bin(int(part)).count("1")
        return prefix

    def get_network_address(self) -> str:
        if self.ip_address == "0.0.0.0":
            return "0.0.0.0"
        ip_parts = [int(p) for p in self.ip_address.split(".")]
        mask_parts = [int(p) for p in self.netmask.split(".")]
        network = ".".join(str(ip & mask) for ip, mask in zip(ip_parts, mask_parts))
        return network

    def get_broadcast(self) -> str:
        if self.ip_address == "0.0.0.0":
            return "255.255.255.255"
        ip_parts = [int(p) for p in self.ip_address.split(".")]
        mask_parts = [int(p) for p in self.netmask.split(".")]
        broadcast = ".".join(str(ip | (~mask & 255)) for ip, mask in zip(ip_parts, mask_parts))
        return broadcast


@dataclass
class RoutingEntry:
    destination: str
    gateway: str
    genmask: str
    interface: str
    metric: int = 0


class Socket:
    TCP_STATES = ["CLOSED", "LISTEN", "SYN_SENT", "SYN_RECV", "ESTABLISHED", 
                  "FIN_WAIT1", "FIN_WAIT2", "CLOSE_WAIT", "CLOSING", "LAST_ACK", "TIME_WAIT"]

    def __init__(self, family: int, type: int, protocol: int = 0):
        self.family = family
        self.type = type
        self.protocol = protocol
        self.local_addr: Optional[Tuple[str, int]] = None
        self.remote_addr: Optional[Tuple[str, int]] = None
        self.state = "CLOSED"
        self.fd: int = secrets.randbelow(9000) + 1000

    def bind(self, address: Tuple[str, int]) -> None:
        self.local_addr = address
        self.state = "BOUND"

    def listen(self, backlog: int = 1) -> None:
        self.state = "LISTEN"

    def connect(self, address: Tuple[str, int]) -> None:
        self.remote_addr = address
        self.state = "SYN_SENT"
        time.sleep(0.01)
        self.state = "ESTABLISHED"

    def accept(self):
        client_sock = Socket(self.family, self.type, self.protocol)
        client_sock.state = "ESTABLISHED"
        client_sock.remote_addr = ("0.0.0.0", 0)
        return client_sock, ("0.0.0.0", 0)

    def send(self, data: bytes) -> int:
        if self.state == "ESTABLISHED":
            return len(data)
        return 0

    def recv(self, bufsize: int = 1024) -> bytes:
        if self.state == "ESTABLISHED":
            return b""
        return b""

    def close(self) -> None:
        self.state = "CLOSED"


class TCPSocketTable:
    def __init__(self):
        self.sockets: Dict[int, Socket] = {}
        self._lock = threading.Lock()

    def add(self, sock: Socket) -> int:
        with self._lock:
            self.sockets[sock.fd] = sock
            return sock.fd

    def remove(self, fd: int) -> Optional[Socket]:
        with self._lock:
            return self.sockets.pop(fd, None)

    def get(self, fd: int) -> Optional[Socket]:
        with self._lock:
            return self.sockets.get(fd)

    def list_all(self) -> List[Dict]:
        with self._lock:
            result = []
            for fd, sock in self.sockets.items():
                result.append({
                    "fd": fd,
                    "local_addr": sock.local_addr,
                    "remote_addr": sock.remote_addr,
                    "state": sock.state,
                    "family": sock.family,
                })
            return result


class UDPSocketTable:
    def __init__(self):
        self.sockets: Dict[int, Socket] = {}
        self._lock = threading.Lock()

    def add(self, sock: Socket) -> int:
        with self._lock:
            self.sockets[sock.fd] = sock
            return sock.fd

    def remove(self, fd: int) -> Optional[Socket]:
        with self._lock:
            return self.sockets.pop(fd, None)

    def get(self, fd: int) -> Optional[Socket]:
        with self._lock:
            return self.sockets.get(fd)

    def list_all(self) -> List[Dict]:
        with self._lock:
            result = []
            for fd, sock in self.sockets.items():
                result.append({
                    "fd": fd,
                    "local_addr": sock.local_addr,
                    "remote_addr": sock.remote_addr,
                    "state": sock.state,
                })
            return result


class NetworkManager:
    SIMULATED_HOSTS = {
        "8.8.8.8": {"name": "dns.google", "rtt": 25},
        "8.8.4.4": {"name": "dns.google", "rtt": 28},
        "1.1.1.1": {"name": "cloudflare-dns.com", "rtt": 30},
        "1.0.0.1": {"name": "cloudflare-dns.com", "rtt": 32},
        "208.67.222.222": {"name": "resolver1.opendns.com", "rtt": 35},
        "208.67.220.220": {"name": "resolver2.opendns.com", "rtt": 36},
        "9.9.9.9": {"name": "dns.quad9.net", "rtt": 40},
        "114.114.114.114": {"name": "114dns.com", "rtt": 50},
        "8.8.8.8": {"name": "dns.google", "rtt": 25},
    }

    SIMULATED_LOCAL = {
        "192.168.1.1": {"name": "router.local", "rtt": 1},
        "192.168.1.254": {"name": "gateway", "rtt": 1},
        "127.0.0.1": {"name": "localhost", "rtt": 0},
    }

    def __init__(self):
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.routes: List[RoutingEntry] = []
        self.tcp_sockets = TCPSocketTable()
        self.udp_sockets = UDPSocketTable()
        self.hostname = "pureos"
        self._lock = threading.Lock()
        self._initialize_defaults()

    def _initialize_defaults(self):
        lo = NetworkInterface(
            name="lo",
            ip_address="127.0.0.1",
            netmask="255.0.0.0",
            mac_address="00:00:00:00:00:00",
            state=NetworkState.UP
        )
        self.interfaces["lo"] = lo

        eth0 = NetworkInterface(
            name="eth0",
            ip_address="192.168.1.100",
            netmask="255.255.255.0",
            mac_address="52:54:00:12:34:56",
            state=NetworkState.UP
        )
        self.interfaces["eth0"] = eth0

        self.routes.append(RoutingEntry(
            destination="0.0.0.0",
            gateway="192.168.1.1",
            genmask="0.0.0.0",
            interface="eth0",
            metric=100
        ))
        self.routes.append(RoutingEntry(
            destination="192.168.1.0",
            gateway="0.0.0.0",
            genmask="255.255.255.0",
            interface="eth0",
            metric=0
        ))
        self.routes.append(RoutingEntry(
            destination="127.0.0.0",
            gateway="0.0.0.0",
            genmask="255.0.0.0",
            interface="lo",
            metric=0
        ))

    def get_interface(self, name: str) -> Optional[NetworkInterface]:
        return self.interfaces.get(name)

    def list_interfaces(self) -> List[NetworkInterface]:
        return list(self.interfaces.values())

    def set_interface_state(self, name: str, state: NetworkState) -> bool:
        iface = self.interfaces.get(name)
        if not iface:
            return False
        iface.state = state
        return True

    def set_interface_ip(self, name: str, ip: str, netmask: Optional[str] = None) -> bool:
        iface = self.interfaces.get(name)
        if not iface:
            return False
        if netmask is None:
            if "/" in ip:
                ip, prefix = ip.split("/")
                iface.netmask = self._prefix_to_netmask(int(prefix))
            else:
                iface.netmask = "255.255.255.0"
        else:
            iface.netmask = netmask
        iface.ip_address = ip
        return True

    def _prefix_to_netmask(self, prefix: int) -> str:
        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        return ".".join(str((mask >> (8 * i)) & 0xFF) for i in range(3, -1, -1))

    def add_route(self, destination: str, gateway: str, genmask: str, interface: str, metric: int = 0) -> None:
        entry = RoutingEntry(destination, gateway, genmask, interface, metric)
        self.routes.append(entry)

    def list_routes(self) -> List[RoutingEntry]:
        return self.routes

    def ping(self, target: str, count: int = 4, timeout: float = 2.0) -> Tuple[bool, List[Dict], str]:
        results = []
        success = True

        if target in self.SIMULATED_LOCAL:
            host_info = self.SIMULATED_LOCAL[target]
            rtt_base = host_info["rtt"]
        elif target in self.SIMULATED_HOSTS:
            host_info = self.SIMULATED_HOSTS[target]
            rtt_base = host_info["rtt"]
        elif target.startswith("192.168.1."):
            rtt_base = 2
            host_info = {"name": target}
        elif target == "localhost" or target == "127.0.0.1":
            rtt_base = 0
            host_info = {"name": "localhost"}
        else:
            rtt_base = random.randint(40, 100)
            host_info = {"name": target}

        for i in range(count):
            rtt = rtt_base + random.uniform(-rtt_base * 0.1, rtt_base * 0.2) if rtt_base > 0 else 0.05
            rtt = max(0.1, rtt)
            success = success and (rtt < timeout * 1000)
            results.append({
                "seq": i + 1,
                "ttl": 64,
                "time": rtt,
                "success": rtt < timeout * 1000
            })
            if i < count - 1:
                time.sleep(0.5)

        hostname = host_info.get("name", target)
        return success, results, hostname

    def traceroute(self, target: str, max_hops: int = 30) -> List[Dict]:
        hops = []

        if target == "127.0.0.1" or target == "localhost":
            hops.append({"hop": 1, "ip": "127.0.0.1", "name": "localhost", "rtt": 0.1})
            return hops

        if target.startswith("192.168.1."):
            hops.append({"hop": 1, "ip": "192.168.1.1", "name": "router.local", "rtt": random.uniform(0.5, 1.5)})
            if target != "192.168.1.1":
                hops.append({"hop": 2, "ip": target, "name": target, "rtt": random.uniform(1, 3)})
            return hops

        hops.append({"hop": 1, "ip": "192.168.1.1", "name": "router.local", "rtt": random.uniform(0.5, 1.5)})
        hops.append({"hop": 2, "ip": "10.0.0.1", "name": "isp-gateway", "rtt": random.uniform(2, 5)})
        hops.append({"hop": 3, "ip": random.choice(["172.16.0.1", "172.16.0.2", "172.16.0.3"]), "name": f"isp-node-{random.randint(1,3)}", "rtt": random.uniform(5, 10)})

        for hop_num in range(4, min(max_hops, 10)):
            hops.append({
                "hop": hop_num,
                "ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                "name": f"router-{hop_num}",
                "rtt": random.uniform(10, 30)
            })

        hops.append({"hop": 10, "ip": target, "name": target, "rtt": random.uniform(20, 40)})

        return hops[:max_hops]

    def netstat(self, show_all: bool = False) -> Dict:
        tcp_conns = self.tcp_sockets.list_all()
        udp_conns = self.udp_sockets.list_all()

        if not show_all:
            tcp_conns = [c for c in tcp_conns if c["state"] == "ESTABLISHED"]
            udp_conns = [c for c in udp_conns if c["state"] == "BOUND"]

        return {
            "tcp": tcp_conns,
            "udp": udp_conns,
            "unix": []
        }

    def get_hostname(self) -> str:
        return self.hostname

    def set_hostname(self, hostname: str) -> bool:
        if len(hostname) > 64:
            return False
        self.hostname = hostname
        return True

    def resolve_hostname(self, hostname: str) -> Optional[str]:
        if hostname in ("localhost", "pureos"):
            return "127.0.0.1"
        for ip, info in self.SIMULATED_HOSTS.items():
            if info.get("name", "").startswith(hostname.split(".")[0]):
                return ip
        if hostname == "google.com":
            return "8.8.8.8"
        if hostname == "cloudflare.com":
            return "1.1.1.1"
        if hostname == "github.com":
            return "140.82.121.3"
        if hostname == "python.org":
            return "151.101.1.69"
        return None

    def get_proc_net_tcp(self) -> str:
        lines = ["  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode"]
        for fd, sock in self.tcp_sockets.sockets.items():
            local = f"{sock.local_addr[0]}:{sock.local_addr[1]}" if sock.local_addr else "0.0.0.0:0"
            remote = f"{sock.remote_addr[0]}:{sock.remote_addr[1]}" if sock.remote_addr else "0.0.0.0:0"
            state_hex = "0A" if sock.state == "LISTEN" else "01"
            lines.append(f"   0: {local:023} {remote:023} {state_hex} 00000000:00000000 00000000 00000000 0        0 {fd} 0 0 0 0")
        return "\n".join(lines)

    def get_proc_net_udp(self) -> str:
        lines = ["  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref  pointer drops"]
        for fd, sock in self.udp_sockets.sockets.items():
            local = f"{sock.local_addr[0]}:{sock.local_addr[1]}" if sock.local_addr else "0.0.0.0:0"
            remote = f"{sock.remote_addr[0]}:{sock.remote_addr[1]}" if sock.remote_addr else "0.0.0.0:0"
            lines.append(f"   0: {local:023} {remote:023} 07 00000000:00000000 00000000 00000000 0        0 {fd} 0 0 0 0")
        return "\n".join(lines)

    def get_proc_net_dev(self) -> str:
        lines = ["Inter-|   Receive                                                |  Transmit"]
        lines.append(" face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed")
        for name, iface in self.interfaces.items():
            rx = iface.rx_bytes
            tx = iface.tx_bytes
            lines.append(f"{name:>6}: {rx:8d} {iface.rx_packets:7d} 0 0 0 0 0 0 0 {tx:8d} {iface.tx_packets:7d} 0 0 0 0 0 0")
        return "\n".join(lines)
