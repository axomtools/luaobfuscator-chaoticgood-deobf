import re
import struct
import math
import json
from foldconst import foldconst, isws, isdig, isid0, isid, skws, rdid, rdnum, skstr, nextkw, wdat, findwd, findblkend, colws, strws

class bufreader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
    def remaining(self):
        return len(self.data) - self.pos
    def byte(self):
        if self.pos >= len(self.data):
            raise EOFError
        b = self.data[self.pos]
        self.pos += 1
        return b
    def u16(self):
        return self.byte() | (self.byte() << 8)
    def u32(self):
        return self.byte() | (self.byte() << 8) | (self.byte() << 16) | (self.byte() << 24)
    def double(self):
        lo = self.u32()
        hi = self.u32()
        return struct.unpack('<d', struct.pack('<II', lo, hi))[0]
    def str(self):
        ln = self.u32()
        if ln == 0:
            return ''
        if self.pos + ln > len(self.data):
            raise EOFError
        s = self.data[self.pos:self.pos+ln].decode('latin1')
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
                A = constants[A] if A < len(constants) else None
            if iskb:
                B = constants[B] if B < len(constants) else None
            if iskc:
                C = constants[C] if C < len(constants) else None
            instructions.append({
                'opcode': opcode, 'A': A, 'B': B, 'C': C, 'mode': mode,
                'kflags': kflags, 'iska': iska, 'iskb': iskb, 'iskc': iskc,
                'rawA': A, 'rawB': B, 'rawC': C, 'flag': flag
            })
        else:
            instructions.append({'skipped': True, 'flag': flag})
    protocount = r.u32()
    for _ in range(protocount):
        try:
            prototypes.append(despr(r))
        except:
            prototypes.append(None)
    return {'params': params, 'constants': constants, 'instructions': instructions, 'prototypes': prototypes}

def decrle(decrypted, sentinel=0x4f):
    buf = decrypted if isinstance(decrypted, bytes) else decrypted.encode('latin1')
    if buf[:4].decode('latin1') != 'LOL!':
        raise ValueError('not lol')
    s = buf[4:].decode('latin1')
    out = bytearray()
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
            out.extend(bytes([byte]) * rep)
            rep = None
        else:
            out.append(byte)
    return bytes(out)

def trydecrle(decrypted, sentinels=(0x4f,0x51,0x40,0x21,0x23,0x5a)):
    last_err = None
    for s in sentinels:
        try:
            return decrle(decrypted, s)
        except Exception as e:
            last_err = e
            continue
    raise last_err or ValueError('no sentinel works')

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
                    'decrypted': content.encode('latin1'),
                    'end': key_end
                })
                from_ = key_end + 1
            else:
                from_ = end
        except:
            from_ = at + len(tag)
    return results

def findlol(src):
    calls = findv7calls(src)
    for c in calls:
        if c['text'].startswith('LOL!'):
            return c
    pat = re.compile(r'v\d+\s*\(\s*(["\'])(LOL!.*?)\1')
    m = pat.search(src)
    if m:
        return {'text': m.group(2), 'decrypted': m.group(2).encode('latin1')}
    at = src.find('"LOL!')
    if at >= 0:
        i = at + 1
        q = src[i-1]
        if q == '"':
            content = ''
            while i < len(src) and src[i] != q:
                if src[i] == '\\':
                    content += src[i]
                    i += 1
                    if i < len(src):
                        content += src[i]
                        i += 1
                else:
                    content += src[i]
                    i += 1
            if i < len(src) and src[i] == q:
                return {'text': content, 'decrypted': content.encode('latin1')}
    at = src.find("'LOL!")
    if at >= 0:
        i = at + 1
        q = src[i-1]
        if q == "'":
            content = ''
            while i < len(src) and src[i] != q:
                if src[i] == '\\':
                    content += src[i]
                    i += 1
                    if i < len(src):
                        content += src[i]
                        i += 1
                else:
                    content += src[i]
                    i += 1
            if i < len(src) and src[i] == q:
                return {'text': content, 'decrypted': content.encode('latin1')}
    return None

def xtrbc(source):
    lol = findlol(source)
    if not lol:
        raise ValueError('no lol payload')
    raw = trydecrle(lol['decrypted'])
    r = bufreader(raw)
    root = despr(r)
    return {'payload': lol, 'raw': raw, 'root': root, 'bytesread': r.pos, 'bytestotal': len(raw)}

def isbin(s):
    if not isinstance(s, str) or len(s) < 2:
        return False
    bad = sum(1 for c in s if ord(c) < 9 or (13 < ord(c) < 32) or ord(c) >= 127)
    return bad / len(s) >= 0.3

def isidstr(s):
    if not isinstance(s, str) or not s or len(s) > 64:
        return False
    if not (s[0].isalpha() or s[0] == '_'):
        return False
    return all(c.isalnum() or c == '_' for c in s)

def isgname(s):
    return isinstance(s, str) and s and not isbin(s) and isidstr(s)

def hascallsoon(ins, proto):
    if not proto or '_index' not in ins:
        return False
    start = ins['_index']
    for i in range(start+1, min(start+8, len(proto.get('instructions', [])))):
        n = proto['instructions'][i] if i < len(proto['instructions']) else None
        if not n or n.get('skipped'):
            continue
        if (n.get('mode') == 0 or n.get('mode') is None) and n.get('A') == ins['A'] and not n.get('iskb') and not n.get('iskc'):
            if isinstance(n.get('B'), (int, float)) or n.get('B') is None:
                return True
        if n.get('mode') == 2:
            return False
    return False

def feedsglobaluse(ins, proto):
    if not proto or '_index' not in ins:
        return False
    if hascallsoon(ins, proto):
        return True
    start = ins['_index']
    for i in range(start+1, min(start+8, len(proto.get('instructions', [])))):
        n = proto['instructions'][i] if i < len(proto['instructions']) else None
        if not n or n.get('skipped'):
            continue
        if n.get('mode') == 2:
            return False
        if (n.get('mode') == 0 or n.get('mode') is None) and n.get('iskc') and isinstance(n.get('B'), (int, float)) and n['B'] == ins['A']:
            return True
        if n.get('A') == ins['A'] and n.get('mode') == 1 and n.get('iskb'):
            continue
        if isinstance(n.get('A'), (int, float)) and n['A'] == ins['A']:
            continue
        break
    return False

def lkargmv(ins, proto):
    if not proto or '_index' not in ins:
        return False
    idx = ins['_index']
    for i in range(idx+1, min(idx+4, len(proto.get('instructions', [])))):
        n = proto['instructions'][i] if i < len(proto['instructions']) else None
        if not n or n.get('skipped'):
            continue
        if n.get('mode') == 2:
            return False
        if (n.get('mode') == 0 or n.get('mode') is None) and not n.get('iskb') and not n.get('iskc') and isinstance(n.get('B'), (int, float)):
            if n['A'] == ins['A'] - 1 and n['B'] == 2:
                return True
            if n['A'] == ins['A'] and n['B'] >= 2:
                return False
        break
    for i in range(idx-1, max(1, idx-4)-1, -1):
        n = proto['instructions'][i] if i < len(proto['instructions']) else None
        if not n or n.get('skipped'):
            continue
        if n.get('mode') == 1 and n.get('iskb') and n['A'] == ins['A'] - 1:
            return True
        break
    return False

def lkcall(ins, proto):
    if not proto or '_index' not in ins:
        return False
    bnum = ins['B'] if isinstance(ins.get('B'), (int, float)) else -1
    idx = ins['_index']
    for i in range(idx-1, max(1, idx-8)-1, -1):
        n = proto['instructions'][i] if i < len(proto['instructions']) else None
        if not n or n.get('skipped'):
            continue
        if n['A'] != ins['A']:
            if n.get('mode') == 1 and n.get('iskb'):
                continue
            if n.get('mode') == 0 and not n.get('iskb') and not n.get('iskc'):
                continue
            if n.get('mode') == 2:
                return False
            continue
        if n.get('mode') == 0 and n.get('iskc'):
            return True
        if n.get('mode') == 1 and n.get('iskb'):
            return True
        if n.get('mode') == 3:
            return True
        break
    if bnum >= 2:
        argloads = 0
        for i in range(idx-1, max(1, idx-8)-1, -1):
            n = proto['instructions'][i] if i < len(proto['instructions']) else None
            if not n or n.get('skipped'):
                continue
            if n.get('mode') == 2:
                break
            if isinstance(n.get('A'), (int, float)) and n['A'] > ins['A'] and n['A'] <= ins['A'] + min(bnum, 8) - 1:
                if n.get('mode') == 1 and n.get('iskb'):
                    argloads += 1
                if n.get('mode') == 0 and n.get('iskc'):
                    argloads += 1
            if n['A'] == ins['A'] and n.get('mode') == 1 and n.get('iskb'):
                return True
        if argloads >= 1:
            return True
    return False

def lkupfollow(ins, proto, closelocalop, opmap):
    if not proto or not isinstance(ins.get('B'), (int, float)) or not isinstance(ins.get('C'), (int, float)):
        return False
    if ins['C'] <= 0 or ins['C'] > 32:
        return False
    pidx = int(ins['B'])
    if pidx < 0 or pidx >= len(proto.get('prototypes', [])) or not proto['prototypes'][pidx]:
        return False
    idx = ins['_index']
    for u in range(ins['C']):
        nxt = proto['instructions'][idx + 1 + u] if idx + 1 + u < len(proto.get('instructions', [])) else None
        if not nxt or nxt.get('skipped'):
            return False
        if closelocalop is not None and nxt.get('opcode') == closelocalop:
            continue
        n = (opmap and opmap.get(nxt.get('opcode'), {}).get('name', '')) or ''
        if n in ('MOVE','GETUPVAL'):
            continue
        if nxt.get('mode') == 0 and not nxt.get('iskb') and not nxt.get('iskc') and isinstance(nxt.get('B'), (int, float)):
            continue
        return False
    return True

def shpguess(ins, proto, closelocalop, opmap):
    if not ins or ins.get('skipped'):
        return None
    mode = ins.get('mode')
    A = ins.get('A')
    B = ins.get('B')
    C = ins.get('C')
    iskb = ins.get('iskb', False)
    iskc = ins.get('iskc', False)
    bnum = isinstance(B, (int, float))
    cnum = isinstance(C, (int, float))
    cstr = isinstance(C, str)
    if mode == 2 and bnum:
        return {'name': 'JMP', 'conf': 95}
    if mode == 3 and bnum and cnum is not None:
        pidx = int(B) if bnum else -1
        if pidx >= 0 and pidx < len(proto.get('prototypes', [])) and proto['prototypes'][pidx] and C >= 0 and C <= 255 and not iskc and not iskb:
            return {'name': 'CLOSURE', 'conf': 90}
        if iskc or iskb:
            return {'name': 'EQ', 'conf': 55}
        if proto and '_index' in ins:
            nxt = proto['instructions'][ins['_index'] + 1] if ins['_index'] + 1 < len(proto.get('instructions', [])) else None
            if nxt and not nxt.get('skipped') and nxt.get('mode') == 2 and isinstance(nxt.get('B'), (int, float)):
                return {'name': 'EQ', 'conf': 75}
        if bnum and B > 0 and proto and B < len(proto.get('instructions', [])) and C == 0:
            return {'name': 'JMP', 'conf': 55}
        return {'name': 'EQ', 'conf': 50}
    if mode == 1 and iskb and C is None:
        if isinstance(B, str):
            if isbin(B):
                return {'name': 'LOADK', 'conf': 95}
            if isidstr(B) and feedsglobaluse(ins, proto):
                return {'name': 'GETGLOBAL', 'conf': 90}
            return {'name': 'LOADK', 'conf': 88}
        if isinstance(B, bool):
            return {'name': 'LOADBOOL', 'conf': 90}
        if bnum:
            return {'name': 'LOADK', 'conf': 85}
        if B is None:
            return {'name': 'LOADNIL', 'conf': 70}
    if mode == 0 and not iskb and not iskc and bnum and (C == 0 or C is None) and B >= A and B <= A + 32:
        if lkcall(ins, proto):
            return {'name': 'CALL', 'conf': 80}
        if B == A:
            return {'name': 'LOADNIL', 'conf': 70}
        if B - A <= 8:
            return {'name': 'LOADNIL', 'conf': 55}
    if mode == 0 and iskb and iskc:
        return {'name': 'SETTABLE', 'conf': 92}
    if mode == 0 and iskc and not iskb and bnum:
        if A == B and cstr and isidstr(C) and hascallsoon(ins, proto):
            return {'name': 'SELF', 'conf': 88}
        return {'name': 'GETTABLE', 'conf': 90}
    if mode == 0 and iskb and not iskc and (bnum or isinstance(B, str) or isinstance(B, bool)) and cnum:
        return {'name': 'ADD', 'conf': 45}
    if bnum and cnum and lkupfollow(ins, proto, closelocalop, opmap):
        return {'name': 'CLOSURE', 'conf': 80}
    if mode == 0 and not iskb and not iskc and bnum:
        if B == 0 and cnum and C >= 1 and C <= 32:
            return {'name': 'CALL', 'conf': 72}
        if B == 0 and (C == 0 or C is None):
            return {'name': 'MOVE', 'conf': 25}
        if B == 0 and C == 1:
            return {'name': 'CALL', 'conf': 50}
        if B == 1 and (C == 0 or C is None or C == 1):
            if lkargmv(ins, proto):
                return {'name': 'MOVE', 'conf': 70}
            return {'name': 'CALL', 'conf': 48}
        if B >= 2 and B <= 32:
            if lkcall(ins, proto):
                return {'name': 'CALL', 'conf': 75}
            if C is None or C == 0 or (cnum and C >= 1 and C <= 32):
                return {'name': 'CALL', 'conf': 55}
        if B <= 255 and (C is None or C == 0):
            return {'name': 'MOVE', 'conf': 50}
    return None

def iscmpop(n):
    return n in ('EQ','LT','LE','TEST')

def isstrongmap(n):
    return n in ('FORLOOP','FORPREP','SETTABLE','NEWTABLE','CONCAT','SETGLOBAL','CLOSURE','SETUPVAL','GETUPVAL')

def isweakmap(n):
    return n in ('UNKNOWN','CALL','SETLIST','SELF','TAILCALL','EQ','LT','LE','TEST','RETURN','MOVE')

def ismodebound(n):
    return n in ('CLOSURE','JMP','GETGLOBAL','LOADK','GETTABLE','SETTABLE','SELF')

