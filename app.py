"""
app.py - Web UI for the SQL Subset Compiler

A clean, academic Flask application that provides a web interface for
the SQL compiler. Shows all compiler phases:
  - SQL Input
  - Tokenization
  - LL(1) Parsing Trace
  - AST / Query Tree
  - Semantic Analysis
  - Query Optimization
  - Execution Plan
  - Query Results

Run: python app.py
Open: http://localhost:5000
"""

import json
from flask import Flask, render_template_string, request, jsonify
from compiler import compile_query, setup_database

app = Flask(__name__)

# =============================================================================
# HTML Template
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Subset Compiler — Compiler Design Project</title>
    <style>
        /* --- Reset & Base --- */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #f5f6fa;
            color: #2d3436;
            line-height: 1.6;
            min-height: 100vh;
        }

        /* --- Header --- */
        .header {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px 32px;
            border-bottom: 3px solid #3498db;
        }
        .header h1 {
            font-size: 1.4rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .header p {
            font-size: 0.85rem;
            color: #bdc3c7;
            margin-top: 4px;
        }

        /* --- Main layout --- */
        .main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }

        /* --- Input Section --- */
        .input-section {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .input-section label {
            font-weight: 600;
            font-size: 0.9rem;
            display: block;
            margin-bottom: 8px;
            color: #2c3e50;
        }
        .input-row {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        textarea {
            flex: 1;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.95rem;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            resize: vertical;
            min-height: 80px;
            background: #fafbfc;
        }
        textarea:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 2px rgba(52,152,219,0.15);
        }
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
        }
        .btn-compile {
            background: #2c3e50;
            color: #fff;
        }
        .btn-compile:hover { background: #34495e; }
        .btn-compile:disabled { background: #95a5a6; cursor: not-allowed; }
        .btn-example {
            background: #ecf0f1;
            color: #2c3e50;
            border: 1px solid #bdc3c7;
        }
        .btn-example:hover { background: #dfe6e9; }
        .btn-trace {
            background: #f39c12;
            color: #fff;
        }
        .btn-trace:hover { background: #e67e22; }

        /* --- Phase sections --- */
        .phase {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
            margin-bottom: 16px;
            overflow: hidden;
        }
        .phase-header {
            background: #ecf0f1;
            padding: 10px 16px;
            font-weight: 600;
            font-size: 0.85rem;
            color: #2c3e50;
            border-bottom: 1px solid #ddd;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .phase-header:hover { background: #dfe6e9; }
        .phase-header .toggle { font-size: 0.75rem; color: #7f8c8d; }
        .phase-body {
            padding: 16px;
            font-size: 0.9rem;
        }
        .phase-body.collapsed { display: none; }

        /* --- Status indicators --- */
        .status { padding: 4px 10px; border-radius: 3px; font-size: 0.8rem; font-weight: 600; display: inline-block; }
        .status-ok { background: #d4edda; color: #155724; }
        .status-err { background: #f8d7da; color: #721c24; }
        .status-info { background: #d1ecf1; color: #0c5460; }

        /* --- Code blocks --- */
        .code-block {
            background: #2d3436;
            color: #dfe6e9;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.82rem;
            padding: 14px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre;
            line-height: 1.5;
        }
        .code-block .token-kw { color: #74b9ff; font-weight: 600; }
        .code-block .token-id { color: #55efc4; }
        .code-block .token-num { color: #ffeaa7; }
        .code-block .token-str { color: #fd79a8; }
        .code-block .token-op { color: #fab1a0; }
        .code-block .token-sym { color: #b2bec3; }

        /* --- Trace table --- */
        .trace-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.78rem;
        }
        .trace-table th {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 8px 10px;
            text-align: left;
            font-weight: 600;
        }
        .trace-table td {
            padding: 5px 10px;
            border-bottom: 1px solid #eee;
            vertical-align: top;
        }
        .trace-table tr:nth-child(even) { background: #f8f9fa; }
        .trace-table .action-match { color: #27ae60; }
        .trace-table .action-expand { color: #2980b9; }
        .trace-table .action-accept { color: #27ae60; font-weight: 700; }
        .trace-table .action-error { color: #e74c3c; font-weight: 700; }

        /* --- Result table --- */
        .result-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .result-table th {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 8px 12px;
            text-align: left;
        }
        .result-table td {
            padding: 6px 12px;
            border-bottom: 1px solid #eee;
        }
        .result-table tr:nth-child(even) { background: #f8f9fa; }

        /* --- Error box --- */
        .error-box {
            background: #fdf2f2;
            border: 1px solid #e74c3c;
            border-left: 4px solid #e74c3c;
            border-radius: 4px;
            padding: 14px;
            margin-top: 8px;
        }
        .error-box .error-type { font-weight: 700; color: #c0392b; margin-bottom: 4px; }
        .error-box .error-msg { font-family: 'Consolas', monospace; font-size: 0.85rem; color: #2d3436; }

        /* --- Plan display --- */
        .plan-display {
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            line-height: 1.8;
        }
        .plan-step {
            padding: 4px 0;
        }
        .plan-arrow {
            color: #7f8c8d;
            padding-left: 8px;
        }

        /* --- Optimization list --- */
        .opt-list { list-style: none; padding: 0; }
        .opt-list li {
            padding: 6px 10px;
            margin: 4px 0;
            background: #eafaf1;
            border-left: 3px solid #27ae60;
            border-radius: 3px;
            font-size: 0.85rem;
        }

        /* --- Examples dropdown --- */
        .examples-panel {
            display: none;
            margin-top: 12px;
            padding: 12px;
            background: #fafbfc;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .examples-panel.visible { display: block; }
        .example-item {
            padding: 6px 10px;
            margin: 3px 0;
            cursor: pointer;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
            font-size: 0.82rem;
        }
        .example-item:hover { background: #d5f5e3; }

        /* --- Footer --- */
        .footer {
            text-align: center;
            padding: 16px;
            color: #7f8c8d;
            font-size: 0.8rem;
        }

        /* --- AST tree --- */
        .ast-tree {
            font-family: 'Consolas', monospace;
            font-size: 0.82rem;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>SQL Subset Compiler</h1>
        <p>Compiler Design — LL(1) Parser &amp; SQL Query Compiler &amp; Optimizer</p>
    </div>

    <div class="main">
        <!-- Input -->
        <div class="input-section">
            <label for="sql-input">SQL Query Input</label>
            <div class="input-row">
                <textarea id="sql-input" placeholder="SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;">SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;</textarea>
                <div class="btn-group">
                    <button class="btn-compile" id="btn-compile" onclick="compileQuery()">Compile &amp; Execute</button>
                    <button class="btn-trace" onclick="compileQuery(true)">Show LL(1) Trace</button>
                    <button class="btn-example" onclick="toggleExamples()">Example Queries</button>
                </div>
            </div>
            <div class="examples-panel" id="examples-panel">
                <div class="example-item" onclick="loadExample(this)">SELECT * FROM employees;</div>
                <div class="example-item" onclick="loadExample(this)">SELECT name, salary FROM employees;</div>
                <div class="example-item" onclick="loadExample(this)">SELECT name FROM employees WHERE salary > 50000;</div>
                <div class="example-item" onclick="loadExample(this)">SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;</div>
                <div class="example-item" onclick="loadExample(this)">SELECT name, age FROM employees WHERE age >= 30 AND department = 'Marketing';</div>
                <div class="example-item" onclick="loadExample(this)">SELECT name FROM employees WHERE department = 'HR' OR department = 'Engineering';</div>
                <hr style="margin:8px 0; border:none; border-top:1px solid #ddd;">
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">SELECT name FROM employees WHERE salary @ 100;</div>
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">SELECT name FROM employees WHERE name = 'hello;</div>
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">SELECT FROM employees;</div>
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">FROM employees;</div>
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">SELECT xyz FROM employees;</div>
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">SELECT name FROM nonexistent;</div>
                <div class="example-item" style="color:#e74c3c;" onclick="loadExample(this)">SELECT name FROM employees WHERE salary = 'hello';</div>
            </div>
        </div>

        <!-- Output sections (hidden by default) -->
        <div id="output" style="display:none;">

            <!-- 1. Tokenization -->
            <div class="phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>1. Lexical Analysis (Tokenization)</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-tokens"></div>
            </div>

            <!-- 2. Parsing -->
            <div class="phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>2. LL(1) Parsing</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-parse"></div>
            </div>

            <!-- 3. LL(1) Trace (only shown when requested) -->
            <div class="phase" id="trace-phase" style="display:none;">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>2b. LL(1) Parsing Trace (Step-by-Step)</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-trace"></div>
            </div>

            <!-- 4. AST -->
            <div class="phase" id="ast-phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>3. Abstract Syntax Tree (AST)</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-ast"></div>
            </div>

            <!-- 5. Semantic Analysis -->
            <div class="phase" id="sem-phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>4. Semantic Analysis</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-semantic"></div>
            </div>

            <!-- 6. Optimization -->
            <div class="phase" id="opt-phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>5. Query Optimization</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-optimize"></div>
            </div>

            <!-- 7. Execution Plan -->
            <div class="phase" id="plan-phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>6. Execution Plan</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-plan"></div>
            </div>

            <!-- 8. Results -->
            <div class="phase" id="result-phase">
                <div class="phase-header" onclick="togglePhase(this)">
                    <span>7. Query Results</span>
                    <span class="toggle">[collapse]</span>
                </div>
                <div class="phase-body" id="phase-result"></div>
            </div>

        </div>
    </div>

    <div class="footer">
        SQL Subset Compiler — Compiler Design Project
    </div>

    <script>
    // Toggle example panel
    function toggleExamples() {
        document.getElementById('examples-panel').classList.toggle('visible');
    }

    // Load an example query
    function loadExample(el) {
        document.getElementById('sql-input').value = el.textContent;
        document.getElementById('examples-panel').classList.remove('visible');
    }

    // Toggle phase collapse
    function togglePhase(header) {
        const body = header.nextElementSibling;
        body.classList.toggle('collapsed');
        const toggle = header.querySelector('.toggle');
        toggle.textContent = body.classList.contains('collapsed') ? '[expand]' : '[collapse]';
    }

    // Format token for display with color coding
    function formatToken(token) {
        const type = token.type;
        const value = token.value;
        const keywords = ['SELECT','FROM','WHERE','ORDER','BY','ASC','DESC','AND','OR'];

        if (keywords.includes(type)) {
            return `<span class="token-kw">${type}</span>`;
        } else if (type === 'IDENTIFIER') {
            return `<span class="token-id">IDENTIFIER(${value})</span>`;
        } else if (type === 'NUMBER') {
            return `<span class="token-num">NUMBER(${value})</span>`;
        } else if (type === 'STRING') {
            return `<span class="token-str">STRING(${value})</span>`;
        } else if (['EQ','NEQ','GT','LT','GEQ','LEQ'].includes(type)) {
            return `<span class="token-op">${type}</span>`;
        } else if (type === '$') {
            return `<span class="token-sym">$</span>`;
        } else {
            return `<span class="token-sym">${type}</span>`;
        }
    }

    // Format trace action with color coding
    function formatAction(action) {
        if (action.startsWith('Match')) {
            return `<span class="action-match">${action}</span>`;
        } else if (action.startsWith('Expand')) {
            return `<span class="action-expand">${action}</span>`;
        } else if (action === 'Accept') {
            return `<span class="action-accept">${action}</span>`;
        } else if (action.startsWith('Error')) {
            return `<span class="action-error">${action}</span>`;
        }
        return action;
    }

    // Main compile function
    function compileQuery(showTrace = false) {
        const sql = document.getElementById('sql-input').value.trim();
        if (!sql) return;

        const btn = document.getElementById('btn-compile');
        btn.disabled = true;
        btn.textContent = 'Compiling...';

        fetch('/compile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({sql: sql, show_trace: showTrace})
        })
        .then(r => r.json())
        .then(data => {
            renderOutput(data, showTrace);
            btn.disabled = false;
            btn.textContent = 'Compile & Execute';
        })
        .catch(err => {
            alert('Error: ' + err);
            btn.disabled = false;
            btn.textContent = 'Compile & Execute';
        });
    }

    // Render all output sections
    function renderOutput(data, showTrace) {
        document.getElementById('output').style.display = 'block';

        // --- 1. Tokens ---
        const tokensDiv = document.getElementById('phase-tokens');
        if (data.tokens && data.tokens.length > 0) {
            const tokenHtml = data.tokens.map(t => formatToken(t)).join('  ');
            tokensDiv.innerHTML = `
                <span class="status status-ok">Lexical Analysis: OK</span>
                <div class="code-block" style="margin-top:10px;">${tokenHtml}</div>
            `;
        } else if (data.error_type === 'LEXICAL') {
            tokensDiv.innerHTML = `
                <span class="status status-err">Lexical Error</span>
                <div class="error-box">
                    <div class="error-type">Lexical Error</div>
                    <div class="error-msg">${data.error_message}</div>
                </div>
            `;
        }

        // --- 2. Parse status ---
        const parseDiv = document.getElementById('phase-parse');
        if (data.error_type === 'LEXICAL') {
            parseDiv.innerHTML = `<span class="status status-info">Skipped (lexical error)</span>`;
        } else if (data.error_type === 'SYNTAX') {
            parseDiv.innerHTML = `
                <span class="status status-err">Syntax Error</span>
                <div class="error-box">
                    <div class="error-type">Syntax Error</div>
                    <div class="error-msg">${data.error_message}</div>
                </div>
            `;
        } else if (data.parse_tree) {
            parseDiv.innerHTML = `
                <span class="status status-ok">Syntax: Valid</span>
                <details style="margin-top:10px;">
                    <summary style="cursor:pointer; font-size:0.85rem; color:#2c3e50;">Show Parse Tree</summary>
                    <div class="code-block" style="margin-top:8px;">${data.parse_tree}</div>
                </details>
            `;
        }

        // --- 2b. LL(1) Trace ---
        const tracePhase = document.getElementById('trace-phase');
        const traceDiv = document.getElementById('phase-trace');
        if (showTrace && data.trace && data.trace.length > 0) {
            tracePhase.style.display = 'block';
            let rows = data.trace.map(s =>
                `<tr>
                    <td>${s.step_num}</td>
                    <td>${s.stack}</td>
                    <td>${s.input_str}</td>
                    <td>${formatAction(s.action)}</td>
                </tr>`
            ).join('');
            traceDiv.innerHTML = `
                <p style="margin-bottom:10px; font-size:0.85rem; color:#7f8c8d;">
                    Stack-based LL(1) predictive parsing — ${data.trace.length} steps
                </p>
                <div style="overflow-x:auto;">
                    <table class="trace-table">
                        <tr><th>Step</th><th>Stack</th><th>Input</th><th>Action</th></tr>
                        ${rows}
                    </table>
                </div>
            `;
        } else {
            tracePhase.style.display = 'none';
        }

        // --- 3. AST ---
        const astDiv = document.getElementById('phase-ast');
        const astPhase = document.getElementById('ast-phase');
        if (data.ast_str) {
            astPhase.style.display = 'block';
            let astJson = JSON.stringify(data.ast_dict, null, 2);
            astDiv.innerHTML = `
                <div class="ast-tree">
                    <div class="code-block">${data.ast_str}</div>
                </div>
                <details style="margin-top:10px;">
                    <summary style="cursor:pointer; font-size:0.85rem; color:#2c3e50;">Show JSON Representation</summary>
                    <div class="code-block" style="margin-top:8px;">${astJson}</div>
                </details>
            `;
        } else {
            astPhase.style.display = data.error_type && data.error_type !== 'SEMANTIC' ? 'none' : 'block';
            if (data.error_type && data.error_type !== 'SEMANTIC') {
                astDiv.innerHTML = `<span class="status status-info">Skipped (earlier error)</span>`;
            }
        }

        // --- 4. Semantic ---
        const semDiv = document.getElementById('phase-semantic');
        const semPhase = document.getElementById('sem-phase');
        if (data.error_type === 'SEMANTIC') {
            semPhase.style.display = 'block';
            const errHtml = data.semantic_errors.map(e =>
                `<div class="error-box" style="margin-bottom:6px;">
                    <div class="error-type">Semantic Error [${e.category}]</div>
                    <div class="error-msg">${e.message}</div>
                </div>`
            ).join('');
            semDiv.innerHTML = `
                <span class="status status-ok">Syntax: Valid</span>&nbsp;
                <span class="status status-err">Semantics: Invalid</span>
                ${errHtml}
            `;
        } else if (!data.error_type || data.success) {
            semPhase.style.display = 'block';
            semDiv.innerHTML = `
                <span class="status status-ok">Syntax: Valid</span>&nbsp;
                <span class="status status-ok">Semantics: Valid</span>
                <p style="margin-top:8px; font-size:0.85rem; color:#7f8c8d;">
                    Table, columns, types, and operators validated against database schema.
                </p>
            `;
        } else {
            semPhase.style.display = 'none';
        }

        // --- 5. Optimization ---
        const optDiv = document.getElementById('phase-optimize');
        const optPhase = document.getElementById('opt-phase');
        if (data.optimizations) {
            optPhase.style.display = 'block';
            if (data.optimizations.length > 0) {
                const listHtml = data.optimizations.map(r => `<li>${r}</li>`).join('');
                optDiv.innerHTML = `
                    <span class="status status-ok">${data.optimizations.length} optimization(s) applied</span>
                    <ul class="opt-list" style="margin-top:10px;">${listHtml}</ul>
                `;
            } else {
                optDiv.innerHTML = `
                    <span class="status status-info">No optimizations applicable</span>
                    <p style="margin-top:8px; font-size:0.85rem; color:#7f8c8d;">
                        The query is already in an efficient form.
                    </p>
                `;
            }
        } else {
            optPhase.style.display = 'none';
        }

        // --- 6. Execution Plan ---
        const planDiv = document.getElementById('phase-plan');
        const planPhase = document.getElementById('plan-phase');
        if (data.original_plan || data.optimized_plan) {
            planPhase.style.display = 'block';
            let planHtml = '';

            if (data.original_plan && data.optimizations && data.optimizations.length > 0) {
                planHtml += `
                    <div style="display:flex; gap:24px; flex-wrap:wrap;">
                        <div style="flex:1; min-width:250px;">
                            <p style="font-weight:600; font-size:0.85rem; margin-bottom:8px;">Original Plan</p>
                            <div class="code-block">${data.original_plan}</div>
                        </div>
                        <div style="flex:1; min-width:250px;">
                            <p style="font-weight:600; font-size:0.85rem; margin-bottom:8px;">Optimized Plan</p>
                            <div class="code-block">${data.optimized_plan}</div>
                        </div>
                    </div>
                `;
            } else {
                planHtml += `
                    <p style="font-weight:600; font-size:0.85rem; margin-bottom:8px;">Execution Plan</p>
                    <div class="code-block">${data.optimized_plan || data.original_plan}</div>
                `;
            }

            if (data.reconstructed_sql) {
                planHtml += `
                    <p style="margin-top:12px; font-size:0.85rem;">
                        <strong>Reconstructed SQL</strong> (generated from AST, not original input):<br>
                        <code style="background:#eee; padding:4px 8px; border-radius:3px; font-size:0.82rem;">
                            ${data.reconstructed_sql}
                        </code>
                    </p>
                `;
            }

            planDiv.innerHTML = planHtml;
        } else {
            planPhase.style.display = 'none';
        }

        // --- 7. Results ---
        const resultDiv = document.getElementById('phase-result');
        const resultPhase = document.getElementById('result-phase');
        if (data.error_type === 'EXECUTION') {
            resultPhase.style.display = 'block';
            resultDiv.innerHTML = `
                <span class="status status-err">Execution Error</span>
                <div class="error-box">
                    <div class="error-type">Execution Error</div>
                    <div class="error-msg">${data.error_message}</div>
                </div>
            `;
        } else if (data.result_columns) {
            resultPhase.style.display = 'block';
            let headerRow = data.result_columns.map(c => `<th>${c}</th>`).join('');
            let bodyRows = '';
            if (data.result_rows.length === 0) {
                bodyRows = `<tr><td colspan="${data.result_columns.length}" style="text-align:center; color:#7f8c8d;">(No rows returned)</td></tr>`;
            } else {
                bodyRows = data.result_rows.map(row =>
                    '<tr>' + row.map(v => `<td>${v !== null ? v : 'NULL'}</td>`).join('') + '</tr>'
                ).join('');
            }
            resultDiv.innerHTML = `
                <span class="status status-ok">${data.result_row_count} row(s) returned</span>
                <div style="overflow-x:auto; margin-top:10px;">
                    <table class="result-table">
                        <tr>${headerRow}</tr>
                        ${bodyRows}
                    </table>
                </div>
            `;
        } else {
            resultPhase.style.display = 'none';
        }
    }

    // Allow Ctrl+Enter to compile
    document.getElementById('sql-input').addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            compileQuery();
        }
    });
    </script>
</body>
</html>
"""


# =============================================================================
# API Endpoint
# =============================================================================

@app.route('/')
def index():
    """Serve the main UI page."""
    setup_database()
    return render_template_string(HTML_TEMPLATE)


@app.route('/compile', methods=['POST'])
def compile_endpoint():
    """
    Compile and execute a SQL query.
    Receives JSON: {"sql": "...", "show_trace": true/false}
    Returns JSON with all phase outputs.
    """
    data = request.get_json()
    sql = data.get('sql', '').strip()
    show_trace = data.get('show_trace', False)

    if not sql:
        return jsonify({"error_message": "Empty query", "error_type": "LEXICAL"})

    result = compile_query(sql)

    response = {
        "success": result.success,
        "error_phase": result.error_phase,
        "error_type": result.error_type,
        "error_message": result.error_message,
    }

    # Tokens
    if result.tokens:
        response["tokens"] = [
            {"type": t.type, "value": t.value, "line": t.line, "col": t.col}
            for t in result.tokens
        ]

    # Parse trace (only if requested)
    if show_trace and result.parse_trace:
        response["trace"] = [
            {
                "step_num": s.step_num,
                "stack": s.stack,
                "input_str": s.input_str,
                "action": s.action,
            }
            for s in result.parse_trace
        ]

    # Parse tree
    if result.parse_tree_str:
        response["parse_tree"] = result.parse_tree_str

    # AST
    if result.ast_str:
        response["ast_str"] = result.ast_str
        response["ast_dict"] = result.ast_dict

    # Semantic errors
    if result.semantic_errors:
        response["semantic_errors"] = [
            {"message": e.message, "category": e.category}
            for e in result.semantic_errors
        ]

    # Optimization
    if result.optimization:
        response["optimizations"] = result.optimization.rules_applied

    # Execution plans
    if result.original_plan_str:
        response["original_plan"] = result.original_plan_str
    if result.optimized_plan_str:
        response["optimized_plan"] = result.optimized_plan_str

    # Reconstructed SQL
    if result.reconstructed_sql:
        response["reconstructed_sql"] = result.reconstructed_sql

    # Results
    if result.result_columns:
        response["result_columns"] = result.result_columns
        response["result_rows"] = [list(row) for row in result.result_rows]
        response["result_row_count"] = result.result_row_count

    return jsonify(response)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    setup_database()
    print("Starting SQL Subset Compiler UI...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
