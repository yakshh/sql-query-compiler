"""
grammar.py — Formal Grammar Definitions for the SQL Subset Compiler

This module defines the grammar, FIRST sets, FOLLOW sets, and LL(1) parsing
table used by the predictive parser. All definitions correspond to the formal
specification in docs/grammar.md.

The grammar supports:
    SELECT [* | col1, col2, ...] FROM table
    [WHERE col op value [AND/OR col op value ...]]
    [ORDER BY col [ASC|DESC]] ;
"""

# =============================================================================
# SECTION 1: Token Types (Terminals)
# =============================================================================
# These are all the terminal symbols in our grammar.
# The lexer produces tokens of these types.

# --- Keywords ---
SELECT    = "SELECT"
FROM      = "FROM"
WHERE     = "WHERE"
ORDER     = "ORDER"
BY        = "BY"
ASC       = "ASC"
DESC      = "DESC"
AND       = "AND"
OR        = "OR"

# --- Identifiers and Literals ---
IDENTIFIER = "IDENTIFIER"
NUMBER     = "NUMBER"
STRING     = "STRING"

# --- Symbols ---
STAR      = "STAR"         # *
COMMA     = "COMMA"        # ,
SEMICOLON = "SEMICOLON"    # ;

# --- Comparison Operators ---
EQ        = "EQ"           # =
NEQ       = "NEQ"          # !=
GT        = "GT"           # >
LT        = "LT"          # <
GEQ       = "GEQ"          # >=
LEQ       = "LEQ"          # <=

# --- Special ---
EOF       = "$"            # End-of-input marker
EPSILON   = "ε"            # Empty production marker

# All keywords (used by the lexer to distinguish keywords from identifiers)
KEYWORDS = {SELECT, FROM, WHERE, ORDER, BY, ASC, DESC, AND, OR}

# All terminal symbols (for reference)
TERMINALS = {
    SELECT, FROM, WHERE, ORDER, BY, ASC, DESC, AND, OR,
    IDENTIFIER, NUMBER, STRING,
    STAR, COMMA, SEMICOLON,
    EQ, NEQ, GT, LT, GEQ, LEQ,
    EOF
}

# =============================================================================
# SECTION 2: Non-Terminal Symbols
# =============================================================================

# Base grammar non-terminals
NT_QUERY         = "Query"
NT_SELECT_LIST   = "SelectList"
NT_COLUMN_LIST   = "ColumnList"
NT_COLUMN_TAIL   = "ColumnTail"
NT_OPT_WHERE     = "OptWhere"
NT_CONDITION     = "Condition"
NT_COMP_OP       = "CompOp"
NT_VALUE         = "Value"
NT_OPT_ORDER_BY  = "OptOrderBy"
NT_OPT_DIRECTION = "OptDirection"

# Extended grammar non-terminals (AND/OR support)
NT_OR_TAIL       = "OrTail"
NT_AND_EXPR      = "AndExpr"
NT_AND_TAIL      = "AndTail"
NT_PREDICATE     = "Predicate"

NON_TERMINALS = {
    NT_QUERY, NT_SELECT_LIST, NT_COLUMN_LIST, NT_COLUMN_TAIL,
    NT_OPT_WHERE, NT_CONDITION, NT_COMP_OP, NT_VALUE,
    NT_OPT_ORDER_BY, NT_OPT_DIRECTION,
    # Extended
    NT_OR_TAIL, NT_AND_EXPR, NT_AND_TAIL, NT_PREDICATE
}

# =============================================================================
# SECTION 3: Production Rules
# =============================================================================
# Each production is stored as: label -> (non_terminal, [list of symbols])
# EPSILON in the list means the production derives the empty string.

