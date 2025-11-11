#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Painter (250 sps, 5 s)

기능
- 250 Hz × 5 s = 1250 샘플 타임라인
- 초기 신호: 0 mV 직선
- 마우스 드래그로 그리기 (이전 지점과 현재 지점을 선형보간하여 연속 수정)
- matplotlib NavigationToolbar로 확대/축소/이동
- Undo / Redo
- CSV 저장/불러오기 (헤더: t_seconds, ecg_mV)

의존성:
    pip install pyqt5 matplotlib numpy
"""

import os
import sys
import csv
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavToolbar
from matplotlib.figure import Figure


FS = 250.0
DUR = 5.0
N = int(FS * DUR)            # 1250
T = np.arange(N) / FS        # seconds


class SignalPainter(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal Painter (250 sps, 5 s)")
        self.resize(1100, 650)

        # data
        self.t = T.copy()
        self.y = np.zeros_like(self.t, dtype=float)
        self._y_before_stroke = None     # for undo capture on stroke start
        self.undo_stack = []             # list of numpy arrays
        self.redo_stack = []

        # central UI
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        # figure
        self.canvas = FigureCanvas(Figure(figsize=(8, 4), dpi=100))
        v.addWidget(self.canvas, 1)
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude (mV)")
        self.line_main, = self.ax.plot(self.t, self.y, lw=1.5, label="signal")
        self.ax.legend(loc="upper right")

        # toolbar (zoom/pan)
        self.toolbar = NavToolbar(self.canvas, self)
        v.addWidget(self.toolbar)

        # bottom buttons
        h = QtWidgets.QHBoxLayout()
        self.btn_new = QtWidgets.QPushButton("New (zero)")
        self.btn_open = QtWidgets.QPushButton("Open CSV")
        self.btn_save = QtWidgets.QPushButton("Save CSV")
        self.btn_undo = QtWidgets.QPushButton("Undo")
        self.btn_redo = QtWidgets.QPushButton("Redo")
        self.lbl_info = QtWidgets.QLabel("Ready")
        self.lbl_info.setStyleSheet("color:#444;")
        h.addWidget(self.btn_new)
        h.addWidget(self.btn_open)
        h.addWidget(self.btn_save)
        h.addWidget(self.btn_undo)
        h.addWidget(self.btn_redo)
        h.addStretch(1)
        h.addWidget(self.lbl_info)
        v.addLayout(h)

        # connections
        self.btn_new.clicked.connect(self.on_new)
        self.btn_open.clicked.connect(self.on_open)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_undo.clicked.connect(self.on_undo)
        self.btn_redo.clicked.connect(self.on_redo)

        # shortcuts
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_N, self, activated=self.on_new)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_O, self, activated=self.on_open)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self, activated=self.on_save)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_Z, self, activated=self.on_undo)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_Y, self, activated=self.on_redo)

        # mouse drawing state
        self.drawing = False
        self.last_ix = None

        # connect mpl events
        self.cid_press   = self.canvas.mpl_connect("button_press_event", self.on_press)
        self.cid_release = self.canvas.mpl_connect("button_release_event", self.on_release)
        self.cid_motion  = self.canvas.mpl_connect("motion_notify_event", self.on_motion)

        self.refresh_plot(autoscale=True)

    # ---------- plotting ----------
    def refresh_plot(self, autoscale=False):
        self.line_main.set_data(self.t, self.y)
        if autoscale:
            if len(self.y) > 0:
                ymin, ymax = float(np.min(self.y)), float(np.max(self.y))
                pad = 0.1 * max(1e-9, ymax - ymin)
                self.ax.set_ylim(ymin - pad, ymax + pad)
            self.ax.set_xlim(float(self.t[0]), float(self.t[-1]))
        self.canvas.draw_idle()

    # ---------- mouse editing ----------
    def on_press(self, event):
        # left button in axes → start drawing
        if event.inaxes != self.ax:
            return
        if event.button == 1:
            self.drawing = True
            # capture undo baseline once per stroke
            self._y_before_stroke = self.y.copy()
            self.redo_stack.clear()
            self.apply_point(event.xdata, event.ydata, interpolate=False)

    def on_motion(self, event):
        # show cursor info in status
        if event.inaxes == self.ax and event.xdata is not None and event.ydata is not None:
            self.lbl_info.setText(f"t={event.xdata:.4f}s, y={event.ydata:.4f} mV")
        if not self.drawing:
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        self.apply_point(event.xdata, event.ydata, interpolate=True)

    def on_release(self, event):
        if not self.drawing:
            return
        self.drawing = False
        self.last_ix = None
        # push undo snapshot if changed
        if self._y_before_stroke is not None and not np.allclose(self._y_before_stroke, self.y):
            self.undo_stack.append(self._y_before_stroke)
        self._y_before_stroke = None

    def apply_point(self, xdata, ydata, interpolate=True):
        # clamp x to timeline
        x = float(np.clip(xdata, self.t[0], self.t[-1]))
        # nearest index
        ix = int(round(x * FS))
        ix = int(np.clip(ix, 0, N - 1))

        if interpolate and self.last_ix is not None and self.last_ix != ix:
            # draw a continuous stroke by filling indices between last_ix and ix
            lo = min(self.last_ix, ix)
            hi = max(self.last_ix, ix)
            # interpolate y between last and current
            y0 = self.y[self.last_ix]
            y1 = float(ydata)
            if hi > lo:
                yy = np.linspace(y0, y1, hi - lo + 1)
                self.y[lo:hi + 1] = yy
        else:
            # single point set
            self.y[ix] = float(ydata)

        self.last_ix = ix
        self.refresh_plot(autoscale=False)

    # ---------- commands ----------
    def on_new(self):
        if self.confirm_discard():
            self.push_undo()
            self.y[:] = 0.0
            self.refresh_plot(autoscale=True)

    def on_open(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV files (*.csv);;All files (*.*)")
        if not path:
            return
        try:
            t, y = self.load_csv(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(e))
            return

        # resample/fit to our fixed grid if needed
        if len(t) != N or not np.allclose(t, self.t, atol=1e-9):
            # linear interpolation onto fixed T
            self.push_undo()
            self.y[:] = np.interp(self.t, t, y)
        else:
            self.push_undo()
            self.y[:] = y

        self.refresh_plot(autoscale=True)
        self.statusBar().showMessage(f"Loaded: {os.path.basename(path)}", 3000)

    def on_save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save CSV", "signal_250sps_5s.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            self.save_csv(path, self.t, self.y)
            self.statusBar().showMessage(f"Saved: {os.path.basename(path)}", 3000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(e))

    def on_undo(self):
        if not self.undo_stack:
            return
        prev = self.undo_stack.pop()
        self.redo_stack.append(self.y.copy())
        self.y[:] = prev
        self.refresh_plot(autoscale=False)

    def on_redo(self):
        if not self.redo_stack:
            return
        nxt = self.redo_stack.pop()
        self.undo_stack.append(self.y.copy())
        self.y[:] = nxt
        self.refresh_plot(autoscale=False)

    def push_undo(self):
        self.undo_stack.append(self.y.copy())
        self.redo_stack.clear()

    def confirm_discard(self) -> bool:
        # 간단 버전: 바로 OK (필요시 확인창 추가 가능)
        return True

    # ---------- CSV I/O ----------
    @staticmethod
    def load_csv(path: str):
        # Expect header: t_seconds, ecg_mV
        t_list, y_list = [], []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            # accept with/without header; if header not numeric, skip first row
            def is_float(s):
                try:
                    float(s); return True
                except Exception:
                    return False
            if header and (not is_float(header[0]) or not is_float(header[1])):
                # header line consumed; read data
                pass
            else:
                # header is actually data
                if header:
                    t_list.append(float(header[0])); y_list.append(float(header[1]))
            for row in reader:
                if len(row) < 2:
                    continue
                t_list.append(float(row[0])); y_list.append(float(row[1]))
        t = np.asarray(t_list, dtype=float)
        y = np.asarray(y_list, dtype=float)
        if t.ndim != 1 or y.ndim != 1 or t.size != y.size or t.size == 0:
            raise ValueError("Invalid CSV shape")
        return t, y

    @staticmethod
    def save_csv(path: str, t: np.ndarray, y: np.ndarray):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t_seconds", "ecg_mV"])
            for ti, yi in zip(t, y):
                w.writerow([f"{ti:.6f}", f"{yi:.9f}"])


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = SignalPainter()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
