import ast, os
for root, dirs, files in os.walk('.'):
    for f in files:
        if not f.endswith('.py') or f == 'check_syntax.py':
            continue
        path = os.path.join(root, f)
        try:
            ast.parse(open(path, encoding='utf-8').read())
        except SyntaxError as e:
            print(f"SYNTAX ERROR: {path}: {e}")
        else:
            pass
print("Syntax check done.")
