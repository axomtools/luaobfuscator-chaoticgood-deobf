import re
import math

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

def rdid(s, i):
    if not isid0(s[i] if i < len(s) else ''):
        return None
    j = i + 1
    while j < len(s) and isid(s[j]):
        j += 1
    return {'name': s[i:j], 'end': j}

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

def nextkw(s, i):
    start = skws(s, i)
    if start >= len(s):
        return None
    if s[start] == '"' or s[start] == "'":
        return {'kind': 'str', 'start': start, 'end': skstr(s, start)}
    id_ = rdid(s, start)
    if not id_:
        return {'kind': 'ch', 'ch': s[start], 'start': start, 'end': start + 1}
    return {'kind': 'kw', 'name': id_['name'], 'start': start, 'end': id_['end']}

def wdat(s, i, word):
    if s[i:i+len(word)] != word:
        return False
    before = '' if i == 0 else s[i-1]
    after = s[i+len(word)] if i+len(word) < len(s) else ''
    if before and isid(before):
        return False
    if after and isid(after):
        return False
    return True

def findwd(s, word, from_=0):
    i = from_
    while i < len(s):
        if s[i] == '"' or s[i] == "'":
            i = skstr(s, i)
            continue
        if wdat(s, i, word):
            return i
        i += 1
    return -1

def findblkend(s, from_):
    head = nextkw(s, from_)
    if not head or head['kind'] != 'kw':
        return -1
    if head['name'] not in ('if','function','repeat','do','for','while'):
        return -1
    i = head['end']
    depth = 1
    if head['name'] in ('for','while'):
        while i < len(s):
            if s[i] == '"' or s[i] == "'":
                i = skstr(s, i)
                continue
            tok = nextkw(s, i)
            if not tok:
                return -1
            if tok['kind'] == 'kw' and tok['name'] == 'do':
                i = tok['end']
                break
            i = tok['end']
    while i < len(s):
        if s[i] == '"' or s[i] == "'":
            i = skstr(s, i)
            continue
        tok = nextkw(s, i)
        if not tok:
            break
        if tok['kind'] != 'kw':
            i = tok['end']
            continue
        name = tok['name']
        if name in ('elseif','else'):
            i = tok['end']
            continue
        if name in ('for','while'):
            i = tok['end']
            continue
        if name in ('if','function','repeat','do'):
            depth += 1
            i = tok['end']
            continue
        if name in ('until','end'):
            depth -= 1
            i = tok['end']
            if depth == 0:
                return i
            continue
        i = tok['end']
    return -1

def evalex(expr):
    try:
        return eval(expr) if expr.strip() else None
    except:
        return None

def safebin(op, a, b):
    try:
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '*': return a * b
        if op == '/':
            if b == 0: return None
            return a / b
        if op == '%':
            if b == 0: return None
            return a % b
        if op == '^':
            if a == 0 and b <= 0: return None
            return a ** b
    except:
        return None
    return None

def foldpar(code):
    out = code
    changed = True
    while changed:
        changed = False
        i = 0
        nxt = ''
        while i < len(out):
            if out[i] == '"' or out[i] == "'":
                q = out[i]
                nxt += q
                i += 1
                while i < len(out) and out[i] != q:
                    if out[i] == '\\':
                        nxt += out[i]
                        i += 1
                        if i < len(out):
                            nxt += out[i]
                            i += 1
                    else:
                        nxt += out[i]
                        i += 1
                if i < len(out):
                    nxt += out[i]
                    i += 1
                continue
            if out[i] == '(':
                depth = 1
                j = i + 1
                inner = ''
                ok = True
                while j < len(out) and depth > 0:
                    if out[j] == '"' or out[j] == "'":
                        ok = False
                        break
                    if out[j] == '(':
                        depth += 1
                    elif out[j] == ')':
                        depth -= 1
                    if depth > 0:
                        inner += out[j]
                    j += 1
                if ok and depth == 0 and inner and any(c in '+-*/%^' for c in inner):
                    v = evalex(inner)
                    if v is not None and isinstance(v, (int, float)):
                        prev = nxt[-1] if nxt else ''
                        lit = str(v) if isinstance(v, int) else format(v, '.12g')
                        if prev and isid(prev):
                            nxt += '(' + lit + ')'
                        else:
                            nxt += lit
                        i = j
                        changed = True
                        continue
            nxt += out[i]
            i += 1
        out = nxt
    return out

