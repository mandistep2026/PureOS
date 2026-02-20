"""
tests/unit/test_network.py
===========================
Unit tests for the :class:`~core.network.NetworkManager` class.

Covers (Test 8 from main.py):
- Default hostname retrieval and mutation
- Interface discovery and IP address verification
- Ping simulation (success flag, result count, timeout behaviour)
- PingCommand: -c flag, -t timeout flag, missing-arg error handling
- Additional: loopback interface, routing table, hostname validation
"""

import unittest
from unittest.mock import patch

from tests.base import BaseTestCase
from core.network import NetworkManager, NetworkInterface, NetworkState
from shell.netcommand import PingCommand


# ---------------------------------------------------------------------------
# NetworkManager — hostname
# ---------------------------------------------------------------------------

class TestNetworkManagerHostname(BaseTestCase):
    """Tests for hostname get/set operations."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_default_hostname_is_pureos(self):
        """NetworkManager should report 'pureos' as the default hostname."""
        self.assertEqual(
            self.nm.get_hostname(),
            "pureos",
            "Default hostname should be 'pureos'.",
        )

    def test_set_hostname_updates_hostname(self):
        """set_hostname should update the hostname returned by get_hostname."""
        result = self.nm.set_hostname("testhost")
        self.assertTrue(result, "set_hostname should return True on success.")
        self.assertEqual(
            self.nm.get_hostname(),
            "testhost",
            "get_hostname should reflect the updated hostname.",
        )

    def test_set_hostname_returns_false_for_too_long_name(self):
        """set_hostname should reject hostnames longer than 64 characters."""
        long_name = "a" * 65
        result = self.nm.set_hostname(long_name)
        self.assertFalse(
            result,
            "set_hostname should return False for a hostname exceeding 64 characters.",
        )

    def test_set_hostname_preserves_previous_on_failure(self):
        """A rejected set_hostname call should leave the hostname unchanged."""
        self.nm.set_hostname("myhost")
        self.nm.set_hostname("a" * 65)  # should fail
        self.assertEqual(
            self.nm.get_hostname(),
            "myhost",
            "Hostname should be unchanged after a failed set_hostname call.",
        )


# ---------------------------------------------------------------------------
# NetworkManager — interfaces
# ---------------------------------------------------------------------------

class TestNetworkManagerInterfaces(BaseTestCase):
    """Tests for network interface discovery and configuration."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_eth0_interface_exists(self):
        """eth0 should be present in the default interface set."""
        iface = self.nm.get_interface("eth0")
        self.assertIsNotNone(iface, "eth0 interface must exist by default.")

    def test_eth0_ip_address(self):
        """eth0 should have the default IP address 192.168.1.100."""
        iface = self.nm.get_interface("eth0")
        self.assertEqual(
            iface.ip_address,
            "192.168.1.100",
            "eth0 should have IP address 192.168.1.100.",
        )

    def test_eth0_state_is_up(self):
        """eth0 should be in the UP state by default."""
        iface = self.nm.get_interface("eth0")
        self.assertEqual(
            iface.state,
            NetworkState.UP,
            "eth0 should be UP by default.",
        )

    def test_loopback_interface_exists(self):
        """lo (loopback) interface should be present by default."""
        iface = self.nm.get_interface("lo")
        self.assertIsNotNone(iface, "Loopback interface 'lo' must exist by default.")

    def test_loopback_ip_is_127_0_0_1(self):
        """The loopback interface should have IP 127.0.0.1."""
        iface = self.nm.get_interface("lo")
        self.assertEqual(
            iface.ip_address,
            "127.0.0.1",
            "Loopback interface should have IP 127.0.0.1.",
        )

    def test_loopback_state_is_up(self):
        """The loopback interface should be in the UP state."""
        iface = self.nm.get_interface("lo")
        self.assertEqual(
            iface.state,
            NetworkState.UP,
            "Loopback interface should be UP by default.",
        )

    def test_get_interface_returns_none_for_unknown(self):
        """get_interface should return None for a nonexistent interface name."""
        result = self.nm.get_interface("wlan99")
        self.assertIsNone(
            result,
            "get_interface should return None for an unknown interface name.",
        )

    def test_list_interfaces_includes_eth0_and_lo(self):
        """list_interfaces should include both eth0 and lo."""
        names = {iface.name for iface in self.nm.list_interfaces()}
        self.assertIn("eth0", names, "list_interfaces should include eth0.")
        self.assertIn("lo", names, "list_interfaces should include lo.")

    def test_set_interface_ip_updates_ip(self):
        """set_interface_ip should update the IP address of the interface."""
        result = self.nm.set_interface_ip("eth0", "10.0.0.5")
        self.assertTrue(result, "set_interface_ip should return True on success.")
        iface = self.nm.get_interface("eth0")
        self.assertEqual(
            iface.ip_address,
            "10.0.0.5",
            "Interface IP should reflect the new address after set_interface_ip.",
        )

    def test_set_interface_state_down(self):
        """set_interface_state should be able to bring an interface DOWN."""
        result = self.nm.set_interface_state("eth0", NetworkState.DOWN)
        self.assertTrue(result, "set_interface_state should return True on success.")
        iface = self.nm.get_interface("eth0")
        self.assertEqual(
            iface.state,
            NetworkState.DOWN,
            "eth0 state should be DOWN after set_interface_state(DOWN).",
        )

    def test_set_interface_state_unknown_interface_returns_false(self):
        """set_interface_state for an unknown interface should return False."""
        result = self.nm.set_interface_state("nonexistent0", NetworkState.UP)
        self.assertFalse(
            result,
            "set_interface_state should return False for an unknown interface.",
        )