def prefnm(mapname, ins, proto, closelocalop, opmap):
    shape = shpguess(ins, proto, closelocalop, opmap)
    name = mapname or 'UNKNOWN'
    if shape and shape['conf'] >= 70 and shape['name'] != 'UNKNOWN':
        protect = isstrongmap(mapname) and shape['name'] != mapname and not (mapname == 'SETTABLE' and shape['name'] == 'GETTABLE')
        retmis = mapname == 'RETURN' and shape['name'] in ('LOADK','LOADNIL','GETGLOBAL','JMP','MOVE','CALL')
        if retmis:
            name = shape['name']
        elif protect:
            name = mapname
        elif not (shape['name'] == 'CALL' and mapname in ('CONCAT','SETGLOBAL','TFORLOOP')):
            name = shape['name']
    elif shape and shape['name'] != 'UNKNOWN' and name == 'UNKNOWN':
        name = shape['name']
    elif shape and shape['name'] != 'UNKNOWN' and shape['conf'] >= 55 and isweakmap(name) and ismodebound(shape['name']):
        name = shape['name']
    if mapname == 'CONCAT':
        name = 'CONCAT'
    if mapname == 'SETGLOBAL' and ins.get('mode') == 1:
        name = 'SETGLOBAL'
    if mapname == 'SETTABLE':
        name = 'SETTABLE'
    if mapname == 'GETTABLE':
        name = 'GETTABLE'
    if mapname in ('FORLOOP','FORPREP'):
        name = mapname
    if mapname == 'RETURN' and ins.get('mode') == 0 and isinstance(ins.get('B'), (int, float)) and ins['B'] >= 2 and not ins.get('iskb') and not ins.get('iskc'):
        name = 'RETURN'
    if mapname == 'MOVE' and ins.get('mode') == 0 and not ins.get('iskb') and not ins.get('iskc') and isinstance(ins.get('B'), (int, float)) and ins['B'] <= 255:
        if not (shape and shape['name'] == 'CALL' and shape['conf'] >= 85 and lkcall(ins, proto)):
            name = 'MOVE'
    if mapname == 'TFORLOOP':
        name = 'TFORLOOP'
    if mapname in ('LT','LE','EQ'):
        if ins.get('mode') == 3 or iscmpop(mapname):
            name = mapname
    if name == 'TFORLOOP' and ins.get('mode') == 0 and isinstance(ins.get('B'), (int, float)) and isinstance(ins.get('A'), (int, float)) and ins['B'] >= 1 and (ins.get('C') == 0 or ins.get('C') == 1 or ins.get('C') is None or (isinstance(ins.get('C'), (int, float)) and 2 <= ins['C'] <= 16)):
        if ins['B'] <= ins['A'] + 8 or (shape and shape['name'] == 'CALL'):
            name = 'CALL'
    if mapname == 'TFORLOOP' and ins.get('mode') == 3:
        name = 'TFORLOOP'
    if ins.get('mode') == 2 and isinstance(ins.get('B'), (int, float)):
        if mapname in ('FORLOOP','FORPREP') or name in ('FORLOOP','FORPREP'):
            name = 'FORPREP' if (mapname == 'FORPREP' or name == 'FORPREP') else 'FORLOOP'
            if mapname == 'FORPREP':
                name = 'FORPREP'
            if mapname == 'FORLOOP':
                name = 'FORLOOP'
        else:
            name = 'JMP'
    if ins.get('mode') == 3 and isinstance(ins.get('B'), (int, float)):
        pidx = ins['B']
        nups = ins['C'] if isinstance(ins.get('C'), (int, float)) else 0
        if pidx >= 0 and pidx < len(proto.get('prototypes', [])) and proto['prototypes'][pidx] and 0 <= nups <= 32 and not ins.get('iskb') and not ins.get('iskc'):
            name = 'CLOSURE'
        elif iscmpop(mapname) or iscmpop(name):
            name = mapname if iscmpop(mapname) else name
        elif name == 'CLOSURE' or mapname == 'CLOSURE':
            name = 'JMP'
        elif mapname and mapname != 'UNKNOWN':
            name = mapname
    if ins.get('mode') == 1 and ins.get('iskb') and ins.get('C') is None:
        if mapname == 'SETGLOBAL':
            name = 'SETGLOBAL'
        elif isinstance(ins.get('B'), str):
            if isbin(ins['B']):
                name = 'LOADK'
            elif isidstr(ins['B']) and feedsglobaluse(ins, proto):
                name = 'GETGLOBAL'
            else:
                name = 'LOADK'
        elif isinstance(ins.get('B'), bool):
            name = 'LOADBOOL'
        elif isinstance(ins.get('B'), (int, float)):
            name = mapname if mapname == 'GETGLOBAL' else 'LOADK'
    if (name in ('GETGLOBAL','GETUPVAL') or mapname == 'GETUPVAL') and ins.get('mode') == 0 and not ins.get('iskb') and not ins.get('iskc') and isinstance(ins.get('B'), (int, float)):
        name = 'GETUPVAL'
    if name == 'GETGLOBAL' and ins.get('mode') == 0 and not ins.get('iskb') and isinstance(ins.get('B'), (int, float)):
        name = 'GETUPVAL'
    if name == 'LOADNIL' and isinstance(ins.get('B'), (int, float)) and isinstance(ins.get('A'), (int, float)) and ins['B'] < ins['A']:
        if mapname == 'MOVE':
            name = 'MOVE'
        elif mapname and mapname != 'UNKNOWN' and mapname != 'LOADNIL':
            name = mapname
        else:
            name = 'MOVE'
    if ins.get('mode') == 0 and ins.get('iskb') and ins.get('iskc'):
        name = 'SETTABLE'
    if ins.get('mode') == 0 and ins.get('iskc') and not ins.get('iskb') and isinstance(ins.get('B'), (int, float)):
        if mapname == 'SETTABLE':
            name = 'SETTABLE'
        elif mapname == 'GETTABLE':
            name = 'GETTABLE'
        elif ins['A'] == ins['B'] and isinstance(ins.get('C'), str) and isidstr(ins['C']) and hascallsoon(ins, proto):
            name = 'SELF'
        else:
            name = 'GETTABLE'
    if name == 'CLOSURE' and ins.get('mode') == 0 and (ins.get('iskc') or ins.get('iskb')):
        if ins.get('iskb') and ins.get('iskc'):
            name = 'SETTABLE'
        elif ins.get('iskc'):
            name = 'GETTABLE'
    if name == 'CLOSURE':
        nups = ins['C'] if isinstance(ins.get('C'), (int, float)) else 0
        pidx = ins['B'] if isinstance(ins.get('B'), (int, float)) else -1
        if nups < 0 or nups > 32 or not proto or pidx < 0 or pidx >= len(proto.get('prototypes', [])) or not proto['prototypes'][pidx]:
            if ins.get('mode') == 3 and isinstance(ins.get('B'), (int, float)):
                name = 'JMP'
            elif ins.get('mode') == 0 and not ins.get('iskb') and not ins.get('iskc') and isinstance(ins.get('B'), (int, float)) and ins['B'] <= 255 and (ins.get('C') == 0 or ins.get('C') is None):
                name = mapname if mapname == 'MOVE' else 'MOVE'
            elif ins.get('mode') == 0 and not ins.get('iskb') and not ins.get('iskc'):
                name = mapname if mapname in ('CALL','SETLIST') else 'CALL'
            elif mapname and mapname != 'UNKNOWN' and mapname != 'CLOSURE':
                name = mapname
            else:
                name = 'UNKNOWN'
    if ins.get('mode') == 0 and not ins.get('iskb') and not ins.get('iskc') and ins.get('B') == 0 and (ins.get('C') == 0 or ins.get('C') is None):
        strongshape = shape and shape['name'] != 'UNKNOWN' and shape['conf'] >= 55
        if strongshape and shape['name'] in ('LOADNIL','MOVE','CALL'):
            name = shape['name']
        elif mapname == 'MOVE':
            name = 'MOVE'
        elif mapname in ('RETURN','TAILCALL'):
            if not strongshape:
                name = mapname
        elif mapname == 'CALL':
            name = 'CALL'
        elif mapname == 'LOADNIL':
            name = 'LOADNIL'
        elif mapname == 'SETLIST':
            name = shape['name'] if strongshape else 'CALL'
        elif name == 'UNKNOWN' and mapname and mapname != 'UNKNOWN':
            name = mapname
    if name in ('JMP','EQ','LT','LE','TEST') and isinstance(ins.get('B'), str):
        if ins.get('mode') == 1 and ins.get('iskb'):
            name = 'GETGLOBAL' if (isidstr(ins['B']) and not isbin(ins['B']) and feedsglobaluse(ins, proto)) else 'LOADK'
        elif mapname and mapname != 'UNKNOWN':
            name = mapname
    return name

def refopmap(root, opmap):
    votes = {}
    def walk(p):
        for i in range(1, len(p.get('instructions', []))):
            ins = p['instructions'][i]
            if not ins or ins.get('skipped'):
                continue
            ins['_index'] = i
            mapname = opmap.get(ins['opcode'], {}).get('name', 'UNKNOWN')
            name = prefnm(mapname, ins, p, None, opmap)
            shape = shpguess(ins, p, None, opmap)
            if not shape or shape['conf'] < 80:
                continue
            if ins['opcode'] not in votes:
                votes[ins['opcode']] = {}
            m = votes[ins['opcode']]
            m[name] = m.get(name, 0) + 1
        for c in p.get('prototypes', []):
            if c:
                walk(c)
    walk(root)
    for op, m in votes.items():
        if op not in opmap:
            opmap[op] = {'name': 'UNKNOWN', 'body': ''}
        if opmap[op]['name'] != 'UNKNOWN':
            continue
        best = None
        bestn = 0
        total = 0
        for name, n in m.items():
            total += n
            if n > bestn:
                best = name
                bestn = n
        if best and bestn == total and bestn >= 2:
            opmap[op]['name'] = best
    return opmap

def rdvar(s, i):
    if i >= len(s) or s[i] != 'v' or not isdig(s[i+1] if i+1 < len(s) else ''):
        return None
    j = i + 1
    while j < len(s) and isdig(s[j]):
        j += 1
    return {'name': s[i:j], 'end': j}

def stripn(body):
    src = foldconst(str(body))
    out = ''
    i = 0
    while i < len(src):
        if wdat(src, i, 'local'):
            j = skws(src, i + 5)
            id_ = rdid(src, j)
            if id_ and id_['name'][0] == 'v' and isdig(id_['name'][1] if len(id_['name']) > 1 else ''):
                j = skws(src, id_['end'])
                if src[j] == '=':
                    j = skws(src, j + 1)
                    if isdig(src[j] if j < len(src) else ''):
                        while j < len(src) and isdig(src[j]):
                            j += 1
                        if src[j] == ';':
                            j += 1
                        i = j
                        continue
                elif src[j] == ';' or isws(src[j]) or j >= len(src):
                    if src[j] == ';':
                        j += 1
                    i = j
                    continue
        if src[i:i+13] == 'while true do':
            i += 13
            continue
        if wdat(src, i, 'if'):
            j = skws(src, i + 2)
            if src[j] == '(':
                left = rdvar(src, skws(src, j + 1))
                if left:
                    j = skws(src, left['end'])
                    if src[j] == '=' and src[j+1] == '=':
                        j = skws(src, j + 2)
                        if isdig(src[j] if j < len(src) else ''):
                            while j < len(src) and isdig(src[j]):
                                j += 1
                            j = skws(src, j)
                            if src[j] == ')':
                                j = skws(src, j + 1)
                                if wdat(src, j, 'then'):
                                    i = j + 4
                                    continue
        if wdat(src, i, 'break'):
            j = i + 5
            if src[j] == ';':
                j += 1
            j = skws(src, j)
            if wdat(src, j, 'end'):
                i = j + 3
                continue
        if wdat(src, i, 'end'):
            i += 3
            continue
        out += src[i]
        i += 1
    return colws(out)

def cmpct(body):
    return strws(stripn(body))

def has(s, part):
    return part in s

def lkcloscall(c):
    from_ = 0
    while from_ < len(c):
        mark = c.find('[2]]=v', from_)
        if mark < 0:
            return False
        v = rdvar(c, mark + 5)
        if not v or c[v['end']] != '(':
            from_ = mark + 6
            continue
        a = rdvar(c, v['end'] + 1)
        if not a:
            from_ = mark + 6
            continue
        if c[a['end']] == '[':
            return True
        if c[a['end']] == ',':
            b = rdvar(c, a['end'] + 1)
            if b and c[b['end']] == ',':
                d = rdvar(c, b['end'] + 1)
                if d and c[d['end']] == ')':
                    return True
        from_ = mark + 6
    return False

def issetl(raw, text, c):
    if not (has(text, 'for ') or has(c, 'for')):
        return False
    if has(c, '[2]]=v') or has(raw, 'setmetatable'):
        return False
    if (has(c, ',v') or has2vasg(c)) and has(c, ']('):
        return False
    if has(raw, 'insert(') or has(raw, 'v15(') or has(raw, 'v6('):
        return True
    if has(c, ']=v') and (has(c, '+1') or has(c, '-1') or has(c, '+v') or hasplusv(c)):
        return True
    if has(c, ']=v') and has(c, '+') and has(c, '[2]'):
        return True
    return False

def isself(c):
    i = 0
    while i < len(c):
        v = rdvar(c, i)
        if not v or c[v['end']] != '[':
            i += 1
            continue
        j = v['end'] + 1
        if c[j] == '#':
            i = v['end']
            continue
        inner = rdvar(c, j)
        if inner and c[inner['end']:inner['end']+4] == '+1]=':
            return True
        plus = c.find('+1]=', j)
        if plus > j and plus < j + 20 and c[plus - 1] != '#':
            slice_ = c[j:plus]
            if '#' not in slice_:
                return True
        i = v['end']
    return False

def isjmp(c):
    a = rdvar(c, 0)
    if not a or c[a['end']] != '=':
        return False
    b = rdvar(c, a['end'] + 1)
    if not b:
        return False
    tail = c[b['end']:]
    return tail == '[3]' or tail == '[3];'

def istest(text, c):
    if not (has(text, 'if') and has(text, 'else') and has(text, 'then')):
        return False
    for ch in c:
        if ch in '<>~':
            return False
        if ch == '=' and c[c.index(ch)+1] == '=':
            return False
    return has(c, '[2]]')

def matchasgidx(c):
    a = rdvar(c, 0)
    if not a or c[a['end']] != '[':
        return None
    b = rdvar(c, a['end'] + 1)
    if not b or c[b['end']:b['end']+4] != '[2]]':
        return None
    i = b['end'] + 4
    if c[i] != '=':
        return None
    i += 1
    d = rdvar(c, i)
    if not d or c[d['end']] != '[':
        return None
    e = rdvar(c, d['end'] + 1)
    if not e:
        return None
    rest = c[e['end']:]
    if rest in ('[3]','[3];','[3]]','[3]];'):
        return {'left': a['name'], 'right': d['name']}
    return None

def isloadk(c):
    a = rdvar(c, 0)
    if not a or c[a['end']] != '[':
        return False
    b = rdvar(c, a['end'] + 1)
    if not b or c[b['end']:b['end']+4] != '[2]]':
        return False
    i = b['end'] + 4
    if c[i] != '=':
        return False
    d = rdvar(c, i + 1)
    if not d:
        return False
    rest = c[d['end']:]
    return rest in ('[3]','[3];')

def issett(c):
    if not has(c, ']['):
        return False
    eq = c.find(']=')
    if eq < 0:
        return False
    closes = sum(1 for i in range(eq+1) if c[i] == ']')
    return closes >= 2

def iscall(c, text):
    if has(c, ']('):
        return True
    if has(text, 'for ') and has(c, '('):
        for i in range(len(c) - 2):
            a = rdvar(c, i)
            if not a or c[a['end']] != ',':
                continue
            b = rdvar(c, a['end'] + 1)
            if b and c[b['end']] == '=':
                return True
    return False

def binop(c, op):
    return c.find(']' + op + 'v') != -1

def has2vasg(c):
    i = 0
    while i < len(c):
        if c[i] != 'v':
            i += 1
            continue
        a = rdvar(c, i)
        if not a or c[a['end']] != ',':
            i += 1
            continue
        b = rdvar(c, a['end'] + 1)
        if b and c[b['end']] == '=':
            return True
        i = a['end']
    return False

def hasplusv(c):
    i = 0
    while i < len(c):
        if c[i] == '+' and c[i+1] == 'v':
            v = rdvar(c, i + 1)
            if v and c[v['end']] == ']':
                return True
        i += 1
    return False

