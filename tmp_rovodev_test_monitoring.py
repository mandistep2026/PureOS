#!/usr/bin/env python3
"""Test script for PureOS v2.1 System Monitoring & Diagnostics"""

import sys
import time

# Add current directory to path
sys.path.insert(0, '.')

from core.kernel import Kernel
from shell.shell import Shell

def test_monitoring_commands():
    """Test all new monitoring commands"""
    print("=" * 60)
    print("PureOS v2.1 - System Monitoring & Diagnostics Test")
    print("=" * 60)
    
    # Initialize kernel and shell
    from core.filesystem import FileSystem
    from core.user import UserManager
    from core.auth import Authenticator
    
    kernel = Kernel()
    kernel.start()
    filesystem = FileSystem()
    user_manager = UserManager(filesystem)
    authenticator = Authenticator(user_manager)
    shell = Shell(kernel, filesystem, authenticator, user_manager)
    
    # Generate some system activity
    print("\n[1/9] Generating system activity...")
    shell.execute("echo 'test data' > /tmp/test1.txt")
    shell.execute("cat /tmp/test1.txt")
    shell.execute("ps")
    time.sleep(0.5)
    
    # Test 1: free (enhanced)
    print("\n[2/9] Testing 'free' command...")
    result = shell.execute("free")
    assert result == 0, "free command failed"
    print("✓ free command working")
    
    # Test 2: iostat
    print("\n[3/9] Testing 'iostat' command...")
    result = shell.execute("iostat")
    assert result == 0, "iostat command failed"
    print("✓ iostat command working")
    
    # Test 3: mpstat
    print("\n[4/9] Testing 'mpstat' command...")
    result = shell.execute("mpstat")
    assert result == 0, "mpstat command failed"
    print("✓ mpstat command working")
    
    # Test 4: sysdiag
    print("\n[5/9] Testing 'sysdiag' command...")
    result = shell.execute("sysdiag")
    assert result == 0, "sysdiag command failed"
    print("✓ sysdiag command working")
    
    # Test 5: syshealth
    print("\n[6/9] Testing 'syshealth' command...")
    result = shell.execute("syshealth")
    assert result == 0, "syshealth command failed"
    print("✓ syshealth command working")
    
    # Test 6: syshealth --brief
    print("\n[7/9] Testing 'syshealth --brief'...")
    result = shell.execute("syshealth --brief")
    assert result == 0, "syshealth --brief failed"
    print("✓ syshealth --brief working")
    
    # Test 7: perf stat
    print("\n[8/9] Testing 'perf stat'...")
    result = shell.execute("perf stat 1")
    assert result == 0, "perf stat failed"
    print("✓ perf stat working")
    
    # Test 8: htop (non-interactive)
    print("\n[9/9] Testing 'htop' (non-interactive)...")
    result = shell.execute("htop")
    assert result == 0, "htop command failed"
    print("✓ htop command working")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nNew commands available:")
    print("  • free      - Enhanced memory usage display")
    print("  • iostat    - I/O statistics and throughput")
    print("  • mpstat    - CPU statistics and utilization")
    print("  • sysdiag   - Comprehensive system diagnostics")
    print("  • syshealth - System health dashboard")
    print("  • perf      - Performance profiling tool")
    print("  • htop      - Real-time process monitor")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_monitoring_commands()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
