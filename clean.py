from rename import renameids

def cleanlua(code):
    return renameids(code.strip()).strip()
