from pathlib import Path
import py_compile

root = Path(__file__).parent
failed = []
for path in root.rglob("*.py"):
    if any(part in {".venv", "__pycache__"} for part in path.parts):
        continue
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        failed.append((str(path), str(exc)))
if failed:
    for item in failed: print("FAIL", item)
    raise SystemExit(1)
print("OK: all Python files compile")
