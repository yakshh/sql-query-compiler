"""
ast_nodes.py - Abstract Syntax Tree (AST) Node Classes for the SQL Compiler

This module defines the AST node types that represent the semantic structure
of a parsed SQL query. The AST is a simplified, meaningful representation
of the query — unlike the parse tree, it omits syntactic noise (keywords,
commas, semicolons) and retains only the essential structure.

AST Node Hierarchy:
    QueryNode           — Root node: holds SELECT, FROM, WHERE, ORDER BY
        ColumnNode      — A column reference (e.g., 'name', 'salary')
        StarNode        — SELECT * (all columns)
        FromNode        — FROM clause with table name
        WhereNode       — WHERE clause containing a condition tree
        ConditionNode   — A single comparison (e.g., salary > 50000)
        LogicalOpNode   — AND/OR combining two condition subtrees
        OrderByNode     — ORDER BY clause with column and direction
        LiteralNode     — A literal value (number or string)
"""


class ASTNode:
    """Base class for all AST nodes."""

    def to_dict(self):
        """Convert to a dictionary for serialization/display."""
        raise NotImplementedError

    def __repr__(self):
        return str(self.to_dict())


class QueryNode(ASTNode):
    """
    Root AST node representing a complete SQL query.

    Attributes:
        columns   (list): List of ColumnNode/StarNode for the SELECT clause.
        table     (FromNode): The FROM clause.
        where     (WhereNode or None): The WHERE clause, if present.
        order_by  (OrderByNode or None): The ORDER BY clause, if present.
    """

    def __init__(self):
        self.columns = []       # list of ColumnNode or [StarNode]
        self.table = None       # FromNode
        self.where = None       # WhereNode or None
        self.order_by = None    # OrderByNode or None

    def to_dict(self):
        result = {
            "type": "Query",
            "select": [c.to_dict() for c in self.columns],
            "from": self.table.to_dict() if self.table else None,
        }
        if self.where:
            result["where"] = self.where.to_dict()
        if self.order_by:
            result["order_by"] = self.order_by.to_dict()
        return result


class ColumnNode(ASTNode):
    """
    Represents a column reference in SELECT, WHERE, or ORDER BY.

    Attributes:
        name (str): The column name (e.g., 'name', 'salary').
    """

    def __init__(self, name):
        self.name = name

    def to_dict(self):
        return {"type": "Column", "name": self.name}


class StarNode(ASTNode):
    """Represents SELECT * (all columns)."""

    def to_dict(self):
        return {"type": "Star", "name": "*"}


class FromNode(ASTNode):
    """
    Represents the FROM clause.

    Attributes:
        table_name (str): The table name.
    """

    def __init__(self, table_name):
        self.table_name = table_name

    def to_dict(self):
        return {"type": "From", "table": self.table_name}


class WhereNode(ASTNode):
    """
    Represents the WHERE clause, containing a condition tree.

    Attributes:
        condition: A ConditionNode or LogicalOpNode.
    """

    def __init__(self, condition):
        self.condition = condition

    def to_dict(self):
        return {"type": "Where", "condition": self.condition.to_dict()}


class ConditionNode(ASTNode):
    """
    Represents a single comparison condition (e.g., salary > 50000).

    Attributes:
        column   (str): The column being compared.
        operator (str): The comparison operator ('=', '!=', '>', '<', '>=', '<=').
        value    (LiteralNode): The literal value being compared to.
    """

    def __init__(self, column, operator, value):
        self.column = column
        self.operator = operator
        self.value = value

    def to_dict(self):
        return {
            "type": "Condition",
            "column": self.column,
            "operator": self.operator,
            "value": self.value.to_dict(),
        }


class LogicalOpNode(ASTNode):
    """
    Represents a logical AND/OR operation combining two condition subtrees.

    Attributes:
        operator (str): 'AND' or 'OR'.
        left:  Left operand (ConditionNode or LogicalOpNode).
        right: Right operand (ConditionNode or LogicalOpNode).
    """

    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right

    def to_dict(self):
        return {
            "type": "LogicalOp",
            "operator": self.operator,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


class OrderByNode(ASTNode):
    """
    Represents the ORDER BY clause.

    Attributes:
        column    (str): The column to sort by.
        direction (str): 'ASC' or 'DESC' (default 'ASC').
    """

    def __init__(self, column, direction="ASC"):
        self.column = column
        self.direction = direction

    def to_dict(self):
        return {
            "type": "OrderBy",
            "column": self.column,
            "direction": self.direction,
        }


class LiteralNode(ASTNode):
    """
    Represents a literal value (number or string).

    Attributes:
        value:     The Python value (int, float, or str).
        lit_type:  'INTEGER', 'DECIMAL', or 'STRING'.
    """

    def __init__(self, value, lit_type):
        self.value = value
        self.lit_type = lit_type

    def to_dict(self):
        return {
            "type": "Literal",
            "value": self.value,
            "lit_type": self.lit_type,
        }
