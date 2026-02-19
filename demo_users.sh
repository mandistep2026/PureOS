#!/bin/sh
# PureOS Demo Script 2 - User Management Demo
# This script demonstrates user creation and management

echo "=== User Management Demo ==="
echo ""

# Check if running as root
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" != "root" ]; then
    echo "Error: This script must be run as root"
    echo "Current user: $CURRENT_USER"
    exit 1
fi

echo "Creating test users..."

# Create users with home directories
for username in dev1 dev2 tester; do
    if [ ! -d "/home/$username" ]; then
        echo "  Creating user: $username"
        useradd -m "$username"
        echo "  User $username created successfully"
    else
        echo "  User $username already exists"
    fi
done

echo ""
echo "User list:"
who

echo ""
echo "Current user info:"
id

echo ""
echo "Home directories created:"
ls -la /home/

echo ""
echo "=== User Management Demo Complete ==="
echo ""
echo "You can switch to a new user with: su dev1"
