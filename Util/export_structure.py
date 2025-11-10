import os
import csv
from datetime import datetime

# === 설정 ===
ROOT_DIR = "."        # 기준 폴더 (현재 프로젝트 루트)
OUT_TXT = "project_structure.txt"
OUT_CSV = "project_structure.csv"


def get_tree_list(root: str):
    """(depth, path, is_dir) 형태의 리스트 반환"""
    records = []
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        records.append((depth, dirpath, True))
        for f in filenames:
            records.append((depth + 1, os.path.join(dirpath, f), False))
    return records


def export_txt(records):
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"# Project Structure (updated {datetime.now()})\n\n")
        for depth, path, is_dir in records:
            name = os.path.basename(path)
            indent = "│   " * (depth - 1) + ("├── " if depth > 0 else "")
            f.write(f"{indent}{name}/\n" if is_dir else f"{indent}{name}\n")
    print(f"✅ TXT 파일 저장 완료: {OUT_TXT}")


def export_csv(records):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Depth", "Type", "Path"])
        for depth, path, is_dir in records:
            writer.writerow([depth, "DIR" if is_dir else "FILE", path])
    print(f"✅ CSV 파일 저장 완료: {OUT_CSV}")


if __name__ == "__main__":
    data = get_tree_list(ROOT_DIR)
    export_txt(data)
    #export_csv(data)
