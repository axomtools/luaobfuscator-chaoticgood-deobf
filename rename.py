import re

def renameids(code):
    renamed = {}
    idpat = re.compile(r"\b(?:v|var|value|f|fn|func|function|t|tbl|table|s|str|string|n|num|number|l|local|a|b|c|d|x|y|z)\d+\b")
    tokpat = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    ls = re.compile(r"\[(=*)\[")
    def repl(m):
        ident = m.group(0)
        pm = re.match(r"[A-Za-z]+", ident)
        nm = re.search(r"\d+", ident)
        if not pm or not nm: return ident
        p = pm.group(0).lower()
        num = nm.group(0)
        names = {"v":"value","var":"value","value":"value",
                 "f":"function","fn":"function","func":"function","function":"function",
                 "t":"table","tbl":"table","table":"table",
                 "s":"string","str":"string","string":"string",
                 "n":"number","num":"number","number":"number",
                 "l":"local","local":"local",
                 "a":"argument","b":"buffer","c":"context","d":"data",
                 "x":"coordinate_x","y":"coordinate_y","z":"coordinate_z"}
        newname = f"{names.get(p,'variable')}_{num}"
        renamed.setdefault(ident, newname)
        return renamed[ident]
    out = []
    i = 0
    n = len(code)
    prev = ""
    while i < n:
        ch = code[i]
        if ch in ("'",'"'):
            q = ch; s = i; i += 1
            while i < n:
                if code[i] == "\\":
                    i += 2; continue
                if code[i] == q:
                    i += 1; break
                i += 1
            out.append(code[s:i]); prev = q; continue
        if ch == "[":
            m = ls.match(code,i)
            if m:
                op = m.group(0); cl = "]" + m.group(1) + "]"
                e = code.find(cl, i + len(op))
                if e == -1:
                    out.append(code[i:]); break
                e += len(cl)
                out.append(code[i:e]); i = e; prev = "]"; continue
        m = tokpat.match(code,i)
        if m:
            ident = m.group(0)
            if prev in (".",":"):
                out.append(ident)
            else:
                out.append(idpat.sub(repl, ident))
            prev = ident[-1]
            i += len(ident)
            continue
        out.append(ch)
        if not ch.isspace(): prev = ch
        i += 1
    return "".join(out)
