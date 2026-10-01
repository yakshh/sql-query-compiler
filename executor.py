"""
executor.py - Query Executor for the SQL Subset Compiler

This module executes the optimized AST against the SQLite database.
IMPORTANT: It does NOT simply pass the original SQL to SQLite.

Instead, it:
  1. Reads the execution plan (from the optimized AST).
  2. Builds a SQL query from the AST's internal representation.
  3. Executes it against SQLite.
  4. Returns the results with column headers.

This demonstrates that the query was fully processed by our own compiler
pipeline (lexer → parser → AST → semantic → optimizer → plan → execute)
before any database interaction occurs.
"""

import sqlite3
from ast_nodes import (
    QueryNode, ColumnNode, StarNode,
    ConditionNode, LogicalOpNode, LiteralNode
)


# =============================================================================
# Execution Error
# =============================================================================

class ExecutionError(Exception):
    """Raised when query execution against the database fails."""

    def __init__(self, message):
        self.message = message
        super().__init__(f"Execution Error: {message}")


# =============================================================================
# Execution Result
# =============================================================================

class ExecutionResult:
    """
    Holds the result of executing a query.

    Attributes:
        columns (list[str]): Column names in the result.
        rows    (list[tuple]): Data rows.
        row_count (int): Number of rows returned.
    """

    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows
        self.row_count = len(rows)


# =============================================================================
# Query Executor
# =============================================================================

class QueryExecutor:
    """
    Executes the optimized AST against SQLite.

    The executor reconstructs SQL from the AST — it does NOT use the
    original input string. This proves that the compiler pipeline
    actually processed the query.

    Usage:
        executor = QueryExecutor("sample.db")
        result = executor.execute(optimized_ast)
    """

    def __init__(self, db_path):
        self.db_path = db_path

    def execute(self, ast):
        """
        Execute the query represented by the AST.

        Args:
            ast (QueryNode): The optimized AST.

        Returns:
            ExecutionResult: The query results.

        Raises:
            ExecutionError: If execution fails.
        """
        try:
            # Reconstruct SQL from the AST (NOT from original input)
            sql, params = self._ast_to_sql(ast)

            # Execute against SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, params)

            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            conn.close()
            return ExecutionResult(columns, rows)

        except sqlite3.Error as e:
            raise ExecutionError(f"Database error: {e}")
        except Exception as e:
            raise ExecutionError(f"Unexpected error: {e}")

    def _ast_to_sql(self, ast):
        """
        Convert the AST back to a SQL string for SQLite execution.
        This is NOT the original input — it is reconstructed from the
        compiler's internal representation.

        Returns:
            tuple: (sql_string, params_list)
        """
        params = []

        # SELECT clause
        col_strs = []
        for col in ast.columns:
            if isinstance(col, StarNode):
                col_strs.append("*")
            elif isinstance(col, ColumnNode):
                col_strs.append(col.name)
        select_clause = ", ".join(col_strs)

        # FROM clause
        from_clause = ast.table.table_name

        # Start building SQL
        sql = f"SELECT {select_clause} FROM {from_clause}"

        # WHERE clause
        if ast.where:
            where_str, where_params = self._condition_to_sql(ast.where.condition)
            sql += f" WHERE {where_str}"
            params.extend(where_params)

        # ORDER BY clause
        if ast.order_by:
            sql += f" ORDER BY {ast.order_by.column} {ast.order_by.direction}"

        return sql, params

    def _condition_to_sql(self, condition):
        """
        Convert a condition tree to a SQL WHERE clause string.
        Uses parameterized queries (?) for values to prevent SQL injection.

        Returns:
            tuple: (condition_string, params_list)
        """
        if isinstance(condition, ConditionNode):
            params = []
            value = condition.value

            if value.lit_type == "STRING":
                params.append(value.value)
            elif value.lit_type == "DECIMAL":
                params.append(float(value.value))
            else:  # INTEGER
                params.append(int(value.value))

            return f"{condition.column} {condition.operator} ?", params

        elif isinstance(condition, LogicalOpNode):
            left_str, left_params = self._condition_to_sql(condition.left)
            right_str, right_params = self._condition_to_sql(condition.right)

            combined = f"({left_str} {condition.operator} {right_str})"
            return combined, left_params + right_params

        return "", []

    def get_reconstructed_sql(self, ast):
        """
        Return the SQL that would be executed (for display purposes).
        Shows that SQL was reconstructed from the AST, not passed through.
        """
        sql, params = self._ast_to_sql(ast)
        # For display, substitute params back in
        display_sql = sql
        for p in params:
            if isinstance(p, str):
                display_sql = display_sql.replace("?", f"'{p}'", 1)
            else:
                display_sql = display_sql.replace("?", str(p), 1)
        return display_sql


# =============================================================================
# Result Printer
# =============================================================================

def print_result(result):
    """Print query results as a formatted table."""
    if result.row_count == 0:
        print("  (No rows returned)")
        return

    # Calculate column widths
    widths = [len(str(col)) for col in result.columns]
    for row in result.rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))

    # Print header
    header = " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(result.columns))
    separator = "-+-".join("-" * w for w in widths)
    print(f"  {header}")
    print(f"  {separator}")

    # Print rows
    for row in result.rows:
        row_str = " | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))
        print(f"  {row_str}")

    print(f"\n  ({result.row_count} row{'s' if result.row_count != 1 else ''} returned)")

