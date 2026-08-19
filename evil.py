import struct
import re
from decode import decodeescaped
from foldconst import foldconst, skws, rdnum, isid, isdig, isws
from detect import matchcandidateevil

class reader:
    def __init__(self, buf):
        self.buf = buf
        self.pos = 0
    def remaining(self):
        return len(self.buf) - self.pos
    def byte(self):
        if self.pos >= len(self.buf):
            raise EOFError
        b = self.buf[self.pos]
        self.pos += 1
        return b
    def u16(self):
        return self.byte() + self.byte() * 256
    def u32(self):
        return self.byte() + self.byte()*256 + self.byte()*65536 + self.byte()*16777216
    def double(self):
        lo = self.u32()
        hi = self.u32()
        return struct.unpack('<d', struct.pack('<II', lo, hi))[0]
    def str(self):
        ln = self.u32()
        if ln == 0:
            return ''
        if self.pos + ln > len(self.buf):
            raise EOFError
        s = self.buf[self.pos:self.pos+ln].decode('latin1')
        self.pos += ln
        return s

def bitfield(n, start, end=None):
    if end is None:
        return (n >> (start-1)) & 1
    return (n >> (start-1)) & ((1 << (end - start + 1)) - 1)

def despr(r):
    constants = [None]
    instructions = [None]
    prototypes = []
    constcount = r.u32()
    for i in range(1, constcount+1):
        t = r.byte()
        if t == 1:
            constants.append(r.byte() != 0)
        elif t == 2:
            constants.append(r.double())
        elif t == 3:
            constants.append(r.str())
        else:
            constants.append(None)
    params = r.byte()
    instcount = r.u32()
    for i in range(1, instcount+1):
        flag = r.byte()
        if bitfield(flag, 1, 1) == 0:
            mode = bitfield(flag, 2, 3)
            kflags = bitfield(flag, 4, 6)
            opcode = r.u16()
            A = r.u16()
            B = None
            C = None
            if mode == 0:
                B = r.u16()
                C = r.u16()
            elif mode == 1:
                B = r.u32()
            elif mode == 2:
                B = r.u32() - 65536
            elif mode == 3:
                B = r.u32() - 65536
                C = r.u16()
            iska = bitfield(kflags, 1, 1) == 1
            iskb = bitfield(kflags, 2, 2) == 1
            iskc = bitfield(kflags, 3, 3) == 1
            if iska:
                A = constants[A]
            if iskb:
                B = constants[B]
            if iskc:
                C = constants[C]
            instructions.append({
                'opcode': opcode, 'A': A, 'B': B, 'C': C, 'mode': mode,
                'kflags': kflags, 'iska': iska, 'iskb': iskb, 'iskc': iskc,
                'rawA': A, 'rawB': B, 'rawC': C, 'flag': flag
            })
        else:
            instructions.append({'skipped': True, 'flag': flag})
    protocount = r.u32()
    for i in range(protocount):
        prototypes.append(despr(r))
    return {'params': params, 'constants': constants, 'instructions': instructions, 'prototypes': prototypes}

def decrle(decrypted, sentinel=0x4f):
    buf = decrypted if isinstance(decrypted, bytes) else decrypted.encode('latin1')
    if buf[:4].decode('latin1') != 'LOL!':
        raise ValueError('not lol')
    s = buf[4:].decode('latin1')
    out = []
    i = 0
    rep = None
    while i + 1 < len(s):
        a = ord(s[i])
        b = ord(s[i+1])
        i += 2
        if b == sentinel:
            rep = int(chr(a), 10)
            if rep is None:
                raise ValueError('rle')
            continue
        byte = int(chr(a) + chr(b), 16)
        if rep is not None:
            for _ in range(rep):
                out.append(byte)
            rep = None
        else:
            out.append(byte)
    return bytes(out)

