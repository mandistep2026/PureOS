"""
PureOS Text Editor
Simple line-based text editor for creating and editing files.
Similar to nano but simplified for PureOS.
Uses only Python standard library.
"""

import sys
import os
from typing import List, Optional


class TextEditor:
    """Simple text editor for PureOS."""
    
    def __init__(self, filesystem, filename: Optional[str] = None):
        self.fs = filesystem
        self.filename = filename
        self.lines: List[str] = []
        self.cursor_line = 0
        self.cursor_col = 0
        self.modified = False
        self.running = False
        self.message = ""
        
        # Load file if it exists
        if filename and self.fs.exists(filename):
            content = self.fs.read_file(filename)
            if content:
                self.lines = content.decode('utf-8', errors='replace').split('\n')
                # Remove trailing empty line if file ends with newline
                if self.lines and self.lines[-1] == '':
                    self.lines.pop()
    
    def display(self) -> None:
        """Display the editor interface."""
        # Clear screen
        print("\033[2J\033[H", end='')
        
        # Title bar
        title = f"PureOS Editor 1.0"
        if self.filename:
            title += f" - {self.filename}"
        if self.modified:
            title += " [Modified]"
        print(f"\033[7m{title:^80}\033[0m")
        print()
        
        # Content area (show up to 20 lines)
        visible_lines = min(len(self.lines), 20)
        for i in range(visible_lines):
            prefix = ">" if i == self.cursor_line else " "
            line_num = f"{i+1:4d}"
            line_content = self.lines[i][:75]  # Truncate long lines
            if i == self.cursor_line:
                print(f"\033[7m{prefix}{line_num} {line_content}\033[0m")
            else:
                print(f"{prefix}{line_num} {line_content}")
        
        # Fill empty space
        for i in range(visible_lines, 20):
            print()
        
        print()
        
        # Message area
        if self.message:
            print(f"\033[7m {self.message:<78}\033[0m")
            self.message = ""
        else:
            print("\033[7m" + " " * 80 + "\033[0m")
        
        # Help bar
        print("\033[7m Ctrl+S: Save | Ctrl+Q: Quit | Ctrl+N: New Line | Ctrl+D: Delete Line | Arrows: Move \033[0m")
    
    def save(self) -> bool:
        """Save the file."""
        if not self.filename:
            self.message = "Error: No filename specified"
            return False
        
        content = '\n'.join(self.lines).encode('utf-8')
        
        if self.fs.write_file(self.filename, content):
            self.modified = False
            self.message = f"Saved {self.filename}"
            return True
        else:
            self.message = f"Error: Could not save {self.filename}"
            return False
    
    def insert_line(self) -> None:
        """Insert a new line at cursor position."""
        self.lines.insert(self.cursor_line, "")
        self.modified = True
        self.message = "New line inserted"
    
    def delete_line(self) -> None:
        """Delete current line."""
        if self.lines and 0 <= self.cursor_line < len(self.lines):
            del self.lines[self.cursor_line]
            if self.cursor_line >= len(self.lines) and self.lines:
                self.cursor_line = len(self.lines) - 1
            self.modified = True
            self.message = "Line deleted"
    
    def move_cursor(self, direction: str) -> None:
        """Move cursor in given direction."""
        if direction == "up":
            if self.cursor_line > 0:
                self.cursor_line -= 1
        elif direction == "down":
            if self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
        elif direction == "left":
            if self.cursor_col > 0:
                self.cursor_col -= 1
        elif direction == "right":
            if self.lines and self.cursor_col < len(self.lines[self.cursor_line]):
                self.cursor_col += 1
    
    def edit_line(self) -> None:
        """Edit the current line (simple input)."""
        if not self.lines:
            self.lines.append("")
        
        current_line = self.lines[self.cursor_line] if self.cursor_line < len(self.lines) else ""
        print(f"\nEditing line {self.cursor_line + 1}")
        print(f"Current: {current_line}")
        print("Enter new text (empty to keep current, Ctrl+C to cancel):")
        
        try:
            new_text = input("> ")
            if self.cursor_line < len(self.lines):
                self.lines[self.cursor_line] = new_text
            else:
                self.lines.append(new_text)
            self.modified = True
            self.message = "Line updated"
        except KeyboardInterrupt:
            self.message = "Edit cancelled"
    
    def run(self) -> int:
        """Run the editor."""
        self.running = True
        
        # Enable raw mode simulation (simplified)
        print("PureOS Text Editor")
        print("=" * 50)
        if self.filename:
            print(f"Editing: {self.filename}")
        else:
            print("New file")
        print()
        
        while self.running:
            self.display()
            
            try:
                # Get command
                print("\nCommand: ", end='', flush=True)
                
                # Try to read a key
                if os.name == 'posix':
                    import tty
                    import termios
                    
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setraw(fd)
                        key = sys.stdin.read(1)
                        
                        # Check for escape sequences (arrow keys)
                        if key == '\x1b':
                            seq = sys.stdin.read(2)
                            if seq == '[A':  # Up
                                self.move_cursor("up")
                                continue
                            elif seq == '[B':  # Down
                                self.move_cursor("down")
                                continue
                            elif seq == '[C':  # Right
                                self.move_cursor("right")
                                continue
                            elif seq == '[D':  # Left
                                self.move_cursor("left")
                                continue
                        elif key == '\x13':  # Ctrl+S
                            self.save()
                            continue
                        elif key == '\x11':  # Ctrl+Q
                            if self.modified:
                                print("\nFile modified. Save? (y/n): ", end='')
                                response = input().lower()
                                if response == 'y':
                                    self.save()
                            self.running = False
                            continue
                        elif key == '\x0e':  # Ctrl+N
                            self.insert_line()
                            continue
                        elif key == '\x04':  # Ctrl+D
                            self.delete_line()
                            continue
                        elif key == '\r' or key == '\n':
                            self.edit_line()
                            continue
                        
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                else:
                    # Windows or other - use simple input
                    cmd = input()
                    if cmd.lower() == 's':
                        self.save()
                    elif cmd.lower() == 'q':
                        if self.modified:
                            print("Save changes? (y/n): ", end='')
                            if input().lower() == 'y':
                                self.save()
                        self.running = False
                    elif cmd.lower() == 'n':
                        self.insert_line()
                    elif cmd.lower() == 'd':
                        self.delete_line()
                    elif cmd.lower() == 'e':
                        self.edit_line()
                    elif cmd == '':
                        self.edit_line()
            
            except KeyboardInterrupt:
                if self.modified:
                    print("\n\nSave changes? (y/n): ", end='')
                    try:
                        if input().lower() == 'y':
                            self.save()
                    except EOFError:
                        pass
                break
            except Exception as e:
                self.message = f"Error: {e}"
        
        print("\nEditor closed.")
        return 0


def edit_file(filesystem, filename: Optional[str] = None) -> int:
    """Convenience function to edit a file."""
    editor = TextEditor(filesystem, filename)
    return editor.run()
