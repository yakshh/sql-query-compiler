"""
lexer.py - Lexical Analyzer for the SQL Subset Compiler

This module converts raw SQL input text into a stream of tokens.
Each token has a type (from grammar.py), a value (the actual text),
and position information (line, column) for error reporting.

The lexer:
  1. Skips whitespace and newlines.
  2. Recognizes keywords (case-insensitive) and classifies them.
  3. Recognizes identifiers, numbers (int/decimal), and strings.
  4. Recognizes comparison operators and punctuation symbols.
  5. Reports meaningful errors with position information.
"""

import grammar as g


# =============================================================================
# Token Class
# =============================================================================

class Token:
    """
    Represents a single lexical token.

    Attributes:
        type  (str): Token type from grammar.py (e.g., 'SELECT', 'IDENTIFIER').
        value (str): The actual text that was matched (e.g., 'name', '50000').
        line  (int): 1-indexed line number where the token starts.
        col   (int): 1-indexed column number where the token starts.
    """

    def __init__(self, type_, value, line, col):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        if self.type in (g.IDENTIFIER, g.NUMBER, g.STRING):
            return f"{self.type}({self.value})"
        return f"{self.type}"

    def __eq__(self, other):
        if isinstance(other, Token):
            return self.type == other.type and self.value == other.value
        return False


# =============================================================================
# Lexer Error
# =============================================================================

class LexerError(Exception):
    """
    Raised when the lexer encounters an invalid character or malformed token.

    Attributes:
        message (str): Description of the error.
        line    (int): Line number where the error occurred.
        col     (int): Column number where the error occurred.
    """

    def __init__(self, message, line, col):
        self.message = message
        self.line = line
        self.col = col
        super().__init__(f"Lexical Error at line {line}, col {col}: {message}")


# =============================================================================
# Keyword Map
# =============================================================================
# Maps uppercase keyword strings to their token types.
# If an identifier matches a keyword (case-insensitive), it becomes that keyword.

KEYWORD_MAP = {
    "SELECT": g.SELECT,
    "FROM":   g.FROM,
    "WHERE":  g.WHERE,
    "ORDER":  g.ORDER,
    "BY":     g.BY,
    "ASC":    g.ASC,
    "DESC":   g.DESC,
    "AND":    g.AND,
    "OR":     g.OR,
}


# =============================================================================
# Lexer Class
# =============================================================================