def hasabcadd(c):
    i = 0
    while i < len(c):
        a = rdid(c, i)
        if not a:
            i += 1
            continue
        if c[a['end']] != '=':
            i = a['end']
            continue
        b = rdid(c, a['end'] + 1)
        if not b or c[b['end']] != '+':
            i = a['end']
            continue
        d = rdid(c, b['end'] + 1)
        if d:
            return True
        i = a['end']
    return False

def hasforadd(c):
    if has(c, ']+v') or has(c, ']+='):
        return True
    if hasabcadd(c) and has(c, '+2'):
        return True
    return False

def isforl(c, text):
    if not has(text, 'if'):
        return False
    if not (has(c, '+2') and has(c, '+1') and has(c, '+3')):
        return False
    if not (has(c, '>0') or has(c, '<0')):
        return False
    if not (has(c, '[3]') or has(c, '[3];')):
        return False
    if not hasforadd(c):
        return False
    return True

def isforp(c, text):
    if not has(c, '+2'):
        return False
    if has(c, ']-v') or has(c, ']-='):
        if not has(c, '[3]') and not has(text, 'if'):
            return False
        return has(c, '[2]]') or has(c, '[2];') or has(c, '[2]=')
    if not has(text, 'if'):
        return False
    if not (has(c, '+1') and has(c, '+3')):
        return False
    if not (has(c, '>0') or has(c, '<0')):
        return False
    if not (has(c, '[3]') or has(c, '[3];')):
        return False
    if hasforadd(c):
        return False
    return True

def issetg(c):
    eq = c.find(']=')
    if eq < 0:
        return False
    left = c[:eq+1]
    if '[3]' not in left:
        return False
    if '][' in left:
        return False
    right = c[eq+2:]
    v = rdvar(right, 0)
    if not v or right[v['end']] != '[':
        return False
    idx = right[v['end']:]
    return idx.startswith('[') and '[2]' in idx

def issetu(c):
    eq = c.find(']=')
    if eq < 0:
        return False
    left = c[:eq+1]
    if '[3]' not in left:
        return False
    right = c[eq+2:]
    v = rdvar(right, 0)
    if not v or right[v['end']] != '[':
        return False
    if '[2]' not in right[v['end']:]:
        return False
    return '][1]' in left or '][2]' in left

def istset(text, c):
    if not (has(text, 'if') and has(text, 'else')):
        return False
    if not (has(c, '[2]]=') and has(c, '[3]')):
        return False
    if has(c, '<') or has(c, '>') or has(c, '=='):
        return False
    return has(c, '[2]]=v')

def isunm(c):
    return has(c, ']=-v') or has(c, ']=-(') or has(c, '[2]]=-')

def isvarg(c):
    return has(c, '...')

def clsh(body):
    raw = foldconst(str(body))
    text = stripn(raw)
    c = cmpct(raw)
    if has(text, 'do return'):
        if not has(text, '('):
            return 'RETURN'
        ri = c.find('returnv')
        if ri >= 0:
            after = c[ri+6:]
            v = rdvar(after, 0)
            if v and after[v['end']] == '[':
                return 'TAILCALL'
            if v and after[v['end']] == '(' and rdvar(after, v['end']+1):
                return 'RETURN'
        return 'TAILCALL'
    if has(raw, 'setmetatable'):
        return 'CLOSURE'
    if lkcloscall(c):
        return 'CLOSURE'
    if issetl(raw, text, c):
        return 'SETLIST'
    if has(c, '..'):
        return 'CONCAT'
    if has(text, 'for') and has(c, '](') and has(c, 'if') and has(c, ',v'):
        return 'TFORLOOP'
    if isself(c):
        return 'SELF'
    if isvarg(c):
        return 'VARARG'
    if isunm(c):
        return 'UNM'
    if has(c, '=nil') and has(text, 'for'):
        return 'LOADNIL'
    if has(c, '={}') and len(c) < 80 and not has(text, 'for') and not has(text, 'while'):
        return 'NEWTABLE'
    if isjmp(c):
        return 'JMP'
    if isforl(c, text):
        return 'FORLOOP'
    if isforp(c, text):
        return 'FORPREP'
    if has(text, 'if') and has(c, '[2]') and has(c, '[4]') and has(c, '[3]') and (has(c, '+1') or has(text, 'else')):
        if has(c, ']==') or has(c, ']==v') or (has(c, '==') and not has(c, '<') and not has(c, '>')):
            return 'EQ'
        if has(c, '<=') or has(c, '>='):
            return 'LE'
        if has(c, '<') or has(c, '>'):
            return 'LT'
    if has(text, 'if') and has(c, '+1') and has(c, '[3]'):
        if has(c, '==') or has(c, '~='):
            return 'EQ'
        if has(c, '<=') or has(c, '>='):
            return 'LE'
        if has(c, '<') or has(c, '>'):
            return 'LT'
    if has(c, '[v') and has(c, '[2]]') and has(c, '=v') and (has(c, '+1') or has(c, '[3]')):
        if has(text, 'if') and (has(c, '==') or has(c, '~=')):
            return 'EQ'
        if has(text, 'if') and (has(c, '<=') or has(c, '>=')):
            return 'LE'
        if has(text, 'if') and (has(c, '<') or has(c, '>')):
            return 'LT'
    if has(c, '==v') and has(c, '[4]') and has(c, '+1'):
        return 'EQ'
    if istset(text, c):
        return 'TESTSET'
    if istest(text, c):
        return 'TEST'
    if has(c, '~=0') and has(c, '[2]]=') and has(c, '[3]') and not has(c, ']('):
        return 'LOADBOOL'
    if has(c, '[2]]=') and has(c, '[3]][') and has(c, '[4]]'):
        return 'GETTABLE'
    if has(c, '=v') and has(c, '[3]][') and has(c, '[4]]'):
        return 'GETTABLE'
    if has(c, '[2]]=') and has(c, '[3]][') and has(c, '[4]'):
        return 'GETTABLE'
    if issett(c):
        return 'SETTABLE'
    if issetu(c):
        return 'SETUPVAL'
    if issetg(c):
        return 'SETGLOBAL'
    mv = matchasgidx(c)
    if mv:
        return 'MOVE' if mv['left'] == mv['right'] else 'GETGLOBAL_OR_UPVAL'
    if isloadk(c):
        return 'LOADK'
    if iscall(c, text):
        return 'CALL'
    if binop(c, '+'):
        return 'ADD'
    if binop(c, '-'):
        return 'SUB'
    if binop(c, '*'):
        return 'MUL'
    if binop(c, '/'):
        return 'DIV'
    if binop(c, '%'):
        return 'MOD'
    if binop(c, '^'):
        return 'POW'
    if has(c, '=#v') or has(c, '=#('):
        return 'LEN'
    if has(text, 'not '):
        return 'NOT'
    if has(c, '={}') and not has(c, '](') and not has(text, 'setmetatable'):
        return 'NEWTABLE'
    return 'UNKNOWN'

def refopnm(name, body, ctx=None):
    if ctx is None:
        ctx = {}
    if name != 'GETGLOBAL_OR_UPVAL':
        return name
    c = cmpct(body)
    if ctx.get('upvalvar') and c.find('=' + ctx['upvalvar'] + '[') != -1:
        return 'GETUPVAL'
    if ctx.get('envvar') and c.find('=' + ctx['envvar'] + '[') != -1:
        return 'GETGLOBAL'
    eq = c.find(']=')
    if eq >= 0:
        v = rdvar(c, eq + 2)
        if v and c[v['end']] == '[':
            if v['name'] == ctx.get('upvalvar'):
                return 'GETUPVAL'
            if v['name'] == ctx.get('envvar'):
                return 'GETGLOBAL'
    return 'GETGLOBAL'

def isopidx(expr):
    folded = colws(foldconst(expr))
    return folded == '1' or evalex(expr) == 1

def evalex(expr):
    try:
        return eval(expr) if expr.strip() else None
    except:
        return None

def scanfetch(folded):
    best = None
    i = 0
    while i < len(folded):
        if folded[i] == '"' or folded[i] == "'":
            i = skstr(folded, i)
            continue
        a = rdid(folded, i)
        if not a:
            i += 1
            continue
        j = skws(folded, a['end'])
        if folded[j] != '=':
            i = a['end']
            continue
        j = skws(folded, j + 1)
        code = rdid(folded, j)
        if not code or folded[code['end']] != '[':
            i = a['end']
            continue
        pc = rdid(folded, code['end'] + 1)
        if not pc or folded[pc['end']] != ']':
            i = a['end']
            continue
        j = skws(folded, pc['end'] + 1)
        if folded[j] == ';':
            j += 1
        j = skws(folded, j)
        op = rdid(folded, j)
        if not op:
            i = a['end']
            continue
        j = skws(folded, op['end'])
        if folded[j] != '=':
            i = a['end']
            continue
        j = skws(folded, j + 1)
        inst2 = rdid(folded, j)
        if not inst2 or inst2['name'] != a['name'] or folded[inst2['end']] != '[':
            i = a['end']
            continue
        idxstart = inst2['end'] + 1
        depth = 1
        k = idxstart
        while k < len(folded) and depth > 0:
            if folded[k] == '[':
                depth += 1
            elif folded[k] == ']':
                depth -= 1
            if depth > 0:
                k += 1
            else:
                break
        if depth != 0:
            i = a['end']
            continue
        idxexpr = folded[idxstart:k]
        if isopidx(idxexpr):
            best = {
                'instvar': a['name'],
                'codevar': code['name'],
                'pcvar': pc['name'],
                'opvar': op['name'],
                'fetchindex': i
            }
        i = a['end']
    if not best:
        raise ValueError('VM fetch not found')
    return best

def findople(folded, opvar):
    hits = []
    from_ = 0
    while from_ < len(folded):
        at = findwd(folded, 'if', from_)
        if at < 0:
            break
        j = skws(folded, at + 2)
        if folded[j] != '(':
            from_ = at + 2
            continue
        j = skws(folded, j + 1)
        while folded[j] == '(':
            j = skws(folded, j + 1)
        id_ = rdid(folded, j)
        if not id_ or id_['name'] != opvar:
            from_ = at + 2
            continue
        j = skws(folded, id_['end'])
        if folded[j] != '<' or folded[j+1] != '=':
            from_ = at + 2
            continue
        j = skws(folded, j + 2)
        num = rdnum(folded, j)
        if not num:
            from_ = at + 2
            continue
        j = skws(folded, num['end'])
        while folded[j] == ')':
            j = skws(folded, j + 1)
        if wdat(folded, j, 'then'):
            hits.append({'at': at, 'bound': num['num']})
        from_ = at + 2
    return hits

def pickdisp(folded, fetch, opvar):
    hits = findople(folded, opvar)
    best = None
    for hit in hits:
        abs_ = hit['at']
        if abs_ <= fetch['fetchindex'] - 50 and abs_ < fetch['fetchindex']:
            pass
        elif abs_ < fetch['fetchindex'] - 5000:
            continue
        end = findblkend(folded, abs_)
        if end < 0:
            continue
        ln = end - abs_
        if ln < 400:
            continue
        bound = hit.get('bound', 0)
        score = ln + bound * 50
        if not best or score > best['score']:
            best = {'start': abs_, 'len': ln, 'raw': folded[abs_:end], 'score': score, 'bound': bound}
    for hit in hits:
        abs_ = hit['at']
        if abs_ <= fetch['fetchindex']:
            continue
        end = findblkend(folded, abs_)
        if end < 0:
            continue
        ln = end - abs_
        if ln < 400:
            continue
        bound = hit.get('bound', 0)
        score = ln + bound * 80 + 1000
        if not best or score > best['score']:
            best = {'start': abs_, 'len': ln, 'raw': folded[abs_:end], 'score': score, 'bound': bound}
    if not best:
        raise ValueError('Dispatch tree not found for ' + opvar)
    return best

def finddisp(source):
    folded = foldconst(source)
    fetch = scanfetch(folded)
    tree = pickdisp(folded, fetch, fetch['opvar'])
    return {**fetch, 'start': tree['start'], 'end': tree['start'] + tree['len'], 'raw': tree['raw'], 'folded': folded}

def scansep(s, from_):
    depth = 0
    i = from_
    hits = []
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
        n = tok['name']
        if n in ('if','function','repeat','do'):
            depth += 1
            i = tok['end']
            continue
        if n == 'until':
            if depth > 0:
                depth -= 1
            i = tok['end']
            continue
        if n == 'elseif':
            if depth == 0:
                hits.append({'type': 'elseif', 'index': tok['start']})
            i = tok['end']
            continue
        if n == 'else':
            if depth == 0:
                hits.append({'type': 'else', 'index': tok['start']})
            i = tok['end']
            continue
        if n == 'end':
            if depth == 0:
                hits.append({'type': 'end', 'index': tok['start']})
                return {'hits': hits, 'end': tok['end']}
            depth -= 1
            i = tok['end']
            continue
        i = tok['end']
    return {'hits': hits, 'end': len(s)}

def parseif(s):
    if not wdat(s, 0, 'if') and not (skws(s, 0) == 0 and wdat(s, 0, 'if')):
        start = skws(s, 0)
        if not wdat(s, start, 'if'):
            return None
    start = 0 if wdat(s, 0, 'if') else skws(s, 0)
    if not wdat(s, start, 'if'):
        return None
    branches = []
    i = start + 2
    while True:
        thenat = findwd(s, 'then', i)
        if thenat < 0:
            return None
        cond = s[i:thenat].strip()
        bodystart = thenat + 4
        res = scansep(s, bodystart)
        if not res['hits']:
            return None
        first = res['hits'][0]
        branches.append({'cond': cond, 'body': s[bodystart:first['index']].strip()})
        if first['type'] == 'end':
            return {'branches': branches, 'elsebody': None, 'end': first['index'] + 3, 'full': s[:first['index']+3]}
        if first['type'] == 'else':
            elsestart = first['index'] + 4
            rest = scansep(s, elsestart)
            endhit = next((h for h in rest['hits'] if h['type'] == 'end'), None)
            elseend = endhit['index'] if endhit else rest['end']
            return {'branches': branches, 'elsebody': s[elsestart:elseend].strip(), 'end': elseend + 3, 'full': s[:elseend+3]}
        if first['type'] == 'elseif':
            i = first['index'] + 6
            continue
        return None

def parsecond(cond, opvar):
    i = 0
    while i < len(cond):
        id_ = rdid(cond, i)
        if id_ and id_['name'] == opvar:
            j = skws(cond, id_['end'])
            op = None
            if cond[j:j+2] in ('<=','>=','==','~='):
                op = cond[j:j+2]
                j += 2
            elif cond[j] in '<>':
                op = cond[j]
                j += 1
            if op:
                j = skws(cond, j)
                num = rdnum(cond, j)
                if num:
                    return {'op': op, 'n': num['num']}
        i += 1
    return None

def evalcond(c, opcode):
    if not c:
        return False
    if c['op'] == '<=':
        return opcode <= c['n']
    if c['op'] == '>=':
        return opcode >= c['n']
    if c['op'] == '==':
        return opcode == c['n']
    if c['op'] == '~=':
        return opcode != c['n']
    if c['op'] == '<':
        return opcode < c['n']
    if c['op'] == '>':
        return opcode > c['n']
    return False

def fmtif(branches, elsebody):
    if not branches:
        return elsebody or ''
    out = ''
    for i, br in enumerate(branches):
        out += ('if ' if i == 0 else 'elseif ') + br['cond'] + ' then ' + br['body'] + ' '
    if elsebody is not None:
        out += 'else ' + elsebody + ' '
    out += 'end'
    return out.strip()

