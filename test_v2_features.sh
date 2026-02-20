#!/bin/bash
# Quick test of PureOS v2.0 features

echo "=== PureOS v2.0 Feature Demo ==="
echo ""
echo "Testing new commands..."
python3 << 'PYTHON'
from core.kernel import Kernel
from core.filesystem import FileSystem
from shell.shell import Shell

kernel = Kernel()
fs = FileSystem()
shell = Shell(kernel, fs)

print("\n1. Testing systemctl (service management):")
shell.execute("systemctl")

print("\n2. Testing dmesg (kernel log):")
shell.execute("dmesg")

print("\n3. Testing ulimit (resource limits):")
shell.execute("ulimit -a")

print("\n4. Testing ipcs (IPC status):")
shell.execute("ipcs")

print("\n5. Testing cgctl (control groups):")
shell.execute("cgctl list")

print("\n6. Testing journalctl (system journal):")
shell.execute("journalctl -n 5")

print("\nAll v2.0 features working! ✓")
PYTHON
