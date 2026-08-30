import re
from decode import decodeescaped, lualiteral
from clean import cleanlua
from extract import extractloadstring
from detect import matchcandidate

def findxorfunc(code):
    pat = re.compile(r'local\s+function\s+(\w+)\s*\([^)]*\)\s*.*?bxor.*?end', re.DOTALL)
    m = pat.search(code)
    if m:
        return m.group(1)
    pat2 = re.compile(r'local\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*.*?bxor.*?end', re.DOTALL)
    m2 = pat2.search(code)
    if m2:
        return m2.group(1)
    return None

def deobfuscatechaoticgood(code):
    if not code or not isinstance(code, str):
        return None
    if not matchcandidate(code):
        return None
    funcname = findxorfunc(code)
    if not funcname:
        return None
    decoded = _deobfuscate(code, funcname)
    if not decoded:
        return None
    payload = extractloadstring(decoded)
    if payload:
        result = cleanlua(payload)
    else:
        result = cleanlua(decoded)
    return result

def _deobfuscate(content, funcname):
    pat = re.compile(r'{}\s*\(\s*"((?:\\.|[^"])*)"\s*,\s*"((?:\\.|[^"])*)"\s*\)'.format(re.escape(funcname)))
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
    out = re.sub(r'\blocal\s+{}\s*=\s*string\.(?:char|byte|sub)\s*;?'.format(re.escape(funcname)), "", out)
    out = re.sub(r'\blocal\s+{}\s*=\s*bit32\s+or\s+bit\s*;?'.format(re.escape(funcname)), "", out)
    out = re.sub(r'\blocal\s+{}\s*=\s*{}\.bxor\s*;?'.format(re.escape(funcname), re.escape(funcname)), "", out)
    out = re.sub(r'\blocal\s+{}\s*=\s*table\.(?:concat|insert)\s*;?'.format(re.escape(funcname)), "", out)
    out = re.sub(r'\blocal\s+function\s+{}\s*\([^)]*\).*?end\s*'.format(re.escape(funcname)), "", out, flags=re.DOTALL)
    out = re.sub(r'\n{3,}', "\n\n", out).strip()
    printcalls = re.findall(r'\bprint\s*\([^;\n]*\)', out)
    if printcalls:
        return "\n".join(printcalls)
    return out if out else None

def deobfuscatechaotic(code):
    return deobfuscatechaoticgood(code)
