# export_structure.py
from pathlib import Path

IGNORE_DIRS = {
    ".venv", "venv", "__pycache__", ".git", ".idea", ".vscode",
    "node_modules", "dist", "build", ".mypy_cache", ".pytest_cache"
}
IGNORE_FILES = {".DS_Store"}

def tree(root: Path, prefix=""):
    entries = sorted([p for p in root.iterdir() if not is_ignored(p)], key=lambda p: (p.is_file(), p.name.lower()))
    lines = []
    for i, p in enumerate(entries):
        connector = "└── " if i == len(entries)-1 else "├── "
        lines.append(prefix + connector + p.name)
        if p.is_dir():
            extension = "    " if i == len(entries)-1 else "│   "
            lines.extend(tree(p, prefix + extension))
    return lines

def is_ignored(p: Path) -> bool:
    name = p.name
    if name in IGNORE_FILES:
        return True
    if p.is_dir() and name in IGNORE_DIRS:
        return True
    return False

if __name__ == "__main__":
    # main.py가 있는 폴더의 한 단계 위를 루트로 설정
    base = Path(__file__).resolve().parent  # 이 파일 기준
    # 필요하면 한 단계 위로: base = base.parent
    root = base.parent  # <- 여기서 base.parent로 바꾸면 한 단계 위
    out = base / "project_structure.txt"
    lines = [root.resolve().as_posix()]
    lines += tree(root)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {out}")