def findv7calls(src):
    results = []
    tag = 'v7("'
    from_ = 0
    while True:
        at = src.find(tag, from_)
        if at < 0:
            break
        try:
            i = at + len(tag)
            if src[i-1] != '"':
                from_ = at + len(tag)
                continue
            content = ''
            while i < len(src) and src[i] != '"':
                if src[i] == '\\':
                    content += src[i]
                    i += 1
                    if i < len(src):
                        content += src[i]
                        i += 1
                else:
                    content += src[i]
                    i += 1
            if i >= len(src) or src[i] != '"':
                from_ = at + len(tag)
                continue
            end = i + 1
            if end+1 >= len(src) or src[end] != ',' or src[end+1] != '"':
                from_ = end
                continue
            j = end + 2
            if src[j-1] != '"':
                from_ = end
                continue
            key = ''
            while j < len(src) and src[j] != '"':
                if src[j] == '\\':
                    key += src[j]
                    j += 1
                    if j < len(src):
                        key += src[j]
                        j += 1
                else:
                    key += src[j]
                    j += 1
            if j >= len(src) or src[j] != '"':
                from_ = end
                continue
            key_end = j+1
            if key_end < len(src) and src[key_end] == ')':
                results.append({
                    'index': at,
                    'text': content,
                    'decrypted': decodeescaped(content).encode('latin1'),
                    'key': decodeescaped(key).encode('latin1'),
                    'end': key_end
                })
                from_ = key_end + 1
            else:
                from_ = end
        except:
            from_ = at + len(tag)
    return results

def guesssentinel(decrypted):
    buf = decrypted if isinstance(decrypted, bytes) else decrypted.encode('latin1')
    s = buf[4:]
    votes = {}
    for i in range(0, min(len(s)-1, 200), 2):
        if i+1 < len(s):
            a = s[i]
            b = s[i+1]
            if not ((48 <= a <= 57) or (65 <= a <= 70) or (97 <= a <= 102)):
                if 48 <= a <= 57:
                    votes[b] = votes.get(b, 0) + 1
    best = 0x4f
    bestn = 0
    for b, n in votes.items():
        if n > bestn:
            best = b
            bestn = n
    return best

def xtrbc(source):
    calls = findv7calls(source)
    payloads = [c for c in calls if c['text'].startswith('LOL!')]
    if not payloads:
        at = source.find('"LOL!')
        if at >= 0:
            i = at + 1
            q = source[i-1]
            if q == '"':
                content = ''
                while i < len(source) and source[i] != q:
                    if source[i] == '\\':
                        content += source[i]
                        i += 1
                        if i < len(source):
                            content += source[i]
                            i += 1
                    else:
                        content += source[i]
                        i += 1
                if i < len(source) and source[i] == q:
                    payloads.append({'text': content, 'decrypted': content.encode('latin1')})
    if not payloads:
        raise ValueError('no lol payload')
    payload = payloads[-1]
    sentinel = guesssentinel(payload['decrypted'])
    raw = decrle(payload['decrypted'], sentinel)
    r = reader(raw)
    root = despr(r)
    return {'payload': payload, 'raw': raw, 'root': root, 'sentinel': sentinel,
            'bytesread': r.pos, 'bytestotal': len(raw)}