def resleaf(fragment, opcode, opvar, depth=0):
    f = fragment.strip()
    if depth > 40:
        return f
    def tryparse(src):
        parsed = parseif(src)
        if not parsed:
            return None
        for bi, br in enumerate(parsed['branches']):
            c = parsecond(br['cond'], opvar)
            if not c:
                return fmtif(parsed['branches'][bi:], parsed['elsebody'])
            if evalcond(c, opcode):
                return resleaf(br['body'], opcode, opvar, depth + 1)
        if parsed['elsebody'] is not None:
            return resleaf(parsed['elsebody'], opcode, opvar, depth + 1)
        return f
    if wdat(f, 0, 'if') and f[:80].find(opvar) != -1:
        got = tryparse(f)
        if got is not None:
            return got
    ifidx = findopif(f, opvar)
    if ifidx >= 0 and ifidx < 80:
        got = tryparse(f[ifidx:])
        if got is not None:
            return got
    return f

def findopif(src, opvar):
    from_ = 0
    best = -1
    while from_ < len(src):
        at = findwd(src, 'if', from_)
        if at < 0:
            break
        j = skws(src, at + 2)
        if src[j] == '(':
            j = skws(src, j + 1)
            while src[j] == '(':
                j = skws(src, j + 1)
            id_ = rdid(src, j)
            if id_ and id_['name'] == opvar:
                j = skws(src, id_['end'])
                op2 = src[j:j+2]
                if op2 in ('<=','==','>=') or src[j] in '<>':
                    if best < 0:
                        best = at
                    if at > best + 200:
                        break
        from_ = at + 2
    return best

def maxoptree(tree, opvar):
    maxop = 0
    i = 0
    while i < len(tree):
        id_ = rdid(tree, i)
        if id_ and id_['name'] == opvar:
            j = skws(tree, id_['end'])
            if tree[j:j+2] in ('<=','==') or tree[j] == '>':
                if tree[j:j+2] in ('<=','=='):
                    j += 2
                else:
                    j += 1
                j = skws(tree, j)
                num = rdnum(tree, j)
                if num:
                    maxop = max(maxop, num['num'])
            i = id_['end']
            continue
        i += 1
    return maxop

def parsedisp(code, opvar):
    folded = foldconst(code)
    start = findopif(folded, opvar)
    if start < 0:
        raise ValueError('Dispatch tree start not found for ' + opvar)
    root = parseif(folded[start:])
    if not root:
        raise ValueError('Failed to parse dispatch if-tree')
    map_ = {}
    probemax = maxoptree(root['full'], opvar) + 8
    for op in range(probemax + 1):
        map_[op] = resleaf(root['full'], op, opvar)
    return {'map': map_, 'foldedtree': root['full'], 'opvar': opvar, 'maxop': probemax}

def findlocfn(source, from_=0):
    i = from_
    while i < len(source):
        at = findwd(source, 'local', i)
        if at < 0:
            return None
        j = skws(source, at + 5)
        if not wdat(source, j, 'function'):
            i = at + 5
            continue
        j = skws(source, j + 8)
        fn = rdid(source, j)
        if not fn:
            i = at + 5
            continue
        j = skws(source, fn['end'])
        if source[j] != '(':
            i = at + 5
            continue
        j += 1
        a = rdid(source, skws(source, j))
        if not a or source[a['end']] != ',':
            i = at + 5
            continue
        b = rdid(source, skws(source, a['end'] + 1))
        if not b or source[b['end']] != ',':
            i = at + 5
            continue
        c = rdid(source, skws(source, b['end'] + 1))
        if not c:
            i = at + 5
            continue
        j = skws(source, c['end'])
        if source[j] != ')':
            i = at + 5
            continue
        j = skws(source, j + 1)
        if not wdat(source, j, 'local'):
            i = at + 5
            continue
        j = skws(source, j + 5)
        d = rdid(source, j)
        if not d:
            i = at + 5
            continue
        j = skws(source, d['end'])
        if source[j] != '=':
            i = at + 5
            continue
        j = skws(source, j + 1)
        e = rdid(source, j)
        if not e or e['name'] != a['name'] or source[e['end']:e['end']+3] != '[1]':
            i = at + 5
            continue
        return {
            'index': at,
            'wrapvar': fn['name'],
            'chunkvar': a['name'],
            'upvalvar': b['name'],
            'envvar': c['name'],
            'codelocal': d['name']
        }
    return None

def infvmctx(source, dispatch):
    instvar = dispatch['instvar']
    opvar = dispatch['opvar']
    pcvar = dispatch['pcvar']
    codevar = dispatch['codevar']
    folded = foldconst(source[dispatch['start']:dispatch['end']])
    wrapvar = 'v40'
    envvar = 'v74'
    upvalvar = 'v73'
    stackvar = 'v88'
    protovar = 'v79'
    unpackvar = 'v21'
    wrapfn = findlocfn(source)
    if wrapfn:
        wrapvar = wrapfn['wrapvar']
        upvalvar = wrapfn['upvalvar']
        envvar = wrapfn['envvar']
        slice_ = source[wrapfn['index']:wrapfn['index'] + 400]
        i = 0
        while i < len(slice_):
            at = findwd(slice_, 'local', i)
            if at < 0:
                break
            j = skws(slice_, at + 5)
            id_ = rdid(slice_, j)
            if id_:
                j = skws(slice_, id_['end'])
                if slice_[j] == '=':
                    j = skws(slice_, j + 1)
                    base = rdid(slice_, j)
                    if base and slice_[base['end']:base['end']+3] == '[2]':
                        protovar = id_['name']
                        break
            i = at + 5
    i = 0
    while i < len(folded):
        left = rdid(folded, i)
        if not left:
            i += 1
            continue
        needle = '[' + instvar + '[2]]='
        if folded[left['end']:left['end']+len(needle)] == needle:
            j = left['end'] + len(needle)
            right = rdid(folded, j)
            if right and folded[right['end']:right['end']+len(needle)-1] == '[' + instvar + '[3]]':
                if left['name'] == right['name']:
                    stackvar = left['name']
                elif left['name'] == stackvar:
                    upvalvar = right['name']
        i = left['end']
    stkneedle = '[' + instvar + '[2]]'
    stkat = folded.find(stkneedle)
    if stkat > 0:
        k = stkat - 1
        while k >= 0 and isdig(folded[k]):
            k -= 1
        if folded[k] == 'v':
            id_ = rdid(folded, k)
            if id_:
                stackvar = id_['name']
    unat = source.find('=unpack or table.unpack')
    if unat > 0:
        k = unat - 1
        while k >= 0 and isws(source[k]):
            k -= 1
        while k >= 0 and (isdig(source[k]) or source[k] == 'v'):
            k -= 1
        id_ = rdid(source, k + 1)
        if id_:
            unpackvar = id_['name']
    return {
        'instvar': instvar, 'opvar': opvar, 'pcvar': pcvar, 'codevar': codevar,
        'envvar': envvar, 'upvalvar': upvalvar, 'stackvar': stackvar, 'protovar': protovar,
        'wrapvar': wrapvar, 'topvar': 'v83', 'unpackvar': unpackvar
    }

def findclosop(source):
    folded = foldconst(source)
    from_ = 0
    while from_ < len(folded):
        at = findwd(folded, 'if', from_)
        if at < 0:
            break
        j = skws(folded, at + 2)
        if folded[j] == '(':
            j = skws(folded, j + 1)
            v = rdid(folded, j)
            if v and folded[v['end']] == '[' and folded[v['end']+1] == '1' and folded[v['end']+2] == ']':
                j = skws(folded, v['end'] + 3)
                if folded[j] == '=' and folded[j+1] == '=':
                    j = skws(folded, j + 2)
                    if folded[j] == '(':
                        j += 1
                    num = rdnum(folded, j)
                    if num:
                        return num['num']
        from_ = at + 2
    return None

def guessop(ins):
    if not ins or ins.get('skipped'):
        return 'UNKNOWN'
    return prefnm('UNKNOWN', ins, None, None, {})

def councn(body):
    n = 0
    i = 0
    while i < len(body):
        if body[i] == 'v' and isdig(body[i+1] if i+1 < len(body) else ''):
            j = i + 1
            while j < len(body) and isdig(body[j]):
                j += 1
            if body[j:j+2] in ('<=','=='):
                n += 1
            i = j
            continue
        i += 1
    return n

def anvm(source):
    try:
        dispatch = finddisp(source)
    except:
        return {'dispatch': None, 'ctx': {}, 'opcodeMap': {}, 'nameToOpcodes': {}, 'closureLocalOp': None, 'opcodeCount': 0}
    folded = dispatch.get('folded') or foldconst(source)
    ctx = infvmctx(folded, dispatch)
    try:
        parsed = parsedisp(dispatch['raw'], dispatch['opvar'])
        map_ = parsed['map']
    except:
        return {'dispatch': dispatch, 'ctx': ctx, 'opcodeMap': {}, 'nameToOpcodes': {}, 'closureLocalOp': findclosop(folded), 'opcodeCount': 0}
    opcodeMap = {}
    nameToOpcodes = {}
    for op, body in map_.items():
        name = refopnm(clsh(body), body, ctx)
        if councn(body) > 3 and op > 45:
            continue
        opcodeMap[op] = {'name': name, 'body': stripn(body)[:200]}
        if name not in nameToOpcodes:
            nameToOpcodes[name] = []
        nameToOpcodes[name].append(op)
    return {
        'dispatch': dispatch,
        'ctx': ctx,
        'opcodeMap': opcodeMap,
        'nameToOpcodes': nameToOpcodes,
        'closureLocalOp': findclosop(folded),
        'opcodeCount': len(opcodeMap)
    }

def issub(op):
    if not op or op.get('name') in ('UNKNOWN','CLOSE'):
        return False
    return op['name'] in ('CALL','TAILCALL','GETGLOBAL','SETGLOBAL','LOADK','SELF','CLOSURE','SETTABLE','GETTABLE','ADD','SUB','MUL','DIV','CONCAT','RETURN','NEWTABLE','SETLIST','LOADBOOL','TEST','EQ','LT','LE','FORPREP','FORLOOP')

def jmpsbefore(ops, i):
    for j in range(i):
        if ops[j].get('name') != 'JMP':
            return False
    return True

def resjmp(ops, bypc, b):
    guard = 0
    ti = bypc.get(b)
    while ti is not None and guard < 12:
        op = ops[ti]
        if op.get('name') == 'JMP' and isinstance(op.get('B'), (int, float)) and op['B'] != b:
            b = op['B']
            ti = bypc.get(b)
            continue
        break
    return {'ti': ti, 'b': b}

def stripredjmp(ops):
    out = []
    for i, op in enumerate(ops):
        if op.get('name') != 'JMP' or not isinstance(op.get('B'), (int, float)):
            out.append(op)
            continue
        if i + 1 < len(ops) and ops[i+1].get('index') == op['B']:
            continue
        if out and out[-1].get('name') == 'JMP' and out[-1].get('B') == op['B']:
            continue
        out.append(op)
    return out

def stripfwdjmp(ops):
    bypc = {op['index']: i for i, op in enumerate(ops)}
    nop = set()
    for i, op in enumerate(ops):
        if op.get('name') != 'JMP' or not isinstance(op.get('B'), (int, float)):
            continue
        resolved = resjmp(ops, bypc, op['B'])
        ti = resolved['ti']
        if ti is None or ti <= i:
            continue
        subst = 0
        for j in range(i+1, ti):
            if issub(ops[j]):
                subst += 1
        if subst < 2:
            continue
        episubst = 0
        for j in range(ti, min(ti+6, len(ops))):
            if issub(ops[j]) and ops[j].get('name') != 'RETURN':
                episubst += 1
        if jmpsbefore(ops, i) and subst >= 2:
            nop.add(i)
            continue
        if subst >= 2 and episubst <= 1:
            nop.add(i)
    if not nop:
        return ops
    return [op for i, op in enumerate(ops) if i not in nop]

def stripmutjmp(ops):
    bypc = {op['index']: i for i, op in enumerate(ops)}
    nop = set()
    for i, a in enumerate(ops):
        if a.get('name') != 'JMP' or not isinstance(a.get('B'), (int, float)):
            continue
        ti = bypc.get(a['B'])
        if ti is None:
            continue
        b = ops[ti]
        if b.get('name') == 'JMP' and b.get('B') == a['index']:
            nop.add(i)
            nop.add(ti)
    if not nop:
        return ops
    return [op for i, op in enumerate(ops) if i not in nop]

def stripbogret(ops):
    nop = set()
    for i, op in enumerate(ops):
        if op.get('name') not in ('RETURN','TAILCALL'):
            continue
        if i + 2 >= len(ops):
            continue
        if op.get('name') == 'TAILCALL':
            continue
        if isinstance(op.get('B'), (int, float)) and op['B'] >= 2:
            keep = False
            for j in range(i+1, min(i+5, len(ops))):
                n = ops[j]
                if n.get('name') == 'EQ' and isinstance(n.get('A'), (int, float)) and n['A'] <= 4 and n.get('iskc'):
                    keep = True
                    break
                if n.get('name') == 'LOADK' and n.get('B') == 0 and isinstance(n.get('A'), (int, float)) and n['A'] <= 4:
                    keep = True
                    break
            if keep:
                continue
        subst = 0
        for j in range(i+1, len(ops)):
            if issub(ops[j]):
                subst += 1
        if subst >= 3:
            nop.add(i)
    if not nop:
        return ops
    return [op for i, op in enumerate(ops) if i not in nop]

def remapjmp(ops):
    if not ops:
        return ops
    present = set(op.get('index') for op in ops)
    sorted_present = sorted(present)
    def resolve(b):
        if b in present:
            return b
        for ix in sorted_present:
            if ix >= b:
                return ix
        return sorted_present[-1] if sorted_present else b
    changed = False
    out = []
    for op in ops:
        if op.get('name') in ('JMP','EQ','LT','LE','TEST','TESTSET','FORLOOP','FORPREP') and isinstance(op.get('B'), (int, float)):
            nb = resolve(op['B'])
            if nb != op['B']:
                changed = True
                newop = dict(op)
                newop['B'] = nb
                out.append(newop)
                continue
        out.append(op)
    return out if changed else ops

def stripnil(ops):
    nop = set()
    for i, op in enumerate(ops):
        if op.get('name') != 'LOADNIL':
            continue
        a = op['A']
        to = op['B'] if isinstance(op.get('B'), (int, float)) else a
        for j in range(i+1, min(i+4, len(ops))):
            n = ops[j]
            if not n:
                break
            if n.get('name') == 'GETTABLE' and n.get('B') == a:
                nop.add(i)
                nop.add(j)
                if j+1 < len(ops) and ops[j+1].get('name') == 'CALL' and ops[j+1].get('A') == n.get('A'):
                    nop.add(j+1)
                break
            if n.get('name') == 'CALL' and n.get('A') == a:
                nop.add(i)
                nop.add(j)
                break
            if n.get('name') == 'LOADNIL':
                continue
            if n.get('name') in ('MOVE','JMP'):
                continue
            break
        if i == 0 and to >= a + 2:
            nop.add(i)
    if not nop:
        return ops
    return [op for i, op in enumerate(ops) if i not in nop]

def stripback(ops):
    nop = set()
    for i, op in enumerate(ops):
        if op.get('name') not in ('EQ','LT','LE'):
            continue
        if isinstance(op.get('A'), (int, float)) and op['A'] > 32:
            nop.add(i)
    if not nop:
        return ops
    return [op for i, op in enumerate(ops) if i not in nop]

