"""
parser.py - LL(1) Predictive Parser for the SQL Subset Compiler

This module implements a table-driven predictive parser using the LL(1) parsing
table defined in grammar.py. It consumes the token stream from the lexer and:

  1. Validates that the input conforms to the grammar (syntax check).
  2. Records every parsing step (stack, input, action) for demonstration.
  3. Builds a parse tree that is later converted to an AST.

The parser does NOT use any external parsing library. It uses a standard
stack-based LL(1) parsing algorithm:
  - Push start symbol onto stack.
  - Repeat:
      - If top of stack is a terminal, match it with current input token.
      - If top of stack is a non-terminal, look up the parsing table to
        decide which production to expand.
      - If no table entry exists, report a syntax error.
  - Accept when both stack and input are exhausted.
"""

import grammar as g
from lexer import Token, Lexer, LexerError


# =============================================================================
# Parse Tree Node
# =============================================================================

class ParseNode:
    """
    A node in the parse tree produced by the LL(1) parser.

    For non-terminal nodes:
        symbol   = the non-terminal name (e.g., 'Query', 'SelectList')
        children = list of child ParseNode objects
        token    = None

    For terminal (leaf) nodes:
        symbol   = the terminal type (e.g., 'SELECT', 'IDENTIFIER')
        children = []
        token    = the actual Token object from the lexer
    """

    def __init__(self, symbol, token=None):
        self.symbol = symbol
        self.token = token      # Only set for terminal leaf nodes
        self.children = []

    def add_child(self, child):
        """Add a child node."""
        self.children.append(child)

    def is_terminal(self):
        """Check if this is a terminal (leaf) node."""
        return self.token is not None

    def __repr__(self):
        if self.token:
            return f"Leaf({self.token})"
        return f"Node({self.symbol}, children={len(self.children)})"

    def print_tree(self, indent=0):
        """Print the parse tree with indentation for debugging."""
        prefix = "  " * indent
        if self.is_terminal():
            print(f"{prefix}{self.token}")
        else:
            print(f"{prefix}{self.symbol}")
            for child in self.children:
                child.print_tree(indent + 1)


# =============================================================================
# Parser Error
# =============================================================================

class ParserError(Exception):
    """
    Raised when the parser encounters a syntax error.

    Attributes:
        message (str): Description of the error.
        token (Token): The token where the error was detected.
    """

    def __init__(self, message, token=None):
        self.message = message
        self.token = token
        if token:
            loc = f" at line {token.line}, col {token.col}"
            super().__init__(f"Syntax Error{loc}: {message}")
        else:
            super().__init__(f"Syntax Error: {message}")


# =============================================================================
# Parsing Step (for trace/demonstration)
# =============================================================================

class ParseStep:
    """
    Records one step of the LL(1) parsing process for demonstration.

    Attributes:
        step_num  (int):  Step number.
        stack     (str):  The parser stack contents (top on the right).
        input_str (str):  The remaining input tokens.
        action    (str):  The action taken (Match, Expand, Accept, Error).
    """

    def __init__(self, step_num, stack, input_str, action):
        self.step_num = step_num
        self.stack = stack
        self.input_str = input_str
        self.action = action

    def __repr__(self):
        return f"Step {self.step_num}: [{self.stack}] | [{self.input_str}] | {self.action}"


# =============================================================================
# LL(1) Predictive Parser
# =============================================================================