def reconstruct_lua(root, opmap, closelocalop):
    lines = []
    def walk(p, name, indent):
        lines.append(f"{indent}function {name}(" + ",".join([f"r{i}" for i in range(p['params'])]) + ")")
        for ins in p['instructions']:
            if ins.get('skipped'):
                continue
            opname = opmap.get(ins['opcode'], {}).get('name', 'UNKNOWN')
            a = ins['A']
            b = ins['B']
            c = ins['C']
            if opname == 'MOVE':
                lines.append(f"{indent}  r{a} = r{b}")
            elif opname == 'LOADK':
                lines.append(f"{indent}  r{a} = {repr(b)}")
            elif opname == 'LOADBOOL':
                lines.append(f"{indent}  r{a} = {'true' if b else 'false'}")
            elif opname == 'LOADNIL':
                lines.append(f"{indent}  r{a} = nil")
            elif opname == 'GETUPVAL':
                lines.append(f"{indent}  r{a} = up{b}")
            elif opname == 'GETGLOBAL':
                lines.append(f"{indent}  r{a} = _ENV[{repr(b)}]")
            elif opname == 'GETTABLE':
                lines.append(f"{indent}  r{a} = r{b}[{repr(c) if isinstance(c,(str,bool)) else f'r{c}'}]")
            elif opname == 'SETGLOBAL':
                lines.append(f"{indent}  _ENV[{repr(b)}] = r{a}")
            elif opname == 'SETUPVAL':
                lines.append(f"{indent}  up{b} = r{a}")
            elif opname == 'SETTABLE':
                lines.append(f"{indent}  r{a}[{repr(b) if isinstance(b,(str,bool)) else f'r{b}'}] = {repr(c) if isinstance(c,(str,bool)) else f'r{c}'}")
            elif opname == 'NEWTABLE':
                lines.append(f"{indent}  r{a} = {{}}")
            elif opname == 'SELF':
                lines.append(f"{indent}  r{a+1} = r{b}; r{a} = r{b}[{repr(c) if isinstance(c,(str,bool)) else f'r{c}'}]")
            elif opname in ('ADD','SUB','MUL','DIV','MOD','POW'):
                op = {'ADD':'+','SUB':'-','MUL':'*','DIV':'/','MOD':'%','POW':'^'}[opname]
                lines.append(f"{indent}  r{a} = r{b} {op} r{c}")
            elif opname == 'UNM':
                lines.append(f"{indent}  r{a} = -r{b}")
            elif opname == 'NOT':
                lines.append(f"{indent}  r{a} = not r{b}")
            elif opname == 'LEN':
                lines.append(f"{indent}  r{a} = #r{b}")
            elif opname == 'CONCAT':
                lines.append(f"{indent}  r{a} = r{b} .. r{c}")
            elif opname == 'JMP':
                lines.append(f"{indent}  goto L{b}")
            elif opname in ('EQ','LT','LE'):
                sym = {'EQ':'==','LT':'<','LE':'<='}[opname]
                lines.append(f"{indent}  if r{a} {sym} {repr(c) if isinstance(c,(str,bool)) else f'r{c}'} then else goto L{b} end")
            elif opname == 'TEST':
                lines.append(f"{indent}  if r{a} then else goto L{b} end")
            elif opname == 'CALL':
                lines.append(f"{indent}  r{a} = r{a}()")
            elif opname == 'TAILCALL':
                lines.append(f"{indent}  return r{a}()")
            elif opname == 'RETURN':
                lines.append(f"{indent}  return r{a}")
            elif opname == 'CLOSURE':
                lines.append(f"{indent}  r{a} = {repr(b)}")
            elif opname == 'SETLIST':
                lines.append(f"{indent}  r{a} = {{}}")
            else:
                lines.append(f"{indent}  -- unknown op {opname}")
        for idx, child in enumerate(p['prototypes']):
            if child:
                walk(child, f"{name}_f{idx}", indent + "  ")
        lines.append(f"{indent}end")
    walk(root, 'main', '')
    return "\n".join(lines)

def findpayload(root):
    if root['prototypes']:
        for p in root['prototypes']:
            if p and len([i for i in p['instructions'] if not i.get('skipped')]) > 2:
                return p
    return root

def deobfuscatechaoticevil(code):
    if not matchcandidateevil(code):
        return None
    try:
        bc = xtrbc(code)
    except:
        return None
    root = bc['root']
    opmap = {
        0: {'name': 'MOVE'},
        1: {'name': 'LOADK'},
        2: {'name': 'LOADBOOL'},
        3: {'name': 'LOADNIL'},
        4: {'name': 'GETUPVAL'},
        5: {'name': 'GETGLOBAL'},
        6: {'name': 'GETTABLE'},
        7: {'name': 'SETGLOBAL'},
        8: {'name': 'SETUPVAL'},
        9: {'name': 'SETTABLE'},
        10: {'name': 'NEWTABLE'},
        11: {'name': 'SELF'},
        12: {'name': 'ADD'},
        13: {'name': 'SUB'},
        14: {'name': 'MUL'},
        15: {'name': 'DIV'},
        16: {'name': 'MOD'},
        17: {'name': 'POW'},
        18: {'name': 'UNM'},
        19: {'name': 'NOT'},
        20: {'name': 'LEN'},
        21: {'name': 'CONCAT'},
        22: {'name': 'JMP'},
        23: {'name': 'EQ'},
        24: {'name': 'LT'},
        25: {'name': 'LE'},
        26: {'name': 'TEST'},
        27: {'name': 'CALL'},
        28: {'name': 'TAILCALL'},
        29: {'name': 'RETURN'},
        30: {'name': 'CLOSURE'},
        31: {'name': 'SETLIST'},
    }
    payload = findpayload(root)
    lua = reconstruct_lua(payload, opmap, None)
    lua = foldconst(lua)
    lua = '\n'.join(line.rstrip() for line in lua.splitlines() if line.strip())
    header = """--[[
Deobfuscated by Axomic LuaObfuscator ChaoticEvil Deobfuscator
Our Discord : https://discord.gg/Sps39CydcZ
Our YouTube : https://youtube.com/@axos0022
]]"""
    return header + "\n" + lua.strip()
