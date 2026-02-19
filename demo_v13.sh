#!/bin/sh
# PureOS v1.3 Demo Script - Tab Completion, Aliases, and Wildcards

echo "=== PureOS v1.3 Feature Demo ==="
echo ""

# Show prompt customization
echo "Current prompt format:"
echo "  PS1=\"$PS1\""
echo ""

echo "Try these prompt customizations:"
echo "  export PS1=\"[\\t] \\u@\\h:\\W\\$ \"    # Show time in prompt"
echo "  export PS1=\"\\u:\\W\\$ \"               # Minimal prompt"
echo ""

# Demonstrate aliases
echo "Built-in aliases:"
alias
echo ""

echo "Creating custom alias:"
echo "  alias hi='echo Hello World!'"
alias hi='echo Hello World!'
echo "  alias"
alias
echo ""

# Demonstrate wildcards
echo "Creating test files..."
touch test1.txt test2.txt test3.txt
touch file1.log file2.log

echo ""
echo "Using wildcards:"
echo "  ls *.txt      # List all .txt files"
ls *.txt

echo ""
echo "  ls file?.log  # List file?.log files"
ls file?.log

echo ""
echo "  rm test*.txt  # Remove all test*.txt files"
rm test*.txt
rm file*.log

echo ""
echo "=== Demo Complete ==="
echo ""
echo "Try these commands:"
echo "  - Press Tab to complete commands, files, and usernames"
echo "  - Press Ctrl+A to go to beginning of line"
echo "  - Press Ctrl+E to go to end of line"
echo "  - Press Ctrl+R to search history"
echo "  - End a line with \\ to continue on next line"
echo ""
echo "Customize your prompt with:"
echo "  export PS1='[\\t] \\u@\\h:\\W\\$ '"