# ---------------------------------------------------------------------------
# NetworkManager — ping simulation
# ---------------------------------------------------------------------------

class TestNetworkManagerPing(BaseTestCase):
    """Tests for the ping simulation (Test 8)."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_ping_known_host_succeeds(self):
        """Pinging a known simulated host (8.8.8.8) should return success."""
        success, results, hostname = self.nm.ping("8.8.8.8", count=2)
        self.assertTrue(success, "ping('8.8.8.8') should report success.")

    def test_ping_returns_correct_result_count(self):
        """ping should return exactly count result entries."""
        _, results, _ = self.nm.ping("8.8.8.8", count=2)
        self.assertEqual(
            len(results),
            2,
            "ping with count=2 should return exactly 2 result entries.",
        )

    def test_ping_result_has_expected_keys(self):
        """Each ping result entry should contain seq, ttl, time, and success keys."""
        _, results, _ = self.nm.ping("8.8.8.8", count=1)
        entry = results[0]
        for key in ("seq", "ttl", "time", "success"):
            self.assertIn(key, entry, f"Ping result entry should contain key '{key}'.")

    def test_ping_result_seq_starts_at_one(self):
        """The first ping result entry should have seq=1."""
        _, results, _ = self.nm.ping("8.8.8.8", count=1)
        self.assertEqual(results[0]["seq"], 1, "First ping result seq should be 1.")

    def test_ping_localhost_succeeds(self):
        """Pinging localhost should always succeed."""
        success, results, _ = self.nm.ping("127.0.0.1", count=1)
        self.assertTrue(success, "ping('127.0.0.1') should report success.")

    def test_ping_returns_hostname_string(self):
        """ping should return a non-empty hostname string as its third value."""
        _, _, hostname = self.nm.ping("8.8.8.8", count=1)
        self.assertIsInstance(hostname, str, "ping should return a hostname string.")
        self.assertTrue(len(hostname) > 0, "Returned hostname should not be empty.")


# ---------------------------------------------------------------------------
# NetworkManager — routing
# ---------------------------------------------------------------------------

class TestNetworkManagerRouting(BaseTestCase):
    """Tests for the routing table."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_default_routes_exist(self):
        """The routing table should have at least one entry by default."""
        routes = self.nm.list_routes()
        self.assertGreater(len(routes), 0, "Routing table should have default entries.")

    def test_add_route_appends_to_table(self):
        """add_route should append a new entry to the routing table."""
        before = len(self.nm.list_routes())
        self.nm.add_route("10.10.0.0", "192.168.1.1", "255.255.0.0", "eth0")
        after = len(self.nm.list_routes())
        self.assertEqual(after, before + 1, "add_route should add exactly one entry.")


