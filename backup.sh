#!/bin/sh
# PureOS Backup Script
# Creates backups of important files

echo "=== PureOS Backup Utility ==="
echo ""

# Configuration
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Backup function
backup_file() {
    local src_file=$1
    local backup_name="${src_file##*/}_${DATE}.bak"
    
    if [ -f "$src_file" ]; then
        cp "$src_file" "$BACKUP_DIR/$backup_name"
        echo "  Backed up: $src_file -> $backup_name"
        return 0
    else
        echo "  Not found: $src_file"
        return 1
    fi
}

echo "Starting backup process..."
echo "Backup location: $BACKUP_DIR"
echo "Timestamp: $DATE"
echo ""

# Backup important files
echo "Backing up configuration files:"
backup_file "/etc/passwd"
backup_file "/etc/group"

echo ""
echo "Backup complete!"
echo "Backup files in $BACKUP_DIR:"
ls -la "$BACKUP_DIR/"
