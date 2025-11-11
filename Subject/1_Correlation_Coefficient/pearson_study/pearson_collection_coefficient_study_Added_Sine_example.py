# Subject/1_Correlation_Coefficient/pearson_study/ecg_60bpm_add_60hz_controls.py
# -*- coding: utf-8 -*-
"""
ECG 60bpm 신호를 Figure1/2에 동일하게 불러오고,
각 Figure별로 '임의 주파수' 사인을 (진폭/위상/평균선) 개별 제어하여
두 결과 신호의 Pearson 상관값 변화를 관찰하는 예제.

변경 사항
- 60 Hz 고정 → 각 Figure별로 주파수 직접 입력 (0.001 ~ fs/2 Hz)
- 사인 생성 함수 일반화(_sine → 주파수 인자 사용)
"""

import os
import numpy as np
from PyQt5 import QtWidgets

from Application.templet.templet_compare_signal import create_window as _tpl_create_window, StudyAPI


class ECG60HzControlStudy:
    def __init__(self):
        # 경로(현재 파일 기준): ../data/ecg_60bpm_250sps_5sec_1mVpp.csv
        here = os.path.dirname(__file__)
        self.csv_path = os.path.normpath(os.path.join(here, "..", "data", "ecg_60bpm_250sps_5sec_1mVpp.csv"))

        # 고정 파라미터
        self.fs = 250.0     # Hz (CSV가 250 sps)

        # Figure1 제어 기본값
        self.f1_add = True
        self.f1_freq_hz = 60.0      # ← 주파수 추가
        self.f1_amp_uv = 50.0       # µV (1 µV = 0.001 mV)
        self.f1_phase_deg = 0.0     # °
        self.f1_show_mean = False

        # Figure2 제어 기본값
        self.f2_add = False
        self.f2_freq_hz = 60.0      # ← 주파수 추가
        self.f2_amp_uv = 0.0
        self.f2_phase_deg = 0.0
        self.f2_show_mean = False

        # UI 핸들
        self.lbl_r = None

        # 데이터 캐시 (로드 1회)
        self._t = None
        self._ecg = None

    # 오른쪽 상단 설명
    def get_description(self) -> str:
        nyq = self.fs / 2.0
        return (
            "ECG(60bpm, 250sps, 5s, 1mVpp) 신호를 Figure1/2에 동일 적용하고, "
            "각 Figure에 '임의 주파수' 사인(진폭/위상)을 개별적으로 추가할 수 있습니다.\n"
            "- Frequency(Hz): 0.001 ~ {:.3f} (나이퀴스트 한계)".format(nyq) + "\n"
            "- Amplitude(µV): 1 µV = 0.001 mV 로 내부 변환\n"
            "- '전체 신호 평균위치 표시': 최종 신호의 평균값에 수평선 표시\n"
            "- 하단 Pearson r: Figure1 최종신호 vs Figure2 최종신호 (실시간/수동 갱신)"
        )

    # 제어부 UI 생성
    def create_controls(self, parent: QtWidgets.QWidget, api: StudyAPI):
        box = QtWidgets.QWidget(parent)
        root = QtWidgets.QVBoxLayout(box)
        root.setSpacing(8)

        fmin = 0.001
        fmax = self.fs / 2.0  # 나이퀴스트
        fdec = 3              # 소수 3자리(0.001 Hz)

        # --- Figure1 Controls ---
        g1 = QtWidgets.QGroupBox("Figure1 Controls")
        f1 = QtWidgets.QFormLayout(g1)

        cb1_add = QtWidgets.QCheckBox("Added Graph Sine (enable)", g1)
        cb1_add.setChecked(self.f1_add)

        sp1_freq = QtWidgets.QDoubleSpinBox(g1)
        sp1_freq.setRange(fmin, fmax); sp1_freq.setDecimals(fdec); sp1_freq.setSingleStep(0.001); sp1_freq.setValue(self.f1_freq_hz)

        sp1_amp = QtWidgets.QDoubleSpinBox(g1)
        sp1_amp.setRange(0.0, 5000.0); sp1_amp.setDecimals(1); sp1_amp.setSingleStep(10.0); sp1_amp.setValue(self.f1_amp_uv)

        sp1_phase = QtWidgets.QDoubleSpinBox(g1)
        sp1_phase.setRange(-360.0, 360.0); sp1_phase.setDecimals(1); sp1_phase.setSingleStep(5.0); sp1_phase.setValue(self.f1_phase_deg)

        cb1_mean = QtWidgets.QCheckBox("전체 신호 평균위치 표시", g1)
        cb1_mean.setChecked(self.f1_show_mean)

        # 이벤트 → 상태 업데이트 + 즉시 업데이트
        cb1_add.toggled.connect(lambda b: (setattr(self, "f1_add", bool(b)), api.request_update()))
        sp1_freq.valueChanged.connect(lambda v: (setattr(self, "f1_freq_hz", float(v)), api.request_update()))
        sp1_amp.valueChanged.connect(lambda v: (setattr(self, "f1_amp_uv", float(v)), api.request_update()))
        sp1_phase.valueChanged.connect(lambda v: (setattr(self, "f1_phase_deg", float(v)), api.request_update()))
        cb1_mean.toggled.connect(lambda b: (setattr(self, "f1_show_mean", bool(b)), api.request_update()))

        f1.addRow(cb1_add)
        f1.addRow("Frequency (Hz)", sp1_freq)
        f1.addRow("Amplitude (µV)", sp1_amp)
        f1.addRow("Phase (°)", sp1_phase)
        f1.addRow(cb1_mean)

        # --- Figure2 Controls ---
        g2 = QtWidgets.QGroupBox("Figure2 Controls")
        f2 = QtWidgets.QFormLayout(g2)

        cb2_add = QtWidgets.QCheckBox("Added Graph Sine (enable)", g2)
        cb2_add.setChecked(self.f2_add)

        sp2_freq = QtWidgets.QDoubleSpinBox(g2)
        sp2_freq.setRange(fmin, fmax); sp2_freq.setDecimals(fdec); sp2_freq.setSingleStep(0.001); sp2_freq.setValue(self.f2_freq_hz)

        sp2_amp = QtWidgets.QDoubleSpinBox(g2)
        sp2_amp.setRange(0.0, 5000.0); sp2_amp.setDecimals(1); sp2_amp.setSingleStep(10.0); sp2_amp.setValue(self.f2_amp_uv)

        sp2_phase = QtWidgets.QDoubleSpinBox(g2)
        sp2_phase.setRange(-360.0, 360.0); sp2_phase.setDecimals(1); sp2_phase.setSingleStep(5.0); sp2_phase.setValue(self.f2_phase_deg)

        cb2_mean = QtWidgets.QCheckBox("전체 신호 평균위치 표시", g2)
        cb2_mean.setChecked(self.f2_show_mean)

        cb2_add.toggled.connect(lambda b: (setattr(self, "f2_add", bool(b)), api.request_update()))
        sp2_freq.valueChanged.connect(lambda v: (setattr(self, "f2_freq_hz", float(v)), api.request_update()))
        sp2_amp.valueChanged.connect(lambda v: (setattr(self, "f2_amp_uv", float(v)), api.request_update()))
        sp2_phase.valueChanged.connect(lambda v: (setattr(self, "f2_phase_deg", float(v)), api.request_update()))
        cb2_mean.toggled.connect(lambda b: (setattr(self, "f2_show_mean", bool(b)), api.request_update()))

        f2.addRow(cb2_add)
        f2.addRow("Frequency (Hz)", sp2_freq)
        f2.addRow("Amplitude (µV)", sp2_amp)
        f2.addRow("Phase (°)", sp2_phase)
        f2.addRow(cb2_mean)

        # --- Pearson r + 수동 Update ---
        bottom = QtWidgets.QHBoxLayout()
        self.lbl_r = QtWidgets.QLabel("Pearson r (Fig1 vs Fig2): -")
        self.lbl_r.setStyleSheet("font-weight:600;")
        btn_update = QtWidgets.QPushButton("Update")
        btn_update.clicked.connect(api.request_update)
        bottom.addWidget(self.lbl_r)
        bottom.addStretch(1)
        bottom.addWidget(btn_update)

        # 레이아웃 조합
        root.addWidget(g1)
        root.addWidget(g2)
        root.addLayout(bottom)

        return box

    # CSV 로딩(1회 캐시)
    def _load_ecg(self, api: StudyAPI):
        if self._t is not None and self._ecg is not None:
            return self._t, self._ecg
        data = api.load_csv(self.csv_path, skip_header=1, delimiter=",")
        # 헤더 1줄 스킵, 컬럼: t_seconds, ecg_mV
        if data.shape[1] < 2:
            t = np.arange(data.shape[0]) / float(self.fs)
            ecg = data[:, 0].astype(float)
        else:
            t = data[:, 0].astype(float)
            ecg = data[:, 1].astype(float)
        self._t, self._ecg = t, ecg
        return t, ecg

    # 사인 생성 (주파수/진폭/위상) - mV 반환
    def _sine(self, t: np.ndarray, freq_hz: float, amp_uv: float, phase_deg: float) -> np.ndarray:
        # 주파수 안전 범위(나이퀴스트) 내로 클램프
        nyq = self.fs / 2.0
        f = max(0.0, min(float(freq_hz), nyq))
        amp_mV = float(amp_uv) * 1e-3  # µV → mV
        phase_rad = np.deg2rad(float(phase_deg))
        return amp_mV * np.sin(2*np.pi*f * t + phase_rad)

    def on_update(self, api: StudyAPI):
        # 데이터 로드
        t, ecg = self._load_ecg(api)

        # Figure1 최종 신호
        y1 = ecg.copy()
        if self.f1_add and self.f1_amp_uv > 0:
            y1 = y1 + self._sine(t, self.f1_freq_hz, self.f1_amp_uv, self.f1_phase_deg)

        # Figure2 최종 신호
        y2 = ecg.copy()
        if self.f2_add and self.f2_amp_uv > 0:
            y2 = y2 + self._sine(t, self.f2_freq_hz, self.f2_amp_uv, self.f2_phase_deg)

        # Pearson r(Fig1 vs Fig2)
        if np.std(y1) < 1e-12 or np.std(y2) < 1e-12:
            r = np.nan
        else:
            r = float(np.corrcoef(y1 - np.mean(y1), y2 - np.mean(y2))[0, 1])

        # Figure1 그리기: 원신호 + 최종신호 (+ 평균선 옵션)
        lbl1 = f"ECG + sine({self.f1_freq_hz:.3f} Hz)" if self.f1_add and self.f1_amp_uv > 0 else "ECG (same)"
        lines1 = [(t, ecg, "ECG"), (t, y1, lbl1)]
        if self.f1_show_mean:
            lines1.append((t, np.full_like(t, np.mean(y1)), "mean"))

        # Figure2 그리기: 원신호 + 최종신호 (+ 평균선 옵션)
        lbl2 = f"ECG + sine({self.f2_freq_hz:.3f} Hz)" if self.f2_add and self.f2_amp_uv > 0 else "ECG (same)"
        lines2 = [(t, ecg, "ECG"), (t, y2, lbl2)]
        if self.f2_show_mean:
            lines2.append((t, np.full_like(t, np.mean(y2)), "mean"))

        api.set_figure1(lines1)
        api.set_figure2(lines2)

        # r 라벨 갱신
        if self.lbl_r is not None:
            self.lbl_r.setText("Pearson r (Fig1 vs Fig2): N/A" if np.isnan(r) else f"Pearson r (Fig1 vs Fig2): {r:.4f}")


# ---- 런처/미리보기 호환 래퍼 ----
def create_window(parent=None):
    return _tpl_create_window(ECG60HzControlStudy())

def description():
    try:
        return ECG60HzControlStudy().get_description()
    except Exception:
        return "ECG + 임의 주파수 사인 제어 예제"
