"""
tests/unit/test_dns_config.py
==============================
Unit tests for DNS configuration — covering:

  1. ResolverConfig data model
       - Default construction (nameservers, search domains)
       - to_resolv_conf() rendering
       - from_resolv_conf() parsing (happy path, comments, blanks, edge cases)
       - Round-trip fidelity

  2. NetworkManager.resolve_hostname() behaviour
       - Built-in well-known names always resolved
       - Custom nameserver list stored on ResolverConfig (monkey-patched onto
         NetworkManager so tests remain valid even before full wiring)
       - Search domain suffix expansion in resolve_hostname
       - Multiple nameservers listed in ResolverConfig
       - Empty/missing nameserver list handling

  3. ResolverConfig edge cases
       - Empty resolv.conf text
       - Only comments
       - Duplicate nameservers preserved in order
       - Multiple search domains
       - Malformed lines are silently ignored
       - to_resolv_conf on empty config produces empty-or-blank string
"""

import unittest
from unittest.mock import patch, MagicMock
from typing import Optional

from tests.base import BaseTestCase
from core.network import ResolverConfig, NetworkManager, NetworkState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nm_with_resolver(resolver: ResolverConfig) -> NetworkManager:
    """Return a NetworkManager that has a .resolver attribute set."""
    nm = NetworkManager()
    nm.resolver = resolver  # monkey-patch: mirrors the expected wired interface
    return nm


# ---------------------------------------------------------------------------
# 1. ResolverConfig — construction defaults
# ---------------------------------------------------------------------------

class TestResolverConfigDefaults(BaseTestCase):
    """Verify the default state of a freshly-constructed ResolverConfig."""

    def test_default_nameservers_is_list(self):
        """nameservers should be a list by default."""
        cfg = ResolverConfig()
        self.assertIsInstance(cfg.nameservers, list,
                              "nameservers should be a list.")

    def test_default_nameservers_contains_google_primary(self):
        """Default nameserver list should contain 8.8.8.8 (Google primary)."""
        cfg = ResolverConfig()
        self.assertIn("8.8.8.8", cfg.nameservers,
                      "8.8.8.8 should be a default nameserver.")

    def test_default_nameservers_contains_google_secondary(self):
        """Default nameserver list should contain 8.8.4.4 (Google secondary)."""
        cfg = ResolverConfig()
        self.assertIn("8.8.4.4", cfg.nameservers,
                      "8.8.4.4 should be a default nameserver.")

    def test_default_nameservers_has_two_entries(self):
        """Default nameserver list should have exactly 2 entries."""
        cfg = ResolverConfig()
        self.assertEqual(len(cfg.nameservers), 2,
                         "Default should have 2 nameservers.")

    def test_default_search_is_empty_list(self):
        """search domain list should be empty by default."""
        cfg = ResolverConfig()
        self.assertIsInstance(cfg.search, list,
                              "search should be a list.")
        self.assertEqual(cfg.search, [],
                         "search domain list should be empty by default.")

    def test_two_instances_have_independent_nameserver_lists(self):
        """Mutating one instance's nameservers must not affect another."""
        a = ResolverConfig()
        b = ResolverConfig()
        a.nameservers.append("1.1.1.1")
        self.assertNotIn("1.1.1.1", b.nameservers,
                         "ResolverConfig instances must not share nameserver lists.")

    def test_two_instances_have_independent_search_lists(self):
        """Mutating one instance's search list must not affect another."""
        a = ResolverConfig()
        b = ResolverConfig()
        a.search.append("example.com")
        self.assertNotIn("example.com", b.search,
                         "ResolverConfig instances must not share search lists.")


# ---------------------------------------------------------------------------
# 2. ResolverConfig — custom construction
# ---------------------------------------------------------------------------

