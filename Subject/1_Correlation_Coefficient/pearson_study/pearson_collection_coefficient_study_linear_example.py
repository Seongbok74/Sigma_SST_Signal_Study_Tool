# Subject/1_Correlation_Coefficient/pearson_study/pearson_linear_only_demo.py
# -*- coding: utf-8 -*-
"""
예제 1️⃣: 피어슨 상관계수는 '선형 관계'만 측정한다

- Figure1(위): 시간영역 파형 (ref vs. test)
- Figure2(아래): 산점도 (x=ref, y=test) → 비선형이면 포물선/곡선이 보이지만 r≈0에 가까움
- 제어부: 주파수/위상/노이즈/변환타입/평균제거(detrend) 조절 + r 값 표시
"""

import numpy as np
from PyQt5 import QtWidgets

# 템플릿 import (리포 구조 기준)
from Application.templet.templet_compare_signal import create_window, StudyAPI


class PearsonLinearOnlyDemo:
    def __init__(self):
        # 기본 파라미터
        self.fs = 250
        self.dur = 5.0
        self.freq = 2.0     # Hz
        self.phase = 0.0    # rad
        self.noise = 0.05   # mV (상대 스케일)
        self.transform = "square(x)"  # 변환 타입 기본값
        self.detrend = True

        # UI 핸들(on_update에서 갱신용)
        self.lbl_r = None

    # 설명 패널 텍스트
    def get_description(self) -> str:
        return (
            "피어슨 상관계수는 오직 '선형적(linear)' 관계만을 측정합니다.\n"
            "- 예: test = square(x), abs(x), x^3 처럼 비선형 변환은 분명 관계가 있어 보여도\n"
            "  피어슨 r 값은 0에 가깝게 나올 수 있습니다.\n"
            "- 아래 산점도(Figure2)에서 ref(가로)와 test(세로)의 비선형 형태를 눈으로 확인하세요."
        )

    # 제어부(오른쪽) UI 생성
    def create_controls(self, parent: QtWidgets.QWidget, api: StudyAPI):
        box = QtWidgets.QWidget(parent)
        form = QtWidgets.QFormLayout(box)

        sp_freq = QtWidgets.QDoubleSpinBox(box)
        sp_freq.setRange(0.1, 20.0); sp_freq.setSingleStep(0.1); sp_freq.setValue(self.freq)
        sp_phase = QtWidgets.QDoubleSpinBox(box)
        sp_phase.setRange(-3.14159, 3.14159); sp_phase.setSingleStep(0.1); sp_phase.setValue(self.phase)
        sp_noise = QtWidgets.QDoubleSpinBox(box)
        sp_noise.setRange(0.0, 1.0); sp_noise.setSingleStep(0.01); sp_noise.setValue(self.noise)

        cb_tr = QtWidgets.QComboBox(box)
        cb_tr.addItems(["square(x)", "abs(x)", "x^3", "identity"])
        cb_tr.setCurrentText(self.transform)

        cb_detrend = QtWidgets.QCheckBox("평균 제거(detrend) 후 r 계산", box)
        cb_detrend.setChecked(self.detrend)

        # 이벤트 → 내부 상태 업데이트
        sp_freq.valueChanged.connect(lambda v: setattr(self, "freq", float(v)))
        sp_phase.valueChanged.connect(lambda v: setattr(self, "phase", float(v)))
        sp_noise.valueChanged.connect(lambda v: setattr(self, "noise", float(v)))
        cb_tr.currentTextChanged.connect(lambda s: setattr(self, "transform", str(s)))
        cb_detrend.toggled.connect(lambda b: setattr(self, "detrend", bool(b)))

        # r 표시 라벨
        self.lbl_r = QtWidgets.QLabel("Pearson r: -")
        self.lbl_r.setStyleSheet("font-weight:600;")

        # 버튼
        btn = QtWidgets.QPushButton("Run / Update")
        btn.clicked.connect(api.request_update)

        # 폼 배치
        form.addRow("주파수 (Hz)", sp_freq)
        form.addRow("위상 (rad)", sp_phase)
        form.addRow("노이즈", sp_noise)
        form.addRow("변환", cb_tr)
        form.addRow("", cb_detrend)
        form.addRow(self.lbl_r)
        form.addRow(btn)

        return box

    # 업데이트: 데이터 생성 → 플로팅 → r 계산/표시
    def on_update(self, api: StudyAPI):
        fs, dur = self.fs, self.dur
        n = int(fs * dur)
        t = np.arange(n) / fs

        # 기준 신호(ref): 사인 + 가우시안 노이즈
        rng = np.random.RandomState(0)
        ref = np.sin(2*np.pi*self.freq*t + self.phase) + self.noise * rng.randn(n)

        # 비선형 변환
        if self.transform == "square(x)":
            test = ref ** 2
        elif self.transform == "abs(x)":
            test = np.abs(ref)
        elif self.transform == "x^3":
            test = ref ** 3
        else:  # identity
            test = ref.copy()

        # 피어슨 r 계산 (선형 상관)
        x = ref.copy()
        y = test.copy()
        if self.detrend:
            x = x - np.mean(x)
            y = y - np.mean(y)
        # 안전 체크
        if np.std(x) < 1e-12 or np.std(y) < 1e-12:
            r = np.nan
        else:
            r = float(np.corrcoef(x, y)[0, 1])

        # Figure1: 시간영역 파형 (ref vs test)
        api.set_figure1([
            (t, ref,  "ref"),
            (t, test, "test"),
        ])

        # Figure2: 산점도 (x=ref, y=test) — 비선형 관계 형태를 직관적으로 보여줌
        # draw_lines에서 style의 'linestyle'을 ''로 두면 점만 찍힘
        # marker 크기는 matplotlib 기본을 사용 (템플릿 내부 스타일과 합쳐짐)
        api.set_figure2([
            (ref, test, "scatter"),
        ], style={"linestyle": "", "marker": ".", "markersize": 3})

        # r 값 갱신
        if self.lbl_r is not None:
            if np.isnan(r):
                self.lbl_r.setText("Pearson r: N/A")
            else:
                self.lbl_r.setText(f"Pearson r: {r:.4f}")


# -------- 단독 실행 테스트 (선택) --------
if __name__ == "__main__":
    from PyQt5 import QtWidgets
    app = QtWidgets.QApplication([])
    w = create_window(PearsonLinearOnlyDemo())
    w.show()
    app.exec_()
