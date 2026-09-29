"""
semantic.py - Semantic Analyzer for the SQL Subset Compiler

This module validates the AST against the actual database schema.
While the parser only checks syntax (grammar conformance), the semantic
analyzer checks meaning:

  1. Does the referenced table exist?
  2. Do all referenced columns exist in that table?
  3. Are comparison operators used with compatible types?
  4. Is the ORDER BY column valid?
  5. Are there duplicate columns in SELECT?
  6. Does SELECT * combined with WHERE/ORDER BY reference valid columns?

The semantic analyzer produces a list of semantic errors (if any),
each clearly labeled as a semantic error (not a syntax error).
"""

import sqlite3
from ast_nodes import (
    QueryNode, ColumnNode, StarNode, FromNode,
    WhereNode, ConditionNode, LogicalOpNode,
    OrderByNode, LiteralNode
)


# =============================================================================
# Semantic Error
# =============================================================================

class SemanticError:
    """
    Represents a single semantic error found during analysis.

    Attributes:
        message (str): Description of the error.
        category (str): Error category (e.g., 'TABLE', 'COLUMN', 'TYPE').
    """

    def __init__(self, message, category="GENERAL"):
        self.message = message
        self.category = category

    def __repr__(self):
        return f"Semantic Error [{self.category}]: {self.message}"


# =============================================================================
# Schema Loader
# =============================================================================

class SchemaLoader:
    """
    Loads table and column metadata from the SQLite database.
    This provides the 'symbol table' for semantic analysis.
    """

    def __init__(self, db_path):
        """
        Load schema from the SQLite database.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self.tables = {}  # table_name -> [column_name, ...]
        self.column_types = {}  # (table_name, column_name) -> type_string
        self._load_schema()

    def _load_schema(self):
        """Query SQLite's PRAGMA to get table and column information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = [row[0] for row in cursor.fetchall()]

        for table_name in table_names:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            col_names = []
            for col in columns:
                col_name = col[1]
                col_type = col[2].upper()
                col_names.append(col_name)
                self.column_types[(table_name.lower(), col_name.lower())] = col_type

            self.tables[table_name.lower()] = [c.lower() for c in col_names]

        conn.close()

    def table_exists(self, table_name):
        """Check if a table exists (case-insensitive)."""
        return table_name.lower() in self.tables

    def get_columns(self, table_name):
        """Get the list of column names for a table (lowercase)."""
        return self.tables.get(table_name.lower(), [])

    def column_exists(self, table_name, column_name):
        """Check if a column exists in a table (case-insensitive)."""
        columns = self.get_columns(table_name)
        return column_name.lower() in columns

    def get_column_type(self, table_name, column_name):
        """Get the SQLite type of a column (e.g., 'INTEGER', 'TEXT', 'REAL')."""
        return self.column_types.get(
            (table_name.lower(), column_name.lower()), "UNKNOWN"
        )


# =============================================================================
# Semantic Analyzer
# =============================================================================

