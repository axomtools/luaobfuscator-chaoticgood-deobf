import re
from decode import decodeescaped, lualiteral
from clean import cleanlua
from extract import extractloadstring
from detect import matchcandidate

def deobfuscatechaoticgood(code):
    if not code or not isinstance(code, str):
        return None
    if not re.search(r'v7\s*\(\s*"', code) and not re.search(r'local\s+function\s+\w+\s*\(\s*\w+\s*\)\s*return\s+\w+\[\s*\w+\s*[-+]\s*\(\s*\d+\s*[-+]\s*\d+\s*\)\s*\]\s*end', code):
        return None
    decoded = _deobfuscate(code)
    if not decoded:
        return None
    decoded = removedeadloops(decoded)
    payload = extractloadstring(decoded)
    if payload:
        result = cleanlua(payload)
    else:
        result = cleanlua(decoded)
    result = beautifylua(result)
    return result

def removedeadloops(code):
    lines = code.splitlines()
    newlines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r'^for\s+\w+\s*=\s*0,\s*255\s+do\s*$', line, re.IGNORECASE):
            depth = 1
            j = i + 1
            while j < len(lines) and depth > 0:
                l = lines[j].strip()
                if re.match(r'^for\s+', l, re.IGNORECASE) or re.match(r'^while\s+', l, re.IGNORECASE) or re.match(r'^if\s+', l, re.IGNORECASE) or re.match(r'^function\s+', l, re.IGNORECASE):
                    depth += 1
                elif re.match(r'^end\s*$', l, re.IGNORECASE):
                    depth -= 1
                j += 1
            i = j
            continue
        if re.match(r'^while\s+true\s+do\s*$', line, re.IGNORECASE):
            depth = 1
            j = i + 1
            blocklines = [line]
            while j < len(lines) and depth > 0:
                blocklines.append(lines[j])
                l = lines[j].strip()
                if re.match(r'^while\s+true\s+do\s*$', l, re.IGNORECASE) or re.match(r'^if\s+', l, re.IGNORECASE) or re.match(r'^for\s+', l, re.IGNORECASE) or re.match(r'^function\s+', l, re.IGNORECASE):
                    depth += 1
                elif re.match(r'^end\s*$', l, re.IGNORECASE):
                    depth -= 1
                j += 1
            blocktext = '\n'.join(blocklines)
            if re.search(r'\b(loadstring|HttpGet|Instance\.new|game\.|workspace\.|print\()', blocktext):
                newlines.extend(blocklines)
            i = j
            continue
        newlines.append(lines[i])
        i += 1
    return '\n'.join(newlines)

def beautifylua(code):
    if not code:
        return code
    lines = code.splitlines()
    indent = 0
    indentsize = 4
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append('')
            continue
        if re.match(r'^(end|until|elseif|else)\b', stripped):
            indent = max(0, indent - 1)
        result.append(' ' * (indent * indentsize) + stripped)
        if re.match(r'^(function|if|for|while|repeat|do)\b', stripped):
            indent += 1
        if re.search(r'\bthen\s*$', stripped):
            indent += 1
        if stripped.endswith('{'):
            indent += 1
        if stripped.startswith('}'):
            indent = max(0, indent - 1)
    return '\n'.join(result)

def _deobfuscate(content):
    pat = re.compile(r'v7\s*\(\s*"((?:\\.|[^"])*)"\s*,\s*"((?:\\.|[^"])*)"\s*\)')
    matches = list(pat.finditer(content))
    if not matches:
        return None
    reps = {}
    for m in matches:
        enc = decodeescaped(m.group(1)).encode("latin1", errors="ignore")
        key = decodeescaped(m.group(2)).encode("latin1", errors="ignore")
        if not enc or not key:
            continue
        dec = bytes(
            b ^ key[i % len(key)] for i, b in enumerate(enc, 1)
        ).decode("utf-8", errors="replace")
        reps[m.group(0)] = lualiteral(dec)
    if not reps:
        return None
    out = content
    for src, dst in reps.items():
        out = out.replace(src, dst)
    out = out.strip()
    out = re.sub(r'\blocal\s+v\d+\s*=\s*string\.(?:char|byte|sub)\s*;?', "", out)
    out = re.sub(r'\blocal\s+v\d+\s*=\s*bit32\s+or\s+bit\s*;?', "", out)
    out = re.sub(r'\blocal\s+v\d+\s*=\s*v\d+\.bxor\s*;?', "", out)
    out = re.sub(r'\blocal\s+v\d+\s*=\s*table\.(?:concat|insert)\s*;?', "", out)
    out = re.sub(r'\blocal\s+function\s+v7\s*\([^)]*\).*?end\s*', "", out, flags=re.DOTALL)
    out = re.sub(r'\n{3,}', "\n\n", out).strip()
    printcalls = re.findall(r'\bprint\s*\([^;\n]*\)', out)
    if printcalls:
        return "\n".join(printcalls)
    return out if out else None

def deobfuscatechaotic(code):
    return deobfuscatechaoticgood(code)
