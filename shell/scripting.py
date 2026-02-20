"""
PureOS Scripting Engine
Execute shell scripts with variables, control flow, and functions.
Uses only Python standard library.
"""

import re
import shlex
from typing import List, Dict, Optional, Any, Callable
from enum import Enum, auto


class TokenType(Enum):
    """Token types for script parsing."""
    WORD = auto()
    STRING = auto()
    NUMBER = auto()
    VARIABLE = auto()
    OPERATOR = auto()
    NEWLINE = auto()
    EOF = auto()


class Token:
    """Represents a token in the script."""
    def __init__(self, type: TokenType, value: str, line: int = 0):
        self.type = type
        self.value = value
        self.line = line
    
    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class ScriptLexer:
    """Lexer for tokenizing shell scripts."""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.current_char = self.text[0] if text else None
    
    def error(self, msg: str):
        """Raise a lexer error."""
        raise SyntaxError(f"Line {self.line}: {msg}")
    
    def advance(self):
        """Move to next character."""
        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            if self.current_char == '\n':
                self.line += 1
            self.current_char = self.text[self.pos]
    
    def skip_whitespace(self):
        """Skip whitespace (but not newlines)."""
        while self.current_char is not None and self.current_char in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        """Skip comment until end of line."""
        while self.current_char is not None and self.current_char != '\n':
            self.advance()
    
    def read_string(self, quote: str) -> str:
        """Read a quoted string."""
        result = []
        self.advance()  # Skip opening quote
        
        while self.current_char is not None and self.current_char != quote:
            if self.current_char == '\\':
                self.advance()
                if self.current_char == 'n':
                    result.append('\n')
                elif self.current_char == 't':
                    result.append('\t')
                elif self.current_char == '\\':
                    result.append('\\')
                elif self.current_char == quote:
                    result.append(quote)
                else:
                    result.append(self.current_char)
            else:
                result.append(self.current_char)
            self.advance()
        
        if self.current_char != quote:
            self.error(f"Unterminated string")
        
        self.advance()  # Skip closing quote
        return ''.join(result)
    
    def read_word(self) -> str:
        """Read a word (identifier or command)."""
        result = []
        while (self.current_char is not None and 
               self.current_char not in ' \t\n\r;|&<>$"\'`#'):
            result.append(self.current_char)
            self.advance()
        return ''.join(result)
    
    def read_variable(self) -> str:
        """Read a variable name ($VAR or ${VAR})."""
        self.advance()  # Skip $
        
        if self.current_char == '{':
            self.advance()  # Skip {
            result = []
            while self.current_char is not None and self.current_char != '}':
                result.append(self.current_char)
                self.advance()
            if self.current_char != '}':
                self.error("Unclosed variable brace")
            self.advance()  # Skip }
            return ''.join(result)
        else:
            # Simple variable name
            result = []
            while (self.current_char is not None and 
                   (self.current_char.isalnum() or self.current_char == '_')):
                result.append(self.current_char)
                self.advance()
            return ''.join(result)
    
    def get_next_token(self) -> Token:
        """Get the next token from input."""
        while self.current_char is not None:
            line = self.line
            
            # Skip whitespace
            if self.current_char in ' \t\r':
                self.skip_whitespace()
                continue
            
            # Comments
            if self.current_char == '#':
                self.skip_comment()
                continue
            
            # Newlines
            if self.current_char == '\n':
                self.advance()
                return Token(TokenType.NEWLINE, '\n', line)
            
            # Semicolons (command separators)
            if self.current_char == ';':
                self.advance()
                return Token(TokenType.NEWLINE, ';', line)
            
            # Strings
            if self.current_char in '"\'':
                quote = self.current_char
                value = self.read_string(quote)
                return Token(TokenType.STRING, value, line)
            
            # Variables
            if self.current_char == '$':
                name = self.read_variable()
                return Token(TokenType.VARIABLE, name, line)
            
            # Numbers
            if self.current_char.isdigit():
                num = []
                while (self.current_char is not None and 
                       (self.current_char.isdigit() or self.current_char == '.')):
                    num.append(self.current_char)
                    self.advance()
                return Token(TokenType.NUMBER, ''.join(num), line)
            
            # Operators
            if self.current_char in '=!<>+-*/':
                op = self.current_char
                self.advance()
                if self.current_char == '=':
                    op += self.current_char
                    self.advance()
                return Token(TokenType.OPERATOR, op, line)
            
            # Words (commands, arguments)
            word = self.read_word()
            if word:
                return Token(TokenType.WORD, word, line)
            
            # Unknown character
            self.error(f"Unexpected character: {self.current_char}")
        
        return Token(TokenType.EOF, '', self.line)
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire input."""
        tokens = []
        while True:
            token = self.get_next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens


class VariableManager:
    """Manages shell variables (local and environment)."""
    
    def __init__(self, environment: Dict[str, str] = None):
        self.local_vars: Dict[str, str] = {}
        self.environment = environment or {}
        self.last_exit_code = 0
    
    def set(self, name: str, value: str):
        """Set a local variable."""
        self.local_vars[name] = value
    
    def get(self, name: str) -> Optional[str]:
        """Get variable value (checks local first, then environment)."""
        # Special variables
        if name == '?':
            return str(self.last_exit_code)
        if name == '$':
            import os
            return str(os.getpid())
        if name == '#':
            # Number of positional parameters
            return str(len(self.local_vars.get('@', [])))
        
        # Check local vars first
        if name in self.local_vars:
            return self.local_vars[name]
        
        # Check environment
        return self.environment.get(name)
    
    def export(self, name: str):
        """Export a local variable to environment."""
        if name in self.local_vars:
            self.environment[name] = self.local_vars[name]
    
    def unset(self, name: str):
        """Remove a variable."""
        if name in self.local_vars:
            del self.local_vars[name]
        if name in self.environment:
            del self.environment[name]
    
    def expand(self, text: str) -> str:
        """Expand variables in text."""
        result = []
        i = 0
        while i < len(text):
            if text[i] == '$':
                # Variable expansion
                if i + 1 < len(text):
                    if text[i + 1] == '{':
                        # ${VAR} format
                        end = text.find('}', i + 2)
                        if end != -1:
                            var_name = text[i + 2:end]
                            value = self.get(var_name) or ''
                            result.append(value)
                            i = end + 1
                            continue
                    elif text[i + 1].isalpha() or text[i + 1] == '_':
                        # $VAR format
                        j = i + 1
                        while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                            j += 1
                        var_name = text[i + 1:j]
                        value = self.get(var_name) or ''
                        result.append(value)
                        i = j
                        continue
            result.append(text[i])
            i += 1
        return ''.join(result)


class ScriptExecutor:
    """Executes parsed shell scripts."""
    
    def __init__(self, shell, filesystem, kernel):
        self.shell = shell
        self.fs = filesystem
        self.kernel = kernel
        self.vars = VariableManager(shell.environment if shell else {})
        self.functions: Dict[str, List[str]] = {}
        self.positional_params: List[str] = []
        self.in_function = False
    
    def execute_script(self, script_text: str, args: List[str] = None) -> int:
        """Execute a script with given arguments."""
        # Set positional parameters
        self.positional_params = args or []
        for i, arg in enumerate(self.positional_params, 1):
            self.vars.set(str(i), arg)
        self.vars.set('0', 'script')  # Script name
        self.vars.set('@', ' '.join(self.positional_params))
        
        # Tokenize and execute
        lexer = ScriptLexer(script_text)
        tokens = lexer.tokenize()
        
        return self._execute_tokens(tokens)
    
    def execute_file(self, filename: str, args: List[str] = None) -> int:
        """Execute a script file."""
        content = self.fs.read_file(filename)
        if content is None:
            print(f"bash: {filename}: No such file or directory")
            return 127
        
        script_text = content.decode('utf-8', errors='replace')
        return self.execute_script(script_text, args)
    
    def _execute_tokens(self, tokens: List[Token]) -> int:
        """Execute a list of tokens."""
        i = 0
        exit_code = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == TokenType.EOF:
                break
            
            if token.type == TokenType.NEWLINE:
                i += 1
                continue
            
            # Parse and execute a command or statement
            cmd_tokens, i = self._collect_command(tokens, i)
            if cmd_tokens:
                exit_code = self._execute_statement(cmd_tokens)
                self.vars.last_exit_code = exit_code
        
        return exit_code
    
    def _collect_command(self, tokens: List[Token], start: int) -> tuple:
        """Collect tokens for a single command/statement.

        For multi-line control structures (if/fi, while/done, for/done,
        case/esac, function bodies), we collect across newlines until the
        matching terminator is seen.
        """
        # Peek at first non-newline token to detect block starters
        peek = start
        while peek < len(tokens) and tokens[peek].type == TokenType.NEWLINE:
            peek += 1

        if peek < len(tokens) and tokens[peek].type != TokenType.EOF:
            first_val = tokens[peek].value

            # Map openers to their terminators (and depth-incrementing keywords)
            block_map = {
                'if':    ('fi',   {'if'}),
                'while': ('done', {'while', 'for'}),
                'for':   ('done', {'while', 'for'}),
                'case':  ('esac', {'case'}),
                'function': ('}', {'{'}),
            }

            if first_val in block_map:
                terminator, depth_words = block_map[first_val]
                cmd_tokens = []
                i = start
                depth = 0
                while i < len(tokens):
                    tok = tokens[i]
                    if tok.type == TokenType.EOF:
                        break
                    if tok.type == TokenType.NEWLINE:
                        # Keep newlines inside block so sub-parsers can use them
                        cmd_tokens.append(tok)
                        i += 1
                        continue
                    if tok.value in depth_words:
                        depth += 1
                    elif tok.value == terminator:
                        if depth > 1:
                            depth -= 1
                        else:
                            cmd_tokens.append(tok)
                            i += 1
                            break
                    cmd_tokens.append(tok)
                    i += 1
                # Strip leading/trailing newline tokens
                return [t for t in cmd_tokens if t.type != TokenType.NEWLINE or
                        any(t2.type != TokenType.NEWLINE for t2 in cmd_tokens)], i

        # Default: collect until end of line
        cmd_tokens = []
        i = start
        while i < len(tokens):
            token = tokens[i]
            if token.type == TokenType.NEWLINE:
                i += 1
                break
            if token.type == TokenType.EOF:
                break
            cmd_tokens.append(token)
            i += 1
        return cmd_tokens, i
    
    def _execute_statement(self, tokens: List[Token]) -> int:
        """Execute a single statement."""
        if not tokens:
            return 0
        
        # Check for control structures
        first_token = tokens[0]
        
        if first_token.value == 'if':
            return self._execute_if(tokens)
        
        if first_token.value == 'for':
            return self._execute_for(tokens)
        
        if first_token.value == 'while':
            return self._execute_while(tokens)
        
        if first_token.value == 'case':
            return self._execute_case(tokens)
        
        if first_token.value == 'function':
            return self._execute_function_def(tokens)
        
        if first_token.value == 'return':
            return self._execute_return(tokens)
        
        # Regular command execution
        return self._execute_command(tokens)
    
    def _execute_command(self, tokens: List[Token]) -> int:
        """Execute a simple command."""
        # Build command line
        args = []
        for token in tokens:
            if token.type in (TokenType.WORD, TokenType.STRING):
                expanded = self.vars.expand(token.value)
                args.append(expanded)
            elif token.type == TokenType.VARIABLE:
                value = self.vars.get(token.value) or ''
                args.append(value)
        
        if not args:
            return 0
        
        # Check for variable assignment
        if '=' in args[0] and not args[0].startswith('='):
            parts = args[0].split('=', 1)
            if len(parts) == 2 and parts[0].isidentifier():
                self.vars.set(parts[0], parts[1])
                return 0
        
        # Execute via shell
        cmd_line = ' '.join(args)
        return self.shell.execute(cmd_line, save_to_history=False)
    
    def _execute_if(self, tokens: List[Token]) -> int:
        """Execute if statement."""
        # Simplified if: if condition; then commands; [elif; then;] [else;] fi
        # For now, support: if [ condition ]; then commands; fi
        
        # Find 'then' and 'fi'
        then_idx = None
        fi_idx = None
        else_idx = None
        
        for i, token in enumerate(tokens):
            if token.value == 'then':
                then_idx = i
            elif token.value == 'else':
                else_idx = i
            elif token.value == 'fi':
                fi_idx = i
        
        if then_idx is None or fi_idx is None:
            print("bash: syntax error in if statement")
            return 1
        
        # Get condition
        condition_tokens = tokens[1:then_idx]
        condition_result = self._evaluate_condition(condition_tokens)
        
        # Execute appropriate branch
        if condition_result:
            # Execute then branch
            if else_idx:
                then_tokens = tokens[then_idx + 1:else_idx]
            else:
                then_tokens = tokens[then_idx + 1:fi_idx]
            return self._execute_tokens(self._tokens_with_newlines(then_tokens))
        else:
            # Execute else branch if present
            if else_idx:
                else_tokens = tokens[else_idx + 1:fi_idx]
                return self._execute_tokens(self._tokens_with_newlines(else_tokens))
        
        return 0
    
    def _execute_for(self, tokens: List[Token]) -> int:
        """Execute for loop."""
        # Format: for var in list; do commands; done
        
        # Find 'in', 'do', and 'done'
        in_idx = None
        do_idx = None
        done_idx = None
        
        for i, token in enumerate(tokens):
            if token.value == 'in':
                in_idx = i
            elif token.value == 'do':
                do_idx = i
            elif token.value == 'done':
                done_idx = i
        
        if in_idx is None or do_idx is None or done_idx is None:
            print("bash: syntax error in for statement")
            return 1
        
        # Get variable name
        var_name = tokens[1].value if len(tokens) > 1 else None
        if not var_name:
            print("bash: syntax error: missing variable name")
            return 1
        
        # Get list items
        list_tokens = tokens[in_idx + 1:do_idx]
        items = []
        for token in list_tokens:
            if token.type in (TokenType.WORD, TokenType.STRING):
                expanded = self.vars.expand(token.value)
                items.append(expanded)
        
        # Get loop body
        body_tokens = tokens[do_idx + 1:done_idx]
        
        # Execute loop
        exit_code = 0
        for item in items:
            self.vars.set(var_name, item)
            exit_code = self._execute_tokens(self._tokens_with_newlines(body_tokens))
        
        return exit_code
    
    def _execute_while(self, tokens: List[Token]) -> int:
        """Execute while loop."""
        # Format: while condition; do commands; done
        
        do_idx = None
        done_idx = None
        
        for i, token in enumerate(tokens):
            if token.value == 'do':
                do_idx = i
            elif token.value == 'done':
                done_idx = i
        
        if do_idx is None or done_idx is None:
            print("bash: syntax error in while statement")
            return 1
        
        condition_tokens = tokens[1:do_idx]
        body_tokens = tokens[do_idx + 1:done_idx]
        
        # Execute loop (with safety limit)
        exit_code = 0
        max_iterations = 1000
        iterations = 0
        
        while self._evaluate_condition(condition_tokens) and iterations < max_iterations:
            exit_code = self._execute_tokens(self._tokens_with_newlines(body_tokens))
            iterations += 1
        
        if iterations >= max_iterations:
            print("bash: while loop exceeded maximum iterations")
        
        return exit_code
    
    def _execute_case(self, tokens: List[Token]) -> int:
        """Execute case statement.
        Format: case WORD in
                  pattern1) cmd1 ;; pattern2) cmd2 ;;
                  *) default ;;
                esac

        Works with the actual tokenizer output:
        - 'apple)' may appear as one WORD token or as WORD('apple') + WORD(')')
        - ';' semicolons appear as NEWLINE tokens
        - '*' appears as OPERATOR token
        """
        import fnmatch as _fnmatch

        if len(tokens) < 3:
            print("bash: syntax error in case statement")
            return 1

        # Find the VARIABLE or WORD token that is the case word
        # tokens[0] = 'case', tokens[1] = word (WORD or VARIABLE), then 'in'
        word_tok = tokens[1] if len(tokens) > 1 else None
        if word_tok is None:
            print("bash: syntax error in case statement")
            return 1

        from shell.scripting import TokenType as TT
        if word_tok.type == TT.VARIABLE:
            word = self.vars.get(word_tok.value) or ''
        else:
            word = self.vars.expand(word_tok.value)

        # Find 'in' and 'esac' indices
        in_idx = None
        esac_idx = None
        for i, t in enumerate(tokens):
            if t.value == 'in' and in_idx is None and i > 1:
                in_idx = i
            elif t.value == 'esac':
                esac_idx = i

        if in_idx is None or esac_idx is None:
            print("bash: syntax error: missing 'in' or 'esac'")
            return 1

        body_tokens = tokens[in_idx + 1:esac_idx]

        # Parse clauses token-by-token.
        # Each clause: <pattern_tokens> ')' <cmd_tokens> ';;'
        # Patterns may be:
        #   - "apple)"  — single WORD with trailing ')'
        #   - WORD('apple') WORD(')')
        #   - OPERATOR('*') WORD(')')
        # ';;' is two consecutive NEWLINE(';') tokens, or a single ';' after cmd

        def is_double_semi(toks: List, idx: int) -> bool:
            """Check if position idx starts a ';;' (two semicolons)."""
            if idx >= len(toks):
                return False
            t = toks[idx]
            # Single token ';;'
            if t.value == ';;':
                return True
            # Two adjacent ';' tokens
            if t.value == ';' and idx + 1 < len(toks) and toks[idx + 1].value == ';':
                return True
            return False

        def skip_double_semi(toks: List, idx: int) -> int:
            t = toks[idx]
            if t.value == ';;':
                return idx + 1
            if t.value == ';' and idx + 1 < len(toks) and toks[idx + 1].value == ';':
                return idx + 2
            return idx + 1

        # Skip leading whitespace/newlines
        bi = 0
        while bi < len(body_tokens) and body_tokens[bi].type == TT.NEWLINE:
            bi += 1

        exit_code = 0

        while bi < len(body_tokens):
            # Collect pattern tokens (before ')')
            pattern_parts = []
            while bi < len(body_tokens):
                tok = body_tokens[bi]
                if tok.type == TT.NEWLINE:
                    bi += 1
                    continue
                # Check for closing paren — end of pattern
                if tok.value.endswith(')'):
                    # The token itself may be "apple)" 
                    pat_val = tok.value.rstrip(')')
                    if pat_val:
                        pattern_parts.append(pat_val)
                    bi += 1
                    break
                if tok.value == ')':
                    bi += 1
                    break
                pattern_parts.append(tok.value)
                bi += 1

            if not pattern_parts:
                # No more clauses
                break

            # Collect command tokens until ';;' or esac-boundary
            cmd_parts = []
            while bi < len(body_tokens):
                if is_double_semi(body_tokens, bi):
                    bi = skip_double_semi(body_tokens, bi)
                    break
                tok = body_tokens[bi]
                if tok.type != TT.NEWLINE:
                    cmd_parts.append(tok.value)
                bi += 1

            # Skip trailing newlines
            while bi < len(body_tokens) and body_tokens[bi].type == TT.NEWLINE:
                bi += 1

            # Check each pattern
            matched = False
            for raw_pat in pattern_parts:
                # Handle | separators inside a single token e.g. "yes|y"
                for pat in raw_pat.split('|'):
                    pat = pat.strip()
                    pat_expanded = self.vars.expand(pat)
                    if pat_expanded == '*' or _fnmatch.fnmatch(word, pat_expanded):
                        matched = True
                        break
                if matched:
                    break

            if matched:
                cmd_str = ' '.join(cmd_parts).strip()
                if cmd_str:
                    exit_code = self.shell.execute(cmd_str, save_to_history=False)
                break

        return exit_code
    
    def _execute_function_def(self, tokens: List[Token]) -> int:
        """Define a function."""
        # Format: function name() { commands; } or name() { commands; }
        # Simplified: function name { commands; }
        
        if len(tokens) < 2:
            print("bash: syntax error in function definition")
            return 1
        
        func_name = tokens[1].value
        
        # Find function body (between { and })
        start_idx = None
        end_idx = None
        
        for i, token in enumerate(tokens):
            if token.value == '{':
                start_idx = i
            elif token.value == '}':
                end_idx = i
        
        if start_idx is None or end_idx is None:
            print("bash: syntax error: expected { and } in function definition")
            return 1
        
        # Store function body
        body_tokens = tokens[start_idx + 1:end_idx]
        self.functions[func_name] = body_tokens
        
        return 0
    
    def _execute_return(self, tokens: List[Token]) -> int:
        """Execute return statement."""
        if len(tokens) > 1:
            try:
                return int(tokens[1].value)
            except ValueError:
                pass
        return 0
    
    def _evaluate_condition(self, tokens: List[Token]) -> bool:
        """Evaluate a test condition."""
        if not tokens:
            return False
        
        # Check for [ or test command
        if tokens[0].value in ('[', 'test'):
            return self._evaluate_test(tokens[1:] if tokens[0].value == '[' else tokens)
        
        # Simple command - check exit code
        exit_code = self._execute_command(tokens)
        return exit_code == 0
    
    def _evaluate_test(self, tokens: List[Token]) -> bool:
        """Evaluate test command conditions."""
        # Remove trailing ] if present
        if tokens and tokens[-1].value == ']':
            tokens = tokens[:-1]
        
        if not tokens:
            return False
        
        # File tests
        if tokens[0].value.startswith('-') and len(tokens) >= 2:
            test = tokens[0].value
            filename = self.vars.expand(tokens[1].value)
            
            if test == '-f':
                return self.fs.is_file(filename)
            elif test == '-d':
                return self.fs.is_directory(filename)
            elif test == '-e':
                return self.fs.exists(filename)
            elif test == '-r':
                # Check readability
                return True  # Simplified
            elif test == '-w':
                # Check writability
                return True  # Simplified
            elif test == '-x':
                # Check executability
                return True  # Simplified
            elif test == '-s':
                # Check if file has size > 0
                inode = self.fs.get_inode(filename)
                return inode is not None and inode.size > 0
        
        # String tests
        if len(tokens) == 3:
            left = self.vars.expand(tokens[0].value)
            op = tokens[1].value
            right = self.vars.expand(tokens[2].value)
            
            if op == '=':
                return left == right
            elif op == '!=':
                return left != right
        
        # Numeric tests
        if len(tokens) == 3:
            try:
                left = int(self.vars.expand(tokens[0].value))
                op = tokens[1].value
                right = int(self.vars.expand(tokens[2].value))
                
                if op == '-eq':
                    return left == right
                elif op == '-ne':
                    return left != right
                elif op == '-lt':
                    return left < right
                elif op == '-le':
                    return left <= right
                elif op == '-gt':
                    return left > right
                elif op == '-ge':
                    return left >= right
            except ValueError:
                pass
        
        # String unary tests
        if tokens[0].value == '-z' and len(tokens) >= 2:
            value = self.vars.expand(tokens[1].value)
            return len(value) == 0
        
        if tokens[0].value == '-n' and len(tokens) >= 2:
            value = self.vars.expand(tokens[1].value)
            return len(value) > 0
        
        return False
    
    def _tokens_with_newlines(self, tokens: List[Token]) -> List[Token]:
        """Add newlines between tokens for proper parsing."""
        result = []
        for i, token in enumerate(tokens):
            result.append(token)
            if i < len(tokens) - 1:
                # Add implicit newlines between statements
                pass
        result.append(Token(TokenType.EOF, '', 0))
        return result


def execute_script_file(filename: str, shell, filesystem, kernel, args: List[str] = None) -> int:
    """Convenience function to execute a script file."""
    executor = ScriptExecutor(shell, filesystem, kernel)
    return executor.execute_file(filename, args)
