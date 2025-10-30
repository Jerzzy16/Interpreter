import sys
import re
from pathlib import Path

# --- Configuration: reserved words & symbol patterns ---
RESERVED_WORDS = {"integer", "double", "output", "if"}
SYMBOLS = {":", ";", ":=", "=", "+", "-", "(", ")", "<<", ">", "<", "==", "!=", '"'}

# Regex patterns
RE_DECL = re.compile(r'^\s*([A-Za-z]\w*)\s*:\s*(integer|double)\s*;\s*$', re.IGNORECASE)
RE_ASSIGN = re.compile(r'^\s*([A-Za-z]\w*)\s*(?::=|=)\s*(.+?)\s*;\s*$', re.IGNORECASE)
RE_OUTPUT = re.compile(r'^\s*output\s*<<\s*(.+?)\s*;\s*$', re.IGNORECASE)
RE_IF = re.compile(r'^\s*if\s*\(\s*(.+?)\s*\)\s*(.+)$', re.IGNORECASE)

RE_COND = re.compile(r'^\s*(.+?)\s*(==|!=|>|<)\s*(.+?)\s*$')

# Helper: remove whitespace (spaces, tabs, newlines)
def remove_whitespace_all(s: str) -> str:
    return re.sub(r'\s+', '', s)

def tokenize_symbols_and_reserved(s: str):
    found = []
    # collect reserved words
    for word in RESERVED_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', s, re.IGNORECASE):
            found.append(word)
    # collect symbols
    for sym in sorted(SYMBOLS, key=len, reverse=True):
        if sym in s:
            found.append(sym)
    return found

