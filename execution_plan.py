"""
execution_plan.py - Execution Plan Generator for the SQL Subset Compiler

This module converts the optimized AST into a readable execution plan.
The execution plan describes the physical operations the database engine
would perform, in order, to produce the query result.

Execution plan operators (in typical execution order):
  1. Table Scan  — read all rows from the table
  2. Filter      — apply WHERE conditions to eliminate rows
  3. Sort        — apply ORDER BY sorting
  4. Projection  — select only the requested columns

The plan is generated from the optimized AST, NOT from the original SQL text.
"""

from ast_nodes import (
    QueryNode, ColumnNode, StarNode,
    ConditionNode, LogicalOpNode, LiteralNode
)


# =============================================================================
# Plan Node
# =============================================================================

class PlanNode:
    """
    A single step in the execution plan.

    Attributes:
        operation (str): The operation type (e.g., 'Table Scan', 'Filter').
        details   (str): Human-readable details of the operation.
        children  (list[PlanNode]): Input nodes (for tree-shaped plans).
    """

    def __init__(self, operation, details=""):
        self.operation = operation
        self.details = details
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def to_dict(self):
        result = {"operation": self.operation, "details": self.details}
        if self.children:
            result["input"] = [c.to_dict() for c in self.children]
        return result

    def __repr__(self):
        return f"{self.operation}: {self.details}"


# =============================================================================
# Execution Plan Generator
# =============================================================================

class ExecutionPlanGenerator:
    """
    Generates an execution plan from the optimized AST.

    The plan is a linear sequence of operations (for our single-table subset).
    In a more complex system with JOINs, this would be a tree.

    Usage:
        planner = ExecutionPlanGenerator()
        plan = planner.generate(optimized_ast)
    """

    def generate(self, ast):
        """
        Generate an execution plan from the AST.

        Args:
            ast (QueryNode): The (optimized) AST.

        Returns:
            list[PlanNode]: Ordered list of execution steps.
        """
        plan = []

        # Step 1: Table Scan — always needed
        table_name = ast.table.table_name
        plan.append(PlanNode("Table Scan", table_name))

        # Step 2: Filter — if WHERE clause exists
        if ast.where:
            filter_desc = self._format_condition(ast.where.condition)
            plan.append(PlanNode("Filter", filter_desc))

        # Step 3: Sort — if ORDER BY exists
        if ast.order_by:
            sort_desc = f"{ast.order_by.column} {ast.order_by.direction}"
            plan.append(PlanNode("Sort", sort_desc))

        # Step 4: Projection — select specific columns
        col_names = []
        for col in ast.columns:
            if isinstance(col, StarNode):
                col_names.append("*")
            elif isinstance(col, ColumnNode):
                col_names.append(col.name)
        plan.append(PlanNode("Projection", ", ".join(col_names)))

        return plan

    def _format_condition(self, condition):
        """Format a condition tree as a readable string."""
        if isinstance(condition, ConditionNode):
            value_str = self._format_value(condition.value)
            return f"{condition.column} {condition.operator} {value_str}"

        elif isinstance(condition, LogicalOpNode):
            left = self._format_condition(condition.left)
            right = self._format_condition(condition.right)
            return f"({left} {condition.operator} {right})"

        return str(condition)

    def _format_value(self, value):
        """Format a literal value for display."""
        if value.lit_type == "STRING":
            return f"'{value.value}'"
        return str(value.value)


# =============================================================================
# Plan Printer
# =============================================================================

def print_execution_plan(plan):
    """
    Print an execution plan as a vertical flow diagram.

    Args:
        plan (list[PlanNode]): The execution plan steps.
    """
    for i, step in enumerate(plan):
        print(f"  {step.operation}: {step.details}")
        if i < len(plan) - 1:
            print("    |")
            print("    v")


# =============================================================================
# Standalone testing
# =============================================================================

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser
    from ast_builder import ASTBuilder
    from semantic import SchemaLoader
    from optimizer import QueryOptimizer

    DB_PATH = "sample.db"
    schema = SchemaLoader(DB_PATH)
    optimizer = QueryOptimizer(schema)
    builder = ASTBuilder()
    planner = ExecutionPlanGenerator()

    test_queries = [
        "SELECT * FROM employees;",
        "SELECT name FROM employees WHERE salary > 50000;",
        "SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;",
        "SELECT id FROM employees WHERE age >= 25 AND salary <= 80000;",
    ]

    print("=" * 60)
    print("  EXECUTION PLAN TEST")
    print("=" * 60)

    for query in test_queries:
        print(f"\nInput: {query}")
        print("-" * 60)

        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        tree = parser.parse()
        ast = builder.build(tree)
        opt_result = optimizer.optimize(ast)
        plan = planner.generate(opt_result.optimized_ast)

        print("\nExecution Plan:")
        print_execution_plan(plan)
