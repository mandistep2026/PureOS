"""
tests/integration/test_shell_network.py
======================================
Integration tests for networking shell commands.

Covers:
- ifconfig
- ip (addr/link/route)
- route
- arp
- hostname
- netstat
- dig
- nslookup
"""

import unittest

from tests.base import BaseTestCase


class TestIfconfigCommand(BaseTestCase):
    """Integration tests for ifconfig."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_ifconfig_is_registered(self):
        self.assertIn("ifconfig", self.shell.commands)

    def test_ifconfig_lists_interfaces(self):
        self.assertShellSuccess(self.shell, "ifconfig > /tmp/ifconfig_all.txt")
        content = self.fs.read_file("/tmp/ifconfig_all.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"eth0", content)
        self.assertIn(b"lo", content)

    def test_ifconfig_single_interface(self):
        self.assertShellSuccess(self.shell, "ifconfig eth0 > /tmp/ifconfig_eth0.txt")
        content = self.fs.read_file("/tmp/ifconfig_eth0.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"eth0", content)

    def test_ifconfig_unknown_interface_fails(self):
        self.assertShellFails(self.shell, "ifconfig no_such0")


class TestIpCommand(BaseTestCase):
    """Integration tests for ip."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_ip_is_registered(self):
        self.assertIn("ip", self.shell.commands)

    def test_ip_no_args_fails(self):
        self.assertShellFails(self.shell, "ip")

    def test_ip_addr_show_outputs_interfaces(self):
        self.assertShellSuccess(self.shell, "ip addr show > /tmp/ip_addr.txt")
        content = self.fs.read_file("/tmp/ip_addr.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"eth0", content)
        self.assertIn(b"inet", content)

    def test_ip_link_show_outputs_links(self):
        self.assertShellSuccess(self.shell, "ip link show > /tmp/ip_link.txt")
        content = self.fs.read_file("/tmp/ip_link.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"link/", content)

    def test_ip_route_show_outputs_default(self):
        self.assertShellSuccess(self.shell, "ip route show > /tmp/ip_route.txt")
        content = self.fs.read_file("/tmp/ip_route.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"default via", content)


class TestRouteCommand(BaseTestCase):
    """Integration tests for route."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_route_is_registered(self):
        self.assertIn("route", self.shell.commands)

    def test_route_outputs_table(self):
        self.assertShellSuccess(self.shell, "route > /tmp/route_out.txt")
        content = self.fs.read_file("/tmp/route_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"Kernel IP routing table", content)
        self.assertIn(b"eth0", content)


class TestArpCommand(BaseTestCase):
    """Integration tests for arp."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_arp_is_registered(self):
        self.assertIn("arp", self.shell.commands)

    def test_arp_outputs_cache(self):
        self.assertShellSuccess(self.shell, "arp > /tmp/arp_out.txt")
        content = self.fs.read_file("/tmp/arp_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"Address", content)
        self.assertIn(b"eth0", content)


class TestHostnameCommand(BaseTestCase):
    """Integration tests for hostname."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_hostname_is_registered(self):
        self.assertIn("hostname", self.shell.commands)

    def test_hostname_prints_default(self):
        self.assertShellSuccess(self.shell, "hostname > /tmp/hostname.txt")
        content = self.fs.read_file("/tmp/hostname.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"pureos", content)

    def test_hostname_short(self):
        self.assertShellSuccess(self.shell, "hostname -s > /tmp/hostname_short.txt")
        content = self.fs.read_file("/tmp/hostname_short.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"pureos", content)

    def test_hostname_ip_address(self):
        self.assertShellSuccess(self.shell, "hostname -i > /tmp/hostname_ip.txt")
        content = self.fs.read_file("/tmp/hostname_ip.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"192.168.1.100", content)


class TestNetstatCommand(BaseTestCase):
    """Integration tests for netstat."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_netstat_is_registered(self):
        self.assertIn("netstat", self.shell.commands)

    def test_netstat_outputs_tcp_and_udp(self):
        self.assertShellSuccess(self.shell, "netstat > /tmp/netstat_out.txt")
        content = self.fs.read_file("/tmp/netstat_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"Active Internet connections", content)
        self.assertIn(b"tcp", content)
        self.assertIn(b"udp", content)

    def test_netstat_tcp_only(self):
        self.assertShellSuccess(self.shell, "netstat -t > /tmp/netstat_tcp.txt")
        content = self.fs.read_file("/tmp/netstat_tcp.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"tcp", content)

    def test_netstat_udp_only(self):
        self.assertShellSuccess(self.shell, "netstat -u > /tmp/netstat_udp.txt")
        content = self.fs.read_file("/tmp/netstat_udp.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"udp", content)


class TestDigCommand(BaseTestCase):
    """Integration tests for dig."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_dig_is_registered(self):
        self.assertIn("dig", self.shell.commands)

    def test_dig_outputs_answer_section(self):
        self.assertShellSuccess(self.shell, "dig google.com > /tmp/dig_out.txt")
        content = self.fs.read_file("/tmp/dig_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"ANSWER SECTION", content)
        self.assertIn(b"google.com", content)


class TestNslookupCommand(BaseTestCase):
    """Integration tests for nslookup."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def test_nslookup_is_registered(self):
        self.assertIn("nslookup", self.shell.commands)

    def test_nslookup_outputs_address(self):
        self.assertShellSuccess(self.shell, "nslookup google.com > /tmp/nslookup_out.txt")
        content = self.fs.read_file("/tmp/nslookup_out.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"Address", content)


if __name__ == "__main__":
    unittest.main()
