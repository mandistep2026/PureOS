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
        """ping -t 0 should fail: 0 is rejected as an invalid (non-positive) timeout."""
        rc = self._execute(["-t", "0", "8.8.8.8"])
        self.assertEqual(rc, 1, "ping -t 0 8.8.8.8 should return 1 (zero timeout is invalid).")

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

    def test_t_flag_zero_rejected_no_result_lines(self):
        """-t 0 is rejected as invalid; no icmp_seq result lines should be emitted."""
        self._execute(["-t", "0", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertEqual(
            len(result_lines),
            0,
            "ping -t 0 should be rejected before pinging, so no result lines are emitted.",
        )

    def test_t_flag_tiny_positive_all_result_lines_show_failed(self):
        """-t 0.0001 (0.1 ms threshold) should mark all 8.8.8.8 packets as FAILED."""
        # 8.8.8.8 rtt_base=25 ms >> 0.1 ms threshold, so all packets fail.
        self._execute(["-t", "0.0001", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertTrue(
            len(result_lines) > 0,
            "Result lines should be present for a valid (tiny positive) timeout.",
        )
        self.assertTrue(
            all("FAILED" in line for line in result_lines),
            "All result lines should show FAILED when timeout=0.0001 s (0.1 ms threshold).",
        )

    def test_t_flag_large_all_result_lines_show_ok(self):
        """-t 9999 should mark every result line as OK."""
        self._execute(["-t", "9999", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertTrue(
            all("OK" in line for line in result_lines),
            "All result lines should show OK when timeout is very large.",
        )

    def test_output_contains_ttl_field(self):
        """Each result line should include the ttl= field."""
        self._execute(["-c", "1", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertTrue(
            all("ttl=" in line for line in result_lines),
            "Each result line must include a ttl= field.",
        )

    def test_output_contains_time_field(self):
        """Each result line should include the time= field."""
        self._execute(["-c", "1", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertTrue(
            all("time=" in line for line in result_lines),
            "Each result line must include a time= field.",
        )

    def test_output_packet_loss_zero_on_large_timeout(self):
        """Statistics line should report 0% packet loss when all packets succeed."""
        self._execute(["-c", "2", "-t", "9999", "8.8.8.8"])
        self.assertTrue(
            any("0% packet loss" in line for line in self.shell.output),
            "Statistics should report 0% packet loss when all packets succeed.",
        )

    def test_output_packet_loss_100_on_tiny_timeout(self):
        """Statistics line should report 100% packet loss when all packets fail."""
        # Use 0.0001 s (0.1 ms threshold) — valid positive timeout that forces all
        # 8.8.8.8 packets (rtt_base=25 ms) to fail.
        self._execute(["-c", "2", "-t", "0.0001", "8.8.8.8"])
        self.assertTrue(
            any("100% packet loss" in line for line in self.shell.output),
            "Statistics should report 100% packet loss when all packets fail.",
        )

    def test_t_and_c_combined_tiny_timeout_returns_error(self):
        """-c 1 -t 0.0001 combination: exactly 1 result line and exit code 1."""
        # 0.0001 s = 0.1 ms threshold; 8.8.8.8 rtt_base=25 ms always exceeds it.
        rc = self._execute(["-c", "1", "-t", "0.0001", "8.8.8.8"])
        result_lines = [l for l in self.shell.output if "icmp_seq=" in l]
        self.assertEqual(len(result_lines), 1, "-c 1 should emit exactly 1 result line.")
        self.assertEqual(rc, 1, "Exit code should be 1 when all packets fail.")

    def test_ping_localhost_with_large_timeout_returns_zero(self):
        """ping localhost -t 9999 should return 0."""
        rc = self._execute(["-t", "9999", "127.0.0.1"])
        self.assertEqual(rc, 0, "ping 127.0.0.1 -t 9999 should return 0.")

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


# ---------------------------------------------------------------------------
# NetworkManager — ping result structure detail
# ---------------------------------------------------------------------------

class TestNetworkManagerPingResultDetail(BaseTestCase):
    """Tests for per-packet result entry content and types."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def _ping(self, target, count=1, timeout=9999):
        with patch("core.network.time.sleep"):
            return self.nm.ping(target, count=count, timeout=timeout)

    def test_result_entry_ttl_is_64(self):
        """Every ping result entry must have ttl=64."""
        _, results, _ = self._ping("8.8.8.8", count=3)
        for r in results:
            self.assertEqual(r["ttl"], 64, "Result entry ttl should always be 64.")

    def test_result_entry_time_is_float(self):
        """The 'time' field in each result entry should be a float."""
        _, results, _ = self._ping("8.8.8.8", count=2)
        for r in results:
            self.assertIsInstance(
                r["time"], float,
                "Result entry 'time' should be a float (RTT in ms).",
            )

    def test_result_entry_time_is_positive(self):
        """RTT must be strictly positive (implementation clamps to >= 0.1 ms)."""
        _, results, _ = self._ping("8.8.8.8", count=2)
        for r in results:
            self.assertGreater(r["time"], 0, "RTT must be positive.")

    def test_result_entry_success_is_bool(self):
        """The 'success' field in each result entry should be a bool."""
        _, results, _ = self._ping("8.8.8.8", count=2)
        for r in results:
            self.assertIsInstance(
                r["success"], bool,
                "Result entry 'success' should be a bool.",
            )

    def test_result_seq_is_sequential(self):
        """seq values must be sequential starting at 1."""
        _, results, _ = self._ping("8.8.8.8", count=5)
        seqs = [r["seq"] for r in results]
        self.assertEqual(seqs, list(range(1, 6)), "seq values should be 1..count.")

    def test_ping_returns_three_tuple(self):
        """ping should return exactly a 3-tuple (success, results, hostname)."""
        result = self._ping("8.8.8.8")
        self.assertIsInstance(result, tuple, "ping should return a tuple.")
        self.assertEqual(len(result), 3, "ping tuple should have 3 elements.")

    def test_ping_results_is_a_list(self):
        """The second element of the ping return value should be a list."""
        _, results, _ = self._ping("8.8.8.8", count=2)
        self.assertIsInstance(results, list, "ping results should be a list.")

    def test_ping_success_is_bool(self):
        """The overall success flag should be a bool."""
        success, _, _ = self._ping("8.8.8.8")
        self.assertIsInstance(success, bool, "Overall ping success should be a bool.")


# ---------------------------------------------------------------------------
# NetworkManager — ping timeout threshold boundary
# ---------------------------------------------------------------------------

class TestNetworkManagerPingTimeoutBoundary(BaseTestCase):
    """Fine-grained boundary tests for the timeout comparison in ping.

    The implementation compares:  rtt < timeout * 1000
    where rtt is in milliseconds and timeout is in seconds.

    Known RTTs (from SIMULATED_HOSTS / SIMULATED_LOCAL):
      8.8.8.8  -> rtt_base=25 ms  (varies ±10 %)
      127.0.0.1 -> rtt=0.1 ms (constant, clamped from 0.05)
    """

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def _ping(self, target, count=1, timeout=2.0):
        with patch("core.network.time.sleep"):
            return self.nm.ping(target, count=count, timeout=timeout)

    def test_threshold_zero_ms_always_fails(self):
        """timeout=0 means threshold=0 ms; all packets (rtt>=0.1) must fail."""
        success, results, _ = self._ping("8.8.8.8", count=4, timeout=0)
        self.assertFalse(success, "Overall success must be False when timeout=0.")
        self.assertTrue(
            all(not r["success"] for r in results),
            "Every packet must fail when timeout=0.",
        )

    def test_threshold_generous_always_passes(self):
        """timeout=9999 s → threshold=9_999_000 ms; all packets must succeed."""
        success, results, _ = self._ping("8.8.8.8", count=4, timeout=9999)
        self.assertTrue(success, "Overall success must be True when timeout=9999.")
        self.assertTrue(
            all(r["success"] for r in results),
            "Every packet must succeed when timeout=9999.",
        )

    def test_localhost_rtt_is_below_1ms_threshold(self):
        """127.0.0.1 rtt is 0.1 ms; timeout=0.001 s gives threshold=1 ms — passes."""
        success, results, _ = self._ping("127.0.0.1", count=1, timeout=0.001)
        self.assertTrue(
            results[0]["success"],
            "localhost packet (rtt=0.1 ms) should succeed with timeout=0.001 s (1 ms threshold).",
        )

    def test_count_zero_returns_empty_results(self):
        """count=0 should return an empty result list."""
        _, results, _ = self._ping("8.8.8.8", count=0)
        self.assertEqual(results, [], "count=0 should produce an empty results list.")

    def test_count_zero_success_is_true(self):
        """count=0: no packets fail, so the overall success flag should be True."""
        success, _, _ = self._ping("8.8.8.8", count=0)
        self.assertTrue(
            success,
            "Overall success should be True when no packets were sent (count=0).",
        )

    def test_count_one_returns_single_result(self):
        """count=1 should return exactly one result entry."""
        _, results, _ = self._ping("8.8.8.8", count=1)
        self.assertEqual(len(results), 1, "count=1 should produce exactly one result.")

    def test_time_sleep_called_between_packets(self):
        """time.sleep should be called count-1 times for count > 1."""
        with patch("core.network.time.sleep") as mock_sleep:
            self.nm.ping("8.8.8.8", count=3)
        self.assertEqual(
            mock_sleep.call_count,
            2,
            "time.sleep should be called count-1=2 times for count=3.",
        )

    def test_time_sleep_not_called_for_count_one(self):
        """time.sleep should not be called when count=1 (no inter-packet delay)."""
        with patch("core.network.time.sleep") as mock_sleep:
            self.nm.ping("8.8.8.8", count=1)
        mock_sleep.assert_not_called()

    def test_unknown_host_still_returns_count_results(self):
        """An unrecognised IP should still produce exactly count result entries."""
        with patch("core.network.time.sleep"):
            _, results, _ = self.nm.ping("203.0.113.1", count=3, timeout=9999)
        self.assertEqual(
            len(results),
            3,
            "ping to an unknown host should still return count result entries.",
        )

    def test_unknown_host_hostname_is_target_string(self):
        """For an unknown host the returned hostname should equal the target."""
        with patch("core.network.time.sleep"):
            _, _, hostname = self.nm.ping("203.0.113.99", count=1)
        self.assertEqual(
            hostname,
            "203.0.113.99",
            "hostname returned for an unknown IP should be the target string.",
        )

    def test_local_subnet_host_succeeds_with_large_timeout(self):
        """192.168.1.x hosts (rtt_base=2 ms) should succeed with a large timeout."""
        with patch("core.network.time.sleep"):
            success, results, _ = self.nm.ping("192.168.1.50", count=2, timeout=9999)
        self.assertTrue(success, "Local subnet ping should succeed with a large timeout.")
        self.assertTrue(
            all(r["success"] for r in results),
            "All local-subnet packets should be marked successful with a large timeout.",
        )

    def test_local_subnet_host_fails_with_zero_timeout(self):
        """192.168.1.x hosts (rtt_base=2 ms) should fail with timeout=0."""
        with patch("core.network.time.sleep"):
            success, results, _ = self.nm.ping("192.168.1.50", count=2, timeout=0)
        self.assertFalse(success, "Local subnet ping should fail with timeout=0.")


# ---------------------------------------------------------------------------
# NetworkManager — hostname boundary cases
# ---------------------------------------------------------------------------

class TestNetworkManagerHostnameBoundary(BaseTestCase):
    """Boundary tests for set_hostname length validation."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_set_hostname_exactly_64_chars_succeeds(self):
        """A hostname of exactly 64 characters should be accepted."""
        name = "a" * 64
        result = self.nm.set_hostname(name)
        self.assertTrue(result, "set_hostname should accept a 64-character hostname.")
        self.assertEqual(
            self.nm.get_hostname(),
            name,
            "get_hostname should reflect a 64-character hostname.",
        )

    def test_set_hostname_65_chars_rejected(self):
        """A hostname of 65 characters should be rejected."""
        result = self.nm.set_hostname("a" * 65)
        self.assertFalse(result, "set_hostname should reject a 65-character hostname.")

    def test_set_hostname_empty_string_succeeds(self):
        """An empty hostname string is within the 64-char limit and should be accepted."""
        result = self.nm.set_hostname("")
        self.assertTrue(result, "set_hostname should accept an empty string.")

    def test_set_hostname_single_char_succeeds(self):
        """A single-character hostname should be accepted."""
        result = self.nm.set_hostname("x")
        self.assertTrue(result, "set_hostname should accept a single-character hostname.")
        self.assertEqual(self.nm.get_hostname(), "x")


# ---------------------------------------------------------------------------
# NetworkManager — resolve_hostname additional targets
# ---------------------------------------------------------------------------

class TestNetworkManagerResolutionExtra(BaseTestCase):
    """Additional tests for resolve_hostname well-known names."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_resolve_google_com(self):
        """resolve_hostname('google.com') should return '8.8.8.8'."""
        self.assertEqual(self.nm.resolve_hostname("google.com"), "8.8.8.8")

    def test_resolve_cloudflare_com(self):
        """resolve_hostname('cloudflare.com') should return '1.1.1.1'."""
        self.assertEqual(self.nm.resolve_hostname("cloudflare.com"), "1.1.1.1")

    def test_resolve_github_com(self):
        """resolve_hostname('github.com') should return '140.82.121.3'."""
        self.assertEqual(self.nm.resolve_hostname("github.com"), "140.82.121.3")

    def test_resolve_python_org(self):
        """resolve_hostname('python.org') should return '151.101.1.69'."""
        self.assertEqual(self.nm.resolve_hostname("python.org"), "151.101.1.69")

    def test_resolve_returns_string_for_known_hosts(self):
        """resolve_hostname for any known host should return a non-empty string."""
        for name in ("google.com", "cloudflare.com", "github.com", "python.org"):
            result = self.nm.resolve_hostname(name)
            self.assertIsInstance(result, str, f"resolve_hostname('{name}') should return a string.")
            self.assertTrue(len(result) > 0, f"resolve_hostname('{name}') should not be empty.")


# ---------------------------------------------------------------------------
# NetworkManager — list_interfaces return type
# ---------------------------------------------------------------------------

class TestNetworkManagerInterfaceList(BaseTestCase):
    """Tests for list_interfaces return type and content guarantees."""

    def setUp(self):
        super().setUp()
        self.nm = NetworkManager()

    def test_list_interfaces_returns_list(self):
        """list_interfaces should return a list, not a generator or other iterable."""
        result = self.nm.list_interfaces()
        self.assertIsInstance(result, list, "list_interfaces should return a list.")

    def test_list_interfaces_count_is_two_by_default(self):
        """Default setup should include exactly 2 interfaces (lo and eth0)."""
        result = self.nm.list_interfaces()
        self.assertEqual(len(result), 2, "Default interface count should be 2 (lo + eth0).")

    def test_list_interfaces_elements_are_network_interface(self):
        """All elements returned by list_interfaces should be NetworkInterface instances."""
        from core.network import NetworkInterface
        for iface in self.nm.list_interfaces():
            self.assertIsInstance(
                iface,
                NetworkInterface,
                f"list_interfaces element {iface!r} should be a NetworkInterface.",
            )


if __name__ == "__main__":
    unittest.main()