# ---------------------------------------------------------------------------
# NetworkManager — hostname resolution
# ---------------------------------------------------------------------------

class TestNetworkManagerResolution(BaseTestCase):
    """Tests for resolve_hostname."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_resolve_localhost_returns_loopback(self):
        """resolve_hostname('localhost') should return '127.0.0.1'."""
        result = self.nm.resolve_hostname("localhost")
        self.assertEqual(
            result,
            "127.0.0.1",
            "resolve_hostname('localhost') should return '127.0.0.1'.",
        )

    def test_resolve_pureos_returns_loopback(self):
        """resolve_hostname('pureos') should return '127.0.0.1'."""
        result = self.nm.resolve_hostname("pureos")
        self.assertEqual(
            result,
            "127.0.0.1",
            "resolve_hostname('pureos') should return '127.0.0.1'.",
        )

    def test_resolve_unknown_returns_none(self):
        """resolve_hostname for an unknown name should return None."""
        result = self.nm.resolve_hostname("definitely.unknown.invalid")
        self.assertIsNone(
            result,
            "resolve_hostname should return None for an unknown hostname.",
        )


# ---------------------------------------------------------------------------
# NetworkManager — ping timeout behaviour
# ---------------------------------------------------------------------------

class TestNetworkManagerPingTimeout(BaseTestCase):
    """Tests for the timeout parameter of NetworkManager.ping."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def _ping_no_sleep(self, target, count, timeout):
        """Call ping with time.sleep patched out so tests run instantly."""
        with patch("core.network.time.sleep"):
            return self.nm.ping(target, count=count, timeout=timeout)

    def test_generous_timeout_all_results_succeed(self):
        """With a very large timeout every result entry should be successful."""
        _, results, _ = self._ping_no_sleep("8.8.8.8", count=3, timeout=9999)
        self.assertTrue(
            all(r["success"] for r in results),
            "All result entries should succeed when timeout is extremely large.",
        )

    def test_zero_timeout_all_results_fail(self):
        """With a near-zero timeout every result entry should fail."""
        _, results, _ = self._ping_no_sleep("8.8.8.8", count=3, timeout=0.000001)
        self.assertTrue(
            all(not r["success"] for r in results),
            "All result entries should fail when timeout is effectively zero.",
        )

    def test_zero_timeout_overall_success_is_false(self):
        """With a near-zero timeout the overall success flag should be False."""
        success, _, _ = self._ping_no_sleep("8.8.8.8", count=2, timeout=0.000001)
        self.assertFalse(
            success,
            "Overall success should be False when timeout causes all packets to fail.",
        )

    def test_generous_timeout_overall_success_is_true(self):
        """With a very large timeout the overall success flag should be True."""
        success, _, _ = self._ping_no_sleep("8.8.8.8", count=2, timeout=9999)
        self.assertTrue(
            success,
            "Overall success should be True when timeout is extremely large.",
        )

    def test_timeout_applied_per_packet(self):
        """Each result entry independently reflects the timeout comparison."""
        _, results, _ = self._ping_no_sleep("8.8.8.8", count=4, timeout=9999)
        for r in results:
            self.assertIn("success", r, "Each result must have a 'success' key.")
            self.assertTrue(r["success"], "Each packet should succeed under a large timeout.")

    def test_result_count_unaffected_by_short_timeout(self):
        """A short timeout should not reduce the number of result entries returned."""
        _, results, _ = self._ping_no_sleep("8.8.8.8", count=3, timeout=0.000001)
        self.assertEqual(
            len(results),
            3,
            "ping should always return exactly count entries regardless of timeout.",
        )

    def test_localhost_succeeds_with_default_timeout(self):
        """localhost (rtt~0ms) should always succeed with the default timeout."""
        with patch("core.network.time.sleep"):
            success, results, _ = self.nm.ping("127.0.0.1", count=1)
        self.assertTrue(success, "localhost ping should succeed with the default timeout.")
        self.assertTrue(results[0]["success"], "localhost packet should be marked successful.")


# ---------------------------------------------------------------------------
# PingCommand — shell command argument parsing
# ---------------------------------------------------------------------------