class SemanticAnalyzer:
    """
    Validates an AST against the database schema.

    Usage:
        schema = SchemaLoader("sample.db")
        analyzer = SemanticAnalyzer(schema)
        errors = analyzer.analyze(ast)
        if errors:
            for e in errors:
                print(e)
    """

    def __init__(self, schema):
        """
        Initialize with a loaded schema.

        Args:
            schema (SchemaLoader): The database schema information.
        """
        self.schema = schema
        self.errors = []

    def analyze(self, ast):
        """
        Perform semantic analysis on the AST.

        Args:
            ast (QueryNode): The AST root.

        Returns:
            list[SemanticError]: List of semantic errors found (empty if valid).
        """
        self.errors = []

        if not isinstance(ast, QueryNode):
            self.errors.append(SemanticError("Expected a QueryNode", "INTERNAL"))
            return self.errors

        # Step 1: Validate the table
        table_name = ast.table.table_name
        if not self.schema.table_exists(table_name):
            self.errors.append(SemanticError(
                f"Unknown table '{table_name}'", "TABLE"
            ))
            # Cannot continue validation without a valid table
            return self.errors

        # Get valid columns for this table
        valid_columns = self.schema.get_columns(table_name)

        # Step 2: Validate SELECT columns
        self._validate_select(ast.columns, table_name, valid_columns)

        # Step 3: Validate WHERE clause
        if ast.where:
            self._validate_where(ast.where, table_name, valid_columns)

        # Step 4: Validate ORDER BY clause
        if ast.order_by:
            self._validate_order_by(ast.order_by, table_name, valid_columns)

        return self.errors

    # -------------------------------------------------------------------------
    # SELECT validation
    # -------------------------------------------------------------------------

    def _validate_select(self, columns, table_name, valid_columns):
        """Validate the columns in the SELECT clause."""
        # If SELECT *, nothing to validate for column existence
        if len(columns) == 1 and isinstance(columns[0], StarNode):
            return

        seen = set()
        for col in columns:
            if isinstance(col, ColumnNode):
                col_lower = col.name.lower()

                # Check column exists
                if col_lower not in valid_columns:
                    self.errors.append(SemanticError(
                        f"Unknown column '{col.name}' in SELECT "
                        f"(table '{table_name}' has columns: {', '.join(valid_columns)})",
                        "COLUMN"
                    ))

                # Check for duplicates
                if col_lower in seen:
                    self.errors.append(SemanticError(
                        f"Duplicate column '{col.name}' in SELECT",
                        "COLUMN"
                    ))
                seen.add(col_lower)

    # -------------------------------------------------------------------------
    # WHERE validation
    # -------------------------------------------------------------------------

    def _validate_where(self, where_node, table_name, valid_columns):
        """Validate the WHERE clause condition tree."""
        self._validate_condition(where_node.condition, table_name, valid_columns)

    def _validate_condition(self, condition, table_name, valid_columns):
        """Recursively validate a condition node (simple or logical)."""
        if isinstance(condition, ConditionNode):
            self._validate_simple_condition(condition, table_name, valid_columns)

        elif isinstance(condition, LogicalOpNode):
            self._validate_condition(condition.left, table_name, valid_columns)
            self._validate_condition(condition.right, table_name, valid_columns)

    def _validate_simple_condition(self, condition, table_name, valid_columns):
        """Validate a single comparison condition."""
        col_lower = condition.column.lower()

        # Check column exists
        if col_lower not in valid_columns:
            self.errors.append(SemanticError(
                f"Unknown column '{condition.column}' in WHERE clause "
                f"(table '{table_name}' has columns: {', '.join(valid_columns)})",
                "COLUMN"
            ))
            return  # Skip type checking if column doesn't exist

        # Type compatibility check
        col_type = self.schema.get_column_type(table_name, condition.column)
        value = condition.value

        # Check operator-value compatibility
        if value.lit_type == "STRING":
            # String values should be used with = or != operators only
            if condition.operator in ('>', '<', '>=', '<='):
                self.errors.append(SemanticError(
                    f"Operator '{condition.operator}' used with string value "
                    f"'{value.value}' on column '{condition.column}' — "
                    f"comparison operators >, <, >=, <= are typically used with numeric types",
                    "TYPE"
                ))

            # String value compared against numeric column
            if col_type in ("INTEGER", "REAL", "NUMERIC"):
                self.errors.append(SemanticError(
                    f"Type mismatch: column '{condition.column}' is {col_type} "
                    f"but compared with string value '{value.value}'",
                    "TYPE"
                ))

        elif value.lit_type in ("INTEGER", "DECIMAL"):
            # Numeric value compared against text column
            if col_type in ("TEXT", "VARCHAR"):
                self.errors.append(SemanticError(
                    f"Type mismatch: column '{condition.column}' is {col_type} "
                    f"but compared with numeric value {value.value}",
                    "TYPE"
                ))

    # -------------------------------------------------------------------------
    # ORDER BY validation
    # -------------------------------------------------------------------------

    def _validate_order_by(self, order_by, table_name, valid_columns):
        """Validate the ORDER BY clause."""
        col_lower = order_by.column.lower()

        if col_lower not in valid_columns:
            self.errors.append(SemanticError(
                f"Unknown column '{order_by.column}' in ORDER BY "
                f"(table '{table_name}' has columns: {', '.join(valid_columns)})",
                "COLUMN"
            ))


# =============================================================================
# Standalone testing
# =============================================================================

if __name__ == "__main__":
    import os
    from lexer import Lexer
    from parser import Parser
    from ast_builder import ASTBuilder

    # Create the sample database for testing
    DB_PATH = "sample.db"

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            department TEXT,
            salary REAL
        );
    """)

    cursor.executemany(
        "INSERT INTO employees (id, name, age, department, salary) VALUES (?, ?, ?, ?, ?);",
        [
            (1, "Alice",   30, "Engineering", 75000.00),
            (2, "Bob",     25, "Marketing",   55000.00),
            (3, "Charlie", 35, "Engineering", 90000.00),
            (4, "Diana",   28, "HR",          60000.00),
            (5, "Eve",     32, "Marketing",   65000.00),
            (6, "Frank",   40, "Engineering", 95000.00),
            (7, "Grace",   27, "HR",          58000.00),
            (8, "Hank",    33, "Marketing",   70000.00),
        ]
    )

    conn.commit()
    conn.close()

    # Load schema
    schema = SchemaLoader(DB_PATH)
    analyzer = SemanticAnalyzer(schema)
    builder = ASTBuilder()

    print("=" * 60)
    print("  SEMANTIC ANALYSIS TEST")
    print("=" * 60)

    # Valid queries
    valid_queries = [
        "SELECT * FROM employees;",
        "SELECT name, salary FROM employees;",
        "SELECT name FROM employees WHERE salary > 50000;",
        "SELECT name FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;",
    ]

    print("\n--- Valid Queries ---")
    for query in valid_queries:
        print(f"\nInput: {query}")
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        tree = parser.parse()
        ast = builder.build(tree)
        errors = analyzer.analyze(ast)
        if errors:
            for e in errors:
                print(f"  {e}")
        else:
            print("  Syntax: valid | Semantics: valid")

    # Semantic error queries
    error_queries = [
        ("SELECT xyz FROM employees;", "Unknown column in SELECT"),
        ("SELECT name FROM nonexistent;", "Unknown table"),
        ("SELECT name FROM employees WHERE xyz > 10;", "Unknown column in WHERE"),
        ("SELECT name FROM employees ORDER BY xyz;", "Unknown column in ORDER BY"),
        ("SELECT name FROM employees WHERE name > 100;", "Type mismatch: numeric vs text column"),
        ("SELECT name FROM employees WHERE salary = 'hello';", "Type mismatch: string vs numeric column"),
        ("SELECT name, name FROM employees;", "Duplicate column"),
    ]

    print("\n--- Semantic Error Queries ---")
    for query, description in error_queries:
        print(f"\nInput: {query}")
        print(f"Testing: {description}")
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        tree = parser.parse()
        ast = builder.build(tree)
        errors = analyzer.analyze(ast)
        if errors:
            for e in errors:
                print(f"  {e}")
        else:
            print("  No errors found (unexpected)")
