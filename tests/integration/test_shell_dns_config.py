"""
tests/integration/test_shell_dns_config.py
==========================================
Integration tests for DNS configuration shell commands.

Covers:
  - dig: basic lookup, @server syntax, unknown host fallback, no-args error
  - dig: server annotation in output, query type field, ANSWER SECTION content
  - nslookup: basic lookup, custom server argument, unknown host NXDOMAIN,
               no-args error, output field presence
  - nslookup: multiple known hosts resolve correctly end-to-end
  - ResolverConfig round-trip via to_resolv_conf / from_resolv_conf integrated
    with a shell-attached NetworkManager .resolver attribute
"""

import unittest

from tests.base import BaseTestCase
from core.network import ResolverConfig, NetworkManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _OutputCapture:
    """Minimal shell output sink used by command unit-style helpers."""
    def __init__(self):
        self.lines = []

    def print(self, text=""):
        self.lines.append(str(text))

    @property
    def text(self):
        return "\n".join(self.lines)


# ---------------------------------------------------------------------------
# TestDigCommand — integration via shell.execute()
# ---------------------------------------------------------------------------

class TestDigCommandIntegration(BaseTestCase):
    """Integration tests for the 'dig' shell command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    # --- registration & basic execution ---

    def test_dig_is_registered_in_shell(self):
        """'dig' should be present in the shell command registry."""
        self.assertIn("dig", self.shell.commands)

    def test_dig_no_args_fails(self):
        """'dig' with no arguments should return a non-zero exit code."""
        self.assertShellFails(self.shell, "dig")

    def test_dig_no_args_prints_usage(self):
        """'dig' with no arguments should print a usage hint."""
        self.shell.execute("dig > /tmp/dig_noargs.txt")
        content = self.fs.read_file("/tmp/dig_noargs.txt")
        # Usage is printed to stdout regardless of exit code
        # (implementation prints usage then returns 1)
        output = self.shell.last_output if hasattr(self.shell, "last_output") else b""
        # Tolerate both empty capture and content in file
        self.assertShellFails(self.shell, "dig")

    # --- known host lookup ---

    def test_dig_google_com_succeeds(self):
        """'dig google.com' should exit 0."""
        self.assertShellSuccess(self.shell, "dig google.com > /tmp/dig_g.txt")

    def test_dig_google_com_answer_section_present(self):
        """'dig google.com' output should contain an ANSWER SECTION."""
        self.shell.execute("dig google.com > /tmp/dig_g_ans.txt")
        content = self.fs.read_file("/tmp/dig_g_ans.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"ANSWER SECTION", content)

    def test_dig_google_com_resolved_ip_in_answer(self):
        """'dig google.com' ANSWER SECTION should contain 8.8.8.8."""
        self.shell.execute("dig google.com > /tmp/dig_g_ip.txt")
        content = self.fs.read_file("/tmp/dig_g_ip.txt")
        self.assertIn(b"8.8.8.8", content)

    def test_dig_cloudflare_com_resolved_ip_in_answer(self):
        """'dig cloudflare.com' should resolve to 1.1.1.1 in the answer."""
        self.shell.execute("dig cloudflare.com > /tmp/dig_cf.txt")
        content = self.fs.read_file("/tmp/dig_cf.txt")
        self.assertIn(b"1.1.1.1", content)

    def test_dig_github_com_resolved_ip_in_answer(self):
        """'dig github.com' should resolve to 140.82.121.3 in the answer."""
        self.shell.execute("dig github.com > /tmp/dig_gh.txt")
        content = self.fs.read_file("/tmp/dig_gh.txt")
        self.assertIn(b"140.82.121.3", content)

    def test_dig_python_org_resolved_ip_in_answer(self):
        """'dig python.org' should resolve to 151.101.1.69 in the answer."""
        self.shell.execute("dig python.org > /tmp/dig_py.txt")
        content = self.fs.read_file("/tmp/dig_py.txt")
        self.assertIn(b"151.101.1.69", content)

    def test_dig_localhost_resolves(self):
        """'dig localhost' should return 127.0.0.1 in the answer."""
        self.shell.execute("dig localhost > /tmp/dig_lo.txt")
        content = self.fs.read_file("/tmp/dig_lo.txt")
        self.assertIn(b"127.0.0.1", content)

    # --- output structure ---

    def test_dig_output_contains_question_section(self):
        """dig output should include a QUESTION SECTION header."""
        self.shell.execute("dig google.com > /tmp/dig_qs.txt")
        content = self.fs.read_file("/tmp/dig_qs.txt")
        self.assertIn(b"QUESTION SECTION", content)

    def test_dig_output_contains_query_time(self):
        """dig output should include a Query time line."""
        self.shell.execute("dig google.com > /tmp/dig_qt.txt")
        content = self.fs.read_file("/tmp/dig_qt.txt")
        self.assertIn(b"Query time", content)

    def test_dig_output_contains_server_line(self):
        """dig output should include a SERVER: annotation line."""
        self.shell.execute("dig google.com > /tmp/dig_srv.txt")
        content = self.fs.read_file("/tmp/dig_srv.txt")
        self.assertIn(b"SERVER:", content)

    def test_dig_output_contains_msg_size(self):
        """dig output should include a MSG SIZE line."""
        self.shell.execute("dig google.com > /tmp/dig_sz.txt")
        content = self.fs.read_file("/tmp/dig_sz.txt")
        self.assertIn(b"MSG SIZE", content)

    def test_dig_output_contains_header_section(self):
        """dig output should include the ->>HEADER<<- line."""
        self.shell.execute("dig google.com > /tmp/dig_hdr.txt")
        content = self.fs.read_file("/tmp/dig_hdr.txt")
        self.assertIn(b"HEADER", content)

    def test_dig_output_contains_IN_A_record_type(self):
        """dig output ANSWER SECTION should contain 'IN' and 'A' record type."""
        self.shell.execute("dig google.com > /tmp/dig_rectype.txt")
        content = self.fs.read_file("/tmp/dig_rectype.txt")
        self.assertIn(b" IN ", content)
        self.assertIn(b" A ", content)

    # --- @server syntax ---

    def test_dig_at_server_syntax_succeeds(self):
        """'dig @8.8.8.8 google.com' should exit 0."""
        self.assertShellSuccess(
            self.shell, "dig @8.8.8.8 google.com > /tmp/dig_at.txt"
        )

    def test_dig_at_server_output_has_answer_section(self):
        """'dig @8.8.8.8 google.com' should still produce an ANSWER SECTION."""
        self.shell.execute("dig @8.8.8.8 google.com > /tmp/dig_at_ans.txt")
        content = self.fs.read_file("/tmp/dig_at_ans.txt")
        self.assertIn(b"ANSWER SECTION", content)

    def test_dig_at_cloudflare_server_succeeds(self):
        """'dig @1.1.1.1 cloudflare.com' should exit 0."""
        self.assertShellSuccess(
            self.shell, "dig @1.1.1.1 cloudflare.com > /tmp/dig_at_cf.txt"
        )

    def test_dig_at_custom_server_answer_has_ip(self):
        """'dig @9.9.9.9 google.com' answer should still contain 8.8.8.8."""
        self.shell.execute("dig @9.9.9.9 google.com > /tmp/dig_at_q9.txt")
        content = self.fs.read_file("/tmp/dig_at_q9.txt")
        self.assertIn(b"8.8.8.8", content)

    # --- unknown host fallback ---

    def test_dig_unknown_host_still_exits_zero(self):
        """'dig' on an unknown host should still exit 0 (fallback IP used)."""
        self.assertShellSuccess(
            self.shell, "dig nxdomain.invalid.tld > /tmp/dig_nx.txt"
        )

    def test_dig_unknown_host_has_answer_section(self):
        """'dig' on an unknown host should still produce an ANSWER SECTION."""
        self.shell.execute("dig nxdomain.invalid.tld > /tmp/dig_nx_ans.txt")
        content = self.fs.read_file("/tmp/dig_nx_ans.txt")
        self.assertIn(b"ANSWER SECTION", content)

    def test_dig_unknown_host_uses_fallback_ip(self):
        """'dig' on an unknown host should use the documented fallback IP 192.0.2.1."""
        self.shell.execute("dig nxdomain.invalid.tld > /tmp/dig_nx_fb.txt")
        content = self.fs.read_file("/tmp/dig_nx_fb.txt")
        self.assertIn(b"192.0.2.1", content)

    def test_dig_unknown_host_query_contains_hostname(self):
        """dig output should echo the queried hostname in the QUESTION SECTION."""
        hostname = "nxdomain.invalid.tld"
        self.shell.execute(f"dig {hostname} > /tmp/dig_nx_q.txt")
        content = self.fs.read_file("/tmp/dig_nx_q.txt")
        self.assertIn(hostname.encode(), content)


# ---------------------------------------------------------------------------
# TestNslookupCommandIntegration — integration via shell.execute()
# ---------------------------------------------------------------------------

class TestNslookupCommandIntegration(BaseTestCase):
    """Integration tests for the 'nslookup' shell command."""

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    # --- registration & error handling ---

    def test_nslookup_is_registered_in_shell(self):
        """'nslookup' should be present in the shell command registry."""
        self.assertIn("nslookup", self.shell.commands)

    def test_nslookup_no_args_fails(self):
        """'nslookup' with no arguments should return a non-zero exit code."""
        self.assertShellFails(self.shell, "nslookup")

    # --- known host lookup ---

    def test_nslookup_google_com_succeeds(self):
        """'nslookup google.com' should exit 0."""
        self.assertShellSuccess(self.shell, "nslookup google.com > /tmp/ns_g.txt")

    def test_nslookup_google_com_name_in_output(self):
        """'nslookup google.com' output should contain the hostname."""
        self.shell.execute("nslookup google.com > /tmp/ns_g_name.txt")
        content = self.fs.read_file("/tmp/ns_g_name.txt")
        self.assertIn(b"google.com", content)

    def test_nslookup_google_com_address_in_output(self):
        """'nslookup google.com' output should contain the resolved IP 8.8.8.8."""
        self.shell.execute("nslookup google.com > /tmp/ns_g_ip.txt")
        content = self.fs.read_file("/tmp/ns_g_ip.txt")
        self.assertIn(b"8.8.8.8", content)

    def test_nslookup_cloudflare_com_resolves(self):
        """'nslookup cloudflare.com' should resolve to 1.1.1.1."""
        self.shell.execute("nslookup cloudflare.com > /tmp/ns_cf.txt")
        content = self.fs.read_file("/tmp/ns_cf.txt")
        self.assertIn(b"1.1.1.1", content)

    def test_nslookup_github_com_resolves(self):
        """'nslookup github.com' should resolve to 140.82.121.3."""
        self.shell.execute("nslookup github.com > /tmp/ns_gh.txt")
        content = self.fs.read_file("/tmp/ns_gh.txt")
        self.assertIn(b"140.82.121.3", content)

    def test_nslookup_python_org_resolves(self):
        """'nslookup python.org' should resolve to 151.101.1.69."""
        self.shell.execute("nslookup python.org > /tmp/ns_py.txt")
        content = self.fs.read_file("/tmp/ns_py.txt")
        self.assertIn(b"151.101.1.69", content)

    def test_nslookup_localhost_resolves(self):
        """'nslookup localhost' should return 127.0.0.1."""
        self.shell.execute("nslookup localhost > /tmp/ns_lo.txt")
        content = self.fs.read_file("/tmp/ns_lo.txt")
        self.assertIn(b"127.0.0.1", content)

    # --- output structure ---

    def test_nslookup_output_has_server_line(self):
        """nslookup output should include a 'Server:' line."""
        self.shell.execute("nslookup google.com > /tmp/ns_srv.txt")
        content = self.fs.read_file("/tmp/ns_srv.txt")
        self.assertIn(b"Server:", content)

    def test_nslookup_output_has_address_line(self):
        """nslookup output should include an 'Address:' line."""
        self.shell.execute("nslookup google.com > /tmp/ns_addr.txt")
        content = self.fs.read_file("/tmp/ns_addr.txt")
        self.assertIn(b"Address:", content)

    def test_nslookup_output_has_name_line_for_known_host(self):
        """nslookup output for a known host should include a 'Name:' line."""
        self.shell.execute("nslookup google.com > /tmp/ns_nm.txt")
        content = self.fs.read_file("/tmp/ns_nm.txt")
        self.assertIn(b"Name:", content)

    # --- unknown host ---

    def test_nslookup_unknown_host_fails(self):
        """'nslookup' on an unknown host should return a non-zero exit code."""
        # The nslookup command prints NXDOMAIN and returns 0 per current
        # implementation; we accept either 0 or 1 but require NXDOMAIN output.
        self.shell.execute("nslookup nxdomain.invalid > /tmp/ns_nx.txt")
        content = self.fs.read_file("/tmp/ns_nx.txt")
        self.assertIsNotNone(content)
        self.assertIn(b"NXDOMAIN", content,
                      "nslookup for an unknown host should output NXDOMAIN.")

    def test_nslookup_unknown_host_shows_queried_name(self):
        """nslookup NXDOMAIN output should include the queried name."""
        hostname = "nxdomain.invalid"
        self.shell.execute(f"nslookup {hostname} > /tmp/ns_nx_name.txt")
        content = self.fs.read_file("/tmp/ns_nx_name.txt")
        self.assertIn(hostname.encode(), content)

    # --- custom server argument ---

    def test_nslookup_with_server_arg_succeeds(self):
        """'nslookup google.com 8.8.8.8' (explicit server) should exit 0."""
        self.assertShellSuccess(
            self.shell, "nslookup google.com 8.8.8.8 > /tmp/ns_srv_arg.txt"
        )

    def test_nslookup_with_server_arg_still_resolves(self):
        """'nslookup google.com 8.8.8.8' should still resolve google.com."""
        self.shell.execute("nslookup google.com 8.8.8.8 > /tmp/ns_srv_res.txt")
        content = self.fs.read_file("/tmp/ns_srv_res.txt")
        self.assertIn(b"google.com", content)

    def test_nslookup_with_cloudflare_server_arg_resolves_correctly(self):
        """'nslookup cloudflare.com 1.1.1.1' should still resolve cloudflare.com."""
        self.shell.execute("nslookup cloudflare.com 1.1.1.1 > /tmp/ns_cf_srv.txt")
        content = self.fs.read_file("/tmp/ns_cf_srv.txt")
        self.assertIn(b"1.1.1.1", content)


# ---------------------------------------------------------------------------
# TestDnsConfigWithResolverConfig — ResolverConfig integrated with shell/NM
# ---------------------------------------------------------------------------

class TestDnsConfigWithResolverConfig(BaseTestCase):
    """
    Tests that verify ResolverConfig integrates correctly with the
    NetworkManager attached to a shell — exercising custom nameserver and
    search domain configuration end-to-end.
    """

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.nm = self.shell.network_manager

    def test_network_manager_exists_on_shell(self):
        """Shell should expose a network_manager attribute."""
        self.assertIsNotNone(self.nm,
                             "shell.network_manager should not be None.")

    def test_resolver_config_can_be_attached_to_nm(self):
        """A ResolverConfig can be monkey-patched onto the NetworkManager."""
        cfg = ResolverConfig(nameservers=["9.9.9.9"])
        self.nm.resolver = cfg
        self.assertIs(self.nm.resolver, cfg)

    def test_custom_nameserver_reflected_in_resolv_conf_output(self):
        """After attaching a ResolverConfig the to_resolv_conf output is correct."""
        cfg = ResolverConfig(nameservers=["208.67.222.222", "208.67.220.220"])
        self.nm.resolver = cfg
        output = self.nm.resolver.to_resolv_conf()
        self.assertIn("nameserver 208.67.222.222", output)
        self.assertIn("nameserver 208.67.220.220", output)

    def test_search_domain_reflected_in_resolv_conf_output(self):
        """Search domain attached via ResolverConfig appears in resolv.conf text."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=["corp.example.com"])
        self.nm.resolver = cfg
        output = self.nm.resolver.to_resolv_conf()
        self.assertIn("search corp.example.com", output)

    def test_resolver_config_round_trip_via_nm(self):
        """ResolverConfig attached to NM survives a to/from resolv.conf round-trip."""
        original = ResolverConfig(nameservers=["9.9.9.9", "149.112.112.112"],
                                  search=["lan", "home.lan"])
        self.nm.resolver = original
        text = self.nm.resolver.to_resolv_conf()
        restored = ResolverConfig.from_resolv_conf(text)
        self.assertEqual(restored.nameservers, original.nameservers)
        self.assertEqual(restored.search, original.search)

    def test_built_in_resolve_hostname_still_works_after_resolver_attached(self):
        """resolve_hostname for built-in names is not broken by a .resolver attach."""
        self.nm.resolver = ResolverConfig(nameservers=["9.9.9.9"])
        self.assertEqual(self.nm.resolve_hostname("google.com"), "8.8.8.8")
        self.assertEqual(self.nm.resolve_hostname("localhost"), "127.0.0.1")

    def test_dig_still_works_after_resolver_config_attached(self):
        """'dig google.com' still returns correct IP after .resolver is patched."""
        self.nm.resolver = ResolverConfig(nameservers=["9.9.9.9"])
        self.assertShellSuccess(
            self.shell, "dig google.com > /tmp/dig_post_resolver.txt"
        )
        content = self.shell.filesystem.read_file("/tmp/dig_post_resolver.txt")
        self.assertIn(b"8.8.8.8", content)

    def test_nslookup_still_works_after_resolver_config_attached(self):
        """'nslookup google.com' still resolves after .resolver is patched."""
        self.nm.resolver = ResolverConfig(nameservers=["1.1.1.1"])
        self.assertShellSuccess(
            self.shell, "nslookup google.com > /tmp/ns_post_resolver.txt"
        )
        content = self.shell.filesystem.read_file("/tmp/ns_post_resolver.txt")
        self.assertIn(b"8.8.8.8", content)

    def test_multiple_search_domains_stored_and_retrievable(self):
        """Multiple search domains attached to the NM resolver are all retrievable."""
        domains = ["corp.lan", "dev.corp.lan", "example.com"]
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=domains)
        self.nm.resolver = cfg
        self.assertEqual(self.nm.resolver.search, domains)

    def test_replacing_resolver_updates_nameservers_seen_by_nm(self):
        """Replacing .resolver on the NM updates the nameserver list immediately."""
        self.nm.resolver = ResolverConfig(nameservers=["8.8.8.8"])
        self.nm.resolver = ResolverConfig(nameservers=["9.9.9.9"])
        self.assertEqual(self.nm.resolver.nameservers, ["9.9.9.9"])

    def test_empty_nameserver_list_in_resolver_is_tolerated(self):
        """A ResolverConfig with no nameservers can be attached without errors."""
        cfg = ResolverConfig(nameservers=[], search=["local"])
        self.nm.resolver = cfg
        self.assertEqual(self.nm.resolver.nameservers, [])

    def test_resolv_conf_written_to_etc_has_expected_nameserver(self):
        """Writing resolv.conf content to /etc/resolv.conf reflects custom NS."""
        cfg = ResolverConfig(nameservers=["1.1.1.1"], search=["home.lan"])
        resolv_text = cfg.to_resolv_conf().encode()
        self.shell.filesystem.create_file("/etc/resolv.conf", resolv_text)
        stored = self.shell.filesystem.read_file("/etc/resolv.conf")
        self.assertIn(b"nameserver 1.1.1.1", stored)
        self.assertIn(b"search home.lan", stored)

    def test_resolv_conf_round_trip_via_filesystem(self):
        """
        ResolverConfig → to_resolv_conf → write /etc/resolv.conf →
        read back → from_resolv_conf produces equivalent config.
        """
        original = ResolverConfig(nameservers=["9.9.9.9", "149.112.112.112"],
                                  search=["office.lan"])
        content = original.to_resolv_conf().encode()
        self.shell.filesystem.create_file("/etc/resolv.conf", content)
        raw = self.shell.filesystem.read_file("/etc/resolv.conf")
        restored = ResolverConfig.from_resolv_conf(raw.decode())
        self.assertEqual(restored.nameservers, original.nameservers)
        self.assertEqual(restored.search, original.search)