def linstcff(ops):
    if not ops or len(ops) < 10:
        return ops
    statereg = None
    for i in range(min(6, len(ops))):
        op = ops[i]
        if op.get('name') == 'LOADK' and op.get('B') == 0 and isinstance(op.get('A'), (int, float)):
            statereg = op['A']
            break
    if statereg is None:
        return ops
    bypc = {op['index']: i for i, op in enumerate(ops)}
    eqstates = []
    for i, op in enumerate(ops):
        if op.get('name') == 'EQ' and op.get('A') == statereg and op.get('iskc') and isinstance(op.get('C'), (int, float)) and isinstance(op.get('B'), (int, float)):
            eqstates.append({'i': i, 'state': op['C'], 'target': op['B']})
    if len(eqstates) < 2:
        return ops
    blocks = {}
    for eq in eqstates:
        start = eq['i'] + 1
        if start < len(ops) and ops[start].get('name') == 'JMP':
            start += 1
        end = len(ops)
        for j in range(start, len(ops)):
            op = ops[j]
            if op.get('name') == 'EQ' and op.get('A') == statereg and op.get('iskc'):
                end = j
                break
            if op.get('name') == 'LOADK' and op.get('A') == statereg and isinstance(op.get('B'), (int, float)) and op['B'] != eq['state']:
                end = j
                break
        if end > start:
            blocks[eq['state']] = ops[start:end]
    if len(blocks) < 2:
        return ops
    ordered = sorted(blocks.keys())
    out = []
    for s in ordered:
        block = blocks[s][:]
        while block:
            last = block[-1]
            if last.get('name') == 'JMP':
                block.pop()
                continue
            if last.get('name') == 'LOADK' and last.get('A') == statereg:
                block.pop()
                continue
            break
        out.extend(block)
    lastorig = ops[-1]
    if lastorig and lastorig.get('name') == 'RETURN' and (not out or out[-1].get('name') != 'RETURN'):
        hasret = any(o.get('name') == 'RETURN' for o in out)
        if not hasret:
            out.append(lastorig)
    return out if len(out) >= 3 else ops

def cleancfg(ops):
    cur = ops[:]
    for _ in range(4):
        n = len(cur)
        cur = stripfwdjmp(cur)
        cur = stripredjmp(cur)
        cur = stripmutjmp(cur)
        cur = stripbogret(cur)
        cur = stripnil(cur)
        cur = stripback(cur)
        cur = remapjmp(cur)
        if len(cur) == n:
            break
    cur = remapjmp(cur)
    cur = linstcff(cur)
    return remapjmp(cur)

def jmpstats(ops):
    jmps = sum(1 for op in ops if op.get('name') == 'JMP')
    cleaned = cleancfg(ops)
    return {'jmps': jmps, 'removed': len(ops) - len(cleaned), 'before': len(ops), 'after': len(cleaned)}

def indof(line):
    i = 0
    while line[i] == ' ':
        i += 1
    return line[:i]

def isnoise(e):
    if e is None:
        return True
    t = str(e)
    if not t or t in ('nil','null','0'):
        return True
    if t.startswith('nil[') or t.startswith('nil.') or t.startswith('null[') or t.startswith('null.'):
        return True
    if t.startswith('0['):
        return True
    if t.startswith('{}('):
        return True
    return False

def anpruse(proto, ops):
    loadkstr = 0
    loadknum = 0
    getg = 0
    getf = 0
    getu = 0
    calls = 0
    setg = 0
    sett = 0
    newt = 0
    clos = 0
    loops = 0
    rets = 0
    for op in ops:
        n = op.get('name', '')
        if n == 'LOADK':
            if isinstance(op.get('B'), str) and op['B']:
                loadkstr += 1
            elif isinstance(op.get('B'), (int, float)):
                loadknum += 1
        elif n == 'GETGLOBAL':
            getg += 1
        elif n in ('GETTABLE','SELF'):
            getf += 1
        elif n == 'GETUPVAL':
            getu += 1
        elif n in ('CALL','TAILCALL'):
            calls += 1
        elif n == 'SETGLOBAL':
            setg += 1
        elif n == 'SETTABLE':
            sett += 1
        elif n == 'NEWTABLE':
            newt += 1
        elif n == 'CLOSURE':
            clos += 1
        elif n in ('FORPREP','FORLOOP','TFORLOOP'):
            loops += 1
        elif n == 'RETURN':
            rets += 1
    interesting = loadkstr > 0 or setg > 0 or sett > 0 or (newt > 0 and (sett > 0 or loops > 0)) or (calls > 0 and loadkstr + setg + sett + newt > 0) or (clos > 0 and calls > 0)
    xorstub = loadkstr == 0 and setg == 0 and sett == 0 and getu >= 1 and (getg + getf) >= 2 and (loops > 0 or calls > 0)
    return {
        'loadkstr': loadkstr, 'loadknum': loadknum, 'getg': getg, 'getf': getf,
        'getu': getu, 'calls': calls, 'setg': setg, 'sett': sett, 'newt': newt,
        'clos': clos, 'loops': loops, 'rets': rets, 'interesting': interesting,
        'xorStub': xorstub,
        'score': loadkstr * 12 + setg * 15 + sett * 8 + newt * 3 + clos * 4 + (10 if calls > 0 and loadkstr > 0 else 0) + (-40 if xorstub else 0) + (5 if interesting else 0)
    }

def parseasg(t):
    if t[0] != 'r':
        return None
    i = 1
    if i >= len(t) or not t[i].isdigit():
        return None
    while i < len(t) and t[i].isdigit():
        i += 1
    if t[i:i+3] != ' = ':
        return None
    return {'lhs': t[:i], 'rhs': t[i+3:]}

def colregs(text, into):
    i = 0
    while i < len(text):
        if text[i] != 'r':
            i += 1
            continue
        if i > 0:
            p = text[i-1]
            if p.isalpha() or p.isdigit() or p == '_':
                i += 1
                continue
        j = i + 1
        if j >= len(text) or not text[j].isdigit():
            i += 1
            continue
        while j < len(text) and text[j].isdigit():
            j += 1
        n = text[j] if j < len(text) else ''
        if n and (n.isalpha() or n == '_'):
            i = j
            continue
        into.add(text[i:j])
        i = j - 1
    return into

def rhscall(rhs):
    i = 0
    while i < len(rhs):
        c = rhs[i]
        if c == '"' or c == "'":
            q = c
            i += 1
            while i < len(rhs) and rhs[i] != q:
                if rhs[i] == '\\':
                    i += 1
                i += 1
            continue
        if c == '(':
            return True
        i += 1
    return False

def labexists(lines, lab):
    needle = '::' + lab + '::'
    return any(line.strip() == needle for line in lines)

def dropemptyif(lines):
    out = []
    i = 0
    while i < len(lines):
        t = lines[i].strip()
        if t.startswith('if ') and t.endswith(' then'):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip() == 'end' and lines[j].startswith(' ' * (len(lines[i]) - len(lines[i].lstrip()))):
                i = j
                continue
        out.append(lines[i])
        i += 1
    return out

def finlines(lines):
    used = set()
    keep = [False] * len(lines)
    demote = [False] * len(lines)
    for i in range(len(lines)-1, -1, -1):
        t = lines[i].strip()
        if not t:
            keep[i] = False
            continue
        if t.startswith('--'):
            keep[i] = True
            continue
        if t.startswith('::') and t.endswith('::'):
            keep[i] = used.issuperset({'#' + t[2:-2]})
            continue
        if t.startswith('goto '):
            lab = t[5:]
            if not labexists(lines, lab):
                keep[i] = False
                continue
            keep[i] = True
            used.add('#' + lab)
            continue
        asg = parseasg(t)
        if asg:
            live = asg['lhs'] in used
            call = rhscall(asg['rhs'])
            keepbind = asg['rhs'].startswith('{') or isid1(asg['rhs'])
            if live or keepbind:
                keep[i] = True
                used.discard(asg['lhs'])
                colregs(asg['rhs'], used)
            elif call:
                keep[i] = True
                demote[i] = True
                colregs(asg['rhs'], used)
            else:
                keep[i] = False
            continue
        keep[i] = True
        colregs(t, used)
    out = []
    for i, line in enumerate(lines):
        if not keep[i]:
            continue
        raw = lines[i]
        if demote[i]:
            asg = parseasg(raw.strip())
            if asg:
                out.append(raw[:len(raw)-len(raw.lstrip())] + asg['rhs'])
                continue
        out.append(raw)
    return dropemptyif(out)

def escstr(s):
    return json.dumps(str(s))

def fmtk(v):
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        if math.isnan(v) or math.isinf(v):
            return str(v)
        if isinstance(v, int):
            return str(v)
        return str(v)
    if v is None:
        return 'nil'
    return json.dumps(str(v))

def reg(n):
    return f'r{n}'

def annpr(proto, opmap, closelocalop):
    out = []
    instructions = proto.get('instructions', [])
    i = 1
    while i < len(instructions):
        ins = instructions[i]
        if not ins or ins.get('skipped'):
            i += 1
            continue
        ins['_index'] = i
        info = opmap.get(ins['opcode'], {'name': 'UNKNOWN'})
        name = info['name']
        if name == 'GETGLOBAL_OR_UPVAL':
            name = 'GETGLOBAL'
        if name == 'UNKNOWN':
            name = guessop(ins)
        name = prefnm(name, ins, proto, closelocalop, opmap)
        if name == 'CALL' and isinstance(ins.get('B'), (int, float)) and ins['B'] >= 1 and ins.get('C') == 1:
            sawtable = False
            loads = 0
            for j in range(i-1, max(1, i-12)-1, -1):
                p = instructions[j] if j < len(instructions) else None
                if not p or p.get('skipped'):
                    continue
                pn = prefnm(opmap.get(p['opcode'], {}).get('name', 'UNKNOWN'), p, proto, closelocalop, opmap)
                if pn == 'NEWTABLE' and p['A'] == ins['A']:
                    sawtable = True
                    break
                if pn in ('LOADK','MOVE','LOADBOOL'):
                    if isinstance(p['A'], (int, float)) and p['A'] > ins['A'] and p['A'] <= ins['A'] + ins['B']:
                        loads += 1
                    continue
                break
            if sawtable and loads >= 1:
                name = 'SETLIST'
        if name == 'SETLIST' and isinstance(ins.get('B'), (int, float)) and isinstance(ins.get('A'), (int, float)) and ins['B'] > ins['A'] + 8:
            name = 'CALL'
        if name == 'SELF' and isinstance(ins.get('C'), (int, float)) and ins['C'] > 0 and isinstance(ins.get('B'), (int, float)):
            protoidx = ins['B']
            if protoidx >= 0 and protoidx < len(proto.get('prototypes', [])) and proto['prototypes'][protoidx]:
                looksup = True
                for u in range(ins['C']):
                    nxt = instructions[i + 1 + u] if i + 1 + u < len(instructions) else None
                    if not nxt or nxt.get('skipped'):
                        looksup = False
                        break
                    n = opmap.get(nxt['opcode'], {}).get('name', '')
                    if closelocalop is not None and nxt.get('opcode') == closelocalop:
                        continue
                    if n in ('MOVE','GETUPVAL'):
                        continue
                    if nxt.get('mode') == 0 and not nxt.get('iskb') and not nxt.get('iskc'):
                        continue
                    looksup = False
                    break
                if looksup:
                    name = 'CLOSURE'
        if name in ('TAILCALL','RETURN') and ins.get('B') == 0 and (ins.get('C') == 0 or ins.get('C') is None) and i + 3 < len(instructions):
            mapname = opmap.get(ins['opcode'], {}).get('name', 'UNKNOWN')
            if mapname not in ('RETURN','TAILCALL'):
                shape = shpguess(ins, proto, closelocalop, opmap)
                if not shape or shape['conf'] < 60 or shape['name'] == 'UNKNOWN':
                    name = mapname if mapname != 'UNKNOWN' else 'MOVE'
        if name == 'CLOSURE':
            nups = ins['C'] if isinstance(ins.get('C'), (int, float)) else 0
            pidx = ins['B'] if isinstance(ins.get('B'), (int, float)) else -1
            if nups < 0 or nups > 32 or not proto or pidx < 0 or pidx >= len(proto.get('prototypes', [])) or not proto['prototypes'][pidx]:
                name = 'UNKNOWN'
            else:
                upvals = []
                for u in range(nups):
                    nxt = instructions[i + 1 + u] if i + 1 + u < len(instructions) else None
                    if not nxt or nxt.get('skipped'):
                        continue
                    islocal = (closelocalop is not None and nxt.get('opcode') == closelocalop) or (opmap.get(nxt.get('opcode'), {}).get('name') == 'MOVE')
                    upvals.append({'islocal': bool(islocal), 'idx': nxt.get('B')})
                out.append({
                    'index': i,
                    'opcode': ins['opcode'],
                    'name': name,
                    'A': ins['A'],
                    'B': ins['B'],
                    'C': ins['C'],
                    'iska': ins.get('iska'),
                    'iskb': ins.get('iskb'),
                    'iskc': ins.get('iskc'),
                    'mode': ins.get('mode'),
                    'upvals': upvals,
                    'skip': nups,
                })
                i += 1 + nups
                continue
        out.append({
            'index': i,
            'opcode': ins['opcode'],
            'name': name,
            'A': ins['A'],
            'B': ins['B'],
            'C': ins['C'],
            'iska': ins.get('iska'),
            'iskb': ins.get('iskb'),
            'iskc': ins.get('iskc'),
            'mode': ins.get('mode'),
        })
        i += 1
    return out

def idxork(v, isk):
    if isinstance(v, str) or isk:
        return fmtk(v)
    if isinstance(v, (int, float)):
        return reg(v)
    return fmtk(v)

def liftins(ins, protoname):
    A = ins['A']
    B = ins['B']
    C = ins['C']
    ra = reg(A) if isinstance(A, (int, float)) else fmtk(A)
    if ins['name'] == 'MOVE':
        return f'{ra} = {reg(B)}'
    if ins['name'] == 'LOADK':
        return f'{ra} = {fmtk(B)}'
    if ins['name'] == 'LOADBOOL':
        return f'{ra} = {"true" if B else "false"}'
    if ins['name'] == 'LOADNIL':
        to = B if isinstance(B, (int, float)) else A
        return '; '.join(f'{reg(i)} = nil' for i in range(A, to+1))
    if ins['name'] == 'GETUPVAL':
        return f'{ra} = upval_{B}'
    if ins['name'] == 'GETGLOBAL':
        return f'{ra} = _ENV[{fmtk(B)}]'
    if ins['name'] == 'GETTABLE':
        return f'{ra} = {reg(B)}[{idxork(C, ins.get("iskc"))}]'
    if ins['name'] == 'SETGLOBAL':
        return f'_ENV[{fmtk(B)}] = {ra}'
    if ins['name'] == 'SETUPVAL':
        return f'upval_{B} = {ra}'
    if ins['name'] == 'SETTABLE':
        return f'{reg(A)}[{idxork(B, ins.get("iskb"))}] = {idxork(C, ins.get("iskc"))}'
    if ins['name'] == 'NEWTABLE':
        return f'{ra} = {{}}'
    if ins['name'] == 'SELF':
        return f'{reg(A+1)} = {reg(B)}; {ra} = {reg(B)}[{idxork(C, ins.get("iskc"))}]'
    if ins['name'] == 'ADD':
        return f'{ra} = {reg(B)} + {reg(C)}'
    if ins['name'] == 'SUB':
        return f'{ra} = {reg(B)} - {reg(C)}'
    if ins['name'] == 'MUL':
        return f'{ra} = {reg(B)} * {reg(C)}'
    if ins['name'] == 'DIV':
        return f'{ra} = {reg(B)} / {reg(C)}'
    if ins['name'] == 'MOD':
        return f'{ra} = {reg(B)} % {reg(C)}'
    if ins['name'] == 'POW':
        return f'{ra} = {reg(B)} ^ {reg(C)}'
    if ins['name'] == 'UNM':
        return f'{ra} = -{reg(B)}'
    if ins['name'] == 'NOT':
        return f'{ra} = not {reg(B)}'
    if ins['name'] == 'LEN':
        return f'{ra} = #{reg(B)}'
    if ins['name'] == 'CONCAT':
        return f'{ra} = {reg(B)} .. {reg(C)}'
    if ins['name'] == 'JMP':
        return f'goto lbl_{B}'
    if ins['name'] in ('EQ','LT','LE'):
        sym = {'EQ':'==','LT':'<','LE':'<='}[ins['name']]
        return f'if {ra} {sym} {fmtk(C)} then else goto lbl_{B} end'
    if ins['name'] == 'TEST':
        return f'if {ra} then else goto lbl_{B} end'
    if ins['name'] == 'CALL':
        if B is None or B == 0:
            return f'{ra} = {ra}({reg(A+1)}, ...)'
        if B == 1:
            return f'{ra} = {ra}()'
        if isinstance(B, (int, float)) and B >= 2:
            args = [reg(i) for i in range(A+1, A+B)]
            return f'{ra} = {ra}({", ".join(args)})'
        return f'{ra} = {ra}()'
    if ins['name'] == 'TAILCALL':
        if B == 1:
            return f'return {ra}()'
        if isinstance(B, (int, float)) and B >= 2:
            args = [reg(i) for i in range(A+1, A+B)]
            return f'return {ra}({", ".join(args)})'
        return f'return {ra}()'
    if ins['name'] == 'RETURN':
        if B == 1 or B == 0:
            return 'return'
        if isinstance(B, (int, float)) and B > 1:
            vals = [reg(i) for i in range(A, A+B-1)]
            return f'return {", ".join(vals)}'
        return f'return {ra}'
    if ins['name'] == 'CLOSURE':
        return f'{ra} = {protoname}_f{B}'
    if ins['name'] in ('SETLIST','VARARG','CLOSE'):
        return 'do end'
    return 'do end'