def fmtnum(v):
    if not math.isfinite(v):
        return str(v)
    if v == 0:
        return '0'
    if isinstance(v, int) and abs(v) < 1e15:
        return str(v)
    rounded = round(v * 1e12) / 1e12
    if isinstance(rounded, int) and abs(rounded) < 1e15:
        return str(rounded)
    t = str(rounded)
    if 'e' in t or 'E' in t:
        return t
    if '.' in t:
        end = len(t)
        while end > 0 and t[end-1] == '0':
            end -= 1
        if end > 0 and t[end-1] == '.':
            end -= 1
        t = t[:end]
    return t

def rdnumat(s, i):
    if not (isdig(s[i]) or (s[i] == '.' and i+1 < len(s) and isdig(s[i+1]))):
        return None
    j = i
    if isdig(s[j]):
        while j < len(s) and isdig(s[j]):
            j += 1
    if s[j] == '.' and isdig(s[j+1] if j+1 < len(s) else ''):
        j += 1
        while j < len(s) and isdig(s[j]):
            j += 1
    if (s[j] == 'e' or s[j] == 'E') and ((isdig(s[j+1] if j+1 < len(s) else '')) or ((s[j+1] == '+' or s[j+1] == '-') and isdig(s[j+2] if j+2 < len(s) else ''))):
        j += 1
        if s[j] == '+' or s[j] == '-':
            j += 1
        while j < len(s) and isdig(s[j]):
            j += 1
    val = s[i:j]
    try:
        num = float(val)
    except:
        return None
    return {'value': val, 'end': j, 'num': num}

def foldbin(code):
    out = code
    changed = True
    while changed:
        changed = False
        i = 0
        nxt = ''
        while i < len(out):
            if out[i] == '"' or out[i] == "'":
                q = out[i]
                nxt += q
                i += 1
                while i < len(out) and out[i] != q:
                    if out[i] == '\\':
                        nxt += out[i]
                        i += 1
                        if i < len(out):
                            nxt += out[i]
                            i += 1
                    else:
                        nxt += out[i]
                        i += 1
                if i < len(out):
                    nxt += out[i]
                    i += 1
                continue
            left = rdnumat(out, i)
            if left and (i == 0 or not isid(out[i-1])):
                j = skws(out, left['end'])
                op = out[j] if j < len(out) else ''
                if op in '+-*/%^':
                    j = skws(out, j + 1)
                    right = rdnumat(out, j)
                    if right and (right['end'] >= len(out) or not isid(out[right['end']])):
                        v = safebin(op, left['num'], right['num'])
                        if v is not None:
                            nxt += fmtnum(v)
                            i = right['end']
                            changed = True
                            continue
            nxt += out[i]
            i += 1
        out = nxt
    return out

def foldcmp(code):
    out = code
    changed = True
    while changed:
        changed = False
        i = 0
        nxt = ''
        while i < len(out):
            if out[i] == '"' or out[i] == "'":
                q = out[i]
                nxt += q
                i += 1
                while i < len(out) and out[i] != q:
                    if out[i] == '\\':
                        nxt += out[i]
                        i += 1
                        if i < len(out):
                            nxt += out[i]
                            i += 1
                    else:
                        nxt += out[i]
                        i += 1
                if i < len(out):
                    nxt += out[i]
                    i += 1
                continue
            left = rdnumat(out, i)
            if left and (i == 0 or not isid(out[i-1])):
                j = skws(out, left['end'])
                op = None
                if out[j:j+2] in ('==','~=','<=','>='):
                    op = out[j:j+2]
                    j += 2
                elif out[j] in '<>':
                    op = out[j]
                    j += 1
                if op:
                    j = skws(out, j)
                    right = rdnumat(out, j)
                    if right and (right['end'] >= len(out) or not isid(out[right['end']])):
                        v = None
                        if op == '==': v = left['num'] == right['num']
                        elif op == '~=': v = left['num'] != right['num']
                        elif op == '<': v = left['num'] < right['num']
                        elif op == '>': v = left['num'] > right['num']
                        elif op == '<=': v = left['num'] <= right['num']
                        elif op == '>=': v = left['num'] >= right['num']
                        if v is not None:
                            nxt += 'true' if v else 'false'
                            i = right['end']
                            changed = True
                            continue
            nxt += out[i]
            i += 1
        out = nxt
    return out

