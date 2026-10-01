"""
compiler.py - Unified Compiler Pipeline for the SQL Subset Compiler

This module ties all compiler phases together into a single pipeline.
It is used by the web UI (app.py) and can also be run standalone.

Pipeline: Input SQL → Lexer → Parser → AST → Semantic → Optimizer → Plan → Execute
"""

import os
import sqlite3
from lexer import Lexer, LexerError, Token
from parser import Parser, ParserError
from ast_builder import ASTBuilder, ASTBuildError, print_ast
from ast_nodes import QueryNode
from semantic import SchemaLoader, SemanticAnalyzer, SemanticError
from optimizer import QueryOptimizer
from executor import QueryExecutor, ExecutionError


class PlanStep:
    """One readable operation in the physical plan."""

    def __init__(self, operation, details=""):
        self.operation, self.details = operation, details


class ExecutionPlanGenerator:
    """Build the linear scan/filter/sort/project plan for one-table SQL."""

    def generate(self, ast):
        plan = [PlanStep("Table Scan", ast.table.table_name)]
        if ast.where:
            plan.append(PlanStep("Filter", self._condition(ast.where.condition)))
        if ast.order_by:
            plan.append(PlanStep("Sort", f"{ast.order_by.column} {ast.order_by.direction}"))
        columns = ["*" if getattr(c, "name", None) is None else c.name for c in ast.columns]
        plan.append(PlanStep("Projection", ", ".join(columns)))
        return plan

    def _condition(self, condition):
        if hasattr(condition, "column"):
            value = condition.value
            text = repr(value.value) if value.lit_type == "STRING" else str(value.value)
            return f"{condition.column} {condition.operator} {text}"
        if hasattr(condition, "left"):
            return f"({self._condition(condition.left)} {condition.operator} {self._condition(condition.right)})"
        return str(condition)


# =============================================================================
# Database Setup
# =============================================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.db")


def setup_database():
    """Create the sample employees database if it doesn't exist."""
    if os.path.exists(DB_PATH):
        return  # Already exists

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


# =============================================================================
# Compilation Result
# =============================================================================

class CompilationResult:
    """
    Holds the output from every phase of the compiler pipeline.

    Attributes:
        success         (bool): True if the entire pipeline completed without errors.
        error_phase     (str or None): Phase where an error occurred.
        error_message   (str or None): Error description.
        error_type      (str or None): 'LEXICAL', 'SYNTAX', 'SEMANTIC', 'EXECUTION'.

        tokens          (list[Token]): Output of lexer.
        parse_trace     (list): LL(1) parsing steps.
        parse_tree_str  (str): Text representation of the parse tree.
        ast             (QueryNode): The AST.
        ast_dict        (dict): AST as a dictionary.
        semantic_errors (list): Semantic errors (empty if valid).
        optimization    (OptimizationResult): Optimization details.
        original_plan   (list[PlanStep]): Plan from original AST.
        optimized_plan  (list[PlanStep]): Plan from optimized AST.
        reconstructed_sql (str): SQL reconstructed from AST.
        result_columns  (list[str]): Result column names.
        result_rows     (list[tuple]): Result data rows.
    """

    def __init__(self):
        self.success = False
        self.error_phase = None
        self.error_message = None
        self.error_type = None

        self.tokens = []
        self.tokens_str = ""
        self.parse_trace = []
        self.parse_tree_str = ""
        self.ast = None
        self.ast_dict = None
        self.ast_str = ""
        self.semantic_errors = []
        self.optimization = None
        self.original_plan = []
        self.optimized_plan = []
        self.original_plan_str = ""
        self.optimized_plan_str = ""
        self.reconstructed_sql = ""
        self.result_columns = []
        self.result_rows = []
        self.result_row_count = 0


# =============================================================================
# Compiler Pipeline
# =============================================================================

