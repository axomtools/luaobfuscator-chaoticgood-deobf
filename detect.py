import re

def matchcandidate(content):
    return bool(re.search(r'v7\s*\(\s*"\\\d+', content) and "LOL!" not in content)

def matchcandidateevil(content):
    return bool(re.search(r'"LOL!', content) or re.search(r'math\.ldexp', content))
