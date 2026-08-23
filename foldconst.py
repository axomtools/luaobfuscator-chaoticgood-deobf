import re

def isws(ch):
    return ch in ' \t\n\r\f\v'

def isdig(ch):
    return ch >= '0' and ch <= '9'

def isid0(ch):
    return ('a' <= ch <= 'z') or ('A' <= ch <= 'Z') or ch == '_'

def isid(ch):
    return isid0(ch) or isdig(ch)

def skws(s, i):
    while i < len(s) and isws(s[i]):
        i += 1
    return i

def rdnum(s, i):
    if not (isdig(s[i]) or (s[i] == '.' and i+1 < len(s) and isdig(s[i+1]))):
        return None
    j = i
    dot_count = 0
    while j < len(s) and (isdig(s[j]) or s[j] == '.'):
        if s[j] == '.':
            dot_count += 1
            if dot_count > 1:
                return None
        j += 1
    val = s[i:j]
    try:
        num = float(val) if '.' in val else int(val)
    except ValueError:
        return None
    return {'value': val, 'end': j, 'num': num}

def skstr(s, i):
    q = s[i]
    if q not in '"\'':
        return i
    j = i + 1
    while j < len(s) and s[j] != q:
        if s[j] == '\\':
            j += 1
        j += 1
    return j + 1

def evalex(expr):
    try:
        return eval(expr) if expr.strip() else None
    except:
        return None

def foldpar(s):
    out = ''
    i = 0
    while i < len(s):
        if s[i] == '"' or s[i] == "'":
            q = s[i]
            out += q
            i += 1
            while i < len(s) and s[i] != q:
                if s[i] == '\\':
                    out += s[i]
                    i += 1
                    if i < len(s):
                        out += s[i]
                        i += 1
                else:
                    out += s[i]
                    i += 1
            if i < len(s):
                out += s[i]
                i += 1
            continue
        if s[i] == '(':
            depth = 1
            j = i + 1
            inner = ''
            ok = True
            while j < len(s) and depth > 0:
                if s[j] == '"' or s[j] == "'":
                    ok = False
                    break
                if s[j] == '(':
                    depth += 1
                elif s[j] == ')':
                    depth -= 1
                if depth > 0:
                    inner += s[j]
                j += 1
            if ok and depth == 0 and inner and any(c in '+-*/%^' for c in inner):
                v = evalex(inner)
                if v is not None and isinstance(v, (int, float)):
                    prev = out[-1] if out else ''
                    lit = str(v) if isinstance(v, int) else format(v, '.12g')
                    if prev and isid(prev):
                        out += '(' + lit + ')'
                    else:
                        out += lit
                    i = j
                    continue
        out += s[i]
        i += 1
    return out

def foldbin(s):
    out = ''
    i = 0
    while i < len(s):
        if s[i] == '"' or s[i] == "'":
            q = s[i]
            out += q
            i += 1
            while i < len(s) and s[i] != q:
                if s[i] == '\\':
                    out += s[i]
                    i += 1
                    if i < len(s):
                        out += s[i]
                        i += 1
                else:
                    out += s[i]
                    i += 1
            if i < len(s):
                out += s[i]
                i += 1
            continue
        left = rdnum(s, i)
        if left and (i == 0 or not isid(s[i-1])):
            j = skws(s, left['end'])
            op = s[j] if j < len(s) else ''
            if op in '+-*/%^':
                j = skws(s, j + 1)
                right = rdnum(s, j)
                if right and (right['end'] >= len(s) or not isid(s[right['end']])):
                    v = None
                    if op == '+': v = left['num'] + right['num']
                    elif op == '-': v = left['num'] - right['num']
                    elif op == '*': v = left['num'] * right['num']
                    elif op == '/': v = left['num'] / right['num']
                    elif op == '%': v = left['num'] % right['num']
                    elif op == '^': v = left['num'] ** right['num']
                    if v is not None:
                        out += str(v) if isinstance(v, int) else format(v, '.12g')
                        i = right['end']
                        continue
        out += s[i]
        i += 1
    return out

def foldcmp(s):
    out = ''
    i = 0
    while i < len(s):
        if s[i] == '"' or s[i] == "'":
            q = s[i]
            out += q
            i += 1
            while i < len(s) and s[i] != q:
                if s[i] == '\\':
                    out += s[i]
                    i += 1
                    if i < len(s):
                        out += s[i]
                        i += 1
                else:
                    out += s[i]
                    i += 1
            if i < len(s):
                out += s[i]
                i += 1
            continue
        left = rdnum(s, i)
        if left and (i == 0 or not isid(s[i-1])):
            j = skws(s, left['end'])
            op = None
            if s[j:j+2] in ('==', '~=', '<=', '>='):
                op = s[j:j+2]
                j += 2
            elif s[j] in '<>':
                op = s[j]
                j += 1
            if op:
                j = skws(s, j)
                right = rdnum(s, j)
                if right and (right['end'] >= len(s) or not isid(s[right['end']])):
                    v = None
                    if op == '==': v = left['num'] == right['num']
                    elif op == '~=': v = left['num'] != right['num']
                    elif op == '<': v = left['num'] < right['num']
                    elif op == '>': v = left['num'] > right['num']
                    elif op == '<=': v = left['num'] <= right['num']
                    elif op == '>=': v = left['num'] >= right['num']
                    if v is not None:
                        out += 'true' if v else 'false'
                        i = right['end']
                        continue
        out += s[i]
        i += 1
    return out

def foldconst(code):
    s = str(code)
    s = foldpar(s)
    s = foldbin(s)
    s = foldcmp(s)
    return s
