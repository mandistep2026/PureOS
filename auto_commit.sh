#!/bin/sh
# Auto-commit changes as soon as they appear.
# Usage: INTERVAL=2 ./auto_commit.sh

set -eu

INTERVAL="${INTERVAL:-2}"
MAX_FILES_IN_SUBJECT="${MAX_FILES_IN_SUBJECT:-5}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: this script must be run inside a git repository."
    exit 1
fi

build_commit_message() {
    name_status=$(git diff --cached --name-status)
    if [ -z "$name_status" ]; then
        return 1
    fi

    total_files=$(printf "%s\n" "$name_status" | wc -l | tr -d ' ')

    added=$(printf "%s\n" "$name_status" | awk '$1 ~ /^A/ {count++} END {print count+0}')
    modified=$(printf "%s\n" "$name_status" | awk '$1 ~ /^M/ {count++} END {print count+0}')
    deleted=$(printf "%s\n" "$name_status" | awk '$1 ~ /^D/ {count++} END {print count+0}')
    renamed=$(printf "%s\n" "$name_status" | awk '$1 ~ /^R/ {count++} END {print count+0}')

    file_list=$(git diff --cached --name-only | head -n "$MAX_FILES_IN_SUBJECT" | tr '\n' ' ' | sed 's/ $//')
    if [ "$total_files" -gt "$MAX_FILES_IN_SUBJECT" ]; then
        file_list="$file_list ..."
    fi

    printf "Auto-commit: %s files changed (A:%s M:%s D:%s R:%s) - %s" \
        "$total_files" "$added" "$modified" "$deleted" "$renamed" "$file_list"
}

while true; do
    if [ -n "$(git status --porcelain)" ]; then
        git add -A
        if [ -n "$(git diff --cached --name-status)" ]; then
            subject=$(build_commit_message) || true
            if [ -n "${subject:-}" ]; then
                git commit -m "$subject" -m "$(git diff --cached --stat)"
            fi
        fi
    fi
    sleep "$INTERVAL"
done
