import re
from decode import decodeescaped, lualiteral
from clean import cleanlua
from extract import extractloadstring
from detect import matchcandidateold

def findxorfunc(code):
    pat = re.compile(r'local\s+function\s+(v\d+)\s*\([^)]*\)\s*.*?bxor.*?end', re.DOTALL)
    m = pat.search(code)
    if m:
        return m.group(1)
    pat2 = re.compile(r'local\s+(v\d+)\s*=\s*function\s*\([^)]*\)\s*.*?bxor.*?end', re.DOTALL)
    m2 = pat2.search(code)
    if m2:
        return m2.group(1)
    return None

def deobfuscateold(code):
    if not matchcandidateold(code):
        return None
    funcname = findxorfunc(code)
    if not funcname:
        return None
    decoded = _deobfuscate_old(code, funcname)
    if not decoded:
        return None
    payload = extractloadstring(decoded)
    if payload:
        return cleanlua(payload)
    return cleanlua(decoded)

def _deobfuscate_old(content, funcname):
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
    out = re.sub(r'\blocal\s+{}\s*=\s*bit\.bxor\s*;?'.format(re.escape(funcname)), "", out)
    out = re.sub(r'\blocal\s+function\s+{}\s*\([^)]*\).*?end\s*'.format(re.escape(funcname)), "", out, flags=re.DOTALL)
    out = re.sub(r'\n{3,}', "\n\n", out).strip()
    return out if out else None
