"""
test_suite.py - Comprehensive Test Suite for the SQL Subset Compiler

This module runs all test cases specified in the project requirements:
  - 5+ valid queries
  - 2+ lexical-error queries
  - 3+ syntax-error queries
  - 3+ semantic-error queries
  - Queries demonstrating optimization

For each test case:
  - Input query
  - Expected phase (where it should succeed or fail)
  - Expected result description
  - Actual result (from running the compiler)
  - PASS/FAIL status
"""

import os
import sys

# Ensure database exists
from compiler import compile_query, setup_database

setup_database()


# =============================================================================
# Test Case Definition
# =============================================================================

class TestCase:
    """
    A single test case.

    Attributes:
        name        (str): Test case name.
        sql         (str): Input SQL query.
        category    (str): 'VALID', 'LEXICAL_ERROR', 'SYNTAX_ERROR',
                           'SEMANTIC_ERROR', 'OPTIMIZATION'.
        expected    (str): Description of expected behavior.
        check_fn    (callable): Function that validates the CompilationResult.
    """

    def __init__(self, name, sql, category, expected, check_fn):
        self.name = name
        self.sql = sql
        self.category = category
        self.expected = expected
        self.check_fn = check_fn
        self.passed = None
        self.actual = ""

    def run(self):
        """Run the test and check the result."""
        result = compile_query(self.sql)
        try:
            self.passed, self.actual = self.check_fn(result)
        except Exception as e:
            self.passed = False
            self.actual = f"Exception: {e}"
        return self.passed


# =============================================================================
# Check Functions
# =============================================================================

def check_valid(expected_rows=None, expected_cols=None):
    """Check that query compiles and executes successfully."""
    def check(result):
        if not result.success:
            return False, f"Failed at {result.error_phase}: {result.error_message}"
        msg = f"Success: {result.result_row_count} rows returned"
        if expected_rows is not None and result.result_row_count != expected_rows:
            return False, f"Expected {expected_rows} rows, got {result.result_row_count}"
        if expected_cols is not None:
            if result.result_columns != expected_cols:
                return False, f"Expected columns {expected_cols}, got {result.result_columns}"
        return True, msg
    return check


def check_lexical_error(expected_substring=None):
    """Check that a lexical error is reported."""
    def check(result):
        if result.error_type != "LEXICAL":
            if result.success:
                return False, "Expected lexical error but query succeeded"
            return False, f"Expected LEXICAL error but got {result.error_type}: {result.error_message}"
        msg = f"Lexical error caught: {result.error_message}"
        if expected_substring and expected_substring not in result.error_message:
            return False, f"Error message doesn't contain '{expected_substring}': {result.error_message}"
        return True, msg
    return check


def check_syntax_error(expected_substring=None):
    """Check that a syntax error is reported."""
    def check(result):
        if result.error_type != "SYNTAX":
            if result.success:
                return False, "Expected syntax error but query succeeded"
            return False, f"Expected SYNTAX error but got {result.error_type}: {result.error_message}"
        msg = f"Syntax error caught: {result.error_message}"
        if expected_substring and expected_substring not in result.error_message:
            return False, f"Error message doesn't contain '{expected_substring}': {result.error_message}"
        return True, msg
    return check


def check_semantic_error(expected_category=None, expected_substring=None):
    """Check that a semantic error is reported."""
    def check(result):
        if result.error_type != "SEMANTIC":
            if result.success:
                return False, "Expected semantic error but query succeeded"
            return False, f"Expected SEMANTIC error but got {result.error_type}: {result.error_message}"
        msg = f"Semantic error caught: {result.error_message}"
        if expected_category:
            categories = [e.category for e in result.semantic_errors]
            if expected_category not in categories:
                return False, f"Expected category {expected_category}, got {categories}"
        if expected_substring and expected_substring not in result.error_message:
            return False, f"Error message doesn't contain '{expected_substring}': {result.error_message}"
        return True, msg
    return check