class Parser:
    """
    Table-driven LL(1) predictive parser.

    Usage:
        parser = Parser(tokens)
        parse_tree = parser.parse()
        trace = parser.get_trace()
    """

    def __init__(self, tokens):
        """
        Initialize the parser with a list of tokens (from the lexer).

        Args:
            tokens (list[Token]): Token list including the trailing EOF token.
        """
        self.tokens = tokens
        self.pos = 0               # Current position in the token list
        self.trace = []            # Parsing steps for demonstration
        self.step_count = 0        # Step counter

    def _current_token(self):
        """Return the current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(g.EOF, "$", -1, -1)

    def _format_stack(self, stack):
        """Format the stack contents as a string (bottom to top, left to right)."""
        return " ".join(stack)

    def _format_remaining_input(self):
        """Format the remaining input tokens as a string."""
        remaining = self.tokens[self.pos:]
        return " ".join(str(t) for t in remaining)

    def _record_step(self, stack, action):
        """Record a parsing step for the trace."""
        self.step_count += 1
        step = ParseStep(
            self.step_count,
            self._format_stack(stack),
            self._format_remaining_input(),
            action
        )
        self.trace.append(step)

    def parse(self):
        """
        Parse the token stream using the LL(1) parsing table.

        Returns:
            ParseNode: The root of the parse tree.

        Raises:
            ParserError: If a syntax error is detected.
        """
        # Initialize the stack with EOF marker and start symbol
        # Stack convention: top of stack is the LAST element of the list
        stack = [g.EOF, g.START_SYMBOL]

        # Create the root parse tree node
        root = ParseNode(g.START_SYMBOL)

        # Node stack mirrors the symbol stack for tree construction
        # Each entry is the ParseNode corresponding to the symbol on the stack
        node_stack = [None, root]

        while len(stack) > 0:
            top = stack[-1]
            current = self._current_token()

            # -----------------------------------------------------------------
            # Case 1: Top of stack is EOF — should match EOF in input
            # -----------------------------------------------------------------
            if top == g.EOF:
                if current.type == g.EOF:
                    self._record_step(stack, "Accept")
                    stack.pop()
                    node_stack.pop()
                    break
                else:
                    self._record_step(stack, f"Error: expected end of input, got {current}")
                    raise ParserError(
                        f"Expected end of input but found '{current.value}'",
                        current
                    )

            # -----------------------------------------------------------------
            # Case 2: Top of stack is a terminal — must match current token
            # -----------------------------------------------------------------
            elif g.is_terminal(top):
                if top == current.type:
                    self._record_step(stack, f"Match {current}")
                    stack.pop()
                    node = node_stack.pop()
                    # Attach the actual token to the leaf node
                    if node:
                        node.token = current
                    self.pos += 1  # consume the token
                else:
                    self._record_step(stack, f"Error: expected {top}, got {current}")
                    raise ParserError(
                        f"Expected {top} but found '{current.value}' ({current.type})",
                        current
                    )

            # -----------------------------------------------------------------
            # Case 3: Top of stack is a non-terminal — look up parsing table
            # -----------------------------------------------------------------
            elif g.is_non_terminal(top):
                action = g.get_parse_action(top, current.type)

                if action is None:
                    # No entry in parsing table — syntax error
                    # Generate a helpful error message
                    expected = self._expected_tokens(top)
                    self._record_step(
                        stack,
                        f"Error: no rule for ({top}, {current.type})"
                    )
                    raise ParserError(
                        f"Unexpected '{current.value}' ({current.type}). "
                        f"Expected one of: {', '.join(sorted(expected))}",
                        current
                    )

                # Get the production
                prod_nt, prod_symbols = g.get_production(action)
                prod_str = g.format_production(action)
                self._record_step(stack, f"Expand: {prod_str}")

                # Pop the non-terminal from both stacks
                stack.pop()
                parent_node = node_stack.pop()

                # Push the production's right-hand side in REVERSE order
                # (so the first symbol ends up on top of the stack)
                if prod_symbols != [g.EPSILON]:
                    for symbol in reversed(prod_symbols):
                        stack.append(symbol)
                        # Create a child node and push it onto the node stack
                        child = ParseNode(symbol)
                        node_stack.append(child)
                        parent_node.add_child(child)
                    # Reverse children so they are in correct order
                    # (we added them in reverse for the stack)
                    parent_node.children.reverse()

            # -----------------------------------------------------------------
            # Case 4: Epsilon — should not appear on the stack normally
            # -----------------------------------------------------------------
            elif top == g.EPSILON:
                stack.pop()
                node_stack.pop()

            else:
                raise ParserError(f"Internal error: unknown symbol '{top}' on stack")

        return root

    def _expected_tokens(self, non_terminal):
        """
        Determine which tokens are valid when a non-terminal is on top of stack.
        Used for error messages.
        """
        expected = set()
        for (nt, terminal), _ in g.PARSE_TABLE.items():
            if nt == non_terminal:
                expected.add(terminal)
        return expected

    def get_trace(self):
        """Return the list of parsing steps recorded during parsing."""
        return self.trace

    def print_trace(self):
        """Print the parsing trace in a formatted table."""
        if not self.trace:
            print("No parsing trace available. Call parse() first.")
            return

        # Column widths
        step_w = 6
        stack_w = max(len(s.stack) for s in self.trace)
        stack_w = max(stack_w, 5)  # minimum width
        input_w = max(len(s.input_str) for s in self.trace)
        input_w = max(input_w, 5)

        # Header
        header = f"{'Step':<{step_w}} {'Stack':<{stack_w}} {'Input':<{input_w}} Action"
        print(header)
        print("-" * len(header))

        # Rows
        for s in self.trace:
            print(f"{s.step_num:<{step_w}} {s.stack:<{stack_w}} {s.input_str:<{input_w}} {s.action}")


# =============================================================================
# Standalone testing
# =============================================================================

if __name__ == "__main__":
    test_queries = [
        "SELECT * FROM employees;",
        "SELECT name FROM employees;",
        "SELECT name, salary FROM employees;",
        "SELECT name FROM employees WHERE salary > 50000;",
        "SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;",
        "SELECT id FROM employees WHERE age >= 25 AND salary <= 80000;",
    ]

    error_queries = [
        "FROM employees;",                    # Missing SELECT
        "SELECT FROM employees;",             # Missing column list
        "SELECT name employees;",             # Missing FROM
        "SELECT name FROM employees WHERE;",  # Incomplete WHERE
    ]

    print("=" * 70)
    print("  LL(1) PARSER TEST - Valid Queries")
    print("=" * 70)

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Input: {query}")
        print("-" * 70)
        try:
            lexer = Lexer(query)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            tree = parser.parse()
            print("Result: ACCEPTED")
            print("\nParsing Trace:")
            parser.print_trace()
            print("\nParse Tree:")
            tree.print_tree()
        except (LexerError, ParserError) as e:
            print(f"ERROR: {e}")

    print(f"\n\n{'='*70}")
    print("  LL(1) PARSER TEST - Syntax Errors")
    print("=" * 70)

    for query in error_queries:
        print(f"\n{'='*70}")
        print(f"Input: {query}")
        print("-" * 70)
        try:
            lexer = Lexer(query)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            tree = parser.parse()
            print("Result: ACCEPTED (unexpected)")
        except LexerError as e:
            print(f"LEXER ERROR: {e}")
        except ParserError as e:
            print(f"SYNTAX ERROR: {e}")
