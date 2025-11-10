#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
templet_compare_signal.py — GUI 템플릿 (부모/베이스)

요약
- 화면을 세로로 반으로 나눔: **왼쪽(그래프)** / **오른쪽(제어부)**
- 왼쪽 그래프는 **2개 고정**: 위 = Figure1, 아래 = Figure2
- 오른쪽 제어부는 **스터디 파일**이 위젯을 추가하여 구성
- 스터디 파일에서 CSV를 읽거나 직접 만든 변수로 **Figure1/2에 그릴 데이터**를 넘김
- 스터디 설명(description)도 **오른쪽 제어부 상단**에 표시

의존성
    pip install pyqt5 matplotlib numpy

💡 스터디 파일을 어떻게 만들지에 대한 가이드는 파일 하단 주석을 참고하세요.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union, Protocol

import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# ===========================
# 내부 유틸 & 타입
# ===========================

LineLike = Union[
    Tuple[Sequence[float], Sequence[float], str],  # (x, y, label)
    Tuple[Sequence[float], Sequence[float]],       # (x, y)
    Sequence[float],                               # y (x는 0..N-1)
]

def _to_xy_label(line: LineLike) -> Tuple[np.ndarray, np.ndarray, Optional[str]]:
    """
    다양한 입력형을 (x, y, label) 표준형으로 변환.
    - (x, y, label)
    - (x, y)
    - y
    """
    if isinstance(line, (list, tuple)):
        if len(line) == 3:
            x, y, label = line
            return np.asarray(x, float), np.asarray(y, float), str(label)
        if len(line) == 2:
            x, y = line
            return np.asarray(x, float), np.asarray(y, float), None
        # len != 2,3 이고 list/tuple 면 y로 간주
    y = np.asarray(line, float)
    x = np.arange(len(y), dtype=float)
    return x, y, None


# ===========================
# Matplotlib 캔버스 (2개 고정)
# ===========================