# Very small evaluator for arithmetic using declared variables
class Interpreter:
    def __init__(self, source_text):
        self.source_lines = source_text.splitlines()
        self.vars = {}  # name -> (type, value)
        self.errors = []
        self.outputs = []

    def error(self, msg, lineno=None):
        if lineno is not None:
            self.errors.append(f"Line {lineno}: {msg}")
        else:
            self.errors.append(msg)

    def parse_and_run(self):
        # First pass: process lines (strip comments if any; comments not specified)
        for i, raw_line in enumerate(self.source_lines, start=1):
            line = raw_line.strip()
            if line == "":
                continue
            # Declaration
            m = RE_DECL.match(line)
            if m:
                name, typ = m.group(1), m.group(2).lower()
                if name in self.vars:
                    self.error(f"Variable '{name}' redeclared.", i)
                else:
                    self.vars[name] = (typ, None)
                continue
            # Assignment
            m = RE_ASSIGN.match(line)
            if m:
                name = m.group(1)
                expr = m.group(2).strip()
                if name not in self.vars:
                    self.error(f"Assignment to undeclared variable '{name}'.", i)
                    continue
                typ, _ = self.vars[name]
                # Evaluate expression (support + and - and numeric literals and variables)
                val, ok = self.eval_expr(expr, i)
                if not ok:
                    continue
                # Type conversion / check
                if typ == "integer":
                    try:
                        val = int(round(float(val)))
                    except Exception:
                        self.error(f"Cannot convert value to integer for '{name}'.", i)
                        continue
                else:  # double
                    val = float(val)
                self.vars[name] = (typ, val)
                continue
            # Output
            m = RE_OUTPUT.match(line)
            if m:
                payload = m.group(1).strip()
                # String literal?
                if payload.startswith('"') and payload.endswith('"'):
                    self.outputs.append(payload[1:-1])
                else:
                    # assume expression or variable
                    val, ok = self.eval_expr(payload, i)
                    if not ok:
                        continue
                    # For display, format floats with up to 2 decimals (as per spec)
                    if isinstance(val, float) and not val.is_integer():
                        val = f"{val:.2f}"
                    else:
                        # integer-like float -> show as integer
                        try:
                            if float(val).is_integer():
                                val = str(int(float(val)))
                        except:
                            val = str(val)
                    self.outputs.append(str(val))
                continue
            # If statement (one-line form allowed)
            m = RE_IF.match(line)
            if m:
                cond = m.group(1).strip()
                stmt = m.group(2).strip()
                cond_ok, cond_res = self.eval_condition(cond, i)
                if cond_ok is None:
                    continue  # error already reported
                if cond_res:
                    # treat stmt as a line by itself (could be an output or assignment)
                    # we will reuse the parsers by feeding it to a small temporary interpreter call
                    # but to keep it simple, we mimic only output and assignment handling
                    # ensure statement ends with semicolon per examples
                    if not stmt.endswith(";"):
                        self.error("Statement inside if must end with semicolon.", i)
                    else:
                        # Use the same matching as above by temporarily matching patterns
                        # Assignment inside if
                        m2 = RE_ASSIGN.match(stmt)
                        if m2:
                            name = m2.group(1)
                            expr = m2.group(2).strip()
                            if name not in self.vars:
                                self.error(f"Assignment to undeclared variable '{name}' inside if.", i)
                                continue
                            typ, _ = self.vars[name]
                            val, ok = self.eval_expr(expr, i)
                            if not ok:
                                continue
                            if typ == "integer":
                                try:
                                    val = int(round(float(val)))
                                except Exception:
                                    self.error(f"Cannot convert value to integer for '{name}'.", i)
                                    continue
                            else:
                                val = float(val)
                            self.vars[name] = (typ, val)
                            continue
                        # Output inside if
                        m2 = RE_OUTPUT.match(stmt)
                        if m2:
                            payload = m2.group(1).strip()
                            if payload.startswith('"') and payload.endswith('"'):
                                self.outputs.append(payload[1:-1])
                            else:
                                val, ok = self.eval_expr(payload, i)
                                if not ok:
                                    continue
                                if isinstance(val, float) and not val.is_integer():
                                    val = f"{val:.2f}"
                                else:
                                    try:
                                        if float(val).is_integer():
                                            val = str(int(float(val)))
                                    except:
                                        val = str(val)
                                self.outputs.append(str(val))
                            continue
                        self.error("Unsupported statement inside If.", i)
                continue
            # If reached here, unrecognized syntax
            self.error("Unrecognized or invalid syntax.", i)

    def eval_expr(self, expr, lineno):
        """
        Evaluate a simple arithmetic expression consisting of numbers (integer/double),
        variable names, plus and minus only. No operator precedence beyond left-to-right
        (which is enough for + and -).
        Returns (value, ok).
        """
        # replace variable names with their values
        # split on + and - but keep signs
        try:
            # validate tokens: allowed chars are letters, digits, ., +, -, parentheses, spaces
            if re.search(r'[^A-Za-z0-9\.\+\-\(\)\s]', expr):
                self.error(f"Illegal character in expression '{expr}'", lineno)
                return (None, False)
            # substitute variables
            def var_repl(m):
                name = m.group(0)
                if name in self.vars:
                    typ, val = self.vars[name]
                    if val is None:
                        self.error(f"Variable '{name}' used before assignment.", lineno)
                        raise ValueError("unassigned")
                    return str(val)
                else:
                    self.error(f"Undeclared variable '{name}' in expression.", lineno)
                    raise ValueError("undeclared")
            expr_sub = re.sub(r'\b[A-Za-z]\w*\b', var_repl, expr)
            # now evaluate expression safely: only digits, ., +, -, parentheses remain
            # as a final safety check:
            if re.search(r'[^0-9\.\+\-\(\)\s]', expr_sub):
                self.error(f"Illegal characters after substitution in '{expr_sub}'", lineno)
                return (None, False)
            # Evaluate using Python eval but in safe environment
            val = eval(expr_sub, {"_builtins_": None}, {})
            # return floats/ints
            return (val, True)
        except ValueError:
            return (None, False)
        except Exception as e:
            self.error(f"Error evaluating expression '{expr}': {e}", lineno)
            return (None, False)

    def eval_condition(self, cond, lineno):
        # cond like: x < 5  or  x == 3+2
        m = RE_COND.match(cond)
        if not m:
            self.error(f"Invalid condition format: '{cond}'", lineno)
            return (None, False)
        left, op, right = m.group(1).strip(), m.group(2), m.group(3).strip()
        lv, ok1 = self.eval_expr(left, lineno)
        if not ok1:
            return (None, False)
        rv, ok2 = self.eval_expr(right, lineno)
        if not ok2:
            return (None, False)
        try:
            if op == "==":
                return (True, lv == rv)
            elif op == "!=":
                return (True, lv != rv)
            elif op == ">":
                return (True, lv > rv)
            elif op == "<":
                return (True, lv < rv)
            else:
                self.error(f"Unsupported operator '{op}' in condition.", lineno)
                return (None, False)
        except Exception as e:
            self.error(f"Error evaluating condition: {e}", lineno)
            return (None, False)

def main():
    if len(sys.argv) != 2:
        print("Usage: python interpret.py path/to/source.HL")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    if not source_path.exists():
        print("Source file not found.")
        sys.exit(1)

    text = source_path.read_text(encoding='utf-8')

    # Produce NOSPACES.TXT (remove all whitespace)
    nospaces = remove_whitespace_all(text)
    Path("NOSPACES.TXT").write_text(nospaces, encoding='utf-8')

    # Produce RES_SYM.TXT (list reserved words and symbols found)
    found = tokenize_symbols_and_reserved(text)
    Path("RES_SYM.TXT").write_text("\n".join(found), encoding='utf-8')

    # Interpret / syntax-check
    interp = Interpreter(text)
    interp.parse_and_run()

    # Print outputs
    for o in interp.outputs:
        print(o)

    # Print result message
    if interp.errors:
        print("ERROR")
        # Optionally print diagnostics lines (you can remove the next lines before submission if only "ERROR" required)
        for e in interp.errors:
            print(e)
    else:
        print("NO ERROR(S) FOUND")

if __name__ == "__main__":
    main()