def check_optimization(expected_count=None, expected_substring=None):
    """Check that optimization rules are applied."""
    def check(result):
        if not result.success:
            return False, f"Failed at {result.error_phase}: {result.error_message}"
        rules = result.optimization.rules_applied if result.optimization else []
        if expected_count is not None and len(rules) != expected_count:
            return False, f"Expected {expected_count} optimizations, got {len(rules)}: {rules}"
        msg = f"Optimizations: {rules}" if rules else "No optimizations applied"
        if expected_substring:
            all_rules = " ".join(rules)
            if expected_substring not in all_rules:
                return False, f"Expected '{expected_substring}' in optimizations: {rules}"
        return True, msg
    return check


# =============================================================================
# Test Cases
# =============================================================================

ALL_TESTS = [
    # =========================================================================
    # VALID QUERIES (5+)
    # =========================================================================
    TestCase(
        "V1: SELECT * FROM table",
        "SELECT * FROM employees;",
        "VALID",
        "Returns all 8 employees with all columns",
        check_valid(expected_rows=8)
    ),
    TestCase(
        "V2: SELECT single column",
        "SELECT name FROM employees;",
        "VALID",
        "Returns 8 names",
        check_valid(expected_rows=8, expected_cols=["name"])
    ),
    TestCase(
        "V3: SELECT multiple columns",
        "SELECT name, salary FROM employees;",
        "VALID",
        "Returns 8 rows with name and salary",
        check_valid(expected_rows=8, expected_cols=["name", "salary"])
    ),
    TestCase(
        "V4: SELECT with WHERE",
        "SELECT name FROM employees WHERE salary > 50000;",
        "VALID",
        "Returns employees with salary > 50000",
        check_valid()
    ),
    TestCase(
        "V5: SELECT with WHERE and ORDER BY",
        "SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;",
        "VALID",
        "Returns 3 engineering employees sorted by salary descending",
        check_valid(expected_rows=3, expected_cols=["name", "salary"])
    ),
    TestCase(
        "V6: SELECT with AND condition",
        "SELECT name, age FROM employees WHERE age >= 30 AND department = 'Marketing';",
        "VALID",
        "Returns marketing employees aged 30+",
        check_valid(expected_rows=2)
    ),
    TestCase(
        "V7: SELECT with OR condition",
        "SELECT name FROM employees WHERE department = 'HR' OR department = 'Engineering';",
        "VALID",
        "Returns HR and Engineering employees",
        check_valid(expected_rows=5)
    ),
    TestCase(
        "V8: SELECT with string comparison",
        "SELECT name, department FROM employees WHERE department = 'HR';",
        "VALID",
        "Returns HR employees only",
        check_valid(expected_rows=2)
    ),

    # =========================================================================
    # LEXICAL ERRORS (2+)
    # =========================================================================
    TestCase(
        "L1: Invalid character @",
        "SELECT name FROM employees WHERE salary @ 100;",
        "LEXICAL_ERROR",
        "Lexer should reject '@' as an invalid character",
        check_lexical_error("Unexpected character '@'")
    ),
    TestCase(
        "L2: Unterminated string literal",
        "SELECT name FROM employees WHERE name = 'hello;",
        "LEXICAL_ERROR",
        "Lexer should detect unterminated string",
        check_lexical_error("Unterminated string")
    ),
    TestCase(
        "L3: Lone exclamation mark",
        "SELECT name FROM employees WHERE age ! 25;",
        "LEXICAL_ERROR",
        "Lexer should reject '!' without '='",
        check_lexical_error("did you mean '!='")
    ),

    # =========================================================================
    # SYNTAX ERRORS (3+)
    # =========================================================================
    TestCase(
        "S1: Missing SELECT keyword",
        "FROM employees;",
        "SYNTAX_ERROR",
        "Parser expects SELECT at the start",
        check_syntax_error("Expected one of: SELECT")
    ),
    TestCase(
        "S2: Missing column list after SELECT",
        "SELECT FROM employees;",
        "SYNTAX_ERROR",
        "Parser expects * or column name after SELECT",
        check_syntax_error("Unexpected 'FROM'")
    ),
    TestCase(
        "S3: Missing FROM keyword",
        "SELECT name employees;",
        "SYNTAX_ERROR",
        "Parser expects FROM or COMMA after column name",
        check_syntax_error()
    ),
    TestCase(
        "S4: Incomplete WHERE clause",
        "SELECT name FROM employees WHERE;",
        "SYNTAX_ERROR",
        "Parser expects a condition after WHERE",
        check_syntax_error()
    ),
    TestCase(
        "S5: Missing semicolon",
        "SELECT name FROM employees",
        "SYNTAX_ERROR",
        "Parser expects semicolon at end",
        check_syntax_error()
    ),

    # =========================================================================
    # SEMANTIC ERRORS (3+)
    # =========================================================================
    TestCase(
        "SE1: Unknown column in SELECT",
        "SELECT xyz FROM employees;",
        "SEMANTIC_ERROR",
        "Column 'xyz' does not exist in employees table",
        check_semantic_error("COLUMN", "Unknown column 'xyz'")
    ),
    TestCase(
        "SE2: Unknown table",
        "SELECT name FROM nonexistent;",
        "SEMANTIC_ERROR",
        "Table 'nonexistent' does not exist",
        check_semantic_error("TABLE", "Unknown table 'nonexistent'")
    ),
    TestCase(
        "SE3: Unknown column in WHERE",
        "SELECT name FROM employees WHERE xyz > 10;",
        "SEMANTIC_ERROR",
        "Column 'xyz' does not exist in WHERE clause",
        check_semantic_error("COLUMN", "Unknown column 'xyz'")
    ),
    TestCase(
        "SE4: Type mismatch - string vs numeric column",
        "SELECT name FROM employees WHERE salary = 'hello';",
        "SEMANTIC_ERROR",
        "Cannot compare REAL column 'salary' with string value",
        check_semantic_error("TYPE", "Type mismatch")
    ),
    TestCase(
        "SE5: Unknown column in ORDER BY",
        "SELECT name FROM employees ORDER BY xyz;",
        "SEMANTIC_ERROR",
        "Column 'xyz' does not exist for ORDER BY",
        check_semantic_error("COLUMN", "Unknown column 'xyz'")
    ),

    # =========================================================================
    # OPTIMIZATION QUERIES
    # =========================================================================
    TestCase(
        "O1: SELECT * expansion",
        "SELECT * FROM employees;",
        "OPTIMIZATION",
        "SELECT * should be expanded to explicit column list",
        check_optimization(expected_count=1, expected_substring="Expanded SELECT *")
    ),
    TestCase(
        "O2: Predicate pushdown + projection pruning",
        "SELECT name FROM employees WHERE salary > 50000;",
        "OPTIMIZATION",
        "WHERE uses column not in SELECT, triggering projection pruning and predicate pushdown",
        check_optimization(expected_count=2, expected_substring="Projection pruning")
    ),
    TestCase(
        "O3: No optimization needed",
        "SELECT name, salary FROM employees;",
        "OPTIMIZATION",
        "Simple query with no WHERE or * — no optimizations applicable",
        check_optimization(expected_count=0)
    ),
    TestCase(
        "O4: SELECT * with WHERE",
        "SELECT * FROM employees WHERE age > 30;",
        "OPTIMIZATION",
        "SELECT * expanded + predicate pushdown",
        check_optimization(expected_substring="Expanded SELECT *")
    ),
]