def liftpr(proto, opmap, closelocalop, protoname='main', indent=0):
    sp = '  ' * indent
    lines = []
    annotated = annpr(proto, opmap, closelocalop)
    params = [reg(p) for p in range(proto['params'])]
    lines.append(f'{sp}function {protoname}({", ".join(params)})')
    for pi, child in enumerate(proto.get('prototypes', [])):
        if child:
            lines.append(liftpr(child, opmap, closelocalop, f'{protoname}_f{pi}', indent+1))
    labels = set()
    for ins in annotated:
        if ins['name'] in ('JMP','EQ','LT','LE','TEST') and isinstance(ins.get('B'), (int, float)):
            labels.add(ins['B'])
    for ins in annotated:
        if ins['index'] in labels:
            lines.append(f'{sp}  ::lbl_{ins["index"]}::')
        lines.append(f'{sp}  {liftins(ins, protoname)}')
    lines.append(f'{sp}end')
    return '\n'.join(lines)

def liftprog(root, opmap, closelocalop):
    return liftpr(root, opmap, closelocalop, 'main', 0) + '\n\nreturn main()'

def disasmpr(proto, opmap, closelocalop, name='main', indent=0):
    sp = '  ' * indent
    lines = []
    lines.append(f'{sp}.proto {name} params={proto["params"]}')
    consts = [f'{i}={fmtk(c)}' for i, c in enumerate(proto.get('constants', [])) if i > 0 and c is not None]
    if consts:
        lines.append(f'{sp}.constants {", ".join(consts)}')
    annotated = annpr(proto, opmap, closelocalop)
    for ins in annotated:
        extra = f' upvals={json.dumps(ins["upvals"])}' if 'upvals' in ins else ''
        lines.append(f'{sp}[{str(ins["index"]).rjust(3)}] {ins["name"].ljust(10)} A={json.dumps(ins["A"])} B={json.dumps(ins["B"])} C={json.dumps(ins["C"])}{extra}')
    for pi, child in enumerate(proto.get('prototypes', [])):
        if child:
            lines.append(disasmpr(child, opmap, closelocalop, f'{name}_f{pi}', indent+1))
    return '\n'.join(lines)

def isid1(s):
    if not isinstance(s, str) or not s:
        return False
    if not (s[0].isalpha() or s[0] == '_'):
        return False
    return all(c.isalnum() or c == '_' for c in s)

def ind(n):
    return '  ' * n

def gname(key):
    if isid1(key):
        return key
    return f'_ENV[{fmtk(key)}]'

def field(base, key, isk):
    if (isinstance(key, str) or isk) and isid1(key):
        return f'{base}.{key}'
    if isinstance(key, str) or isk:
        return f'{base}[{fmtk(key)}]'
    if isinstance(key, (int, float)) and isk:
        return f'{base}[{key}]'
    if isinstance(key, (int, float)):
        return f'{base}[{reg(key)}]'
    return f'{base}[{fmtk(key)}]'

def lit(v):
    if isinstance(v, str):
        return fmtk(v)
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return 'nil'
    return fmtk(str(v))

def rk(v, isk, regs):
    if isk or isinstance(v, (str, bool)):
        return lit(v)
    if v is None:
        return 'nil'
    if isinstance(v, (int, float)):
        return regs.get(v) or reg(v)
    return lit(v)

def callargs(op, regs, defined):
    A, B, C = op['A'], op['B'], op['C']
    if isinstance(B, (int, float)) and A+1 <= B <= A+8 and (C == 0 or C is None or C == 1 or C == 2):
        out = []
        for r in range(A+1, B+1):
            e = regs.get(r) or reg(r)
            if defined and e == reg(r) and r not in defined:
                continue
            if e == 'nil':
                continue
            out.append(e)
        return out
    if B is None or B == 0:
        if defined and (A+1) in defined:
            e = regs.get(A+1) or reg(A+1)
            if e != 'nil':
                return [e]
        for r in range(A+2, A+9):
            if not defined or r not in defined:
                continue
            e = regs.get(r) or reg(r)
            if e != 'nil':
                return [e]
        return []
    if B == 1:
        return []
    if isinstance(B, (int, float)) and B >= 2:
        out = []
        for r in range(A+1, A+B):
            e = regs.get(r) or reg(r)
            if defined and e == reg(r) and r not in defined:
                continue
            out.append(e)
        while out and out[-1] == 'nil':
            out.pop()
        while out and out[0] == 'nil':
            out.pop(0)
        return out
    return []

def jmptgts(ops):
    t = set()
    for op in ops:
        if op['name'] in ('JMP','EQ','LT','LE','TEST','TESTSET','FORLOOP','FORPREP') and isinstance(op.get('B'), (int, float)):
            t.add(op['B'])
    return t

def byidx(ops):
    return {op['index']: i for i, op in enumerate(ops)}

def cmpsym(n):
    return {'EQ':'==','LT':'<','LE':'<='}.get(n)

def tidy(lines):
    text = '\n'.join(lines)
    out = []
    dead = False
    for i, line in enumerate(lines):
        t = line.strip()
        if not t:
            continue
        if t.startswith('::') and t.endswith('::'):
            dead = False
            lab = t[2:-2]
            if f'goto {lab}' not in text:
                continue
            out.append(line)
            continue
        if dead:
            continue
        if t == 'return' and out and out[-1].strip().startswith('return'):
            continue
        if t.startswith('goto L'):
            lab = t[5:]
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip() == f'::{lab}::':
                continue
            out.append(line)
            dead = True
            continue
        if t == 'return' or t.startswith('return '):
            out.append(line)
            dead = True
            continue
        out.append(line)
    return out

def foldln(lines):
    out = []
    i = 0
    while i < len(lines):
        a = matchasg(lines[i])
        b = None
        if i+1 < len(lines):
            b = matchasg(lines[i+1])
        if a and b and a['left'] == b['left']:
            if b['right'].startswith(a['left'] + '.') or b['right'].startswith(a['left'] + '['):
                out.append(f"{a['ind']}{a['left']} = {a['right']}{b['right'][len(a['left']):]}")
                i += 1
            else:
                out.append(lines[i])
        else:
            out.append(lines[i])
        i += 1
    return out

def matchasg(line):
    i = 0
    while i < len(line) and line[i] == ' ':
        i += 1
    if line[i] != 'r':
        return None
    j = i + 1
    while j < len(line) and line[j].isdigit():
        j += 1
    left = line[i:j]
    if line[j:j+3] != ' = ':
        return None
    return {'ind': line[:i], 'left': left, 'right': line[j+3:]}

def isplnline(s):
    if not s or not s[0].isalpha():
        return False
    return all(c.isalnum() or c == '_' for c in s)

def fnnmof(src):
    i = src.find('function ')
    if i < 0:
        return None
    j = i + 9
    if src.startswith('local function ', i):
        j = i + 15
    k = j
    while k < len(src) and src[k] != '(':
        k += 1
    name = src[j:k].strip()
    return name or None

def isemptyfn(src):
    flat = colws(src).strip()
    if 'while true do' not in flat:
        return False
    if 'while true do end' in flat:
        return True
    if 'while true do {} end' in flat:
        return True
    if 'while true do table.insert({}) end' in flat:
        return True
    a = flat.find('while true do')
    if a < 0:
        return False
    b = flat.rfind('end')
    if b <= a:
        return False
    body = flat[a+13:b].strip()
    return not body or body == '{}' or body == 'table.insert({})'

def defups(proto, opmap, closelocalop):
    ops = annpr(proto, opmap, closelocalop)
    max_ = -1
    for op in ops:
        if op['name'] in ('GETUPVAL','SETUPVAL') and isinstance(op.get('B'), (int, float)) and op['B'] > max_:
            max_ = op['B']
    return [f'up{i}' for i in range(max_+1)]

def parsenum(t):
    if not t:
        return None
    i = 0
    neg = False
    if t[i] == '-':
        neg = True
        i += 1
    if i >= len(t) or not t[i].isdigit():
        return None
    j = i
    while j < len(t) and t[j].isdigit():
        j += 1
    if t[j] == '.':
        j += 1
        if j >= len(t) or not t[j].isdigit():
            return None
        while j < len(t) and t[j].isdigit():
            j += 1
    if j != len(t):
        return None
    n = float(t[i:j])
    return -n if neg else n

def parsebin(t, op):
    s = t.strip()
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1].strip()
    for i in range(1, len(s)):
        if s[i] == op[0] and (len(op) == 1 or s[i:i+len(op)] == op):
            left = parsenum(s[:i].strip())
            right = parsenum(s[i+len(op):].strip())
            if left is not None and right is not None:
                return left + right if op == '+' else left - right
    return None

def parsestat(expr):
    if isinstance(expr, (int, float)):
        return expr
    if not isinstance(expr, str):
        return None
    t = expr.strip()
    n = parsenum(t)
    if n is not None:
        return n
    if t == 'true':
        return True
    if t == 'false':
        return False
    add = parsebin(t, '+')
    if add is not None:
        return add
    sub = parsebin(t, '-')
    if sub is not None:
        return sub
    return None

def evalcmp(name, left, right):
    a = parsestat(left)
    b = parsestat(right)
    if a is None or b is None:
        return None
    if name == 'EQ':
        return a == b
    if name == 'LT':
        return a < b
    if name == 'LE':
        return a <= b
    return None

def cmpl(op, regs):
    if op.get('iska') and isinstance(op.get('A'), (int, float)):
        return lit(op['A'])
    return regs.get(op['A']) or reg(op['A'])

def cmpr(op, regs):
    if op['name'] == 'TEST':
        return None
    if op.get('iska') and isinstance(op.get('C'), (int, float)) and not op.get('iskc'):
        return regs.get(op['C']) or reg(op['C'])
    return rk(op['C'], op.get('iskc', False), regs)

def trynumfor(ops, i, idx, targets, regs, defined, depth, upvals, childnames, closurebinds):
    op = ops[i]
    if op['name'] != 'FORPREP' or not isinstance(op.get('B'), (int, float)):
        return None
    loopI = idx.get(op['B'])
    if loopI is None or loopI <= i:
        return None
    loopOp = ops[loopI]
    if not loopOp or loopOp['name'] != 'FORLOOP':
        return None
    A = op['A']
    init = regs.get(A) or reg(A)
    limit = regs.get(A+1) or reg(A+1)
    step = regs.get(A+2) or reg(A+2)
    varR = A + 3
    sp = '  ' * depth
    bodyregs = dict(regs)
    bodydef = set(defined)
    bodyregs[varR] = reg(varR)
    bodydef.add(varR)
    bodydef.add(A)
    bodydef.add(A+1)
    bodydef.add(A+2)
    ne = matcnns(ops, i+1, loopI, varR, bodyregs)
    if ne:
        bodylines = ['  ' * (depth+1) + ne]
    else:
        bodylines = emitsl(ops, i+1, loopI, bodyregs, bodydef, depth+1, upvals, childnames, closurebinds, targets)
        neat = recnestone(bodylines, varR)
        if neat:
            bodylines = neat
    steplit = parsestat(step)
    header = f"{sp}for {reg(varR)} = {init}, {limit} do" if (steplit == 1 or step == '1') else f"{sp}for {reg(varR)} = {init}, {limit}, {step} do"
    for k, v in bodyregs.items():
        regs[k] = v
    for k in bodydef:
        defined.add(k)
    return {'lines': [header] + bodylines + [f'{sp}end'], 'next': loopI + 1}

def matcnns(ops, from_, to, varR, regs):
    vr = reg(varR)
    for i in range(from_, to-2):
        eq = ops[i]
        if not eq or eq['name'] != 'EQ' or not eq.get('iska'):
            continue
        left = cmpl(eq, regs)
        right = cmpr(eq, regs)
        if str(left) != '1' and left != 1:
            continue
        if right != vr:
            continue
        fb = None
        tb = None
        st = None
        for j in range(i+1, to):
            o = ops[j]
            if not o:
                continue
            if o['name'] == 'JMP':
                continue
            if o['name'] == 'LOADBOOL' and o['B'] == 0 and fb is None:
                fb = o
                continue
            if o['name'] == 'LOADBOOL' and o['B'] == 1 and fb is not None and tb is None:
                tb = o
                continue
            if o['name'] == 'SETTABLE' and fb is not None and tb is not None and o['B'] == varR and o['C'] == fb['A']:
                st = o
                break
            if o['name'] == 'SETTABLE' and fb is not None and tb is not None and o['B'] == varR:
                st = o
                break
            if o['name'] not in ('LOADBOOL','EQ','JMP') and st is None and tb is not None:
                break
        if st:
            base = regs.get(st['A']) or reg(st['A'])
            return f'{base}[{vr}] = (1 ~= {vr})'
    return None

def leadws(s):
    return s[:len(s)-len(s.lstrip())]

def isfalsasg(a):
    if not a or len(a) < 10:
        return None
    if not a.startswith('r') or not a.endswith(' = false'):
        return None
    i = 1
    while i < len(a) and a[i].isdigit():
        i += 1
    if i == 1 or a[i:] != ' = false':
        return None
    return a[1:i]

def istrueasg(a, n):
    return a == f'r{n} = true'

def isstorefr(a, n, vr):
    needle = f'[{vr}] = r{n}'
    k = a.find(needle)
    if k <= 0:
        return None
    left = a[:k]
    if not left.startswith('r'):
        return None
    i = 1
    while i < len(left) and left[i].isdigit():
        i += 1
    if i != len(left):
        return None
    return left

