import re

def matchcandidate(content):
    return bool(re.search(r'v7\s*\(\s*"\\\d+', content) and "LOL!" not in content)

def matchcandidateevil(content):
    if re.search(r'v7\s*\(\s*"LOL!', content):
        return True
    if re.search(r'math\.ldexp', content):
        return True
    if re.search(r'return\s*\(\s*function\s*\(\)', content) and re.search(r'v7\s*\(', content):
        return True
    if re.search(r'while\s+true\s+do', content) and re.search(r'v\d+\s*=\s*v\d+\s*\[\s*v\d+\s*\[\s*2\s*\]\s*\]', content):
        return True
    if re.search(r'local\s+function\s+v7\s*\(', content) and re.search(r'LOL!', content):
        return True
    return False
