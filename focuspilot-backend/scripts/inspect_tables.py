import re
from pathlib import Path

app_dir = Path("c:/Dev/FocusPilot/focuspilot-backend/app")
inserts = {}

for py_file in app_dir.rglob("*.py"):
    text = py_file.read_text(encoding="utf-8")
    matches = re.finditer(r"table\(['\"]([a-zA-Z0-9_]+)['\"]\)\.(insert|upsert|update)\(([\s\S]*?)\)", text)
    for m in matches:
        tbl = m.group(1)
        body = m.group(3)
        keys = re.findall(r"['\"]([a-zA-Z0-9_]+)['\"]\s*:", body)
        if tbl not in inserts:
            inserts[tbl] = set()
        for k in keys:
            inserts[tbl].add(k)

for tbl, cols in sorted(inserts.items()):
    print(f"{tbl}: {sorted(cols)}")