PRODUCTIONS = {
    # --- Base Grammar ---
    "P1":  (NT_QUERY,         [SELECT, NT_SELECT_LIST, FROM, IDENTIFIER,
                               NT_OPT_WHERE, NT_OPT_ORDER_BY, SEMICOLON]),
    "P2":  (NT_SELECT_LIST,   [STAR]),
    "P3":  (NT_SELECT_LIST,   [NT_COLUMN_LIST]),
    "P4":  (NT_COLUMN_LIST,   [IDENTIFIER, NT_COLUMN_TAIL]),
    "P5":  (NT_COLUMN_TAIL,   [COMMA, IDENTIFIER, NT_COLUMN_TAIL]),
    "P6":  (NT_COLUMN_TAIL,   [EPSILON]),
    "P7":  (NT_OPT_WHERE,     [WHERE, NT_CONDITION]),
    "P8":  (NT_OPT_WHERE,     [EPSILON]),
    "P9":  (NT_CONDITION,     [NT_AND_EXPR, NT_OR_TAIL]),
    "P9a": (NT_OR_TAIL,       [OR, NT_AND_EXPR, NT_OR_TAIL]),
    "P9b": (NT_OR_TAIL,       [EPSILON]),
    "P9c": (NT_AND_EXPR,      [NT_PREDICATE, NT_AND_TAIL]),
    "P9d": (NT_AND_TAIL,      [AND, NT_PREDICATE, NT_AND_TAIL]),
    "P9e": (NT_AND_TAIL,      [EPSILON]),
    "P9f": (NT_PREDICATE,     [IDENTIFIER, NT_COMP_OP, NT_VALUE]),
    "P10": (NT_COMP_OP,       [EQ]),
    "P11": (NT_COMP_OP,       [NEQ]),
    "P12": (NT_COMP_OP,       [GT]),
    "P13": (NT_COMP_OP,       [LT]),
    "P14": (NT_COMP_OP,       [GEQ]),
    "P15": (NT_COMP_OP,       [LEQ]),
    "P16": (NT_VALUE,         [NUMBER]),
    "P17": (NT_VALUE,         [STRING]),
    "P18": (NT_OPT_ORDER_BY,  [ORDER, BY, IDENTIFIER, NT_OPT_DIRECTION]),
    "P19": (NT_OPT_ORDER_BY,  [EPSILON]),
    "P20": (NT_OPT_DIRECTION, [ASC]),
    "P21": (NT_OPT_DIRECTION, [DESC]),
    "P22": (NT_OPT_DIRECTION, [EPSILON]),
}

# =============================================================================
# SECTION 4: FIRST Sets
# =============================================================================
# FIRST(A) = set of terminals that can appear as the first symbol in any
# string derived from A. If A can derive ε, then ε is included.

FIRST = {
    NT_QUERY:         {SELECT},
    NT_SELECT_LIST:   {STAR, IDENTIFIER},
    NT_COLUMN_LIST:   {IDENTIFIER},
    NT_COLUMN_TAIL:   {COMMA, EPSILON},
    NT_OPT_WHERE:     {WHERE, EPSILON},
    NT_CONDITION:     {IDENTIFIER},
    NT_OR_TAIL:       {OR, EPSILON},
    NT_AND_EXPR:      {IDENTIFIER},
    NT_AND_TAIL:      {AND, EPSILON},
    NT_PREDICATE:     {IDENTIFIER},
    NT_COMP_OP:       {EQ, NEQ, GT, LT, GEQ, LEQ},
    NT_VALUE:         {NUMBER, STRING},
    NT_OPT_ORDER_BY:  {ORDER, EPSILON},
    NT_OPT_DIRECTION: {ASC, DESC, EPSILON},
}

# =============================================================================
# SECTION 5: FOLLOW Sets
# =============================================================================
# FOLLOW(A) = set of terminals that can appear immediately after A in
# some sentential form. $ is included if A can be the last symbol.

FOLLOW = {
    NT_QUERY:         {EOF},
    NT_SELECT_LIST:   {FROM},
    NT_COLUMN_LIST:   {FROM},
    NT_COLUMN_TAIL:   {FROM},
    NT_OPT_WHERE:     {ORDER, SEMICOLON},
    NT_CONDITION:     {ORDER, SEMICOLON},
    NT_OR_TAIL:       {ORDER, SEMICOLON},
    NT_AND_EXPR:      {OR, ORDER, SEMICOLON},
    NT_AND_TAIL:      {OR, ORDER, SEMICOLON},
    NT_PREDICATE:     {AND, OR, ORDER, SEMICOLON},
    NT_COMP_OP:       {NUMBER, STRING},
    NT_VALUE:         {AND, OR, ORDER, SEMICOLON},
    NT_OPT_ORDER_BY:  {SEMICOLON},
    NT_OPT_DIRECTION: {SEMICOLON},
}

