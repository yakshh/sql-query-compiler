"""
ast_builder.py - Parse Tree to AST Converter

This module walks the parse tree produced by the LL(1) parser and constructs
a clean Abstract Syntax Tree (AST) using the node classes from ast_nodes.py.

The parse tree contains every grammar symbol (keywords, commas, etc.).
The AST discards syntactic noise and keeps only the meaningful structure:
  - Which columns are selected
  - Which table is queried
  - What conditions filter rows
  - What ordering is applied

This separation is a key compiler-design concept: the parse tree validates
syntax, while the AST captures semantics.
"""

import grammar as g
from ast_nodes import (
    QueryNode, ColumnNode, StarNode, FromNode,
    WhereNode, ConditionNode, LogicalOpNode,
    OrderByNode, LiteralNode
)


class ASTBuildError(Exception):
    """Raised when the AST builder encounters an unexpected parse tree structure."""
    pass


class ASTBuilder:
    """
    Converts a parse tree (from the LL(1) parser) into an AST.

    Usage:
        builder = ASTBuilder()
        ast = builder.build(parse_tree_root)
    """

    def build(self, parse_tree_root):
        """
        Build an AST from the parse tree root node.

        Args:
            parse_tree_root (ParseNode): Root of the parse tree (symbol='Query').

        Returns:
            QueryNode: The root of the AST.
        """
        if parse_tree_root.symbol != g.NT_QUERY:
            raise ASTBuildError(f"Expected Query node, got {parse_tree_root.symbol}")
        return self._build_query(parse_tree_root)

    # -------------------------------------------------------------------------
    # Query → SELECT SelectList FROM IDENTIFIER OptWhere OptOrderBy SEMICOLON
    # -------------------------------------------------------------------------

    def _build_query(self, node):
        """Build a QueryNode from the Query parse tree node."""
        query = QueryNode()

        # Children of Query: SELECT, SelectList, FROM, IDENTIFIER, OptWhere, OptOrderBy, SEMICOLON
        children = node.children

        # SelectList is at index 1
        select_list_node = children[1]
        query.columns = self._build_select_list(select_list_node)

        # Table name is the IDENTIFIER at index 3
        table_token = children[3].token
        query.table = FromNode(table_token.value)

        # OptWhere is at index 4
        opt_where_node = children[4]
        query.where = self._build_opt_where(opt_where_node)

        # OptOrderBy is at index 5
        opt_order_node = children[5]
        query.order_by = self._build_opt_order_by(opt_order_node)

        return query

    # -------------------------------------------------------------------------
    # SelectList → STAR | ColumnList
    # -------------------------------------------------------------------------

    def _build_select_list(self, node):
        """Build the column list from SelectList."""
        if not node.children:
            raise ASTBuildError("SelectList has no children")

        first_child = node.children[0]

        # SelectList → STAR
        if first_child.symbol == g.STAR:
            return [StarNode()]

        # SelectList → ColumnList
        if first_child.symbol == g.NT_COLUMN_LIST:
            return self._build_column_list(first_child)

        raise ASTBuildError(f"Unexpected SelectList child: {first_child.symbol}")

    # -------------------------------------------------------------------------
    # ColumnList → IDENTIFIER ColumnTail
    # ColumnTail → COMMA IDENTIFIER ColumnTail | ε
    # -------------------------------------------------------------------------

    def _build_column_list(self, node):
        """Build a list of ColumnNode from ColumnList."""
        columns = []

        # First child is IDENTIFIER
        id_token = node.children[0].token
        columns.append(ColumnNode(id_token.value))

        # Second child is ColumnTail
        if len(node.children) > 1:
            self._build_column_tail(node.children[1], columns)

        return columns

    def _build_column_tail(self, node, columns):
        """Recursively extract columns from ColumnTail."""
        # ColumnTail → ε (no children — done)
        if not node.children:
            return

        # ColumnTail → COMMA IDENTIFIER ColumnTail
        # children[0] = COMMA, children[1] = IDENTIFIER, children[2] = ColumnTail
        if len(node.children) >= 2:
            id_token = node.children[1].token
            columns.append(ColumnNode(id_token.value))

            # Recurse into the next ColumnTail
            if len(node.children) >= 3:
                self._build_column_tail(node.children[2], columns)

    # -------------------------------------------------------------------------
    # OptWhere → WHERE Condition | ε
    # -------------------------------------------------------------------------

    def _build_opt_where(self, node):
        """Build WhereNode from OptWhere, or return None if ε."""
        # OptWhere → ε (no children)
        if not node.children:
            return None

        # OptWhere → WHERE Condition
        # children[0] = WHERE, children[1] = Condition
        condition_node = node.children[1]
        condition = self._build_condition(condition_node)
        return WhereNode(condition)

    # -------------------------------------------------------------------------
    # Condition → AndExpr OrTail
    # OrTail    → OR AndExpr OrTail | ε
    # AndExpr   → Predicate AndTail
    # AndTail   → AND Predicate AndTail | ε
    # Predicate → IDENTIFIER CompOp Value
    # -------------------------------------------------------------------------

    def _build_condition(self, node):
        """Build the condition tree from Condition node."""
        # Condition → AndExpr OrTail
        and_expr_node = node.children[0]
        or_tail_node = node.children[1]

        left = self._build_and_expr(and_expr_node)
        return self._build_or_tail(or_tail_node, left)

    def _build_or_tail(self, node, left):
        """Build OR chain from OrTail. Returns the accumulated condition tree."""
        # OrTail → ε
        if not node.children:
            return left

        # OrTail → OR AndExpr OrTail
        and_expr_node = node.children[1]
        or_tail_node = node.children[2]

        right = self._build_and_expr(and_expr_node)
        combined = LogicalOpNode("OR", left, right)
        return self._build_or_tail(or_tail_node, combined)

    def _build_and_expr(self, node):
        """Build AND expression from AndExpr node."""
        # AndExpr → Predicate AndTail
        pred_node = node.children[0]
        and_tail_node = node.children[1]

        left = self._build_predicate(pred_node)
        return self._build_and_tail(and_tail_node, left)

    def _build_and_tail(self, node, left):
        """Build AND chain from AndTail. Returns the accumulated condition tree."""
        # AndTail → ε
        if not node.children:
            return left

        # AndTail → AND Predicate AndTail
        pred_node = node.children[1]
        and_tail_node = node.children[2]

        right = self._build_predicate(pred_node)
        combined = LogicalOpNode("AND", left, right)
        return self._build_and_tail(and_tail_node, combined)

    def _build_predicate(self, node):
        """Build a ConditionNode from Predicate node."""
        # Predicate → IDENTIFIER CompOp Value
        column_name = node.children[0].token.value
        operator = self._build_comp_op(node.children[1])
        value = self._build_value(node.children[2])

        return ConditionNode(column_name, operator, value)

    # -------------------------------------------------------------------------
    # CompOp → EQ | NEQ | GT | LT | GEQ | LEQ
    # -------------------------------------------------------------------------

    def _build_comp_op(self, node):
        """Extract the operator string from CompOp node."""
        # CompOp has one child — the operator terminal
        op_token = node.children[0].token
        # Map token type back to the operator string
        op_map = {
            g.EQ:  "=",
            g.NEQ: "!=",
            g.GT:  ">",
            g.LT:  "<",
            g.GEQ: ">=",
            g.LEQ: "<=",
        }
        return op_map.get(op_token.type, op_token.value)

    # -------------------------------------------------------------------------
    # Value → NUMBER | STRING
    # -------------------------------------------------------------------------

    def _build_value(self, node):
        """Build a LiteralNode from Value node."""
        # Value has one child — NUMBER or STRING terminal
        val_token = node.children[0].token

        if val_token.type == g.NUMBER:
            # Determine if integer or decimal
            if '.' in val_token.value:
                return LiteralNode(float(val_token.value), "DECIMAL")
            else:
                return LiteralNode(int(val_token.value), "INTEGER")
        elif val_token.type == g.STRING:
            return LiteralNode(val_token.value, "STRING")
        else:
            raise ASTBuildError(f"Unexpected value token type: {val_token.type}")

    # -------------------------------------------------------------------------
    # OptOrderBy → ORDER BY IDENTIFIER OptDirection | ε
    # OptDirection → ASC | DESC | ε
    # -------------------------------------------------------------------------

    def _build_opt_order_by(self, node):
        """Build OrderByNode from OptOrderBy, or return None if ε."""
        # OptOrderBy → ε
        if not node.children:
            return None

        # OptOrderBy → ORDER BY IDENTIFIER OptDirection
        column_name = node.children[2].token.value

        # OptDirection
        direction = self._build_opt_direction(node.children[3])

        return OrderByNode(column_name, direction)

    def _build_opt_direction(self, node):
        """Extract sort direction from OptDirection. Defaults to 'ASC'."""
        # OptDirection → ε (default ASC)
        if not node.children:
            return "ASC"

        # OptDirection → ASC | DESC
        return node.children[0].token.type  # "ASC" or "DESC"