def foldhash(code):
    out = ''
    i = 0
    while i < len(code):
        if code[i] == '"' or code[i] == "'":
            q = code[i]
            out += q
            i += 1
            while i < len(code) and code[i] != q:
                if code[i] == '\\':
                    out += code[i]
                    i += 1
                    if i < len(code):
                        out += code[i]
                        i += 1
                else:
                    out += code[i]
                    i += 1
            if i < len(code):
                out += code[i]
                i += 1
            continue
        if code[i] == '#' and (code[i+1] == '"' or code[i+1] == "'"):
            q = code[i+1]
            j = i + 2
            ln = 0
            while j < len(code) and code[j] != q:
                if code[j] == '\\':
                    j += 1
                j += 1
                ln += 1
            if code[j] == q:
                out += str(ln)
                i = j + 1
                continue
        out += code[i]
        i += 1
    return out

def replpln(s, a, b):
    if not a:
        return s
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
        if s.startswith(a, i):
            out += b
            i += len(a)
            continue
        out += s[i]
        i += 1
    return out

def simpbt(code):
    out = replpln(code, ' or_TRUE', '')
    out = replpln(out, 'true or ', 'true or_KEEP ')
    out = replpln(out, 'true or_KEEP ', 'true or ')
    return out

def foldbool(code):
    out = code
    guard = 0
    while guard < 40:
        prev = out
        out = replpln(out, '(true)', 'true')
        out = replpln(out, '(false)', 'false')
        out = replpln(out, 'true and ', '')
        out = replpln(out, ' and true', '')
        out = replpln(out, 'false or ', '')
        out = replpln(out, ' or false', '')
        out = replpln(out, 'false and ', 'false and_STOP ')
        out = replpln(out, ' or true', ' or_TRUE')
        out = replpln(out, 'and_STOP ', 'and ')
        out = simpbt(out)
        if out == prev:
            break
        guard += 1
    return out

def foldt(code):
    out = ''
    i = 0
    needle = '(function() return'
    while i < len(code):
        if code[i] == '"' or code[i] == "'":
            q = code[i]
            out += q
            i += 1
            while i < len(code) and code[i] != q:
                if code[i] == '\\':
                    out += code[i]
                    i += 1
                    if i < len(code):
                        out += code[i]
                        i += 1
                else:
                    out += code[i]
                    i += 1
            if i < len(code):
                out += code[i]
                i += 1
            continue
        if code.startswith(needle, i):
            j = skws(code, i + len(needle))
            num = rdnumat(code, j)
            if num:
                j = skws(code, num['end'])
                if code[j] == ';':
                    j = skws(code, j + 1)
                if code.startswith('end)()', j):
                    out += str(num['num'])
                    i = j + 6
                    continue
        out += code[i]
        i += 1
    return out

def foldconst(code):
    src = str(code)
    out = src
    out = foldhash(out)
    out = foldpar(out)
    out = foldbin(out)
    out = foldcmp(out)
    out = foldt(out)
    out = foldbool(out)
    out = foldpar(out)
    out = foldbin(out)
    return out

def colws(s):
    out = ''
    space = False
    for ch in s:
        if isws(ch):
            if not space and out:
                out += ' '
                space = True
        else:
            out += ch
            space = False
    return out.strip()

def strws(s):
    return ''.join(ch for ch in s if not isws(ch))
