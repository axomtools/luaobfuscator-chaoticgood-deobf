import re

def matchcandidate(content):
    if re.search(r'LOL!', content):
        return False
    if re.search(r'math\.ldexp', content):
        return False
    if re.search(r'local\s+function\s+\w+\s*\(', content) and re.search(r'bxor', content) and re.search(r'string\.char', content):
        return True
    return False
