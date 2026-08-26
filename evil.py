import subprocess
import tempfile
import os
import sys
from detect import matchcandidateevil

def deobfuscatechaoticevil(code):
    if not code or not isinstance(code, str):
        return None
    if not matchcandidateevil(code):
        return None
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False, encoding='utf-8') as f:
        f.write(code)
        tmpname = f.name
    try:
        proc = subprocess.run(
            ['node', 'deobf.js', '--stdout', tmpname],
            capture_output=True,
            text=True,
            timeout=120
        )
        if proc.returncode != 0:
            sys.stderr.write(f'node error: {proc.stderr}\n')
            return None
        return proc.stdout.strip()
    except FileNotFoundError:
        sys.stderr.write('node.js not found\n')
        return None
    except subprocess.TimeoutExpired:
        sys.stderr.write('timeout\n')
        return None
    except Exception as e:
        sys.stderr.write(f'error: {e}\n')
        return None
    finally:
        try:
            os.unlink(tmpname)
        except:
            pass