class Lexer:
    """
    Lexical analyzer that converts SQL text into a list of tokens.

    Usage:
        lexer = Lexer("SELECT name FROM employees;")
        tokens = lexer.tokenize()
    """

    def __init__(self, text):
        """
        Initialize the lexer with input text.

        Args:
            text (str): The raw SQL query string.
        """
        self.text = text
        self.pos = 0          # Current position in the text (0-indexed)
        self.line = 1         # Current line number (1-indexed)
        self.col = 1          # Current column number (1-indexed)
        self.tokens = []      # Accumulated tokens

    # -------------------------------------------------------------------------
    # Character inspection helpers
    # -------------------------------------------------------------------------

    def _current_char(self):
        """Return the character at the current position, or None if at end."""
        if self.pos < len(self.text):
            return self.text[self.pos]
        return None

    def _peek_char(self):
        """Return the next character (pos+1), or None if at end."""
        if self.pos + 1 < len(self.text):
            return self.text[self.pos + 1]
        return None

    def _advance(self):
        """
        Move to the next character, updating line and column numbers.
        Returns the character that was consumed.
        """
        char = self.text[self.pos]
        if char == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1
        return char

    # -------------------------------------------------------------------------
    # Whitespace handling
    # -------------------------------------------------------------------------

    def _skip_whitespace(self):
        """Advance past any whitespace characters (spaces, tabs, newlines)."""
        while self.pos < len(self.text) and self.text[self.pos] in (' ', '\t', '\n', '\r'):
            self._advance()

    # -------------------------------------------------------------------------
    # Token recognition methods
    # -------------------------------------------------------------------------

    def _read_identifier_or_keyword(self):
        """
        Read an identifier (letter/underscore followed by letters/digits/underscores).
        If it matches a SQL keyword, return the keyword token type instead.
        """
        start_line = self.line
        start_col = self.col
        result = []

        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            result.append(self._advance())

        word = "".join(result)
        upper_word = word.upper()

        # Check if this identifier is actually a keyword
        if upper_word in KEYWORD_MAP:
            return Token(KEYWORD_MAP[upper_word], upper_word, start_line, start_col)
        else:
            return Token(g.IDENTIFIER, word, start_line, start_col)

    def _read_number(self):
        """
        Read a numeric literal (integer or decimal).
        Supports: 123, 45.67, 0.5
        Does NOT support: .5, 1.2.3, 1e10
        """
        start_line = self.line
        start_col = self.col
        result = []
        has_dot = False

        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char.isdigit():
                result.append(self._advance())
            elif char == '.' and not has_dot:
                # Check that the next character is a digit (not just a trailing dot)
                next_char = self._peek_char()
                if next_char is not None and next_char.isdigit():
                    has_dot = True
                    result.append(self._advance())  # consume the '.'
                else:
                    break  # Trailing dot — stop here
            else:
                break

        return Token(g.NUMBER, "".join(result), start_line, start_col)

    def _read_string(self):
        """
        Read a single-quoted string literal.
        Example: 'Engineering', 'hello world'
        Reports an error if the string is not terminated.
        """
        start_line = self.line
        start_col = self.col
        self._advance()  # consume the opening quote
        result = []

        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "'":
                self._advance()  # consume the closing quote
                return Token(g.STRING, "".join(result), start_line, start_col)
            elif char == '\n':
                raise LexerError("Unterminated string literal (newline found)", start_line, start_col)
            else:
                result.append(self._advance())

        raise LexerError("Unterminated string literal (reached end of input)", start_line, start_col)

    # -------------------------------------------------------------------------
    # Main tokenization method
    # -------------------------------------------------------------------------

    def tokenize(self):
        """
        Scan the entire input text and return a list of tokens.
        Appends an EOF token at the end.

        Returns:
            list[Token]: The list of tokens including a trailing EOF token.

        Raises:
            LexerError: If an invalid character or malformed token is found.
        """
        self.tokens = []

        while self.pos < len(self.text):
            self._skip_whitespace()

            if self.pos >= len(self.text):
                break

            char = self._current_char()
            start_line = self.line
            start_col = self.col

            # --- Identifiers and keywords ---
            if char.isalpha() or char == '_':
                self.tokens.append(self._read_identifier_or_keyword())

            # --- Numbers ---
            elif char.isdigit():
                self.tokens.append(self._read_number())

            # --- String literals ---
            elif char == "'":
                self.tokens.append(self._read_string())

            # --- Star ---
            elif char == '*':
                self._advance()
                self.tokens.append(Token(g.STAR, "*", start_line, start_col))

            # --- Comma ---
            elif char == ',':
                self._advance()
                self.tokens.append(Token(g.COMMA, ",", start_line, start_col))

            # --- Semicolon ---
            elif char == ';':
                self._advance()
                self.tokens.append(Token(g.SEMICOLON, ";", start_line, start_col))

            # --- Comparison operators ---
            # Must check two-character operators before single-character ones

            elif char == '!' and self._peek_char() == '=':
                self._advance()  # consume '!'
                self._advance()  # consume '='
                self.tokens.append(Token(g.NEQ, "!=", start_line, start_col))

            elif char == '>' and self._peek_char() == '=':
                self._advance()  # consume '>'
                self._advance()  # consume '='
                self.tokens.append(Token(g.GEQ, ">=", start_line, start_col))

            elif char == '<' and self._peek_char() == '=':
                self._advance()  # consume '<'
                self._advance()  # consume '='
                self.tokens.append(Token(g.LEQ, "<=", start_line, start_col))

            elif char == '>':
                self._advance()
                self.tokens.append(Token(g.GT, ">", start_line, start_col))

            elif char == '<':
                self._advance()
                self.tokens.append(Token(g.LT, "<", start_line, start_col))

            elif char == '=':
                self._advance()
                self.tokens.append(Token(g.EQ, "=", start_line, start_col))

            # --- '!' without '=' is an error ---
            elif char == '!':
                self._advance()
                raise LexerError(
                    f"Unexpected character '!' — did you mean '!='?",
                    start_line, start_col
                )

            # --- Unknown character ---
            else:
                self._advance()
                raise LexerError(
                    f"Unexpected character '{char}'",
                    start_line, start_col
                )

        # Append end-of-input marker
        self.tokens.append(Token(g.EOF, "$", self.line, self.col))
        return self.tokens


# =============================================================================
# Standalone testing
# =============================================================================

if __name__ == "__main__":
    # Test queries to demonstrate lexer behavior
    test_queries = [
        # Valid queries
        "SELECT * FROM employees;",
        "SELECT name, salary FROM employees WHERE salary > 50000;",
        "SELECT name FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;",
        "SELECT id, name, age FROM employees WHERE age >= 25 AND salary <= 80000;",
        # Edge cases
        "select NAME from EMPLOYEES;",  # Case insensitivity
        "SELECT salary FROM employees WHERE salary != 0;",
    ]

    error_queries = [
        "SELECT name FROM employees WHERE salary @ 100;",   # Invalid character
        "SELECT name FROM employees WHERE name = 'hello;",  # Unterminated string
    ]

    print("=" * 60)
    print("  LEXER TEST — Valid Queries")
    print("=" * 60)

    for query in test_queries:
        print(f"\nInput:  {query}")
        try:
            lexer = Lexer(query)
            tokens = lexer.tokenize()
            print(f"Tokens: {' | '.join(str(t) for t in tokens)}")
        except LexerError as e:
            print(f"ERROR:  {e}")

    print("\n" + "=" * 60)
    print("  LEXER TEST — Error Queries")
    print("=" * 60)

    for query in error_queries:
        print(f"\nInput:  {query}")
        try:
            lexer = Lexer(query)
            tokens = lexer.tokenize()
            print(f"Tokens: {' | '.join(str(t) for t in tokens)}")
        except LexerError as e:
            print(f"ERROR:  {e}")