# =============================================================================
# Test Runner
# =============================================================================

def run_all_tests():
    """Run all test cases and print a formatted report."""
    print("=" * 80)
    print("  SQL SUBSET COMPILER — COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    categories = {}
    for test in ALL_TESTS:
        if test.category not in categories:
            categories[test.category] = []
        categories[test.category].append(test)

    total = 0
    passed = 0
    failed = 0

    for cat_name, tests in categories.items():
        print(f"\n{'='*80}")
        print(f"  {cat_name}")
        print(f"{'='*80}")

        for test in tests:
            total += 1
            result = test.run()

            if result:
                passed += 1
                status = "PASS"
                symbol = "[+]"
            else:
                failed += 1
                status = "FAIL"
                symbol = "[X]"

            print(f"\n  {symbol} {test.name}")
            print(f"      Input:    {test.sql}")
            print(f"      Expected: {test.expected}")
            print(f"      Actual:   {test.actual}")
            print(f"      Status:   {status}")

    # Summary
    print(f"\n{'='*80}")
    print(f"  TEST SUMMARY")
    print(f"{'='*80}")
    print(f"  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Rate:   {passed/total*100:.1f}%")
    print(f"{'='*80}")

    return failed == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    success = run_all_tests()
    sys.exit(0 if success else 1)