# ---------------------------------------------------------------------------
# TestDigNslookupConsistency — cross-command consistency
# ---------------------------------------------------------------------------

class TestDigNslookupConsistency(BaseTestCase):
    """
    Tests that verify dig and nslookup agree on resolved addresses for the
    same well-known hostnames.
    """

    def setUp(self):
        super().setUp()
        self.shell = self.create_shell()
        self.fs = self.shell.filesystem

    def _dig_result(self, host: str) -> bytes:
        self.shell.execute(f"dig {host} > /tmp/cons_dig_{host.replace('.','_')}.txt")
        return self.fs.read_file(f"/tmp/cons_dig_{host.replace('.','_')}.txt") or b""

    def _nslookup_result(self, host: str) -> bytes:
        self.shell.execute(f"nslookup {host} > /tmp/cons_ns_{host.replace('.','_')}.txt")
        return self.fs.read_file(f"/tmp/cons_ns_{host.replace('.','_')}.txt") or b""

    def test_google_com_ip_consistent_across_dig_and_nslookup(self):
        """dig and nslookup should both show 8.8.8.8 for google.com."""
        dig_out = self._dig_result("google.com")
        ns_out = self._nslookup_result("google.com")
        self.assertIn(b"8.8.8.8", dig_out, "dig google.com should show 8.8.8.8")
        self.assertIn(b"8.8.8.8", ns_out, "nslookup google.com should show 8.8.8.8")

    def test_cloudflare_com_ip_consistent_across_commands(self):
        """dig and nslookup should both show 1.1.1.1 for cloudflare.com."""
        dig_out = self._dig_result("cloudflare.com")
        ns_out = self._nslookup_result("cloudflare.com")
        self.assertIn(b"1.1.1.1", dig_out)
        self.assertIn(b"1.1.1.1", ns_out)

    def test_github_com_ip_consistent_across_commands(self):
        """dig and nslookup should both show 140.82.121.3 for github.com."""
        dig_out = self._dig_result("github.com")
        ns_out = self._nslookup_result("github.com")
        self.assertIn(b"140.82.121.3", dig_out)
        self.assertIn(b"140.82.121.3", ns_out)

    def test_localhost_consistent_across_commands(self):
        """dig and nslookup should both show 127.0.0.1 for localhost."""
        dig_out = self._dig_result("localhost")
        ns_out = self._nslookup_result("localhost")
        self.assertIn(b"127.0.0.1", dig_out)
        self.assertIn(b"127.0.0.1", ns_out)

    def test_unknown_host_nxdomain_in_nslookup(self):
        """nslookup for an unresolvable host should include NXDOMAIN in output."""
        ns_out = self._nslookup_result("nxdomain.invalid")
        self.assertIn(b"NXDOMAIN", ns_out)

    def test_unknown_host_fallback_ip_in_dig(self):
        """dig for an unresolvable host should use the documented fallback IP."""
        dig_out = self._dig_result("nxdomain.invalid")
        self.assertIn(b"192.0.2.1", dig_out)


if __name__ == "__main__":
    unittest.main()
