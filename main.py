#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
https://github.com/Seongbok74/Sigma_SST_Signal_Study_Tool.git

main.py — Study *.py Finder (recursive) + description() preview (PyQt5)

요구사항
- 기준 위치: ./Subject (main.py와 같은 경로)
- Subject 하위 모든 깊이에서 파일명에 'study'가 포함된 *.py 파일을 찾는다.
  예) signal_study.py, StudyECG.py, foo/bar/my_study_v2.py ...
- 파일을 선택하면, 그 모듈의 `def description():` 함수를 호출해
  그 반환값(한글 설명 텍스트)을 오른쪽 패널에 표시한다.

주의
- 선택한 파이썬 파일은 import 되며, top-level 코드가 실행될 수 있음.
  무거운 처리는 `if __name__ == '__main__':` 아래로 옮기세요.
- description()은 문자열(str)을 반환하도록 구현하세요.

실행
    pip install pyqt5
    python main.py
"""

import os
import sys
import traceback
import importlib.util
from types import ModuleType
from typing import List, Tuple

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

APP_TITLE = "Study File Selector"
SUBJECT_DIR = "Subject"


# ---------------------------- FS Utilities ----------------------------

def subjects_root() -> str:
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, SUBJECT_DIR)


def find_study_py_recursive(base_folder: str) -> List[Tuple[str, str]]:
    """
    base_folder (예: ./Subject) 하위 모든 깊이에서
    파일명에 'study' 가 포함되고, '.py' 로 끝나는 파일을 찾는다.
    반환: (표시용 상대경로, 전체경로)
    """
    results: List[Tuple[str, str]] = []
    if not os.path.isdir(base_folder):
        return results

    base_folder = os.path.abspath(base_folder)
    for root, dirs, files in os.walk(base_folder):
        # 불필요 폴더 스킵(원하면 확장 가능)
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for fn in files:
            if not fn.lower().endswith(".py"):
                continue
            if "study" not in fn.lower():
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, base_folder)
            results.append((rel, full))

    results.sort(key=lambda x: x[0].lower())
    return results


# ---------------------------- Dynamic Import ----------------------------

def import_module_from_path(module_name: str, file_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def call_description(mod: ModuleType) -> str:
    """
    모듈의 description()을 찾아 호출하고 문자열을 반환.
    함수가 없거나 예외 발생 시 안내 메시지 반환.
    """
    if not hasattr(mod, "description"):
        return ("이 파일에는 description() 함수가 없습니다.\n"
                "예시:\n\n"
                "def description():\n"
                "    return '이 스터디는 ... 에 대해 설명합니다.'\n")
    func = getattr(mod, "description")
    try:
        text = func()
        if text is None:
            return "(description() → None 반환)"
        return str(text)
    except Exception as e:
        return f"[오류] description() 실행 중 예외 발생:\n{e}\n\n{traceback.format_exc()}"


# ---------------------------- GUI ----------------------------

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 560)

        # 중앙 레이아웃
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        hl = QtWidgets.QHBoxLayout(central)
        hl.setContentsMargins(10, 10, 10, 10)
        hl.setSpacing(12)

        # 좌: 파일 리스트
        left = QtWidgets.QVBoxLayout()
        self.list = QtWidgets.QListWidget()
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        btns_row = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.populate_list)
        btns_row.addWidget(self.btn_refresh)
        btns_row.addStretch(1)

        left.addWidget(QtWidgets.QLabel("Study files (recursive: ./Subject/**/*study*.py)"))
        left.addWidget(self.list, 1)
        left.addLayout(btns_row)

        # 우: 상세/설명
        right = QtWidgets.QVBoxLayout()
        self.lab_title = QtWidgets.QLabel("<b>Select a study .py file</b>")
        self.lab_title.setTextFormat(Qt.RichText)
        self.lab_title.setWordWrap(True)

        self.lab_path = QtWidgets.QLabel("")
        self.lab_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lab_path.setWordWrap(True)

        self.txt_desc = QtWidgets.QPlainTextEdit()
        self.txt_desc.setReadOnly(True)

        hint = QtWidgets.QLabel(
            "<i>선택된 파일을 import 한 뒤, description()을 호출해 내용을 표시합니다.</i>"
        )
        hint.setTextFormat(Qt.RichText)
        hint.setStyleSheet("color:#555;")

        right.addWidget(self.lab_title)
        right.addWidget(self.lab_path)
        right.addWidget(QtWidgets.QLabel("description() 반환 내용:"))
        right.addWidget(self.txt_desc, 1)
        right.addWidget(hint)

        # 합치기
        hl.addLayout(left, 3)
        hl.addLayout(right, 6)

        # 상태바
        self.status = self.statusBar()
        self.status.showMessage("Ready")

        # 이벤트 연결
        self.list.currentItemChanged.connect(self.on_selection_changed)
        self.list.itemDoubleClicked.connect(self.on_selection_changed)
        QtWidgets.QShortcut(Qt.Key_F5, self, activated=self.populate_list)

        # 초기 로드
        self.populate_list()

    # --------- Data population & selection ---------

    def populate_list(self):
        root = subjects_root()
        self.list.clear()
        if not os.path.isdir(root):
            self.status.showMessage(f"Folder not found: {root}")
            QtWidgets.QMessageBox.information(
                self, "Notice",
                f"'Subject' 폴더가 없습니다.\n아래 경로에 폴더를 만들고 "
                f"이름에 'study'가 포함된 파이썬 파일을 추가해 주세요.\n\n{root}"
            )
            self.lab_title.setText("<b>Select a study .py file</b>")
            self.lab_path.setText("")
            self.txt_desc.setPlainText("")
            return

        files = find_study_py_recursive(root)
        for rel, path in files:
            item = QtWidgets.QListWidgetItem(rel)  # 표시: Subject 기준 상대경로
            item.setData(Qt.UserRole, path)        # 실제 전체 경로
            self.list.addItem(item)

        self.status.showMessage(f"Found {self.list.count()} file(s) under {root}")
        if self.list.count() > 0:
            self.list.setCurrentRow(0)
        else:
            self.lab_title.setText("<b>No study files found</b>")
            self.lab_path.setText(root)
            self.txt_desc.setPlainText(
                "예: Subject/ecg_study.py, Subject/tools/hrvStudy.py, Subject/foo/bar/my_study_v2.py"
            )

    def on_selection_changed(self, cur, prev=None):
        if cur is None:
            self.lab_title.setText("<b>Select a study .py file</b>")
            self.lab_path.setText("")
            self.txt_desc.setPlainText("")
            return

        rel = cur.text()
        full = cur.data(Qt.UserRole)
        self.lab_title.setText(f"<b>{rel}</b>")
        self.lab_path.setText(full)

        # 모듈 import & description() 호출
        try:
            # 모듈명은 경로 기반으로 유니크하게 구성
            rel_module_name = rel.replace(os.sep, "_").replace("-", "_").replace(".", "_")
            module_name = f"subject_auto_{rel_module_name}"
            mod = import_module_from_path(module_name, full)
            text = call_description(mod)
        except Exception as e:
            text = f"[오류] 모듈 import 중 예외 발생:\n{e}\n\n{traceback.format_exc()}"

        self.txt_desc.setPlainText(text)


# ---------------------------- Entry ----------------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
