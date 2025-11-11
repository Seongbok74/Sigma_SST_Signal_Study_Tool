# Subject/1_Correlation_Coefficient/pearson_study/ecg_60bpm_tri_pulse_controls.py
# -*- coding: utf-8 -*-
"""
ECG 60bpm 신호를 Figure1/2에 동일하게 불러오고,
각 Figure별로 '삼각 펄스(train)'를 (주파수/진폭/위상/듀티/폭/평균선) 개별 제어하여
두 결과 신호의 Pearson 상관값 변화를 관찰하는 예제.

- Frequency(Hz): 0.001 ~ fs/2
- Amplitude(µV): 1 µV = 0.001 mV 로 내부 변환
- Phase(°): 주기 위상 이동
- Duty(%): 한 주기 중 펄스 ON 구간 비율 (양수 펄스, 나머지는 0)
- Width(%): ON 구간 안에서 꼭짓점 위치 (50%면 대칭 삼각, 0~100%로 비대칭 제어)
"""

import os
import numpy as np
from PyQt5 import QtWidgets

from Application.templet.templet_compare_signal import create_window as _tpl_create_window, StudyAPI


class ECGTriPulseControlStudy:
    def __init__(self):
        # 경로(현재 파일 기준): ../data/ecg_60bpm_250sps_5sec_1mVpp.csv
        here = os.path.dirname(__file__)
        self.csv_path = os.path.normpath(os.path.join(here, "..", "data", "ecg_60bpm_250sps_5sec_1mVpp.csv"))

        self.fs = 250.0  # Hz

        # Figure1 기본값
        self.f1_add = True
        self.f1_freq_hz = 10.0
        self.f1_amp_uv = 50.0
        self.f1_phase_deg = 0.0
        self.f1_duty_pct = 20.0     # ON 구간
        self.f1_width_pct = 50.0    # 꼭짓점 위치(ON 구간 내)
        self.f1_show_mean = False

        # Figure2 기본값
        self.f2_add = False
        self.f2_freq_hz = 10.0
        self.f2_amp_uv = 0.0
        self.f2_phase_deg = 0.0
        self.f2_duty_pct = 20.0
        self.f2_width_pct = 50.0
        self.f2_show_mean = False

        self.lbl_r = None
        self._t = None
        self._ecg = None

    def get_description(self) -> str:
        nyq = self.fs / 2.0
        return (
            "ECG(60bpm, 250sps, 5s, 1mVpp) 위에 삼각 펄스(train)를 개별 추가해 Pearson r 변화를 관찰합니다.\n"
            f"- Frequency: 0.001 ~ {nyq:.3f} Hz\n"
            "- Duty: 한 주기 내 ON 비율(%), Width: ON 구간 내 꼭짓점 위치(%)\n"
            "- 펄스는 양수(0~Amp)로 더해지며, 평균선 표시 옵션 제공"
        )

    def create_controls(self, parent: QtWidgets.QWidget, api: StudyAPI):
        box = QtWidgets.QWidget(parent)
        root = QtWidgets.QVBoxLayout(box); root.setSpacing(8)

        fmin, fmax, fdec = 0.001, self.fs/2.0, 3

        # ---- Figure1 ----
        g1 = QtWidgets.QGroupBox("Figure1 Controls (Triangle Pulse)")
        f1 = QtWidgets.QFormLayout(g1)

        cb1_add = QtWidgets.QCheckBox("Add Triangle Pulse", g1); cb1_add.setChecked(self.f1_add)
        sp1_freq  = QtWidgets.QDoubleSpinBox(g1); sp1_freq.setRange(fmin, fmax); sp1_freq.setDecimals(fdec); sp1_freq.setSingleStep(0.001); sp1_freq.setValue(self.f1_freq_hz)
        sp1_amp   = QtWidgets.QDoubleSpinBox(g1); sp1_amp.setRange(0.0, 5000.0); sp1_amp.setDecimals(1); sp1_amp.setSingleStep(10.0); sp1_amp.setValue(self.f1_amp_uv)
        sp1_phase = QtWidgets.QDoubleSpinBox(g1); sp1_phase.setRange(-360.0, 360.0); sp1_phase.setDecimals(1); sp1_phase.setSingleStep(5.0); sp1_phase.setValue(self.f1_phase_deg)
        sp1_duty  = QtWidgets.QDoubleSpinBox(g1); sp1_duty.setRange(0.1, 99.9); sp1_duty.setDecimals(1); sp1_duty.setSingleStep(0.5); sp1_duty.setValue(self.f1_duty_pct)
        sp1_width = QtWidgets.QDoubleSpinBox(g1); sp1_width.setRange(1.0, 99.0); sp1_width.setDecimals(1); sp1_width.setSingleStep(0.5); sp1_width.setValue(self.f1_width_pct)
        cb1_mean  = QtWidgets.QCheckBox("전체 신호 평균위치 표시", g1); cb1_mean.setChecked(self.f1_show_mean)

        cb1_add.toggled.connect(lambda b: (setattr(self, "f1_add", bool(b)), api.request_update()))
        sp1_freq.valueChanged.connect(lambda v: (setattr(self, "f1_freq_hz", float(v)), api.request_update()))
        sp1_amp.valueChanged.connect(lambda v: (setattr(self, "f1_amp_uv", float(v)), api.request_update()))
        sp1_phase.valueChanged.connect(lambda v: (setattr(self, "f1_phase_deg", float(v)), api.request_update()))
        sp1_duty.valueChanged.connect(lambda v: (setattr(self, "f1_duty_pct", float(v)), api.request_update()))
        sp1_width.valueChanged.connect(lambda v: (setattr(self, "f1_width_pct", float(v)), api.request_update()))
        cb1_mean.toggled.connect(lambda b: (setattr(self, "f1_show_mean", bool(b)), api.request_update()))

        f1.addRow(cb1_add)
        f1.addRow("Frequency (Hz)", sp1_freq)
        f1.addRow("Amplitude (µV)", sp1_amp)
        f1.addRow("Phase (°)", sp1_phase)
        f1.addRow("Duty (%)", sp1_duty)
        f1.addRow("Width (%)", sp1_width)
        f1.addRow(cb1_mean)

        # ---- Figure2 ----
        g2 = QtWidgets.QGroupBox("Figure2 Controls (Triangle Pulse)")
        f2 = QtWidgets.QFormLayout(g2)

        cb2_add = QtWidgets.QCheckBox("Add Triangle Pulse", g2); cb2_add.setChecked(self.f2_add)
        sp2_freq  = QtWidgets.QDoubleSpinBox(g2); sp2_freq.setRange(fmin, fmax); sp2_freq.setDecimals(fdec); sp2_freq.setSingleStep(0.001); sp2_freq.setValue(self.f2_freq_hz)
        sp2_amp   = QtWidgets.QDoubleSpinBox(g2); sp2_amp.setRange(0.0, 5000.0); sp2_amp.setDecimals(1); sp2_amp.setSingleStep(10.0); sp2_amp.setValue(self.f2_amp_uv)
        sp2_phase = QtWidgets.QDoubleSpinBox(g2); sp2_phase.setRange(-360.0, 360.0); sp2_phase.setDecimals(1); sp2_phase.setSingleStep(5.0); sp2_phase.setValue(self.f2_phase_deg)
        sp2_duty  = QtWidgets.QDoubleSpinBox(g2); sp2_duty.setRange(0.1, 99.9); sp2_duty.setDecimals(1); sp2_duty.setSingleStep(0.5); sp2_duty.setValue(self.f2_duty_pct)
        sp2_width = QtWidgets.QDoubleSpinBox(g2); sp2_width.setRange(1.0, 99.0); sp2_width.setDecimals(1); sp2_width.setSingleStep(0.5); sp2_width.setValue(self.f2_width_pct)
        cb2_mean  = QtWidgets.QCheckBox("전체 신호 평균위치 표시", g2); cb2_mean.setChecked(self.f2_show_mean)

        cb2_add.toggled.connect(lambda b: (setattr(self, "f2_add", bool(b)), api.request_update()))
        sp2_freq.valueChanged.connect(lambda v: (setattr(self, "f2_freq_hz", float(v)), api.request_update()))
        sp2_amp.valueChanged.connect(lambda v: (setattr(self, "f2_amp_uv", float(v)), api.request_update()))
        sp2_phase.valueChanged.connect(lambda v: (setattr(self, "f2_phase_deg", float(v)), api.request_update()))
        sp2_duty.valueChanged.connect(lambda v: (setattr(self, "f2_duty_pct", float(v)), api.request_update()))
        sp2_width.valueChanged.connect(lambda v: (setattr(self, "f2_width_pct", float(v)), api.request_update()))
        cb2_mean.toggled.connect(lambda b: (setattr(self, "f2_show_mean", bool(b)), api.request_update()))

        f2.addRow(cb2_add)
        f2.addRow("Frequency (Hz)", sp2_freq)
        f2.addRow("Amplitude (µV)", sp2_amp)
        f2.addRow("Phase (°)", sp2_phase)
        f2.addRow("Duty (%)", sp2_duty)
        f2.addRow("Width (%)", sp2_width)
        f2.addRow(cb2_mean)

        # Pearson r + 수동 Update
        bottom = QtWidgets.QHBoxLayout()
        self.lbl_r = QtWidgets.QLabel("Pearson r (Fig1 vs Fig2): -"); self.lbl_r.setStyleSheet("font-weight:600;")
        btn_update = QtWidgets.QPushButton("Update"); btn_update.clicked.connect(api.request_update)
        bottom.addWidget(self.lbl_r); bottom.addStretch(1); bottom.addWidget(btn_update)

        root.addWidget(g1); root.addWidget(g2); root.addLayout(bottom)
        return box

    # CSV 1회 로드
    def _load_ecg(self, api: StudyAPI):
        if self._t is not None and self._ecg is not None:
            return self._t, self._ecg
        data = api.load_csv(self.csv_path, skip_header=1, delimiter=",")
        if data.shape[1] < 2:
            t = np.arange(data.shape[0]) / float(self.fs)
            ecg = data[:, 0].astype(float)
        else:
            t = data[:, 0].astype(float)
            ecg = data[:, 1].astype(float)
        self._t, self._ecg = t, ecg
        return t, ecg

    # 삼각 펄스(train) 생성: 양수(0~Amp)로 출력
    def _tri_pulse(self, t: np.ndarray, freq_hz: float, amp_uv: float,
                   phase_deg: float, duty_pct: float, width_pct: float) -> np.ndarray:
        nyq = self.fs / 2.0
        f = max(0.0, min(float(freq_hz), nyq))
        amp_mV = float(amp_uv) * 1e-3  # µV → mV
        phase = np.deg2rad(float(phase_deg))
        duty = np.clip(float(duty_pct), 0.1, 99.9) / 100.0   # ON 비율
        apex = np.clip(float(width_pct), 1.0, 99.0) / 100.0  # ON 구간 내 꼭짓점 위치(0~1)

        # 주기 위상 [0,1)
        frac = (f * t + phase / (2.0*np.pi)) % 1.0

        y = np.zeros_like(t, dtype=float)
        on = frac < duty
        if not np.any(on):
            return y

        # ON 구간 내부 정규화 [0,1)
        u = np.zeros_like(frac)
        u[on] = frac[on] / duty

        # 삼각 펄스: 0~amp_mV (apex에서 최대)
        # u <= apex: 0 -> 1 선형상승 / u > apex: 1 -> 0 선형하강
        # apex==0/1 방어
        left = (u <= apex) & on
        right = (u > apex) & on
        if apex > 1e-6:
            y[left] = amp_mV * (u[left] / apex)
        else:
            y[left] = 0.0
        if (1.0 - apex) > 1e-6:
            y[right] = amp_mV * ((1.0 - u[right]) / (1.0 - apex))
        else:
            y[right] = 0.0

        return y

    def on_update(self, api: StudyAPI):
        t, ecg = self._load_ecg(api)

        y1 = ecg.copy()
        if self.f1_add and self.f1_amp_uv > 0.0 and self.f1_duty_pct > 0.0:
            y1 = y1 + self._tri_pulse(t, self.f1_freq_hz, self.f1_amp_uv,
                                      self.f1_phase_deg, self.f1_duty_pct, self.f1_width_pct)

        y2 = ecg.copy()
        if self.f2_add and self.f2_amp_uv > 0.0 and self.f2_duty_pct > 0.0:
            y2 = y2 + self._tri_pulse(t, self.f2_freq_hz, self.f2_amp_uv,
                                      self.f2_phase_deg, self.f2_duty_pct, self.f2_width_pct)

        # Pearson r(Fig1 vs Fig2) — 평균 제거 후 계산
        if np.std(y1) < 1e-12 or np.std(y2) < 1e-12:
            r = np.nan
        else:
            r = float(np.corrcoef(y1 - np.mean(y1), y2 - np.mean(y2))[0, 1])

        # Figure1
        lbl1 = (f"ECG + triPulse({self.f1_freq_hz:.3f} Hz, "
                f"D{self.f1_duty_pct:.1f}%, W{self.f1_width_pct:.1f}%)"
                if self.f1_add and self.f1_amp_uv > 0 else "ECG (same)")
        lines1 = [(t, ecg, "ECG"), (t, y1, lbl1)]
        if self.f1_show_mean:
            lines1.append((t, np.full_like(t, np.mean(y1)), "mean"))

        # Figure2
        lbl2 = (f"ECG + triPulse({self.f2_freq_hz:.3f} Hz, "
                f"D{self.f2_duty_pct:.1f}%, W{self.f2_width_pct:.1f}%)"
                if self.f2_add and self.f2_amp_uv > 0 else "ECG (same)")
        lines2 = [(t, ecg, "ECG"), (t, y2, lbl2)]
        if self.f2_show_mean:
            lines2.append((t, np.full_like(t, np.mean(y2)), "mean"))

        api.set_figure1(lines1)
        api.set_figure2(lines2)

        if self.lbl_r is not None:
            self.lbl_r.setText("Pearson r (Fig1 vs Fig2): N/A" if np.isnan(r) else f"Pearson r (Fig1 vs Fig2): {r:.4f}")


# ---- 런처/미리보기 호환 래퍼 ----
def create_window(parent=None):
    return _tpl_create_window(ECGTriPulseControlStudy())

def description():
    try:
        return ECGTriPulseControlStudy().get_description()
    except Exception:
        return "ECG + 삼각 펄스(train) 제어 예제"