# =============================================================================
# SECTION 6: LL(1) Parsing Table
# =============================================================================
# Table format: PARSE_TABLE[(non_terminal, terminal)] = production_label
#
# To use: look up (top_of_stack, current_lookahead). If an entry exists,
# expand the non-terminal using that production. If no entry exists, it
# is a syntax error.
#
# Construction rule:
#   For production A → α with label L:
#     - For each terminal a in FIRST(α), set TABLE[A, a] = L
#     - If ε ∈ FIRST(α), for each terminal b in FOLLOW(A), set TABLE[A, b] = L

PARSE_TABLE = {
    # Query: only starts with SELECT
    (NT_QUERY, SELECT):          "P1",

    # SelectList: STAR → P2, IDENTIFIER → P3
    (NT_SELECT_LIST, STAR):      "P2",
    (NT_SELECT_LIST, IDENTIFIER):"P3",

    # ColumnList: always starts with IDENTIFIER
    (NT_COLUMN_LIST, IDENTIFIER):"P4",

    # ColumnTail: COMMA → P5 (more columns), FROM → P6 (ε, done)
    (NT_COLUMN_TAIL, COMMA):     "P5",
    (NT_COLUMN_TAIL, FROM):      "P6",

    # OptWhere: WHERE → P7 (has condition), ORDER/SEMICOLON → P8 (ε, skip)
    (NT_OPT_WHERE, WHERE):       "P7",
    (NT_OPT_WHERE, ORDER):       "P8",
    (NT_OPT_WHERE, SEMICOLON):   "P8",

    # Condition: starts with IDENTIFIER (via AndExpr → Predicate)
    (NT_CONDITION, IDENTIFIER):  "P9",

    # OrTail: OR → P9a (more OR terms), else → P9b (ε)
    (NT_OR_TAIL, OR):            "P9a",
    (NT_OR_TAIL, ORDER):         "P9b",
    (NT_OR_TAIL, SEMICOLON):     "P9b",

    # AndExpr: starts with IDENTIFIER (via Predicate)
    (NT_AND_EXPR, IDENTIFIER):   "P9c",

    # AndTail: AND → P9d (more AND terms), else → P9e (ε)
    (NT_AND_TAIL, AND):          "P9d",
    (NT_AND_TAIL, OR):           "P9e",
    (NT_AND_TAIL, ORDER):        "P9e",
    (NT_AND_TAIL, SEMICOLON):    "P9e",

    # Predicate: starts with IDENTIFIER
    (NT_PREDICATE, IDENTIFIER):  "P9f",

    # CompOp: one entry per comparison operator
    (NT_COMP_OP, EQ):            "P10",
    (NT_COMP_OP, NEQ):           "P11",
    (NT_COMP_OP, GT):            "P12",
    (NT_COMP_OP, LT):            "P13",
    (NT_COMP_OP, GEQ):           "P14",
    (NT_COMP_OP, LEQ):           "P15",

    # Value: NUMBER → P16, STRING → P17
    (NT_VALUE, NUMBER):          "P16",
    (NT_VALUE, STRING):          "P17",

    # OptOrderBy: ORDER → P18 (has ORDER BY), SEMICOLON → P19 (ε, skip)
    (NT_OPT_ORDER_BY, ORDER):    "P18",
    (NT_OPT_ORDER_BY, SEMICOLON):"P19",

    # OptDirection: ASC → P20, DESC → P21, SEMICOLON → P22 (ε, default)
    (NT_OPT_DIRECTION, ASC):     "P20",
    (NT_OPT_DIRECTION, DESC):    "P21",
    (NT_OPT_DIRECTION, SEMICOLON):"P22",
}

# Start symbol for the parser
START_SYMBOL = NT_QUERY


# =============================================================================
# SECTION 7: Utility Functions
# =============================================================================

def is_terminal(symbol):
    """Check if a symbol is a terminal (not a non-terminal or epsilon)."""
    return symbol not in NON_TERMINALS and symbol != EPSILON


def is_non_terminal(symbol):
    """Check if a symbol is a non-terminal."""
    return symbol in NON_TERMINALS


