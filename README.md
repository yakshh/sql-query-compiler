# SQL Compiler — structure and complete execution flow

This folder is a second, flatter implementation of the same Mini-SQL compiler.
It accepts a restricted query such as:

```sql
SELECT name, salary FROM employees
WHERE department = 'Engineering' ORDER BY salary DESC;
```

The query passes through seven phases:

`text -> tokens -> parse tree -> AST -> semantic checks -> optimized AST -> plan -> SQLite result`

## Files and responsibilities

- `app.py` is the Flask web interface. It renders the page and exposes the
  `/compile` endpoint. It does not implement parsing itself; it calls
  `compiler.compile_query()` and serializes the returned `CompilationResult`.
- `compiler.py` is the coordinator and public entry point. It initializes the
  sample database, invokes every phase, catches phase-specific errors, and
  stores diagnostics and intermediate representations in `CompilationResult`.
  The small `PlanStep` and `ExecutionPlanGenerator` classes live here because
  the plan is only consumed by this pipeline; this removes the old extra
  `execution_plan.py` module without changing the web API.
- `grammar.py` is the language definition. It contains token constants,
  non-terminals, productions, FIRST/FOLLOW sets, and the LL(1) parse table.
  `P9`-series productions split conditions into AND and OR tails so one token
  of lookahead is enough.
- `lexer.py` scans characters from left to right. It recognizes keywords,
  identifiers, numbers, quoted strings, commas, semicolons, and comparison
  operators. It returns `Token` objects and raises `LexerError` with position
  information for invalid characters or unfinished strings.
- `parser.py` uses the parse table with a stack. For a terminal it matches the
  input; for a non-terminal it chooses the production indexed by
  `(non-terminal, lookahead)`. `ParseNode` preserves the concrete derivation,
  and `ParseStep` records the stack/input/action trace shown by the UI.
- `ast_nodes.py` defines the meaningful query objects: `QueryNode`, columns,
  table, WHERE conditions, logical operators, order-by, and literals. AST nodes
  can be formatted and converted to dictionaries for the UI.
- `ast_builder.py` transforms the verbose parse tree into those AST objects.
  It validates the expected grammar shape while transforming, so malformed
  structures become `ASTBuildError` instead of obscure attribute errors.
- `semantic.py` loads SQLite schema metadata and checks table names, selected
  columns, WHERE columns, ORDER BY columns, and value types. It returns clear
  categorized `SemanticError` objects.
- `optimizer.py` transforms a copy of the AST and records rules such as
  expanding `SELECT *`, removing duplicate columns, pruning internal filter or
  sort columns from the final projection, and pushing filtering before
  projection.
- `executor.py` is the SQLite backend. It reconstructs SQL from the optimized
  AST, binds WHERE values as `?` parameters, executes it, and returns columns,
  rows, and row count. It never sends the original raw query directly to
  SQLite.
- `sample.db` is the small SQLite database used by the demo. `requirements.txt`
  lists Flask; `test_suite.py` contains 25 checks covering valid queries,
  lexical errors, syntax errors, semantic errors, and optimizer behavior.
- `docs/` contains the formal grammar, report, presentation content, and viva
  preparation. It explains the theory; the Python files are the executable
  implementation.

## What happens for one query

1. `compile_query()` calls `setup_database()` and creates an empty result.
2. `Lexer.tokenize()` emits tokens. A lexical failure returns immediately.
3. `Parser.parse()` consumes tokens until `$`. A missing table entry or
   unexpected terminal returns a syntax failure and retains the partial trace.
4. `ASTBuilder.build()` creates a `QueryNode` and the UI receives both a tree
   string and dictionary form.
5. `SemanticAnalyzer` checks the AST against the real `employees` schema.
6. `ExecutionPlanGenerator` creates an original plan; `QueryOptimizer` then
   records transformations; a second plan shows the optimized pipeline.
7. `QueryExecutor` reconstructs a safe SQL statement from the optimized AST,
   executes it, and puts the result in `CompilationResult`.

Run the tests with:

```powershell
python test_suite.py
```

Run the web UI with:

```powershell
python app.py
```

Then open `http://localhost:5000`.