def recnestone(lines, varR):
    if not lines or len(lines) < 1:
        return None
    vr = reg(varR)
    out = []
    i = 0
    changed = False
    while i < len(lines):
        a = lines[i].strip() if lines[i] else None
        b = lines[i+1].strip() if i+1 < len(lines) else None
        c = lines[i+2].strip() if i+2 < len(lines) else None
        n = isfalsasg(a)
        okT = n and b and istrueasg(b, int(n))
        left = okT and c and isstorefr(c, int(n), vr)
        if n and okT and left:
            out.append(f"{leadws(lines[i+2])}{left}[{vr}] = (1 ~= {vr})")
            i += 3
            changed = True
            continue
        if a and a.startswith('if 1 == ') and 'then else goto' in a:
            i += 1
            changed = True
            continue
        out.append(lines[i])
        i += 1
    return out if changed else None

def trygenfor(ops, i, idx, targets, regs, defined, depth, upvals, childnames, closurebinds):
    op = ops[i]
    if not (op['name'] == 'CALL' or (op['name'] == 'TFORLOOP' and op.get('mode') != 3)):
        return None
    jmp = ops[i+1] if i+1 < len(ops) else None
    if not jmp or jmp['name'] != 'JMP' or not isinstance(jmp.get('B'), (int, float)):
        return None
    A = op['A']
    tforI = None
    for j in range(i+2, len(ops)):
        n = ops[j]
        if n['name'] == 'TFORLOOP' and (n.get('mode') == 3 or isinstance(n.get('B'), (int, float))) and n['A'] == A:
            tforI = j
            if n.get('mode') == 3:
                break
    if tforI is None:
        return None
    tfor = ops[tforI]
    nvars = min(tfor['C'] if isinstance(tfor.get('C'), (int, float)) and tfor['C'] > 0 else 2, 4)
    bodystart = i + 2
    bodyend = tforI
    bodyregs = dict(regs)
    bodydef = set(defined)
    gen = bodyregs.get(A) or reg(A)
    state = bodyregs.get(A+1) or reg(A+1)
    for v in range(nvars):
        bodydef.add(A + 3 + v)
        bodyregs[A + 3 + v] = reg(A + 3 + v)
    bodylines = emitsl(ops, bodystart, bodyend, bodyregs, bodydef, depth+1, upvals, childnames, closurebinds, targets)
    sp = '  ' * depth
    vars_ = [reg(A + 3 + v) for v in range(nvars)]
    iterExpr = None
    callfn = regs.get(A)
    if isinstance(callfn, str) and 'pairs' in callfn:
        iterExpr = callfn if '(' in callfn else f"{callfn}({regs.get(A+1) or reg(A+1)})"
    elif callfn == 'pairs' or regs.get(A) == 'pairs':
        iterExpr = f"pairs({regs.get(A+1) or state})"
    else:
        prev = regs.get(A)
        if isinstance(prev, str) and prev.startswith('pairs('):
            iterExpr = prev
    if not iterExpr:
        iterExpr = f"{getreg(regs, A)}({getreg(regs, A+1)})"
    fnbefore = regs.get(A)
    argbefore = regs.get(A+1)
    if fnbefore == 'pairs' and argbefore:
        iterExpr = f"pairs({argbefore})"
    elif isinstance(fnbefore, str) and fnbefore.startswith('pairs('):
        iterExpr = fnbefore
    for k, v in bodyregs.items():
        regs[k] = v
    for k in bodydef:
        defined.add(k)
    next_ = tforI + 1
    if next_ < len(ops) and ops[next_]['name'] == 'JMP' and isinstance(ops[next_].get('B'), (int, float)):
        back = idx.get(ops[next_]['B'])
        if back is not None and i <= back <= tforI:
            next_ += 1
    return {'lines': [f"{sp}for {', '.join(vars_)} in {iterExpr} do"] + bodylines + [f"{sp}end"], 'next': next_}

def getreg(regs, r):
    return regs.get(r) or reg(r)

def thentii(ops, elseI):
    t = ops[elseI] if elseI < len(ops) else None
    if not t:
        return False
    if t['name'] in ('JMP','RETURN','EQ','LT','LE','TEST'):
        return False
    if t['name'] in ('FORLOOP','FORPREP'):
        return False
    n = ops[elseI+1] if elseI+1 < len(ops) else None
    if not n:
        return False
    if t['name'] == 'TFORLOOP':
        return False
    if n['name'] in ('TFORLOOP','FORLOOP'):
        return True
    if t['name'] == 'CALL' and n['name'] in ('TFORLOOP','JMP'):
        return True
    if t['name'] == 'SETTABLE' and n['name'] in ('FORLOOP','JMP'):
        return True
    return False

def iste(ops, elseI):
    if elseI is None or elseI >= len(ops):
        return False
    a = ops[elseI]
    b = ops[elseI+1] if elseI+1 < len(ops) else None
    if not a:
        return False
    if a['name'] == 'GETTABLE' and b and b['name'] == 'RETURN':
        return elseI + 2 >= len(ops)
    if a['name'] == 'RETURN' and elseI + 1 >= len(ops):
        return True
    return False

def tryif(ops, i, idx, targets, regs, defined, depth, upvals, childnames, closurebinds):
    op = ops[i]
    if op['name'] not in ('EQ','LT','LE','TEST') or not isinstance(op.get('B'), (int, float)):
        return None
    elseI = idx.get(op['B'])
    if elseI is None or elseI <= i:
        return None
    inclusivethen = thentii(ops, elseI)
    thenEnd = elseI + 1 if inclusivethen else elseI
    joinPc = None
    elseAnchor = elseI + 1 if inclusivethen else elseI
    beforeElse = ops[elseAnchor - 1] if elseAnchor > 0 else None
    if not inclusivethen and beforeElse and beforeElse['name'] == 'JMP' and isinstance(beforeElse.get('B'), (int, float)) and beforeElse['B'] > op['B']:
        joinPc = beforeElse['B']
        thenEnd = elseI - 1
    sp = '  ' * depth
    left = cmpl(op, regs)
    right = cmpr(op, regs)
    if op['name'] == 'EQ' and left == right:
        thenregs = dict(regs)
        thendef = set(defined)
        thenlines = emitsl(ops, i+1, thenEnd, thenregs, thendef, depth, upvals, childnames, closurebinds, targets)
        nxt = idx.get(joinPc) if joinPc is not None else elseAnchor
        if nxt is None:
            return None
        if joinPc is None and iste(ops, elseAnchor):
            nxt = len(ops)
        if not thenlines and iste(ops, elseAnchor):
            elselines = emitsl(ops, elseAnchor, len(ops), dict(regs), set(defined), depth, upvals, childnames, closurebinds, targets)
            return {'lines': elselines, 'next': len(ops)}
        return {'lines': thenlines, 'next': nxt}
    if op['name'] != 'TEST':
        hit = evalcmp(op['name'], left, right)
        if hit is True:
            thenregs = dict(regs)
            thendef = set(defined)
            thenlines = emitsl(ops, i+1, thenEnd, thenregs, thendef, depth, upvals, childnames, closurebinds, targets)
            for k, v in thenregs.items():
                regs[k] = v
            for k in thendef:
                defined.add(k)
            nxt = idx.get(joinPc) if joinPc is not None else elseAnchor
            if nxt is None:
                nxt = elseAnchor
            return {'lines': thenlines, 'next': nxt}
        if hit is False:
            nxt = idx.get(joinPc) if joinPc is not None else elseAnchor
            if nxt is None:
                return None
            if joinPc is not None and not iste(ops, elseAnchor):
                elseregs = dict(regs)
                elsedef = set(defined)
                elselines = emitsl(ops, elseAnchor, nxt, elseregs, elsedef, depth, upvals, childnames, closurebinds, targets)
                for k, v in elseregs.items():
                    regs[k] = v
                return {'lines': elselines, 'next': nxt}
            return {'lines': [], 'next': nxt}
    cond = left if op['name'] == 'TEST' else f'{left} {cmpsym(op["name"])} {right}'
    thenregs = dict(regs)
    thendef = set(defined)
    thenlines = emitsl(ops, i+1, thenEnd, thenregs, thendef, depth+1, upvals, childnames, closurebinds, targets)
    if inclusivethen:
        return {'lines': [f'{sp}if {cond} then'] + thenlines + [f'{sp}end'], 'next': elseAnchor}
    if joinPc is not None:
        joinI = idx.get(joinPc)
        if joinI is None:
            return None
        if iste(ops, elseI):
            flat = emitsl(ops, i+1, thenEnd, dict(regs), set(defined), depth, upvals, childnames, closurebinds, targets)
            return {'lines': flat, 'next': joinI}
        elseregs = dict(regs)
        elsedef = set(defined)
        elselines = emitsl(ops, elseI, joinI, elseregs, elsedef, depth+1, upvals, childnames, closurebinds, targets)
        lines = [f'{sp}if {cond} then'] + thenlines
        if elselines:
            lines.append(f'{sp}else')
            lines.extend(elselines)
        lines.append(f'{sp}end')
        return {'lines': lines, 'next': joinI}
    if thenEnd > i + 1:
        if iste(ops, elseI):
            flat = emitsl(ops, i+1, thenEnd, dict(regs), set(defined), depth, upvals, childnames, closurebinds, targets)
            return {'lines': flat, 'next': len(ops)}
        return {'lines': [f'{sp}if {cond} then'] + thenlines + [f'{sp}end'], 'next': elseI}
    if not thenlines or thenEnd == i + 1:
        elseregs = dict(regs)
        elsedef = set(defined)
        elselines = emitsl(ops, elseI, len(ops), elseregs, elsedef, depth, upvals, childnames, closurebinds, targets)
        if iste(ops, elseI):
            return {'lines': elselines, 'next': len(ops)}
        return {'lines': [], 'next': elseI}
    return None

def emitsl(ops, from_, to, regs, defined, depth, upvals, childnames, closurebinds, targets):
    lines = []
    idx = byidx(ops)
    i = from_
    while i < to:
        op = ops[i] if i < len(ops) else None
        if not op:
            i += 1
            continue
        if op['index'] in targets:
            lines.append('  ' * depth + f'::L{op["index"]}::')
        asFor = trynumfor(ops, i, idx, targets, regs, defined, depth, upvals, childnames, closurebinds)
        if asFor and asFor['next'] > i:
            loopAtBoundary = asFor['next'] == to + 1 and ops[to] and ops[to]['name'] == 'FORLOOP' if to < len(ops) else False
            if asFor['next'] <= to or loopAtBoundary:
                lines.extend(asFor['lines'])
                i = to if loopAtBoundary else asFor['next']
                continue
        asGfor = trygenfor(ops, i, idx, targets, regs, defined, depth, upvals, childnames, closurebinds)
        if asGfor and asGfor['next'] > i and asGfor['next'] <= to:
            lines.extend(asGfor['lines'])
            i = asGfor['next']
            continue
        structured = tryif(ops, i, idx, targets, regs, defined, depth, upvals, childnames, closurebinds)
        if structured and structured['next'] > i and structured['next'] <= to:
            lines.extend(structured['lines'])
            i = structured['next']
            continue
        if op['name'] in ('JMP','FORLOOP','FORPREP'):
            i += 1
            continue
        em = step(op, ops, i, regs, defined, depth, upvals, childnames, closurebinds)
        if em.get('lines'):
            lines.extend(em['lines'])
        i += 1 + (em.get('skip', 0))
    return lines

