"""
tests/unit/test_dns_config.py
=============================
Unit tests for DNS resolver configuration:
- ResolverConfig dataclass (serialisation, parsing)
- NetworkManager DNS getter/setter methods
- /etc/resolv.conf seeded in FileSystem
- Persistence save/load round-trip for DNS config
"""

import unittest

from tests.base import BaseTestCase
from core.network import NetworkManager, ResolverConfig
from core.filesystem import FileSystem
from core.persistence import PersistenceManager


# ---------------------------------------------------------------------------
# ResolverConfig — construction and defaults
# ---------------------------------------------------------------------------

class TestResolverConfigDefaults(BaseTestCase):
    """ResolverConfig should ship with sensible defaults."""

    def test_default_nameservers(self):
        rc = ResolverConfig()
        self.assertEqual(rc.nameservers, ["8.8.8.8", "8.8.4.4"])

    def test_default_search_is_empty(self):
        rc = ResolverConfig()
        self.assertEqual(rc.search, [])


# ---------------------------------------------------------------------------
# ResolverConfig — to_resolv_conf
# ---------------------------------------------------------------------------

class TestResolverConfigToResolvConf(BaseTestCase):
    """to_resolv_conf should produce valid resolv.conf content."""

    def test_single_nameserver(self):
        rc = ResolverConfig(nameservers=["1.1.1.1"], search=[])
        self.assertIn("nameserver 1.1.1.1", rc.to_resolv_conf())

    def test_multiple_nameservers(self):
        rc = ResolverConfig(nameservers=["1.1.1.1", "9.9.9.9"], search=[])
        text = rc.to_resolv_conf()
        self.assertIn("nameserver 1.1.1.1", text)
        self.assertIn("nameserver 9.9.9.9", text)

    def test_search_domain_included(self):
        rc = ResolverConfig(nameservers=["8.8.8.8"], search=["example.com"])
        self.assertIn("search example.com", rc.to_resolv_conf())

    def test_multiple_search_domains(self):
        rc = ResolverConfig(nameservers=["8.8.8.8"], search=["a.com", "b.com"])
        self.assertIn("search a.com b.com", rc.to_resolv_conf())

    def test_no_search_line_when_empty(self):
        rc = ResolverConfig(nameservers=["8.8.8.8"], search=[])
        self.assertNotIn("search", rc.to_resolv_conf())

    def test_ends_with_newline(self):
        rc = ResolverConfig(nameservers=["8.8.8.8"], search=[])
        self.assertTrue(rc.to_resolv_conf().endswith("\n"))

    def test_empty_config_returns_empty_string(self):
        rc = ResolverConfig(nameservers=[], search=[])
        self.assertEqual(rc.to_resolv_conf(), "")


# ---------------------------------------------------------------------------
# ResolverConfig — from_resolv_conf
# ---------------------------------------------------------------------------

class TestResolverConfigFromResolvConf(BaseTestCase):
    """from_resolv_conf should correctly parse resolv.conf text."""

    def test_parse_single_nameserver(self):
        rc = ResolverConfig.from_resolv_conf("nameserver 1.2.3.4\n")
        self.assertEqual(rc.nameservers, ["1.2.3.4"])

    def test_parse_multiple_nameservers(self):
        text = "nameserver 1.1.1.1\nnameserver 9.9.9.9\n"
        rc = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(rc.nameservers, ["1.1.1.1", "9.9.9.9"])

    def test_parse_search_domain(self):
        text = "nameserver 8.8.8.8\nsearch example.com\n"
        rc = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(rc.search, ["example.com"])

    def test_parse_multiple_search_domains(self):
        text = "nameserver 8.8.8.8\nsearch a.com b.com\n"
        rc = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(rc.search, ["a.com", "b.com"])

    def test_comments_ignored(self):
        text = "# This is a comment\nnameserver 8.8.8.8\n"
        rc = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(rc.nameservers, ["8.8.8.8"])

    def test_blank_lines_ignored(self):
        text = "\n\nnameserver 8.8.8.8\n\n"
        rc = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(rc.nameservers, ["8.8.8.8"])

    def test_empty_string_gives_empty_lists(self):
        rc = ResolverConfig.from_resolv_conf("")
        self.assertEqual(rc.nameservers, [])
        self.assertEqual(rc.search, [])

    def test_round_trip(self):
        original = ResolverConfig(nameservers=["1.1.1.1", "8.8.8.8"], search=["corp.local"])
        parsed = ResolverConfig.from_resolv_conf(original.to_resolv_conf())
        self.assertEqual(parsed.nameservers, original.nameservers)
        self.assertEqual(parsed.search, original.search)


# ---------------------------------------------------------------------------
# NetworkManager — DNS getter/setter
# ---------------------------------------------------------------------------

