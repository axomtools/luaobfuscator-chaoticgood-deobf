import re
from decode import decodeescaped, lualiteral
from clean import cleanlua
from extract import extractloadstring
from detect import matchcandidateold

def deobfuscateold(code):
    if not matchcandidateold(code):
        return None
    if re.search(r'local\s+function\s+v15\s*\(', code):
        return deobfuscateold_v15(code)
    else:
        return deobfuscateold_classic(code)

def deobfuscateold_classic(code):
    funcname = findxorfunc(code)
    if not funcname:
        return None
    decoded = _deobfuscate_old_classic(code, funcname)
    if not decoded:
        return None
    payload = extractloadstring(decoded)
    if payload:
        return cleanlua(payload)
    return cleanlua(decoded)

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

def _deobfuscate_old_classic(content, funcname):
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

def deobfuscateold_v15(code):
    match = re.search(r'return\s+v15\(\s*"([^"]+)"', code)
    if not match:
        return None
    blob = match.group(1)
    try:
        raw = decode_v15_blob(blob)
    except Exception:
        return None
    try:
        disasm = disassemble_vm(raw)
    except Exception:
        return None
    header = """--[[
Deobfuscated by Axomic LuaObfuscator OldObf Deobfuscator
Our Discord : https://discord.gg/Sps39CydcZ
Our YouTube : https://youtube.com/@axos0022
]]"""
    return header + "\n" + disasm

def decode_v15_blob(blob):
    if not blob.startswith('LOL!'):
        raise ValueError('no lol prefix')
    data = blob[4:]
    result = bytearray()
    repeat = None
    chunks = data.split('..')
    for chunk in chunks:
        if not chunk:
            continue
        if len(chunk) >= 2 and ord(chunk[1]) == 81:
            repeat = int(chunk[0])
            continue
        try:
            val = int(chunk, 16)
            byte_val = val & 0xFF
        except ValueError:
            continue
        if repeat is not None:
            result.extend(bytes([byte_val]) * repeat)
            repeat = None
        else:
            result.append(byte_val)
    return bytes(result)

def disassemble_vm(raw):
    cursor = 0
    lines = []
    lines.append(f"[+] Decoded {len(raw)} bytes")
    lines.append("")
    lines.append("Disassembly:")
    while cursor < len(raw):
        pos = cursor
        try:
            op = raw[cursor]; cursor += 1
            entry = f"[{pos:04X}] {op:02X}"
            if op <= 1:
                A = raw[cursor]; cursor += 1
                Bx = (raw[cursor] << 8) | raw[cursor+1] if cursor+1 < len(raw) else 0
                cursor += 2
                entry += f"  LOADK/MOVE A={A} Bx={Bx}"
            elif op == 2:
                A = raw[cursor]; cursor += 1
                Bx = (raw[cursor] << 8) | raw[cursor+1] if cursor+1 < len(raw) else 0
                cursor += 2
                entry += f"  GETGLOBAL A={A} Bx={Bx}"
            elif op == 3:
                A = raw[cursor]; cursor += 1
                B = raw[cursor]; cursor += 1
                C = raw[cursor]; cursor += 1
                entry += f"  CALL A={A} B={B} C={C}"
            elif op == 4:
                A = raw[cursor]; cursor += 1
                B = raw[cursor]; cursor += 1
                entry += f"  RETURN A={A} B={B}"
            elif op == 5:
                A = raw[cursor]; cursor += 1
                Bx = (raw[cursor] << 8) | raw[cursor+1] if cursor+1 < len(raw) else 0
                cursor += 2
                entry += f"  SETGLOBAL A={A} Bx={Bx}"
            else:
                entry += f"  UNKNOWN_{op}"
            lines.append(entry)
            if op == 4:
                break
        except IndexError:
            break
    return "\n".join(lines)
