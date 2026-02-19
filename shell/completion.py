"""
PureOS Tab Completion and Line Editing
Advanced input handling with tab completion and key bindings.
Uses only Python standard library.
"""

import sys
import os
import re
from typing import List, Optional, Tuple, Dict


class TabCompleter:
    """Handles tab completion for commands, files, and usernames."""
    
    def __init__(self, shell):
        self.shell = shell
        self.matches: List[str] = []
        self.match_index = 0
        self.last_text = ""
    
    def complete(self, text: str, cursor_pos: int) -> Tuple[str, int, List[str]]:
        """
        Generate completion for text at cursor position.
        
        Returns:
            (new_text, new_cursor_pos, all_matches)
        """
        # Determine context
        line_before = text[:cursor_pos]
        
        # Check if completing a variable ($VAR)
        if self._is_variable_completion(line_before):
            return self._complete_variable(text, cursor_pos)
        
        # Check if completing a username (after su, userdel, etc.)
        if self._is_username_completion(line_before):
            return self._complete_username(text, cursor_pos)
        
        # Check if completing a command (at start of line)
        if self._is_command_completion(line_before):
            return self._complete_command(text, cursor_pos)
        
        # Otherwise, complete filename
        return self._complete_filename(text, cursor_pos)
    
    def _is_variable_completion(self, line_before: str) -> bool:
        """Check if we're completing a variable name."""
        # Look for $ followed by incomplete variable name
        if '$' in line_before:
            parts = line_before.rsplit('$', 1)
            if len(parts) == 2:
                after_dollar = parts[1]
                # Check if no spaces after $
                return ' ' not in after_dollar
        return False
    
    def _is_username_completion(self, line_before: str) -> bool:
        """Check if context suggests username completion."""
        # Check if line starts with user-related commands
        user_commands = ['su', 'userdel', 'passwd', 'chown', 'chgrp']
        words = line_before.split()
        if words and words[0] in user_commands:
            return True
        # Check if completing second argument of chown
        if len(words) >= 2 and words[0] == 'chown':
            return ':' not in line_before.split()[-1]
        return False
    
    def _is_command_completion(self, line_before: str) -> bool:
        """Check if we're at the start of line (completing command)."""
        words = line_before.split()
        return len(words) <= 1
    
    def _complete_command(self, text: str, cursor_pos: int) -> Tuple[str, int, List[str]]:
        """Complete command names."""
        # Get partial command
        words = text[:cursor_pos].split()
        partial = words[0] if words else ""
        
        matches = []
        
        # Match built-in commands
        if self.shell and hasattr(self.shell, 'commands'):
            for cmd_name in self.shell.commands.keys():
                if cmd_name.startswith(partial):
                    matches.append(cmd_name)
        
        # Match aliases
        if self.shell and hasattr(self.shell, 'aliases'):
            for alias in self.shell.aliases.keys():
                if alias.startswith(partial):
                    matches.append(alias)
        
        # Sort matches
        matches.sort()
        
        if not matches:
            return text, cursor_pos, []
        
        if len(matches) == 1:
            # Complete the command
            completion = matches[0]
            new_text = completion + text[cursor_pos:]
            return new_text, len(completion), matches
        else:
            # Multiple matches - find common prefix
            prefix = os.path.commonprefix(matches)
            if prefix != partial:
                # Complete to common prefix
                new_text = prefix + text[cursor_pos:]
                return new_text, len(prefix), matches
            else:
                # Show all matches
                return text, cursor_pos, matches
    
    def _complete_filename(self, text: str, cursor_pos: int) -> Tuple[str, int, List[str]]:
        """Complete file/directory paths."""
        # Get the word being completed
        line_before = text[:cursor_pos]
        
        # Find the start of the current word
        word_start = cursor_pos
        for i in range(cursor_pos - 1, -1, -1):
            if text[i] in ' \t|;<>':
                word_start = i + 1
                break
            word_start = i
        
        partial = text[word_start:cursor_pos]
        
        # Determine directory to search
        if partial.startswith('/'):
            # Absolute path
            if '/' in partial:
                dir_part = partial.rsplit('/', 1)[0]
                search_dir = dir_part if dir_part else '/'
                file_prefix = partial.rsplit('/', 1)[1]
            else:
                search_dir = '/'
                file_prefix = partial[1:]
        elif partial.startswith('~'):
            # Home directory
            if '/' in partial:
                # ~/path
                home = self._get_home_dir()
                rest = partial[1:]  # Remove ~
                if '/' in rest:
                    dir_part = rest.rsplit('/', 1)[0]
                    search_dir = home + dir_part
                    file_prefix = rest.rsplit('/', 1)[1]
                else:
                    search_dir = home
                    file_prefix = rest[1:] if rest.startswith('/') else rest
            else:
                # Just ~
                search_dir = self._get_home_dir()
                file_prefix = partial[1:]
        else:
            # Relative path
            if '/' in partial:
                search_dir = partial.rsplit('/', 1)[0]
                file_prefix = partial.rsplit('/', 1)[1]
            else:
                search_dir = '.'
                file_prefix = partial
        
        # Resolve search_dir
        if search_dir == '.':
            search_dir = self.shell.fs.get_current_directory() if self.shell else '/'
        elif not search_dir.startswith('/'):
            current = self.shell.fs.get_current_directory() if self.shell else '/'
            search_dir = current + '/' + search_dir
        
        # Normalize path
        search_dir = self._normalize_path(search_dir)
        
        # Get directory contents
        try:
            entries = self.shell.fs.list_directory(search_dir) if self.shell else []
        except:
            entries = []
        
        # Filter matches
        matches = []
        for entry in entries:
            if entry.name.startswith(file_prefix):
                # Add trailing slash for directories
                name = entry.name
                if entry.type.value == 'directory':
                    name += '/'
                matches.append(name)
        
        # Sort: directories first, then files
        matches.sort(key=lambda x: (not x.endswith('/'), x.lower()))
        
        if not matches:
            return text, cursor_pos, []
        
        # Build the full match path
        if partial.startswith('/'):
            base = search_dir if search_dir != '/' else ''
        elif partial.startswith('~'):
            base = '~' + (search_dir[len(self._get_home_dir()):] if search_dir.startswith(self._get_home_dir()) else search_dir)
        else:
            if '/' in partial:
                base = partial.rsplit('/', 1)[0] + '/'
            else:
                base = ''
        
        if len(matches) == 1:
            # Complete to the single match
            completion = base + matches[0]
            new_text = text[:word_start] + completion + text[cursor_pos:]
            return new_text, word_start + len(completion), matches
        else:
            # Find common prefix
            common = os.path.commonprefix(matches)
            if common != file_prefix:
                completion = base + common
                new_text = text[:word_start] + completion + text[cursor_pos:]
                return new_text, word_start + len(completion), matches
            else:
                # Show all matches
                full_matches = [base + m for m in matches]
                return text, cursor_pos, full_matches
    
    def _complete_username(self, text: str, cursor_pos: int) -> Tuple[str, int, List[str]]:
        """Complete usernames."""
        # Get partial username
        line_before = text[:cursor_pos]
        words = line_before.split()
        
        # Get the word being completed
        if words:
            partial = words[-1]
        else:
            partial = ""
        
        # Find word start position
        word_start = cursor_pos - len(partial)
        
        # Get all users
        matches = []
        if self.shell and hasattr(self.shell, 'um') and self.shell.um:
            for username in self.shell.um.users.keys():
                if username.startswith(partial):
                    matches.append(username)
        
        matches.sort()
        
        if not matches:
            return text, cursor_pos, []
        
        if len(matches) == 1:
            completion = matches[0]
            new_text = text[:word_start] + completion + text[cursor_pos:]
            return new_text, word_start + len(completion), matches
        else:
            common = os.path.commonprefix(matches)
            if common != partial:
                new_text = text[:word_start] + common + text[cursor_pos:]
                return new_text, word_start + len(common), matches
            else:
                return text, cursor_pos, matches
    
    def _complete_variable(self, text: str, cursor_pos: int) -> Tuple[str, int, List[str]]:
        """Complete variable names."""
        # Get partial variable name (after $)
        line_before = text[:cursor_pos]
        if '$' not in line_before:
            return text, cursor_pos, []
        
        parts = line_before.rsplit('$', 1)
        partial = parts[1] if len(parts) > 1 else ""
        dollar_pos = line_before.rfind('$')
        
        # Get all variables
        matches = []
        
        # Environment variables
        if self.shell and hasattr(self.shell, 'environment'):
            for var in self.shell.environment.keys():
                if var.startswith(partial):
                    matches.append(var)
        
        # Special variables
        special_vars = ['?', '$$', '#', '@', '*', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        for var in special_vars:
            if var.startswith(partial) and var not in matches:
                matches.append(var)
        
        matches.sort()
        
        if not matches:
            return text, cursor_pos, []
        
        if len(matches) == 1:
            completion = '$' + matches[0]
            new_text = text[:dollar_pos] + completion + text[cursor_pos:]
            return new_text, dollar_pos + len(completion), matches
        else:
            common = os.path.commonprefix(matches)
            if common != partial:
                new_text = text[:dollar_pos] + '$' + common + text[cursor_pos:]
                return new_text, dollar_pos + len(common) + 1, matches
            else:
                full_matches = ['$' + m for m in matches]
                return text, cursor_pos, full_matches
    
    def _get_home_dir(self) -> str:
        """Get current user's home directory."""
        if self.shell and hasattr(self.shell, 'auth') and self.shell.auth:
            return self.shell.auth.get_user_home()
        return '/root'
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a path."""
        # Remove double slashes
        while '//' in path:
            path = path.replace('//', '/')
        
        # Handle . and ..
        parts = path.split('/')
        result = []
        for part in parts:
            if part == '' or part == '.':
                continue
            elif part == '..':
                if result and result[-1] != '':
                    result.pop()
            else:
                result.append(part)
        
        normalized = '/' + '/'.join(result)
        return normalized if normalized != '' else '/'


class LineEditor:
    """Advanced line editing with tab completion and key bindings."""
    
    def __init__(self, shell):
        self.shell = shell
        self.completer = TabCompleter(shell)
        self.kill_buffer = ""
        self.history_search = ""
        self.searching = False
    
    def read_line(self, prompt: str) -> str:
        """
        Read a line with full editing support.
        Falls back to standard input if terminal doesn't support raw mode.
        """
        # Try to use advanced editing, fall back to basic input
        try:
            return self._read_line_advanced(prompt)
        except:
            # Fallback to basic input
            return input(prompt)
    
    def _read_line_advanced(self, prompt: str) -> str:
        """Read line with advanced editing (Unix only)."""
        if os.name != 'posix':
            raise NotImplementedError("Advanced editing only on Unix")
        
        import tty
        import termios
        import select
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        buffer = []
        cursor = 0
        history_idx = len(self.shell.history) if self.shell else 0
        
        # Print prompt
        sys.stdout.write(prompt)
        sys.stdout.flush()
        
        try:
            tty.setraw(fd)
            
            while True:
                # Read single character
                ready, _, _ = select.select([fd], [], [], 0.1)
                if ready:
                    char = sys.stdin.read(1)
                    
                    # Handle special keys
                    if char == '\r' or char == '\n':  # Enter
                        sys.stdout.write('\r\n')
                        sys.stdout.flush()
                        return ''.join(buffer)
                    
                    elif char == '\x03':  # Ctrl+C
                        sys.stdout.write('^C\r\n')
                        sys.stdout.flush()
                        raise KeyboardInterrupt()
                    
                    elif char == '\x04':  # Ctrl+D (EOF)
                        if not buffer:
                            sys.stdout.write('\r\n')
                            sys.stdout.flush()
                            raise EOFError()
                        else:
                            # Delete character under cursor
                            if cursor < len(buffer):
                                del buffer[cursor]
                                self._redraw_line(prompt, buffer, cursor)
                    
                    elif char == '\x7f' or char == '\x08':  # Backspace
                        if cursor > 0:
                            cursor -= 1
                            del buffer[cursor]
                            self._redraw_line(prompt, buffer, cursor)
                    
                    elif char == '\t':  # Tab - completion
                        text = ''.join(buffer)
                        new_text, new_cursor, matches = self.completer.complete(text, cursor)
                        
                        if len(matches) == 1:
                            # Complete to single match
                            buffer = list(new_text)
                            cursor = new_cursor
                            self._redraw_line(prompt, buffer, cursor)
                        elif len(matches) > 1:
                            # Show matches
                            sys.stdout.write('\r\n')
                            # Display in columns
                            self._display_matches(matches)
                            sys.stdout.write(prompt + ''.join(buffer))
                            sys.stdout.flush()
                        else:
                            # No matches - bell
                            sys.stdout.write('\x07')
                            sys.stdout.flush()
                    
                    elif char == '\x01':  # Ctrl+A - beginning of line
                        cursor = 0
                        self._move_cursor(prompt, cursor)
                    
                    elif char == '\x05':  # Ctrl+E - end of line
                        cursor = len(buffer)
                        self._move_cursor(prompt, cursor)
                    
                    elif char == '\x0b':  # Ctrl+K - kill to end
                        self.kill_buffer = ''.join(buffer[cursor:])
                        del buffer[cursor:]
                        self._redraw_line(prompt, buffer, cursor)
                    
                    elif char == '\x15':  # Ctrl+U - kill to beginning
                        self.kill_buffer = ''.join(buffer[:cursor])
                        del buffer[:cursor]
                        cursor = 0
                        self._redraw_line(prompt, buffer, cursor)
                    
                    elif char == '\x17':  # Ctrl+W - delete word back
                        # Find start of previous word
                        start = cursor
                        while start > 0 and buffer[start-1] == ' ':
                            start -= 1
                        while start > 0 and buffer[start-1] != ' ':
                            start -= 1
                        self.kill_buffer = ''.join(buffer[start:cursor])
                        del buffer[start:cursor]
                        cursor = start
                        self._redraw_line(prompt, buffer, cursor)
                    
                    elif char == '\x19':  # Ctrl+Y - yank (paste)
                        for c in self.kill_buffer:
                            buffer.insert(cursor, c)
                            cursor += 1
                        self._redraw_line(prompt, buffer, cursor)
                    
                    elif char == '\x0c':  # Ctrl+L - clear screen
                        sys.stdout.write('\x1b[2J\x1b[H')
                        sys.stdout.write(prompt + ''.join(buffer))
                        sys.stdout.flush()
                    
                    elif char == '\x12':  # Ctrl+R - history search
                        # Simple history search
                        self._show_message("History search (Ctrl+G to cancel): ")
                        search_term = ""
                        while True:
                            char2 = sys.stdin.read(1)
                            if char2 == '\x07':  # Ctrl+G - cancel
                                self._redraw_line(prompt, buffer, cursor)
                                break
                            elif char2 == '\r':
                                break
                            elif char2 == '\x7f':  # Backspace
                                search_term = search_term[:-1]
                            else:
                                search_term += char2
                            
                            # Search
                            if search_term and self.shell:
                                for i in range(len(self.shell.history) - 1, -1, -1):
                                    if search_term in self.shell.history[i]:
                                        buffer = list(self.shell.history[i])
                                        cursor = len(buffer)
                                        self._redraw_line(prompt, buffer, cursor)
                                        self._show_message(f"(reverse-i-search)`{search_term}': ")
                                        break
                    
                    elif char == '\x1b':  # Escape sequence
                        seq = sys.stdin.read(2)
                        if seq == '[A':  # Up arrow
                            if self.shell and self.shell.history:
                                if history_idx > 0:
                                    history_idx -= 1
                                    buffer = list(self.shell.history[history_idx])
                                    cursor = len(buffer)
                                    self._redraw_line(prompt, buffer, cursor)
                        elif seq == '[B':  # Down arrow
                            if self.shell and self.shell.history:
                                if history_idx < len(self.shell.history) - 1:
                                    history_idx += 1
                                    buffer = list(self.shell.history[history_idx])
                                    cursor = len(buffer)
                                else:
                                    history_idx = len(self.shell.history)
                                    buffer = []
                                    cursor = 0
                                self._redraw_line(prompt, buffer, cursor)
                        elif seq == '[C':  # Right arrow
                            if cursor < len(buffer):
                                cursor += 1
                                self._move_cursor(prompt, cursor)
                        elif seq == '[D':  # Left arrow
                            if cursor > 0:
                                cursor -= 1
                                self._move_cursor(prompt, cursor)
                        elif seq == '[H':  # Home
                            cursor = 0
                            self._move_cursor(prompt, cursor)
                        elif seq == '[F':  # End
                            cursor = len(buffer)
                            self._move_cursor(prompt, cursor)
                        elif seq == '[3':  # Delete key
                            # Read one more char (~)
                            sys.stdin.read(1)
                            if cursor < len(buffer):
                                del buffer[cursor]
                                self._redraw_line(prompt, buffer, cursor)
                    
                    elif ord(char) >= 32:  # Printable character
                        buffer.insert(cursor, char)
                        cursor += 1
                        # Redraw efficiently
                        sys.stdout.write(''.join(buffer[cursor-1:]))
                        # Move cursor back if needed
                        if cursor < len(buffer):
                            sys.stdout.write('\x1b[' + str(len(buffer) - cursor) + 'D')
                        sys.stdout.flush()
        
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def _redraw_line(self, prompt: str, buffer: List[str], cursor: int):
        """Redraw the entire line."""
        # Clear to end of line, write buffer, position cursor
        sys.stdout.write('\x1b[2K\r')  # Clear line and return to start
        sys.stdout.write(prompt + ''.join(buffer))
        # Position cursor
        if cursor < len(buffer):
            sys.stdout.write('\x1b[' + str(len(buffer) - cursor) + 'D')
        sys.stdout.flush()
    
    def _move_cursor(self, prompt: str, cursor: int):
        """Move cursor to specific position."""
        sys.stdout.write('\r' + prompt)
        if cursor > 0:
            sys.stdout.write('\x1b[' + str(cursor) + 'C')
        sys.stdout.flush()
    
    def _display_matches(self, matches: List[str]):
        """Display completion matches in columns."""
        if not matches:
            return
        
        # Calculate column width
        max_len = max(len(m) for m in matches) + 2
        
        # Get terminal width (default 80)
        try:
            import shutil
            term_width = shutil.get_terminal_size().columns
        except:
            term_width = 80
        
        cols = max(1, term_width // max_len)
        
        # Display matches
        sys.stdout.write('\r\n')
        for i, match in enumerate(matches):
            sys.stdout.write(match.ljust(max_len))
            if (i + 1) % cols == 0:
                sys.stdout.write('\r\n')
        if len(matches) % cols != 0:
            sys.stdout.write('\r\n')
        sys.stdout.flush()
    
    def _show_message(self, message: str):
        """Show a message at bottom of screen."""
        sys.stdout.write('\r\n' + message)
        sys.stdout.flush()