class TestNetworkManagerDNS(BaseTestCase):
    """NetworkManager should expose and mutate the resolver config."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_get_resolver_config_returns_resolver_config(self):
        self.assertIsInstance(self.nm.get_resolver_config(), ResolverConfig)

    def test_default_nameservers_are_set(self):
        rc = self.nm.get_resolver_config()
        self.assertGreater(len(rc.nameservers), 0)

    def test_set_nameservers_updates_config(self):
        self.nm.set_nameservers(["1.1.1.1"])
        self.assertEqual(self.nm.get_resolver_config().nameservers, ["1.1.1.1"])

    def test_set_nameservers_multiple(self):
        self.nm.set_nameservers(["1.1.1.1", "9.9.9.9"])
        self.assertEqual(self.nm.get_resolver_config().nameservers, ["1.1.1.1", "9.9.9.9"])

    def test_set_search_domains_updates_config(self):
        self.nm.set_search_domains(["example.com"])
        self.assertEqual(self.nm.get_resolver_config().search, ["example.com"])

    def test_set_search_domains_multiple(self):
        self.nm.set_search_domains(["a.com", "b.com"])
        self.assertEqual(self.nm.get_resolver_config().search, ["a.com", "b.com"])

    def test_set_resolver_config_replaces_config(self):
        new_rc = ResolverConfig(nameservers=["5.5.5.5"], search=["new.domain"])
        self.nm.set_resolver_config(new_rc)
        rc = self.nm.get_resolver_config()
        self.assertEqual(rc.nameservers, ["5.5.5.5"])
        self.assertEqual(rc.search, ["new.domain"])

    def test_set_nameservers_does_not_affect_search(self):
        self.nm.set_search_domains(["keep.me"])
        self.nm.set_nameservers(["1.2.3.4"])
        self.assertEqual(self.nm.get_resolver_config().search, ["keep.me"])

    def test_set_search_does_not_affect_nameservers(self):
        self.nm.set_nameservers(["1.2.3.4"])
        self.nm.set_search_domains(["new.domain"])
        self.assertEqual(self.nm.get_resolver_config().nameservers, ["1.2.3.4"])


# ---------------------------------------------------------------------------
# FileSystem — /etc/resolv.conf seeded at boot
# ---------------------------------------------------------------------------

class TestFilesystemResolvConf(BaseTestCase):
    """/etc/resolv.conf must exist and contain nameserver entries after init."""

    def setUp(self):
        super().setUp()
        self.fs = FileSystem()

    def test_resolv_conf_exists(self):
        self.assertFileExists(self.fs, "/etc/resolv.conf")

    def test_resolv_conf_contains_nameserver(self):
        self.assertFileContains(self.fs, "/etc/resolv.conf", b"nameserver")

    def test_resolv_conf_contains_default_nameserver(self):
        self.assertFileContains(self.fs, "/etc/resolv.conf", b"8.8.8.8")


# ---------------------------------------------------------------------------
# Persistence — DNS config save/load round-trip
# ---------------------------------------------------------------------------

class _FakeShell:
    """Minimal shell stub for persistence tests."""
    def __init__(self, nm):
        self.network_manager = nm
        self.environment = {}
        self.aliases = {}
        self.history = []
        self.history_position = 0


class TestPersistenceDNSConfig(BaseTestCase):
    """PersistenceManager should save and restore the DNS resolver config."""

    def _make_pm_and_components(self, state_dir):
        fs = FileSystem()
        nm = NetworkManager()
        shell = _FakeShell(nm)
        kernel = None
        pm = PersistenceManager(state_dir=state_dir)
        return pm, fs, shell, nm, kernel

    def test_save_and_load_nameservers(self):
        with self.temporary_state_dir() as state_dir:
            pm, fs, shell, nm, kernel = self._make_pm_and_components(state_dir)
            nm.set_nameservers(["1.1.1.1", "9.9.9.9"])
            pm.save_state(fs, shell, kernel)

            # Create fresh components and load
            fs2 = FileSystem()
            nm2 = NetworkManager()
            shell2 = _FakeShell(nm2)
            pm.load_state(fs2, shell2, kernel)

            self.assertEqual(nm2.get_resolver_config().nameservers, ["1.1.1.1", "9.9.9.9"])

    def test_save_and_load_search_domains(self):
        with self.temporary_state_dir() as state_dir:
            pm, fs, shell, nm, kernel = self._make_pm_and_components(state_dir)
            nm.set_search_domains(["corp.local", "internal"])
            pm.save_state(fs, shell, kernel)

            fs2 = FileSystem()
            nm2 = NetworkManager()
            shell2 = _FakeShell(nm2)
            pm.load_state(fs2, shell2, kernel)

            self.assertEqual(nm2.get_resolver_config().search, ["corp.local", "internal"])

    def test_load_syncs_resolv_conf_in_vfs(self):
        """After loading, /etc/resolv.conf in the VFS should reflect saved config."""
        with self.temporary_state_dir() as state_dir:
            pm, fs, shell, nm, kernel = self._make_pm_and_components(state_dir)
            nm.set_nameservers(["5.5.5.5"])
            pm.save_state(fs, shell, kernel)

            fs2 = FileSystem()
            nm2 = NetworkManager()
            shell2 = _FakeShell(nm2)
            pm.load_state(fs2, shell2, kernel)

            self.assertFileContains(fs2, "/etc/resolv.conf", b"5.5.5.5")

    def test_save_state_includes_dns_config(self):
        """Saved state file should contain the dns_config key."""
        import json
        with self.temporary_state_dir() as state_dir:
            pm, fs, shell, nm, kernel = self._make_pm_and_components(state_dir)
            nm.set_nameservers(["7.7.7.7"])
            pm.save_state(fs, shell, kernel)

            with open(pm.state_file) as f:
                state = json.load(f)

            self.assertIn("dns_config", state)
            self.assertIn("7.7.7.7", state["dns_config"]["nameservers"])

    def test_load_without_dns_config_in_state_does_not_crash(self):
        """Loading a state file that has no dns_config key should not raise."""
        import json
        with self.temporary_state_dir() as state_dir:
            pm, fs, shell, nm, kernel = self._make_pm_and_components(state_dir)
            pm.save_state(fs, shell, kernel)

            # Remove dns_config from saved state
            with open(pm.state_file) as f:
                state = json.load(f)
            state.pop("dns_config", None)
            with open(pm.state_file, "w") as f:
                json.dump(state, f)

            fs2 = FileSystem()
            nm2 = NetworkManager()
            shell2 = _FakeShell(nm2)
            # Should not raise
            result = pm.load_state(fs2, shell2, kernel)
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
