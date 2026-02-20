"""
Integration tests for the resolvectl status command.
"""

import unittest

from tests.base import BaseTestCase


class TestResolvectlStatusCommand(BaseTestCase):
    """Integration tests for resolvectl status output and registration."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        self.nm = self.shell.network_manager

    def test_resolvectl_is_registered(self):
        self.assertIn("resolvectl", self.shell.commands)

    def test_resolvectl_status_succeeds(self):
        self.assertShellSuccess(self.shell, "resolvectl status > /tmp/resolvectl_status.txt")

    def test_resolvectl_status_reports_current_dns_server(self):
        self.assertShellSuccess(self.shell, "resolvectl status > /tmp/resolvectl_status.txt")
        content = self.fs.read_file("/tmp/resolvectl_status.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"Current DNS Server", content)
        self.assertIn(b"8.8.8.8", content)

    def test_resolvectl_status_reports_dns_servers(self):
        self.assertShellSuccess(self.shell, "resolvectl status > /tmp/resolvectl_status.txt")
        content = self.fs.read_file("/tmp/resolvectl_status.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"DNS Servers", content)
        self.assertIn(b"8.8.4.4", content)

    def test_resolvectl_status_reports_dns_domain(self):
        self.shell.execute("resolvconf -s corp.local")
        self.assertShellSuccess(self.shell, "resolvectl status > /tmp/resolvectl_status.txt")
        content = self.fs.read_file("/tmp/resolvectl_status.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"DNS Domain", content)
        self.assertIn(b"corp.local", content)

    def test_resolvectl_status_reports_multiple_dns_domains(self):
        self.shell.execute("resolvconf -s corp.local example.com")
        self.assertShellSuccess(self.shell, "resolvectl status > /tmp/resolvectl_status.txt")
        content = self.fs.read_file("/tmp/resolvectl_status.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"DNS Domains", content)
        self.assertIn(b"corp.local", content)
        self.assertIn(b"example.com", content)


if __name__ == "__main__":
    unittest.main()