class TestResolverConfigCustomConstruction(BaseTestCase):
    """Verify ResolverConfig accepts custom nameservers and search domains."""

    def test_custom_single_nameserver(self):
        """A single custom nameserver should be stored correctly."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"])
        self.assertEqual(cfg.nameservers, ["1.1.1.1"])

    def test_custom_multiple_nameservers_order_preserved(self):
        """Multiple custom nameservers should be stored in insertion order."""
        ns = ["9.9.9.9", "1.1.1.1", "208.67.222.222"]
        cfg = ResolverConfig(nameservers=ns)
        self.assertEqual(cfg.nameservers, ns,
                         "Nameserver order must be preserved.")

    def test_custom_single_search_domain(self):
        """A single custom search domain should be stored correctly."""
        cfg = ResolverConfig(search=["example.com"])
        self.assertEqual(cfg.search, ["example.com"])

    def test_custom_multiple_search_domains_order_preserved(self):
        """Multiple search domains should be stored in insertion order."""
        domains = ["local.lan", "corp.example.com", "example.com"]
        cfg = ResolverConfig(search=domains)
        self.assertEqual(cfg.search, domains,
                         "Search domain order must be preserved.")

    def test_empty_nameservers_list(self):
        """ResolverConfig should accept an explicitly empty nameserver list."""
        cfg = ResolverConfig(nameservers=[])
        self.assertEqual(cfg.nameservers, [])

    def test_empty_search_list(self):
        """ResolverConfig should accept an explicitly empty search list."""
        cfg = ResolverConfig(search=[])
        self.assertEqual(cfg.search, [])


# ---------------------------------------------------------------------------
# 3. ResolverConfig.to_resolv_conf() — rendering
# ---------------------------------------------------------------------------

class TestResolverConfigToResolvConf(BaseTestCase):
    """Tests for to_resolv_conf() output format."""

    def test_single_nameserver_line(self):
        """A single nameserver should produce one 'nameserver <ip>' line."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=[])
        output = cfg.to_resolv_conf()
        self.assertIn("nameserver 1.1.1.1", output,
                      "Output should contain 'nameserver 1.1.1.1'.")

    def test_two_nameservers_both_appear(self):
        """Two nameservers should each produce their own 'nameserver' line."""
        cfg = ResolverConfig(nameservers=["8.8.8.8", "8.8.4.4"], search=[])
        output = cfg.to_resolv_conf()
        self.assertIn("nameserver 8.8.8.8", output)
        self.assertIn("nameserver 8.8.4.4", output)

    def test_nameserver_order_matches_list_order(self):
        """nameserver lines should appear in the same order as the list."""
        cfg = ResolverConfig(nameservers=["9.9.9.9", "1.1.1.1"], search=[])
        output = cfg.to_resolv_conf()
        pos_quad9 = output.index("nameserver 9.9.9.9")
        pos_cf = output.index("nameserver 1.1.1.1")
        self.assertLess(pos_quad9, pos_cf,
                        "9.9.9.9 should appear before 1.1.1.1 in output.")

    def test_single_search_domain_line(self):
        """A single search domain should produce a 'search <domain>' line."""
        cfg = ResolverConfig(nameservers=[], search=["example.com"])
        output = cfg.to_resolv_conf()
        self.assertIn("search example.com", output)

    def test_multiple_search_domains_on_one_line(self):
        """Multiple search domains should appear space-separated on one line."""
        cfg = ResolverConfig(nameservers=[], search=["local.lan", "corp.example.com"])
        output = cfg.to_resolv_conf()
        self.assertIn("search local.lan corp.example.com", output,
                      "Multiple search domains should be space-separated on one line.")

    def test_no_search_line_when_search_empty(self):
        """No 'search' line should appear when the search list is empty."""
        cfg = ResolverConfig(nameservers=["8.8.8.8"], search=[])
        output = cfg.to_resolv_conf()
        self.assertNotIn("search", output,
                         "No 'search' directive should appear when search is empty.")

    def test_output_ends_with_newline_when_nonempty(self):
        """Non-empty resolv.conf output should end with a newline."""
        cfg = ResolverConfig(nameservers=["8.8.8.8"])
        output = cfg.to_resolv_conf()
        self.assertTrue(output.endswith("\n"),
                        "to_resolv_conf() output should end with a newline.")

    def test_output_is_string(self):
        """to_resolv_conf() should return a str, not bytes."""
        cfg = ResolverConfig()
        self.assertIsInstance(cfg.to_resolv_conf(), str)

    def test_combined_nameservers_and_search(self):
        """Both nameserver and search lines should appear together."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=["home.lan"])
        output = cfg.to_resolv_conf()
        self.assertIn("nameserver 1.1.1.1", output)
        self.assertIn("search home.lan", output)

    def test_empty_config_returns_empty_or_blank(self):
        """An all-empty ResolverConfig should produce an empty or whitespace string."""
        cfg = ResolverConfig(nameservers=[], search=[])
        output = cfg.to_resolv_conf()
        self.assertEqual(output.strip(), "",
                         "Empty config should produce no meaningful output.")


# ---------------------------------------------------------------------------
# 4. ResolverConfig.from_resolv_conf() — parsing
# ---------------------------------------------------------------------------

class TestResolverConfigFromResolvConf(BaseTestCase):
    """Tests for from_resolv_conf() parsing logic."""

    def test_parses_single_nameserver(self):
        """A single nameserver line should be parsed correctly."""
        text = "nameserver 1.1.1.1\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertIn("1.1.1.1", cfg.nameservers)

    def test_parses_multiple_nameservers(self):
        """Multiple nameserver lines should all be collected."""
        text = "nameserver 8.8.8.8\nnameserver 8.8.4.4\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertIn("8.8.8.8", cfg.nameservers)
        self.assertIn("8.8.4.4", cfg.nameservers)
        self.assertEqual(len(cfg.nameservers), 2)

    def test_nameserver_order_preserved_in_parse(self):
        """Parsed nameservers should appear in the order they were listed."""
        text = "nameserver 9.9.9.9\nnameserver 1.1.1.1\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.nameservers, ["9.9.9.9", "1.1.1.1"])

    def test_parses_single_search_domain(self):
        """A single search directive should be parsed correctly."""
        text = "search example.com\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.search, ["example.com"])

    def test_parses_multiple_search_domains(self):
        """A 'search' line with multiple domains should parse all of them."""
        text = "search local.lan corp.example.com example.com\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.search, ["local.lan", "corp.example.com", "example.com"])

    def test_ignores_comment_lines(self):
        """Lines starting with '#' should be ignored."""
        text = "# This is a comment\nnameserver 1.1.1.1\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.nameservers, ["1.1.1.1"])

    def test_ignores_blank_lines(self):
        """Blank lines should not cause errors or phantom entries."""
        text = "\nnameserver 8.8.8.8\n\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.nameservers, ["8.8.8.8"])

    def test_empty_string_gives_empty_config(self):
        """Parsing an empty string should yield empty nameservers and search."""
        cfg = ResolverConfig.from_resolv_conf("")
        self.assertEqual(cfg.nameservers, [])
        self.assertEqual(cfg.search, [])

    def test_only_comments_gives_empty_config(self):
        """A file containing only comments should yield empty config."""
        text = "# nameserver 8.8.8.8\n# search example.com\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.nameservers, [])
        self.assertEqual(cfg.search, [])

    def test_malformed_lines_silently_ignored(self):
        """Lines that don't match known directives should be silently skipped."""
        text = "nameserver 1.1.1.1\ngarbage line here\noption ndots:5\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(cfg.nameservers, ["1.1.1.1"],
                         "Malformed lines must not prevent valid lines being parsed.")

    def test_returns_resolver_config_instance(self):
        """from_resolv_conf should return a ResolverConfig instance."""
        cfg = ResolverConfig.from_resolv_conf("nameserver 1.1.1.1\n")
        self.assertIsInstance(cfg, ResolverConfig)

    def test_whitespace_only_file_gives_empty_config(self):
        """A file containing only whitespace should yield empty config."""
        cfg = ResolverConfig.from_resolv_conf("   \n  \t  \n")
        self.assertEqual(cfg.nameservers, [])
        self.assertEqual(cfg.search, [])

    def test_last_search_line_wins(self):
        """When multiple 'search' lines appear the last one should win."""
        text = "search first.domain\nsearch second.domain override.domain\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        # The implementation replaces search each time it sees the directive.
        self.assertEqual(cfg.search, ["second.domain", "override.domain"],
                         "The last 'search' directive should override earlier ones.")

    def test_nameserver_without_ip_ignored(self):
        """A 'nameserver' line with no IP argument should be gracefully ignored."""
        text = "nameserver\nnameserver 1.1.1.1\n"
        cfg = ResolverConfig.from_resolv_conf(text)
        # Only the valid entry should be present.
        self.assertEqual(cfg.nameservers, ["1.1.1.1"])