def compile_query(sql_input):
    """
    Run the full compiler pipeline on the given SQL input.

    Args:
        sql_input (str): The raw SQL query string.

    Returns:
        CompilationResult: Complete results from all phases.
    """
    setup_database()

    result = CompilationResult()

    # -------------------------------------------------------------------------
    # Phase 1: Lexical Analysis
    # -------------------------------------------------------------------------
    try:
        lexer = Lexer(sql_input)
        tokens = lexer.tokenize()
        result.tokens = tokens
        result.tokens_str = " ".join(str(t) for t in tokens)
    except LexerError as e:
        result.error_phase = "Lexical Analysis"
        result.error_type = "LEXICAL"
        result.error_message = str(e)
        return result

    # -------------------------------------------------------------------------
    # Phase 2: Parsing (LL(1) Predictive Parser)
    # -------------------------------------------------------------------------
    try:
        parser = Parser(tokens)
        parse_tree = parser.parse()
        result.parse_trace = parser.get_trace()

        # Capture parse tree as string
        import io, sys
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        parse_tree.print_tree()
        sys.stdout = old_stdout
        result.parse_tree_str = buffer.getvalue()

    except ParserError as e:
        result.error_phase = "Parsing"
        result.error_type = "SYNTAX"
        result.error_message = str(e)
        # Still include tokens and any partial trace
        result.parse_trace = parser.get_trace() if parser else []
        return result

    # -------------------------------------------------------------------------
    # Phase 3: AST Construction
    # -------------------------------------------------------------------------
    try:
        builder = ASTBuilder()
        ast = builder.build(parse_tree)
        result.ast = ast
        result.ast_dict = ast.to_dict()

        # Capture AST as string
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        print_ast(ast)
        sys.stdout = old_stdout
        result.ast_str = buffer.getvalue()

    except ASTBuildError as e:
        result.error_phase = "AST Construction"
        result.error_type = "SYNTAX"
        result.error_message = str(e)
        return result

    # -------------------------------------------------------------------------
    # Phase 4: Semantic Analysis
    # -------------------------------------------------------------------------
    schema = SchemaLoader(DB_PATH)
    analyzer = SemanticAnalyzer(schema)
    sem_errors = analyzer.analyze(ast)

    if sem_errors:
        result.error_phase = "Semantic Analysis"
        result.error_type = "SEMANTIC"
        result.semantic_errors = sem_errors
        result.error_message = "; ".join(str(e) for e in sem_errors)
        return result

    # -------------------------------------------------------------------------
    # Phase 5: Query Optimization
    # -------------------------------------------------------------------------
    optimizer = QueryOptimizer(schema)

    # Generate plan for original AST (before optimization)
    planner = ExecutionPlanGenerator()
    import copy
    original_ast_copy = copy.deepcopy(ast)
    result.original_plan = planner.generate(original_ast_copy)
    result.original_plan_str = _format_plan(result.original_plan)

    # Optimize
    opt_result = optimizer.optimize(ast)
    result.optimization = opt_result

    # -------------------------------------------------------------------------
    # Phase 6: Execution Plan (from optimized AST)
    # -------------------------------------------------------------------------
    result.optimized_plan = planner.generate(opt_result.optimized_ast)
    result.optimized_plan_str = _format_plan(result.optimized_plan)

    # -------------------------------------------------------------------------
    # Phase 7: Execution
    # -------------------------------------------------------------------------
    try:
        executor = QueryExecutor(DB_PATH)
        result.reconstructed_sql = executor.get_reconstructed_sql(opt_result.optimized_ast)
        exec_result = executor.execute(opt_result.optimized_ast)
        result.result_columns = exec_result.columns
        result.result_rows = exec_result.rows
        result.result_row_count = exec_result.row_count
        result.success = True

    except ExecutionError as e:
        result.error_phase = "Execution"
        result.error_type = "EXECUTION"
        result.error_message = str(e)
        return result

    return result


def _format_plan(plan):
    """Format an execution plan as a string."""
    lines = []
    for i, step in enumerate(plan):
        lines.append(f"{step.operation}: {step.details}")
        if i < len(plan) - 1:
            lines.append("  |")
            lines.append("  v")
    return "\n".join(lines)


# =============================================================================
# Standalone testing
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    test = compile_query("SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;")

    if test.success:
        print("Compilation successful!")
        print(f"Tokens: {test.tokens_str}")
        print(f"AST:\n{test.ast_str}")
        print(f"Optimizations: {[r for r in test.optimization.rules_applied]}")
        print(f"Plan:\n{test.optimized_plan_str}")
        print(f"SQL: {test.reconstructed_sql}")
        print(f"Result: {test.result_columns}")
        for row in test.result_rows:
            print(f"  {row}")
    else:
        print(f"Error in {test.error_phase}: {test.error_message}")
