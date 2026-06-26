import sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '                "extension": item.extension,'
new = '                "extension": item.extension or item.filename.rsplit(".", 1)[-1].lower() if "." in item.filename else "",'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed:", path)
else:
    print("Pattern not found in:", path)
    # Debug: find lines with 'extension'
    for i, line in enumerate(content.split('\n'), 1):
        if 'extension' in line:
            print(f"  L{i}: {line}")
