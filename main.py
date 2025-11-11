#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
https://github.com/Seongbok74/Sigma_SST_Signal_Study_Tool.git

main.py — Study *.py Finder (recursive) + description() preview (PyQt5)
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
    results: List[Tuple[str, str]] = []
    if not os.path.isdir(base_folder):
        return results

    base_folder = os.path.abspath(base_folder)
    for root, dirs, files in os.walk(base_folder):
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

        # === ADDED: Open 버튼 ===
        self.btn_open = QtWidgets.QPushButton("Open")  # <--- 추가
        self.btn_open.clicked.connect(self.on_open_clicked)  # <--- 추가

        btns_row.addWidget(self.btn_refresh)
        btns_row.addWidget(self.btn_open)  # <--- 추가
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

        hl.addLayout(left, 3)
        hl.addLayout(right, 6)

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        # 이벤트 연결
        self.list.currentItemChanged.connect(self.on_selection_changed)
        # === CHANGED: 더블클릭 시 '열기' ===
        self.list.itemDoubleClicked.connect(self.on_open_clicked)  # <--- 변경

        QtWidgets.QShortcut(Qt.Key_F5, self, activated=self.populate_list)
        # === ADDED: Enter/Return으로도 열기 ===
        QtWidgets.QShortcut(Qt.Key_Return, self, activated=self.on_open_clicked)  # <--- 추가
        QtWidgets.QShortcut(Qt.Key_Enter, self, activated=self.on_open_clicked)   # <--- 추가

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

        # 모듈 import & description() 호출 (미리보기)
        try:
            rel_module_name = rel.replace(os.sep, "_").replace("-", "_").replace(".", "_")
            module_name = f"subject_auto_{rel_module_name}"
            mod = import_module_from_path(module_name, full)
            text = call_description(mod)
        except Exception as e:
            text = f"[오류] 모듈 import 중 예외 발생:\n{e}\n\n{traceback.format_exc()}"

        self.txt_desc.setPlainText(text)

    # --------- OPEN (추가) ---------
    def on_open_clicked(self, *args):
        """선택한 study 모듈의 create_window()를 호출해 창을 띄운다."""
        item = self.list.currentItem()
        if item is None:
            QtWidgets.QMessageBox.information(self, "Open", "먼저 파일을 선택하세요.")
            return

        full = item.data(Qt.UserRole)
        rel = item.text()
        try:
            rel_module_name = rel.replace(os.sep, "_").replace("-", "_").replace(".", "_")
            module_name = f"subject_auto_{rel_module_name}"
            mod = import_module_from_path(module_name, full)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import Error",
                                           f"모듈 불러오기 실패:\n{e}\n\n{traceback.format_exc()}")
            return

        if not hasattr(mod, "create_window"):
            QtWidgets.QMessageBox.information(
                self, "Open",
                "이 파일에 create_window() 함수가 없습니다.\n\n"
                "스터디 파일 끝에 아래 래퍼를 추가하세요:\n"
                "  def create_window(parent=None):\n"
                "      from Application.templet.templet_compare_signal import create_window as _tpl\n"
                "      return _tpl(YourStudyClass())")
            return

        try:
            w = mod.create_window(parent=None)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Run Error",
                                           f"create_window() 실행 실패:\n{e}\n\n{traceback.format_exc()}")
            return

        if hasattr(w, "show"):
            w.setAttribute(Qt.WA_DeleteOnClose, True)
            w.show()
            self.status.showMessage(f"Opened: {rel}")
        else:
            QtWidgets.QMessageBox.information(self, "Open",
                                              f"반환 객체가 Qt 위젯이 아닙니다: {type(w)}")


# ---------------------------- Entry ----------------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
