"""
tests/integration/test_shell_dns.py
====================================
Integration tests for the resolvconf shell command and DNS-aware behaviour
of dig / nslookup.
"""

import unittest

from tests.base import BaseTestCase


class TestResolvconfCommand(BaseTestCase):
    """Integration tests for resolvconf."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        self.nm = self.shell.network_manager

    # --- registration ---

    def test_resolvconf_is_registered(self):
        self.assertIn("resolvconf", self.shell.commands)

    # --- show (no args) ---

    def test_resolvconf_no_args_succeeds(self):
        self.assertShellSuccess(self.shell, "resolvconf > /tmp/rc_show.txt")

    def test_resolvconf_show_contains_nameserver(self):
        self.assertShellSuccess(self.shell, "resolvconf > /tmp/rc_show.txt")
        content = self.fs.read_file("/tmp/rc_show.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"nameserver", content)

    def test_resolvconf_show_contains_default_nameserver(self):
        self.assertShellSuccess(self.shell, "resolvconf > /tmp/rc_show.txt")
        content = self.fs.read_file("/tmp/rc_show.txt")
        self.assertIn(b"8.8.8.8", content)

    # --- -n flag (set nameservers) ---

    def test_resolvconf_set_nameserver_succeeds(self):
        self.assertShellSuccess(self.shell, "resolvconf -n 1.1.1.1")

    def test_resolvconf_set_nameserver_updates_network_manager(self):
        self.shell.execute("resolvconf -n 1.1.1.1")
        self.assertEqual(self.nm.get_resolver_config().nameservers, ["1.1.1.1"])

    def test_resolvconf_set_multiple_nameservers(self):
        self.shell.execute("resolvconf -n 1.1.1.1 9.9.9.9")
        self.assertEqual(self.nm.get_resolver_config().nameservers, ["1.1.1.1", "9.9.9.9"])

    def test_resolvconf_set_nameserver_updates_resolv_conf(self):
        self.shell.execute("resolvconf -n 5.5.5.5")
        self.assertFileContains(self.fs, "/etc/resolv.conf", b"5.5.5.5")

    def test_resolvconf_set_nameserver_removes_old_nameserver_from_file(self):
        self.shell.execute("resolvconf -n 5.5.5.5")
        content = self.fs.read_file("/etc/resolv.conf")
        self.assertNotIn(b"8.8.8.8", content)

    def test_resolvconf_n_no_args_fails(self):
        self.assertShellFails(self.shell, "resolvconf -n")

    # --- -s flag (set search domains) ---

    def test_resolvconf_set_search_succeeds(self):
        self.assertShellSuccess(self.shell, "resolvconf -s example.com")

    def test_resolvconf_set_search_updates_network_manager(self):
        self.shell.execute("resolvconf -s example.com")
        self.assertEqual(self.nm.get_resolver_config().search, ["example.com"])

    def test_resolvconf_set_multiple_search_domains(self):
        self.shell.execute("resolvconf -s a.com b.com")
        self.assertEqual(self.nm.get_resolver_config().search, ["a.com", "b.com"])

    def test_resolvconf_set_search_updates_resolv_conf(self):
        self.shell.execute("resolvconf -s corp.local")
        self.assertFileContains(self.fs, "/etc/resolv.conf", b"search corp.local")

    def test_resolvconf_s_no_args_fails(self):
        self.assertShellFails(self.shell, "resolvconf -s")

    # --- --set flag ---

    def test_resolvconf_set_nameserver_via_set_flag(self):
        self.assertShellSuccess(self.shell, "resolvconf --set nameserver=3.3.3.3")
        self.assertIn("3.3.3.3", self.nm.get_resolver_config().nameservers)

    def test_resolvconf_set_search_via_set_flag(self):
        self.assertShellSuccess(self.shell, "resolvconf --set search=my.domain")
        self.assertIn("my.domain", self.nm.get_resolver_config().search)

    def test_resolvconf_set_unknown_key_fails(self):
        self.assertShellFails(self.shell, "resolvconf --set badkey=value")

    def test_resolvconf_set_missing_equals_fails(self):
        self.assertShellFails(self.shell, "resolvconf --set noequalssign")

    # --- --help ---

    def test_resolvconf_help_succeeds(self):
        self.assertShellSuccess(self.shell, "resolvconf --help > /tmp/rc_help.txt")

    def test_resolvconf_help_output_mentions_usage(self):
        self.assertShellSuccess(self.shell, "resolvconf --help > /tmp/rc_help.txt")
        content = self.fs.read_file("/tmp/rc_help.txt")
        self.assertIn(b"Usage", content)

    # --- unknown option ---

    def test_resolvconf_unknown_option_fails(self):
        self.assertShellFails(self.shell, "resolvconf --unknown")

    # --- show reflects changes ---

    def test_resolvconf_show_reflects_set_nameserver(self):
        self.shell.execute("resolvconf -n 4.4.4.4")
        self.assertShellSuccess(self.shell, "resolvconf > /tmp/rc_after.txt")
        content = self.fs.read_file("/tmp/rc_after.txt")
        self.assertIn(b"4.4.4.4", content)

    def test_resolvconf_show_reflects_set_search(self):
        self.shell.execute("resolvconf -s mynet.local")
        self.assertShellSuccess(self.shell, "resolvconf > /tmp/rc_search.txt")
        content = self.fs.read_file("/tmp/rc_search.txt")
        self.assertIn(b"mynet.local", content)


# ---------------------------------------------------------------------------
# dig — uses configured nameserver in output
# ---------------------------------------------------------------------------

class TestDigUsesConfiguredNameserver(BaseTestCase):
    """dig should report the configured primary nameserver."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        self.nm = self.shell.network_manager

    def test_dig_shows_default_nameserver(self):
        self.assertShellSuccess(self.shell, "dig google.com > /tmp/dig_ns.txt")
        content = self.fs.read_file("/tmp/dig_ns.txt")
        # Default primary nameserver is 8.8.8.8
        self.assertIn(b"8.8.8.8", content)

    def test_dig_shows_custom_nameserver_after_resolvconf(self):
        self.shell.execute("resolvconf -n 1.1.1.1")
        self.assertShellSuccess(self.shell, "dig google.com > /tmp/dig_custom.txt")
        content = self.fs.read_file("/tmp/dig_custom.txt")
        self.assertIn(b"1.1.1.1", content)


# ---------------------------------------------------------------------------
# nslookup — uses configured nameserver in output
# ---------------------------------------------------------------------------

class TestNslookupUsesConfiguredNameserver(BaseTestCase):
    """nslookup should report the configured primary nameserver."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem
        self.nm = self.shell.network_manager

    def test_nslookup_shows_default_nameserver(self):
        self.assertShellSuccess(self.shell, "nslookup google.com > /tmp/ns_default.txt")
        content = self.fs.read_file("/tmp/ns_default.txt")
        self.assertIn(b"8.8.8.8", content)

    def test_nslookup_shows_custom_nameserver_after_resolvconf(self):
        self.shell.execute("resolvconf -n 9.9.9.9")
        self.assertShellSuccess(self.shell, "nslookup google.com > /tmp/ns_custom.txt")
        content = self.fs.read_file("/tmp/ns_custom.txt")
        self.assertIn(b"9.9.9.9", content)


if __name__ == "__main__":
    unittest.main()