def step(op, ops, i, regs, defined, depth, upvals, childnames, closurebinds):
    sp = '  ' * depth
    A = op['A']
    B = op['B']
    C = op['C']
    lines = []
    def getr(r):
        return regs.get(r) or reg(r)
    def setr(r, e, def_=True):
        regs[r] = e
        if def_:
            defined.add(r)
    if op['name'] == 'MOVE':
        setr(A, getr(B))
        return {'lines': lines, 'skip': 0}
    if op['name'] in ('LOADK','LOADBOOL'):
        if isinstance(B, str):
            if isbin(B) or B is None:
                return {'lines': lines, 'skip': 0}
        if B is None:
            return {'lines': lines, 'skip': 0}
        if op['name'] == 'LOADK' and isinstance(B, str) and isid1(B):
            if isgname(B):
                for j in range(i+1, min(i+8, len(ops))):
                    n = ops[j] if j < len(ops) else None
                    if not n:
                        break
                    if n['name'] == 'CALL' and n['A'] == A:
                        setr(A, gname(B))
                        return {'lines': lines, 'skip': 0}
                    if n['name'] in ('LOADK','LOADBOOL','GETGLOBAL','MOVE','CLOSURE','GETTABLE','SELF'):
                        continue
                    if n['name'] in ('JMP','EQ','TEST'):
                        break
                    break
        setr(A, lit(B))
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'LOADNIL':
        to = B if isinstance(B, (int, float)) else A
        for r in range(A, to+1):
            setr(r, 'nil')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'GETUPVAL':
        setr(A, upvals[B] if B < len(upvals) else f'up{B}')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'GETGLOBAL':
        if isinstance(B, str) and not isgname(B):
            asfn = False
            for j in range(i+1, min(i+5, len(ops))):
                n = ops[j] if j < len(ops) else None
                if not n:
                    break
                if n['name'] == 'CALL' and n['A'] == A:
                    asfn = True
                    break
                if n['name'] in ('LOADK','LOADBOOL','MOVE','GETUPVAL'):
                    continue
                break
            setr(A, gname(B) if asfn else lit(B))
        else:
            setr(A, gname(B))
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'GETTABLE':
        base = getr(B)
        if isnoise(base) or base in ('nil','null'):
            return {'lines': lines, 'skip': 0}
        expr = field(base, C, op.get('iskc', False))
        if isnoise(expr):
            return {'lines': lines, 'skip': 0}
        nxt = ops[i+1] if i+1 < len(ops) else None
        if nxt and nxt['name'] == 'RETURN' and isinstance(nxt.get('B'), (int, float)) and nxt['B'] <= 1:
            lines.append(f'{sp}return {expr}')
            return {'lines': lines, 'skip': 1}
        if nxt and nxt['name'] == 'RETURN' and nxt['B'] == 2 and nxt['A'] == A:
            lines.append(f'{sp}return {expr}')
            return {'lines': lines, 'skip': 1}
        setr(A, expr)
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'SETGLOBAL':
        lines.append(f'{sp}{gname(B)} = {getr(A)}')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'SETUPVAL':
        lines.append(f'{sp}{upvals[B] if B < len(upvals) else f"up{B}"} = {getr(A)}')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'SETTABLE':
        base = getr(A)
        if base == '{}':
            lines.append(f'{sp}{reg(A)} = {{}}')
            base = reg(A)
            setr(A, base)
        lines.append(f'{sp}{field(base, B, op.get("iskb", False))} = {rk(C, op.get("iskc", False), regs)}')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'NEWTABLE':
        lines.append(f'{sp}{reg(A)} = {{}}')
        setr(A, reg(A))
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'SELF':
        j = i + 1
        while j < len(ops) and j <= i + 8:
            n = ops[j] if j < len(ops) else None
            if not n:
                break
            if n['name'] == 'CALL' and n['A'] == A:
                break
            if n['name'] in ('LOADK','LOADBOOL','MOVE','GETGLOBAL','GETTABLE','GETUPVAL') and n['A'] != A:
                step(n, ops, j, regs, defined, depth, upvals, childnames, closurebinds)
                j += 1
                continue
            break
        if j < len(ops) and ops[j]['name'] == 'CALL' and ops[j]['A'] == A:
            setr(A+1, getr(B))
            args = callargs(ops[j], regs, defined)[1:]
            expr = f"{getr(B)}:{C}({', '.join(args)})" if isid1(C) else f"{field(getr(B), C, True)}({', '.join([getr(B)] + args)})"
            lines.append(f'{sp}{reg(A)} = {expr}')
            setr(A, reg(A))
            return {'lines': lines, 'skip': j - i}
        setr(A+1, getr(B))
        setr(A, field(getr(B), C, op.get('iskc', False)))
        return {'lines': lines, 'skip': 0}
    if op['name'] in ('ADD','SUB','MUL','DIV','MOD','POW'):
        sym = {'ADD':'+','SUB':'-','MUL':'*','DIV':'/','MOD':'%','POW':'^'}[op['name']]
        setr(A, f'({rk(B, op.get("iskb", False), regs)} {sym} {rk(C, op.get("iskc", False), regs)})')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'UNM':
        setr(A, f'(-{rk(B, op.get("iskb", False), regs)})')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'NOT':
        setr(A, f'(not {rk(B, op.get("iskb", False), regs)})')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'LEN':
        setr(A, f'(#{rk(B, op.get("iskb", False), regs)})')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'CONCAT':
        if isinstance(B, (int, float)) and isinstance(C, (int, float)) and C > B:
            parts = [getr(r) for r in range(B, C+1)]
            setr(A, f'({" .. ".join(parts)})')
        else:
            setr(A, f'({getr(B)} .. {getr(C)})')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'JMP':
        if isinstance(B, (int, float)):
            lines.append(f'{sp}goto L{B}')
        return {'lines': lines, 'skip': 0}
    if op['name'] in ('EQ','LT','LE'):
        sym = cmpsym(op['name'])
        if isinstance(B, (int, float)):
            left = cmpl(op, regs)
            right = cmpr(op, regs)
            if op['name'] == 'EQ' and left == right:
                skip = 1 if i+1 < len(ops) and ops[i+1]['name'] == 'JMP' else 0
                return {'lines': lines, 'skip': skip}
            if isnoise(left) or isnoise(right) or left in ('nil','null') or right in ('nil','null'):
                return {'lines': lines, 'skip': 0}
            if isinstance(A, (int, float)) and A > 32 and not op.get('iska'):
                return {'lines': lines, 'skip': 0}
            hit = evalcmp(op['name'], left, right)
            if hit is True:
                skip = 1 if i+1 < len(ops) and ops[i+1]['name'] == 'JMP' and ops[i+1]['B'] == B else 0
                return {'lines': lines, 'skip': skip}
            if hit is False:
                lines.append(f'{sp}goto L{B}')
                return {'lines': lines, 'skip': 0}
            lines.append(f'{sp}if {left} {sym} {right} then else goto L{B} end')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'TEST':
        if isinstance(B, (int, float)):
            left = getr(A)
            if isnoise(left) or left == 'nil':
                return {'lines': lines, 'skip': 0}
            lines.append(f'{sp}if {left} then else goto L{B} end')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'TESTSET':
        if not isinstance(B, (int, float)):
            return {'lines': lines, 'skip': 0}
        jmp = B
        val = getr(C) if isinstance(C, (int, float)) and C <= 255 and not op.get('iskc') else getr(A)
        if isnoise(val) or val == 'nil':
            return {'lines': lines, 'skip': 0}
        lines.append(f'{sp}if {val} then')
        lines.append(f'{sp}  {reg(A)} = {val}')
        lines.append(f'{sp}else goto L{jmp} end')
        setr(A, reg(A))
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'CALL':
        fn = getr(A)
        if A not in defined and fn == reg(A):
            return {'lines': lines, 'skip': 0}
        if isnoise(fn) or fn in ('nil','null','0'):
            return {'lines': lines, 'skip': 0}
        if isinstance(fn, str) and (fn.startswith('"') or fn.startswith("'")) or fn in ('true','false'):
            return {'lines': lines, 'skip': 0}
        args = callargs(op, regs, defined)
        if args and len(args) >= 1:
            a0 = args[0]
            if isinstance(a0, str) and (a0.startswith('"') or a0.startswith("'")):
                looksup = fn == 'dec'
                if not looksup and isinstance(fn, str) and len(fn) >= 3 and fn[0] == 'u' and fn[1] == 'p' and all(fn[k].isdigit() for k in range(2, len(fn))):
                    looksup = True
                nxt = ops[i+1] if i+1 < len(ops) else None
                feedsprint = nxt and nxt['name'] == 'CALL' and nxt['B'] == 0 and nxt['A'] != A
                if looksup or feedsprint:
                    setr(A, a0)
                    return {'lines': lines, 'skip': 0}
        args = [a for idx, a in enumerate(args) if idx == 0 or not (isinstance(a, str) and (a.startswith('"') or a.startswith("'")) and len(a) > 2 and sum(1 for c in a[1:-1] if ord(c) < 32 or ord(c) >= 127) / len(a[1:-1]) >= 0.3)]
        expr = f'{fn}({", ".join(args)})'
        if op.get('C') == 1:
            lines.append(f'{sp}{expr}')
            return {'lines': lines, 'skip': 0}
        lines.append(f'{sp}{reg(A)} = {expr}')
        setr(A, reg(A))
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'TFORLOOP':
        if op.get('mode') == 3 and isinstance(B, (int, float)):
            return {'lines': lines, 'skip': 0}
        fn = getr(A)
        args = callargs({'A': A, 'B': B if isinstance(B, (int, float)) and B <= 32 else 2, 'C': C}, regs, defined)
        if fn and fn != reg(A) and not isnoise(fn):
            nret = min(C if isinstance(C, (int, float)) and C > 1 else 3, 4)
            lines.append(f'{sp}{reg(A)} = {fn}({", ".join(args)})')
            setr(A, reg(A))
            for r in range(1, nret):
                setr(A + r, reg(A + r))
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'TAILCALL':
        args = callargs(op, regs, defined)
        lines.append(f'{sp}return {getr(A)}({", ".join(args)})')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'RETURN':
        if B == 1 or B == 0:
            lines.append(f'{sp}return')
        elif isinstance(B, (int, float)) and B > 1:
            vals = [getr(r) for r in range(A, A+B-1)]
            lines.append(f'{sp}return {", ".join(vals)}')
        else:
            lines.append(f'{sp}return {getr(A)}')
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'CLOSURE':
        name = childnames.get(B, f'f{B}')
        ups = []
        for u in range(len(op.get('upvals', []))):
            uv = op['upvals'][u]
            ups.append(getr(uv['idx']) if uv['islocal'] else (upvals[uv['idx']] if uv['idx'] < len(upvals) else f'up{uv["idx"]}'))
        closurebinds.append({'idx': B, 'ups': ups})
        fname = name
        nxt = ops[i+1] if i+1 < len(ops) else None
        if nxt and nxt['name'] == 'SETGLOBAL' and nxt['A'] == A and isinstance(nxt.get('B'), str) and isid1(nxt['B']):
            fname = nxt['B']
            childnames[B] = fname
            setr(A, fname)
            return {'lines': lines, 'skip': 1}
        setr(A, name)
        return {'lines': lines, 'skip': 0}
    if op['name'] == 'SETLIST':
        n = B if isinstance(B, (int, float)) and B > 0 else 32
        parts = []
        for r in range(A+1, A+n+1):
            if r not in regs and r not in defined:
                break
            parts.append(getr(r))
        if parts:
            expr = f'{{ {", ".join(parts)} }}'
            lines.append(f'{sp}{reg(A)} = {expr}')
            setr(A, expr)
        else:
            setr(A, '{}' if getr(A) == '{}' else getr(A))
        return {'lines': lines, 'skip': 0}
    if op['name'] in ('FORPREP','FORLOOP','VARARG','CLOSE','UNKNOWN'):
        return {'lines': lines, 'skip': 0}
    return {'lines': lines, 'skip': 0}

def isatr(proto):
    names = {c for c in proto.get('constants', []) if isinstance(c, str)}
    return all(x in names for x in ('string','match','pcall','tonumber'))

def islcp(proto):
    names = {c for c in proto.get('constants', []) if isinstance(c, str)}
    return ':%d+:' in names and '%d+' in names

def findpp(root):
    if not root or not isatr(root):
        return None
    mid = next((p for p in root.get('prototypes', []) if p and islcp(p)), None)
    if not mid:
        return None
    payload = next((p for p in mid.get('prototypes', []) if p), None)
    return payload

def isep(proto):
    if not proto:
        return True
    consts = proto.get('constants', [])[1:]
    if any(isinstance(c, str) and len(c) > 1 for c in consts):
        return False
    ops = [i for i in proto.get('instructions', []) if i and not i.get('skipped')]
    return len(ops) <= 8

def findil(root, opmap, closelocalop):
    best = None
    bestscore = 0
    def score(p):
        ops = annpr(p, opmap, closelocalop)
        return anpruse(p, ops)['score']
    def walk(p):
        nonlocal best, bestscore
        sc = score(p)
        kids = [c for c in p.get('prototypes', []) if c]
        if sc > bestscore and (not kids or sc >= 20):
            bestscore = sc
            best = p
        for k in kids:
            walk(k)
    walk(root)
    if not best or best is root or bestscore < 15:
        return None
    rootscore = score(root)
    if rootscore >= bestscore:
        return None
    rootusage = anpruse(root, cleancfg(annpr(root, opmap, closelocalop)))
    if not rootusage.get('xorStub') and rootscore >= 8:
        return None
    return best

def reconpr(proto, opmap, closelocalop, fname, upvals, depth):
    ops = annpr(proto, opmap, closelocalop)
    ops = cleancfg(ops)
    targets = jmptgts(ops)
    idx = byidx(ops)
    regs = {}
    defined = set()
    for p in range(proto['params']):
        regs[p] = reg(p)
        defined.add(p)
    childnames = {}
    for i, child in enumerate(proto.get('prototypes', [])):
        if child:
            childnames[i] = f'{fname}_f{i}'
    closurebinds = []
    lines = []
    sp = '  ' * depth
    bsp = '  ' * (depth + 1)
    i = 0
    while i < len(ops):
        op = ops[i]
        if op['index'] in targets:
            lines.append(f'{bsp}::L{op["index"]}::')
        asFor = trynumfor(ops, i, idx, targets, regs, defined, depth+1, upvals, childnames, closurebinds)
        if asFor:
            lines.extend(asFor['lines'])
            i = asFor['next']
            continue
        asGfor = trygenfor(ops, i, idx, targets, regs, defined, depth+1, upvals, childnames, closurebinds)
        if asGfor:
            lines.extend(asGfor['lines'])
            i = asGfor['next']
            continue
        structured = tryif(ops, i, idx, targets, regs, defined, depth+1, upvals, childnames, closurebinds)
        if structured:
            lines.extend(structured['lines'])
            i = structured['next']
            continue
        em = step(op, ops, i, regs, defined, depth+1, upvals, childnames, closurebinds)
        if em.get('lines'):
            lines.extend(em['lines'])
        i += 1 + (em.get('skip', 0))
    body = finlines(tidy(foldln(lines)))
    bodytext = '\n'.join(body)
    nested = []
    for pi, child in enumerate(proto.get('prototypes', [])):
        if not child:
            continue
        cname = childnames.get(pi, f'f{pi}')
        childops = cleancfg(annpr(child, opmap, closelocalop))
        childusage = anpruse(child, childops)
        if childusage.get('xorStub') and not childusage.get('interesting'):
            continue
        bound = any(b['idx'] == pi for b in closurebinds)
        if cname not in bodytext and not bound:
            continue
        bind = next((b for b in closurebinds if b['idx'] == pi), None)
        ups = bind['ups'] if bind else defups(child, opmap, closelocalop)
        src = reconpr(child, opmap, closelocalop, cname, ups, depth+1)
        if isemptyfn(src):
            continue
        nested.append(src)
    keptnames = set()
    for n in nested:
        k = fnnmof(n)
        if k:
            keptnames.add(k)
    body2 = []
    for line in body:
        t = line.strip()
        if not t or t[0] != 'r':
            body2.append(line)
            continue
        spn = t.find(' = ')
        if spn < 0:
            body2.append(line)
            continue
        rhs = t[spn+3:]
        if isplnline(rhs) and rhs.startswith(fname) and rhs not in keptnames:
            continue
        body2.append(line)
    params = [reg(p) for p in range(proto['params'])]
    early = []
    late = []
    for line in body2:
        t = line.strip()
        plain = None
        if t and t[0] == 'r':
            j = 1
            while j < len(t) and t[j].isdigit():
                j += 1
            if j < len(t) and t[j:j+3] == ' = ':
                plain = t[j+3:]
        if plain is not None and '(' not in plain and isplnline(plain):
            early.append(line)
        elif plain is not None and '(' not in plain and plain.startswith('{'):
            early.append(line)
        else:
            late.append(line)
    out = [
        f'{sp}local function {fname}({", ".join(params)})',
        *early,
        *nested,
        *late,
        f'{sp}end'
    ]
    return '\n'.join(out)

def reconprog(root, opmap, closelocalop):
    try:
        payload = findpp(root)
        if payload and not isep(payload):
            body = reconpr(payload, opmap, closelocalop, 'main', [], 0)
            return body + '\n\nreturn main()'
        leaf = findil(root, opmap, closelocalop)
        if leaf and leaf is not root:
            body = reconpr(leaf, opmap, closelocalop, 'main', [], 0)
            return body + '\n\nreturn main()'
        body = reconpr(root, opmap, closelocalop, 'main', [], 0)
        return body + '\n\nreturn main()'
    except Exception:
        return liftprog(root, opmap, closelocalop)

def deobfuscatechaoticevil(code):
    if not code or not isinstance(code, str):
        return None
    try:
        bc = xtrbc(code)
    except Exception:
        return None
    root = bc['root']
    try:
        vminfo = anvm(code)
    except Exception:
        vminfo = {'opcodeMap': {}, 'closureLocalOp': None}
    opmap = vminfo.get('opcodeMap', {})
    if not opmap:
        opmap = {
            0: {'name': 'MOVE'}, 1: {'name': 'LOADK'}, 2: {'name': 'LOADBOOL'},
            3: {'name': 'LOADNIL'}, 4: {'name': 'GETUPVAL'}, 5: {'name': 'GETGLOBAL'},
            6: {'name': 'GETTABLE'}, 7: {'name': 'SETGLOBAL'}, 8: {'name': 'SETUPVAL'},
            9: {'name': 'SETTABLE'}, 10: {'name': 'NEWTABLE'}, 11: {'name': 'SELF'},
            12: {'name': 'ADD'}, 13: {'name': 'SUB'}, 14: {'name': 'MUL'},
            15: {'name': 'DIV'}, 16: {'name': 'MOD'}, 17: {'name': 'POW'},
            18: {'name': 'UNM'}, 19: {'name': 'NOT'}, 20: {'name': 'LEN'},
            21: {'name': 'CONCAT'}, 22: {'name': 'JMP'}, 23: {'name': 'EQ'},
            24: {'name': 'LT'}, 25: {'name': 'LE'}, 26: {'name': 'TEST'},
            27: {'name': 'CALL'}, 28: {'name': 'TAILCALL'}, 29: {'name': 'RETURN'},
            30: {'name': 'CLOSURE'}, 31: {'name': 'SETLIST'}
        }
    refopmap(root, opmap)
    closelocalop = vminfo.get('closureLocalOp')
    try:
        lua = reconprog(root, opmap, closelocalop)
    except Exception:
        lua = liftprog(root, opmap, closelocalop)
    header = """--[[
Deobfuscated by Axomic LuaObfuscator ChaoticEvil Deobfuscator
Our Discord : https://discord.gg/Sps39CydcZ
Our YouTube : https://youtube.com/@axos0022
]]"""
    return header + "\n" + lua.strip()