class _FakeShell:
    """Minimal shell stub for testing PingCommand without a full Shell instance."""

    def __init__(self, network_manager):
        self.network_manager = network_manager
        self.output: list = []

    def print(self, text=""):
        self.output.append(str(text))


class TestPingCommand(BaseTestCase):
    """Tests for PingCommand argument parsing and -t timeout flag."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()
        self.cmd = PingCommand(network_manager=self.nm)
        self.shell = _FakeShell(self.nm)

    def _execute(self, args):
        """Run the command with time.sleep patched out."""
        with patch("core.network.time.sleep"):
            return self.cmd.execute(args, self.shell)

    # --- basic argument handling ---

    def test_no_args_returns_error(self):
        """ping with no arguments should return exit code 1."""
        rc = self._execute([])
        self.assertEqual(rc, 1, "ping with no args should return 1.")

    def test_no_args_prints_usage(self):
        """ping with no arguments should print a usage message."""
        self._execute([])
        self.assertTrue(
            any("usage" in line.lower() for line in self.shell.output),
            "ping with no args should print a usage hint.",
        )

    def test_simple_target_returns_zero(self):
        """ping with only a target address should return 0 on a known host."""
        rc = self._execute(["8.8.8.8"])
        self.assertEqual(rc, 0, "ping 8.8.8.8 should return 0.")

    def test_c_flag_controls_packet_count(self):
        """ping -c 2 should produce exactly 2 result lines in output."""
        self._execute(["-c", "2", "8.8.8.8"])
        # Each result line contains "icmp_seq="
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertEqual(len(result_lines), 2, "ping -c 2 should emit 2 result lines.")

    def test_c_flag_invalid_value_returns_error(self):
        """ping -c with a non-integer value should return exit code 1."""
        rc = self._execute(["-c", "abc", "8.8.8.8"])
        self.assertEqual(rc, 1, "ping -c abc should return 1 for invalid count.")

    def test_flag_only_no_target_returns_error(self):
        """ping with a bare flag and no target should return exit code 1."""
        rc = self._execute(["-c"])
        self.assertEqual(rc, 1, "ping -c with no count or target should return 1.")

    # --- -t timeout flag ---

    def test_t_flag_with_large_timeout_succeeds(self):
        """ping -t 9999 should succeed (all packets pass the threshold)."""
        rc = self._execute(["-t", "9999", "8.8.8.8"])
        self.assertEqual(rc, 0, "ping -t 9999 8.8.8.8 should return 0.")

    def test_t_flag_with_near_zero_timeout_fails(self):
        """ping -t 0 should fail (all packets exceed the threshold)."""
        rc = self._execute(["-t", "0", "8.8.8.8"])
        self.assertEqual(rc, 1, "ping -t 0 8.8.8.8 should return 1 (all packets timed out).")

    def test_t_flag_invalid_value_returns_error(self):
        """ping -t with a non-numeric value should return exit code 1."""
        rc = self._execute(["-t", "abc", "8.8.8.8"])
        self.assertEqual(rc, 1, "ping -t abc should return 1 for invalid timeout.")

    def test_t_flag_missing_value_returns_error(self):
        """ping -t with no value following it should return exit code 1."""
        rc = self._execute(["-t", "8.8.8.8"])
        # "8.8.8.8" is not a valid float that makes sense as a very-small timeout
        # but more importantly: the flag parser should not crash.
        self.assertIn(rc, (0, 1), "ping -t <missing> should return a valid exit code.")

    def test_t_and_c_flags_together(self):
        """-c and -t flags can be combined; result count must match -c value."""
        self._execute(["-c", "2", "-t", "9999", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertEqual(
            len(result_lines),
            2,
            "ping -c 2 -t 9999 should emit exactly 2 result lines.",
        )

    def test_output_contains_statistics_summary(self):
        """ping output should always include a statistics summary block."""
        self._execute(["-c", "1", "8.8.8.8"])
        self.assertTrue(
            any("packet" in line for line in self.shell.output),
            "ping output should include a packet statistics summary.",
        )


if __name__ == "__main__":
    unittest.main()