def get_production(label):
    """Retrieve a production rule by its label (e.g., 'P1')."""
    return PRODUCTIONS.get(label)


def get_parse_action(non_terminal, terminal):
    """
    Look up the parsing table entry for a (non_terminal, terminal) pair.
    Returns the production label if found, or None (indicating syntax error).
    """
    return PARSE_TABLE.get((non_terminal, terminal))


def format_production(label):
    """Return a human-readable string for a production rule."""
    if label not in PRODUCTIONS:
        return f"Unknown production: {label}"
    nt, symbols = PRODUCTIONS[label]
    rhs = " ".join(symbols) if symbols != [EPSILON] else "ε"
    return f"{label}: {nt} → {rhs}"


# =============================================================================
# SECTION 8: Self-Verification
# =============================================================================
# When this module is run directly, it verifies that the parsing table has
# no conflicts and that FIRST/FOLLOW sets are consistent.

def verify_grammar():
    """
    Verify the LL(1) parsing table for conflicts.
    A conflict occurs if two different productions map to the same
    (non_terminal, terminal) pair.
    """
    print("=" * 60)
    print("  LL(1) Grammar Verification")
    print("=" * 60)

    # Check for conflicts: rebuild the table and look for duplicates
    table_check = {}
    conflicts = []

    for label, (nt, symbols) in PRODUCTIONS.items():
        # Compute the predict set for this production
        predict_set = set()

        if symbols == [EPSILON]:
            # ε-production: predict on FOLLOW(nt)
            predict_set = FOLLOW[nt]
        else:
            first_sym = symbols[0]
            if is_terminal(first_sym):
                predict_set = {first_sym}
            elif is_non_terminal(first_sym):
                predict_set = FIRST[first_sym] - {EPSILON}
                if EPSILON in FIRST[first_sym]:
                    predict_set |= FOLLOW[nt]

        for terminal in predict_set:
            key = (nt, terminal)
            if key in table_check:
                conflicts.append(
                    f"  CONFLICT at ({nt}, {terminal}): "
                    f"{table_check[key]} vs {label}"
                )
            else:
                table_check[key] = label

    if conflicts:
        print("\n❌ CONFLICTS FOUND:")
        for c in conflicts:
            print(c)
    else:
        print("\n✅ No conflicts — grammar is LL(1).")

    # Verify that our hardcoded PARSE_TABLE matches the computed table
    mismatches = []
    for key in set(list(PARSE_TABLE.keys()) + list(table_check.keys())):
        pt_val = PARSE_TABLE.get(key)
        tc_val = table_check.get(key)
        if pt_val != tc_val:
            mismatches.append(
                f"  ({key[0]}, {key[1]}): "
                f"hardcoded={pt_val}, computed={tc_val}"
            )

    if mismatches:
        print("\n⚠️  PARSE_TABLE vs computed mismatches:")
        for m in mismatches:
            print(m)
    else:
        print("✅ Hardcoded PARSE_TABLE matches computed table.")

    # Print summary
    print(f"\n  Productions:     {len(PRODUCTIONS)}")
    print(f"  Non-terminals:   {len(NON_TERMINALS)}")
    print(f"  Terminals:       {len(TERMINALS)}")
    print(f"  Table entries:   {len(PARSE_TABLE)}")
    print("=" * 60)

    return len(conflicts) == 0 and len(mismatches) == 0


if __name__ == "__main__":
    verify_grammar()

    # Print all productions for reference
    print("\nProductions:")
    for label in sorted(PRODUCTIONS.keys(), key=lambda x: (x.replace("a","~a").replace("b","~b").replace("c","~c").replace("d","~d").replace("e","~e").replace("f","~f") if len(x)>2 else x)):
        print(f"  {format_production(label)}")

    # Print FIRST sets
    print("\nFIRST sets:")
    for nt in sorted(FIRST.keys()):
        print(f"  FIRST({nt}) = {{ {', '.join(sorted(FIRST[nt]))} }}")

    # Print FOLLOW sets
    print("\nFOLLOW sets:")
    for nt in sorted(FOLLOW.keys()):
        print(f"  FOLLOW({nt}) = {{ {', '.join(sorted(FOLLOW[nt]))} }}")