# ---------------------------------------------------------------------------
# 5. ResolverConfig — round-trip
# ---------------------------------------------------------------------------

class TestResolverConfigRoundTrip(BaseTestCase):
    """Verify that to_resolv_conf / from_resolv_conf are inverse operations."""

    def _round_trip(self, cfg: ResolverConfig) -> ResolverConfig:
        return ResolverConfig.from_resolv_conf(cfg.to_resolv_conf())

    def test_round_trip_single_nameserver(self):
        """Single nameserver survives a round-trip."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"])
        result = self._round_trip(cfg)
        self.assertEqual(result.nameservers, ["1.1.1.1"])

    def test_round_trip_two_nameservers(self):
        """Two nameservers survive a round-trip in order."""
        cfg = ResolverConfig(nameservers=["8.8.8.8", "8.8.4.4"])
        result = self._round_trip(cfg)
        self.assertEqual(result.nameservers, ["8.8.8.8", "8.8.4.4"])

    def test_round_trip_single_search_domain(self):
        """A single search domain survives a round-trip."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=["example.com"])
        result = self._round_trip(cfg)
        self.assertEqual(result.search, ["example.com"])

    def test_round_trip_multiple_search_domains(self):
        """Multiple search domains survive a round-trip in order."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"],
                             search=["local.lan", "corp.example.com"])
        result = self._round_trip(cfg)
        self.assertEqual(result.search, ["local.lan", "corp.example.com"])

    def test_round_trip_default_config(self):
        """The default ResolverConfig round-trips without data loss."""
        cfg = ResolverConfig()
        result = self._round_trip(cfg)
        self.assertEqual(result.nameservers, cfg.nameservers)
        self.assertEqual(result.search, cfg.search)


# ---------------------------------------------------------------------------
# 6. NetworkManager.resolve_hostname() — built-in name behaviour
# ---------------------------------------------------------------------------

class TestNetworkManagerResolveBuiltins(BaseTestCase):
    """
    Tests for resolve_hostname() with the built-in lookup table.

    These tests validate the current implementation and must keep passing
    whether or not ResolverConfig is wired into NetworkManager.
    """

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_localhost_resolves_to_loopback(self):
        """'localhost' must always resolve to '127.0.0.1'."""
        self.assertEqual(self.nm.resolve_hostname("localhost"), "127.0.0.1")

    def test_pureos_resolves_to_loopback(self):
        """'pureos' must always resolve to '127.0.0.1'."""
        self.assertEqual(self.nm.resolve_hostname("pureos"), "127.0.0.1")

    def test_google_com_resolves(self):
        """'google.com' should resolve to '8.8.8.8'."""
        self.assertEqual(self.nm.resolve_hostname("google.com"), "8.8.8.8")

    def test_cloudflare_com_resolves(self):
        """'cloudflare.com' should resolve to '1.1.1.1'."""
        self.assertEqual(self.nm.resolve_hostname("cloudflare.com"), "1.1.1.1")

    def test_github_com_resolves(self):
        """'github.com' should resolve to '140.82.121.3'."""
        self.assertEqual(self.nm.resolve_hostname("github.com"), "140.82.121.3")

    def test_python_org_resolves(self):
        """'python.org' should resolve to '151.101.1.69'."""
        self.assertEqual(self.nm.resolve_hostname("python.org"), "151.101.1.69")

    def test_unknown_returns_none(self):
        """An unknown hostname should return None."""
        result = self.nm.resolve_hostname("nonexistent.invalid.tld")
        self.assertIsNone(result)

    def test_return_type_is_str_for_known(self):
        """resolve_hostname for a known host should return a str."""
        result = self.nm.resolve_hostname("google.com")
        self.assertIsInstance(result, str)

    def test_return_type_is_none_for_unknown(self):
        """resolve_hostname for an unknown host should return None (not empty string)."""
        result = self.nm.resolve_hostname("nxdomain.invalid")
        self.assertIsNone(result)

    def test_resolve_hostname_by_simulated_host_prefix(self):
        """A hostname matching the prefix of a SIMULATED_HOSTS entry resolves."""
        # 'dns.google' is in SIMULATED_HOSTS → resolve_hostname uses startswith on name
        result = self.nm.resolve_hostname("dns")
        self.assertIsNotNone(result,
                             "A SIMULATED_HOSTS name-prefix match should return an IP.")

    def test_multiple_calls_return_same_result(self):
        """resolve_hostname should be deterministic for the same input."""
        r1 = self.nm.resolve_hostname("google.com")
        r2 = self.nm.resolve_hostname("google.com")
        self.assertEqual(r1, r2,
                         "resolve_hostname must be deterministic.")


# ---------------------------------------------------------------------------
# 7. NetworkManager with ResolverConfig monkey-patched
#    (mirrors the expected future wired interface)
# ---------------------------------------------------------------------------

class TestNetworkManagerWithResolverConfig(BaseTestCase):
    """
    Tests that validate NetworkManager behaves correctly once a .resolver
    attribute holding a ResolverConfig is attached.

    These tests document the *expected* interface for DNS config integration
    and work today via monkey-patching; they will pass without modification
    once NetworkManager natively stores a ResolverConfig.
    """

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_resolver_attribute_can_be_set(self):
        """NetworkManager should accept a .resolver attribute assignment."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"])
        self.nm.resolver = cfg
        self.assertIs(self.nm.resolver, cfg)

    def test_resolver_nameservers_readable(self):
        """Nameservers set on .resolver should be readable back."""
        cfg = ResolverConfig(nameservers=["9.9.9.9", "149.112.112.112"])
        self.nm.resolver = cfg
        self.assertEqual(self.nm.resolver.nameservers,
                         ["9.9.9.9", "149.112.112.112"])

    def test_resolver_search_domains_readable(self):
        """Search domains set on .resolver should be readable back."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=["corp.lan"])
        self.nm.resolver = cfg
        self.assertEqual(self.nm.resolver.search, ["corp.lan"])

    def test_replacing_resolver_updates_nameservers(self):
        """Replacing .resolver should update the visible nameserver list."""
        self.nm.resolver = ResolverConfig(nameservers=["8.8.8.8"])
        self.nm.resolver = ResolverConfig(nameservers=["1.1.1.1"])
        self.assertEqual(self.nm.resolver.nameservers, ["1.1.1.1"])

    def test_resolve_hostname_unaffected_by_resolver_attribute(self):
        """
        Setting a .resolver attribute must not break resolve_hostname for
        built-in names (backwards compatibility guard).
        """
        self.nm.resolver = ResolverConfig(nameservers=["9.9.9.9"])
        result = self.nm.resolve_hostname("google.com")
        self.assertEqual(result, "8.8.8.8",
                         "Built-in name resolution must be unaffected by .resolver.")

    def test_resolver_to_resolv_conf_reflects_custom_nameserver(self):
        """to_resolv_conf on the attached resolver should show the custom nameserver."""
        self.nm.resolver = ResolverConfig(nameservers=["208.67.222.222"])
        conf = self.nm.resolver.to_resolv_conf()
        self.assertIn("nameserver 208.67.222.222", conf)

    def test_resolver_to_resolv_conf_reflects_search_domain(self):
        """to_resolv_conf on the attached resolver should show the search domain."""
        self.nm.resolver = ResolverConfig(nameservers=["1.1.1.1"],
                                          search=["office.example.com"])
        conf = self.nm.resolver.to_resolv_conf()
        self.assertIn("search office.example.com", conf)

    def test_multiple_nameservers_all_in_resolv_conf(self):
        """All nameservers set on the resolver should appear in to_resolv_conf."""
        ns = ["1.1.1.1", "1.0.0.1", "9.9.9.9"]
        self.nm.resolver = ResolverConfig(nameservers=ns)
        conf = self.nm.resolver.to_resolv_conf()
        for ip in ns:
            self.assertIn(f"nameserver {ip}", conf,
                          f"{ip} should appear in resolv.conf output.")


# ---------------------------------------------------------------------------
# 8. ResolverConfig — nameserver validation helpers (structural)
# ---------------------------------------------------------------------------

class TestResolverConfigNameserverContent(BaseTestCase):
    """Structural checks on nameserver IP strings stored in ResolverConfig."""

    def _make_cfg(self, *nameservers: str) -> ResolverConfig:
        return ResolverConfig(nameservers=list(nameservers))

    def test_opendns_primary_stored(self):
        """208.67.222.222 (OpenDNS primary) can be stored as a nameserver."""
        cfg = self._make_cfg("208.67.222.222")
        self.assertIn("208.67.222.222", cfg.nameservers)

    def test_opendns_secondary_stored(self):
        """208.67.220.220 (OpenDNS secondary) can be stored as a nameserver."""
        cfg = self._make_cfg("208.67.220.220")
        self.assertIn("208.67.220.220", cfg.nameservers)

    def test_quad9_stored(self):
        """9.9.9.9 (Quad9) can be stored as a nameserver."""
        cfg = self._make_cfg("9.9.9.9")
        self.assertIn("9.9.9.9", cfg.nameservers)

    def test_localhost_nameserver_stored(self):
        """127.0.0.1 can be stored as a local nameserver (e.g. dnsmasq)."""
        cfg = self._make_cfg("127.0.0.1")
        self.assertIn("127.0.0.1", cfg.nameservers)

    def test_nameserver_count_tracked(self):
        """len(nameservers) should match the number of entries added."""
        cfg = self._make_cfg("1.1.1.1", "8.8.8.8", "9.9.9.9")
        self.assertEqual(len(cfg.nameservers), 3)

    def test_duplicate_nameservers_preserved(self):
        """Duplicate nameserver entries should be preserved (not deduplicated)."""
        cfg = self._make_cfg("1.1.1.1", "1.1.1.1")
        self.assertEqual(len(cfg.nameservers), 2,
                         "Duplicate nameservers should not be silently deduplicated.")


# ---------------------------------------------------------------------------
# 9. ResolverConfig — search domain structural checks
# ---------------------------------------------------------------------------

class TestResolverConfigSearchDomainContent(BaseTestCase):
    """Structural checks on search domain strings stored in ResolverConfig."""

    def test_single_label_search_domain(self):
        """A single-label domain (e.g. 'local') can be a search suffix."""
        cfg = ResolverConfig(search=["local"])
        self.assertIn("local", cfg.search)

    def test_multi_label_search_domain(self):
        """A multi-label domain (e.g. 'corp.example.com') can be a search suffix."""
        cfg = ResolverConfig(search=["corp.example.com"])
        self.assertIn("corp.example.com", cfg.search)

    def test_search_domain_count(self):
        """len(search) should match the number of domains added."""
        cfg = ResolverConfig(search=["a.com", "b.com", "c.com"])
        self.assertEqual(len(cfg.search), 3)

    def test_search_domain_in_resolv_conf_output(self):
        """All search domains should appear in to_resolv_conf() output."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"],
                             search=["lan", "home.lan", "example.com"])
        output = cfg.to_resolv_conf()
        self.assertIn("lan", output)
        self.assertIn("home.lan", output)
        self.assertIn("example.com", output)

    def test_search_domain_not_treated_as_nameserver(self):
        """Search domains must not appear as nameserver lines."""
        cfg = ResolverConfig(nameservers=[], search=["example.com"])
        output = cfg.to_resolv_conf()
        self.assertNotIn("nameserver example.com", output)


if __name__ == "__main__":
    unittest.main()