class PlotCanvas(FigureCanvas):
    """단일 Figure+Axes를 캡슐화한 캔버스."""
    def __init__(self, title: str, parent=None):
        self.fig = Figure(figsize=(6, 2.8), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title(title)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Amplitude")
        super().__init__(self.fig)
        self.setParent(parent)

    def draw_lines(self, lines: Iterable[LineLike], style: Optional[Dict[str, Any]] = None):
        """여러 라인을 현재 축에 그림."""
        self.ax.clear()
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Amplitude")
        style = {"lw": 1.2} | (style or {})

        ymin, ymax = None, None
        legend_labels = []
        for line in lines:
            x, y, label = _to_xy_label(line)
            self.ax.plot(x, y, label=label, **style)
            if ymin is None:
                ymin, ymax = float(np.min(y)), float(np.max(y))
            else:
                ymin, ymax = min(ymin, float(np.min(y))), max(ymax, float(np.max(y)))
            if label:
                legend_labels.append(label)

        if ymin is not None and ymax is not None:
            pad = 0.1 * max(1e-9, (ymax - ymin))
            self.ax.set_ylim(ymin - pad, ymax + pad)

        if legend_labels:
            self.ax.legend(loc="upper right")
        self.draw()


# ===========================
# 스터디 → 템플릿 상호작용용 API
# ===========================

class StudyAPI:
    """
    스터디 파일이 사용할 템플릿 API.
    - Figure1/2에 라인들을 그릴 수 있게 제공
    - 설명/상태 메시지, 업데이트 트리거 등
    - (선택) CSV 로딩 헬퍼 제공
    """
    def __init__(self, window: "CompareTemplateWindow"):
        self._w = window

    # ---- Plot API ----
    def set_figure1(self, lines: Iterable[LineLike], style: Optional[Dict[str, Any]] = None):
        """Figure1(위)에 라인 세트 그리기."""
        self._w.canvas_top.draw_lines(lines, style)

    def set_figure2(self, lines: Iterable[LineLike], style: Optional[Dict[str, Any]] = None):
        """Figure2(아래)에 라인 세트 그리기."""
        self._w.canvas_bottom.draw_lines(lines, style)

    def clear_figures(self):
        """두 Figure 모두 초기화."""
        self._w.canvas_top.draw_lines([])
        self._w.canvas_bottom.draw_lines([])

    # ---- Control/Description ----
    def set_description(self, text: str):
        """오른쪽 제어부 상단 설명 텍스트 교체."""
        self._w.desc_label.setText(text or "")

    def add_control_widget(self, widget: QtWidgets.QWidget):
        """
        스터디 제어용 위젯을 제어부 영역에 추가.
        (스터디가 직접 위젯을 만들어 호출)
        """
        self._w.controls_layout.addWidget(widget)

    def add_spacer(self):
        self._w.controls_layout.addStretch(1)

    def set_status(self, msg: str):
        self._w.statusBar().showMessage(msg)

    # ---- Update Trigger ----
    def request_update(self):
        """
        'Run/Update'와 동일한 흐름을 트리거.
        스터디에서 파라미터가 바뀔 때 호출 가능.
        """
        self._w.on_update_clicked()

    # ---- CSV Helper (옵션) ----
    def load_csv(self, path: str, skip_header: int = 0, delimiter: Optional[str] = None) -> np.ndarray:
        """
        CSV 로딩 헬퍼. numpy로 간단히 로딩하여 2D array 반환(행=샘플, 열=컬럼).
        - delimiter가 None이면 numpy가 자동 판단(공백/콤마 등)
        - 에러는 예외로 전달
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"CSV not found: {path}")
        data = np.loadtxt(path, delimiter=delimiter, skiprows=skip_header)
        return np.atleast_2d(data)


# ===========================
# 스터디 훅(Study Hooks) 프로토콜
# ===========================

class StudyHooks(Protocol):
    """
    스터디 파일은 다음 3가지를 '선택적으로' 제공할 수 있습니다.
    - get_description() -> str | None              : 오른쪽 상단 설명 텍스트
    - create_controls(parent, api) -> QWidget | None: 제어부에 붙일 컨트롤 UI
    - on_update(api) -> None                       : Run/Update 시 호출되어 Figure1/2에 데이터 반영

    ⚠️ 최소 구현: on_update(api)
       (Figure1/2에 무엇을 그릴지 이 함수에서 호출)
    """
    def get_description(self) -> Optional[str]: ...
    def create_controls(self, parent: QtWidgets.QWidget, api: StudyAPI) -> Optional[QtWidgets.QWidget]: ...
    def on_update(self, api: StudyAPI) -> None: ...


# ===========================
# 메인 윈도우 (좌: Figure1/2, 우: 설명+컨트롤)
# ===========================

class CompareTemplateWindow(QtWidgets.QMainWindow):
    def __init__(self, study: StudyHooks):
        super().__init__()
        self.study = study
        self.setWindowTitle("[SST] Compare Template")
        self.resize(1200, 720)

        # ---- 중앙 영역: splitter로 좌/우 분할 ----
        splitter = QtWidgets.QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(splitter)

        # ---- 좌: 그래프 (세로로 2개) ----
        left_widget = QtWidgets.QWidget(splitter)
        left_vbox = QtWidgets.QVBoxLayout(left_widget)
        left_vbox.setContentsMargins(8, 8, 8, 8)
        left_vbox.setSpacing(10)

        self.canvas_top = PlotCanvas("Figure1", left_widget)
        self.canvas_bottom = PlotCanvas("Figure2", left_widget)
        left_vbox.addWidget(self.canvas_top, 1)
        left_vbox.addWidget(self.canvas_bottom, 1)

        # ---- 우: 제어부 (설명 + 컨트롤 + 공통 버튼) ----
        right_widget = QtWidgets.QWidget(splitter)
        right_vbox = QtWidgets.QVBoxLayout(right_widget)
        right_vbox.setContentsMargins(8, 8, 8, 8)
        right_vbox.setSpacing(10)

        # 설명
        self.desc_label = QtWidgets.QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color:#333;")
        desc_box = QtWidgets.QGroupBox("Description")
        desc_layout = QtWidgets.QVBoxLayout(desc_box)
        desc_layout.addWidget(self.desc_label)
        right_vbox.addWidget(desc_box)

        # 컨트롤 박스 (스터디에서 붙임)
        self.controls_box = QtWidgets.QGroupBox("Controls (from study)")
        self.controls_layout = QtWidgets.QVBoxLayout(self.controls_box)
        self.controls_layout.setContentsMargins(8, 8, 8, 8)
        self.controls_layout.setSpacing(6)
        right_vbox.addWidget(self.controls_box, 1)

        # 공통 버튼
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_update = QtWidgets.QPushButton("Run / Update")
        self.btn_update.clicked.connect(self.on_update_clicked)
        self.btn_clear = QtWidgets.QPushButton("Clear Figures")
        self.btn_clear.clicked.connect(self.on_clear_clicked)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        right_vbox.addLayout(btn_row)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)

        # ---- Study API 연결 ----
        self.api = StudyAPI(self)

        # 설명 & 컨트롤 초기 세팅
        try:
            if hasattr(self.study, "get_description"):
                txt = self.study.get_description() or ""
                self.desc_label.setText(txt)
        except Exception as e:
            self.desc_label.setText(f"[오류] get_description() 예외: {e}")

        try:
            if hasattr(self.study, "create_controls"):
                w = self.study.create_controls(self.controls_box, self.api)
                if w is not None:
                    self.controls_layout.addWidget(w)
        except Exception as e:
            err = QtWidgets.QLabel(f"[오류] create_controls() 예외: {e}")
            err.setStyleSheet("color:#a00;")
            self.controls_layout.addWidget(err)

        # 최초 1회 업데이트
        self.on_update_clicked()

    # ---- 공통 버튼 동작 ----
    def on_update_clicked(self):
        """스터디의 on_update(api)를 호출해서 Figure1/2를 갱신."""
        if not hasattr(self.study, "on_update"):
            QtWidgets.QMessageBox.information(self, "Info", "이 스터디는 on_update(api)를 구현하지 않았습니다.")
            return
        try:
            self.api.set_status("Updating...")
            self.study.on_update(self.api)
            self.api.set_status("Updated")
        except Exception as e:
            self.api.set_status("Error")
            QtWidgets.QMessageBox.critical(self, "on_update() 오류", str(e))

    def on_clear_clicked(self):
        self.api.clear_figures()
        self.api.set_status("Cleared")


# ===========================
# 팩토리 함수
# ===========================

def create_window(study: StudyHooks) -> CompareTemplateWindow:
    """
    외부(스터디 파일, 런처 등)에서 호출할 팩토리.
    - study: get_description/create_controls/on_update를 제공하는 객체(또는 모듈 래퍼)
    """
    return CompareTemplateWindow(study)


# ===========================
# 데모 스터디 (예시) — 제거해도 됨
# ===========================

class _DemoStudy:
    """
    ✨ 예시 스터디
    - Controls: Sine 파라미터 조정(진폭/주파수) + 노이즈 on/off
    - Figure1: 기준 vs 테스트 신호
    - Figure2: 테스트의 제곱(비선형 예시)
    💡 이 클래스를 참고하여 자신의 study 파일을 만드세요.
    """
    def __init__(self):
        # 내부 상태(컨트롤 값)는 간단히 멤버로 보관
        self.amp = 1.0
        self.freq = 2.0
        self.noise_on = True

    def get_description(self) -> str:
        return (
            "이 데모는 사인파(reference)와 변형된 신호(test)를 비교합니다.\n"
            "- 오른쪽 Controls에서 파라미터를 바꾸고 Run/Update를 눌러 갱신하세요."
        )

    def create_controls(self, parent: QtWidgets.QWidget, api: StudyAPI):
        box = QtWidgets.QWidget(parent)
        form = QtWidgets.QFormLayout(box)

        amp = QtWidgets.QDoubleSpinBox(box)
        amp.setRange(0.0, 5.0); amp.setSingleStep(0.1); amp.setValue(self.amp)

        freq = QtWidgets.QDoubleSpinBox(box)
        freq.setRange(0.1, 20.0); freq.setSingleStep(0.1); freq.setValue(self.freq)

        noise = QtWidgets.QCheckBox("노이즈 추가", box)
        noise.setChecked(self.noise_on)

        # 변경 시 바로 업데이트를 원하면 valueChanged → api.request_update 연결 가능
        amp.valueChanged.connect(lambda v: setattr(self, "amp", float(v)))
        freq.valueChanged.connect(lambda v: setattr(self, "freq", float(v)))
        noise.toggled.connect(lambda v: setattr(self, "noise_on", bool(v)))

        form.addRow("진폭", amp)
        form.addRow("주파수(Hz)", freq)
        form.addRow("", noise)

        # 편의 버튼
        btn = QtWidgets.QPushButton("즉시 업데이트")
        btn.clicked.connect(api.request_update)
        form.addRow(btn)

        return box

    def on_update(self, api: StudyAPI):
        fs = 500
        dur = 5.0
        n = int(fs * dur)
        t = np.arange(n) / fs

        ref = np.sin(2*np.pi*self.freq*t)
        test = self.amp * np.sin(2*np.pi*self.freq*t + 0.3)
        if self.noise_on:
            rng = np.random.RandomState(0)
            ref = ref + 0.05 * rng.randn(n)
            test = test + 0.05 * rng.randn(n)

        quad = (test ** 2)

        # Figure1: ref/test
        api.set_figure1([
            (t, ref, "ref"),
            (t, test, "test"),
        ])

        # Figure2: quad
        api.set_figure2([
            (t, quad, "test^2"),
        ])


def _run_demo():
    app = QtWidgets.QApplication(sys.argv)
    w = create_window(_DemoStudy())
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    _run_demo()


# =============================================================================
#                            📚 스터디 파일 작성 가이드
# =============================================================================
# 1) 파일 예시명: pearson_collection_coefficient_study_linear_example.py
#
# 2) 최소 구현 요구:
#    - on_update(api) 하나만 있어도 동작합니다.
#      여기서 api.set_figure1([...]), api.set_figure2([...])를 호출해
#      두 Figure에 라인을 그려 넣으세요.
#
# 3) 선택 구현:
#    - get_description() -> str : 오른쪽 상단 설명 텍스트 제공
#    - create_controls(parent, api) -> QWidget :
#        제어부에 붙일 위젯을 만들어 반환(버튼/슬라이더/체크박스 등)
#        반환한 QWidget은 템플릿이 Controls 박스에 자동으로 addWidget 합니다.
#
# 4) 지원되는 Plot 호출 형식(LineLike):
#    - (x, y, "label")
#    - (x, y)
#    - y            # 이 경우 x는 0..N-1 자동 생성
#
# 5) CSV 로드가 필요하면 api.load_csv(path, skip_header=0, delimiter=None) 사용 가능
#    - 2D numpy array 반환(행=샘플, 열=컬럼)
#
# 6) 실전 예시(아래 코드 그대로 복사해서 시작해 보세요):
#
#    from templet_compare_signal import create_window, StudyAPI
#    from PyQt5 import QtWidgets
#    import numpy as np
#
#    class MyPearsonStudy:
#        def get_description(self):
#            return "피어슨 상관 데모 입니다. Run/Update를 눌러 결과를 보세요."
#
#        def create_controls(self, parent, api: StudyAPI):
#            box = QtWidgets.QWidget(parent)
#            lay = QtWidgets.QVBoxLayout(box)
#            btn = QtWidgets.QPushButton("데이터 갱신")
#            btn.clicked.connect(api.request_update)
#            lay.addWidget(btn)
#            lay.addStretch(1)
#            return box
#
#        def on_update(self, api: StudyAPI):
#            fs = 250; dur = 5.0
#            n = int(fs*dur)
#            t = np.arange(n)/fs
#            ref = np.sin(2*np.pi*2*t)
#            test = np.sin(2*np.pi*2*t + 0.4)
#            api.set_figure1([(t, ref, "ref"), (t, test, "test")])
#            api.set_figure2([ref * test])  # 예: 단순 곱 신호
#
#    if __name__ == "__main__":
#        app = QtWidgets.QApplication([])
#        from templet_compare_signal import create_window
#        w = create_window(MyPearsonStudy())
#        w.show()
#        app.exec_()
#
# 7) 런처(main.py)에서 동적 로딩을 한다면:
#    - 스터디 모듈을 import 한 뒤, 모듈 내 클래스를 인스턴스화 해서
#      create_window(study_instance)를 호출하면 됩니다.
#
# 8) 문제 해결 팁:
#    - 그래프가 비어 있으면 on_update(api)가 호출되고 있는지 확인
#    - CSV 경로 문제는 api.load_csv()가 FileNotFoundError를 던집니다
#    - 컨트롤에서 값 변경 시 즉시 반영하고 싶다면 시그널에서 api.request_update() 호출
# =============================================================================
