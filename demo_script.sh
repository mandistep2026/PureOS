#!/bin/sh
# PureOS Demo Script 1 - Basic Scripting
# This script demonstrates variables, conditionals, and loops

echo "=== PureOS Scripting Demo ==="
echo ""

# Variables
NAME="PureOS"
VERSION="1.2"

echo "Welcome to $NAME version $VERSION"
echo ""

# File test
CONFIG_FILE="/etc/config.txt"

if [ -f "$CONFIG_FILE" ]; then
    echo "Config file exists"
else
    echo "Creating config file..."
    echo "name=PureOS" > "$CONFIG_FILE"
    echo "version=1.2" >> "$CONFIG_FILE"
    echo "Config file created"
fi

echo ""

# For loop - iterate over files
echo "Files in current directory:"
for file in *; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

echo ""

# While loop with counter
echo "Counting from 1 to 3:"
count=1
while [ $count -le 3 ]; do
    echo "  Count: $count"
    count=$((count + 1))
done

echo ""
echo "=== Demo Complete ==="