# =============================================================================
# Pretty Printer for AST
# =============================================================================

def print_ast(ast_node, indent=0):
    """
    Print an AST in a readable tree format.

    Args:
        ast_node: Any ASTNode subclass.
        indent:   Current indentation level.
    """
    prefix = "  " * indent

    if isinstance(ast_node, QueryNode):
        print(f"{prefix}Query")
        print(f"{prefix}  SELECT:")
        for col in ast_node.columns:
            print_ast(col, indent + 2)
        print(f"{prefix}  FROM:")
        print_ast(ast_node.table, indent + 2)
        if ast_node.where:
            print(f"{prefix}  WHERE:")
            print_ast(ast_node.where, indent + 2)
        if ast_node.order_by:
            print(f"{prefix}  ORDER BY:")
            print_ast(ast_node.order_by, indent + 2)

    elif isinstance(ast_node, ColumnNode):
        print(f"{prefix}Column: {ast_node.name}")

    elif isinstance(ast_node, StarNode):
        print(f"{prefix}* (all columns)")

    elif isinstance(ast_node, FromNode):
        print(f"{prefix}Table: {ast_node.table_name}")

    elif isinstance(ast_node, WhereNode):
        print_ast(ast_node.condition, indent)

    elif isinstance(ast_node, ConditionNode):
        print(f"{prefix}{ast_node.column} {ast_node.operator} ", end="")
        if ast_node.value.lit_type == "STRING":
            print(f"'{ast_node.value.value}'")
        else:
            print(f"{ast_node.value.value}")

    elif isinstance(ast_node, LogicalOpNode):
        print(f"{prefix}{ast_node.operator}")
        print_ast(ast_node.left, indent + 1)
        print_ast(ast_node.right, indent + 1)

    elif isinstance(ast_node, OrderByNode):
        print(f"{prefix}{ast_node.column} {ast_node.direction}")

    elif isinstance(ast_node, LiteralNode):
        print(f"{prefix}{ast_node.value} ({ast_node.lit_type})")

    else:
        print(f"{prefix}Unknown node: {ast_node}")


# =============================================================================
# Standalone testing
# =============================================================================

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    test_queries = [
        "SELECT * FROM employees;",
        "SELECT name, salary FROM employees;",
        "SELECT name FROM employees WHERE salary > 50000;",
        "SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;",
        "SELECT id FROM employees WHERE age >= 25 AND salary <= 80000;",
        "SELECT name FROM employees WHERE department = 'HR' OR department = 'Engineering';",
    ]

    print("=" * 60)
    print("  AST BUILDER TEST")
    print("=" * 60)

    builder = ASTBuilder()

    for query in test_queries:
        print(f"\nInput: {query}")
        print("-" * 60)

        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        parse_tree = parser.parse()

        ast = builder.build(parse_tree)

        print("AST:")
        print_ast(ast, indent=1)

        print("\nDict representation:")
        import json
        print(json.dumps(ast.to_dict(), indent=2))
