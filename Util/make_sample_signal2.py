#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Painter (250 sps, 5 s) — with Background, Error plot, Metrics, Mean lines

옵션(체크박스 On일 때만 동작)
- Show Error: 하단 error = y - background 그래프
- Show Metrics: Pearson r / RMSE / SNR(dB) 실시간 표시
- Show Mean Lines: 상단 그래프에 신호/배경 평균선 표시

단축키: Ctrl+N/O/S/Z/Y
"""

import os
import sys
import csv
import numpy as np

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavToolbar
from matplotlib.figure import Figure

FS = 250.0
DUR = 5.0
N = int(FS * DUR)
T = np.arange(N) / FS


class SignalPainter(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal Painter (250 sps, 5 s) — with BG/ERROR/METRICS/MEAN")
        self.resize(1180, 740)

        # data
        self.t = T.copy()
        self.y = np.zeros_like(self.t, dtype=float)

        # background
        self.bg_y = None
        self.bg_visible = True

        # undo/redo
        self._y_before_stroke = None
        self.undo_stack = []
        self.redo_stack = []

        # ===== UI =====
        central = QtWidgets.QWidget(self); self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central); v.setContentsMargins(8, 8, 8, 8); v.setSpacing(6)

        # figure (2-row layout: main / error)
        self.canvas = FigureCanvas(Figure(figsize=(8, 4), dpi=100))
        v.addWidget(self.canvas, 1)
        self.fig = self.canvas.figure
        self.gs = self.fig.add_gridspec(2, 1, height_ratios=[3, 1])
        self.ax = self.fig.add_subplot(self.gs[0])
        self.ax_err = self.fig.add_subplot(self.gs[1], sharex=self.ax)

        # main axes
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude (mV)")
        # background & means
        self.line_bg, = self.ax.plot(self.t, np.zeros_like(self.t), lw=1.0, linestyle="--", alpha=0.6, label="background")
        self.line_bg.set_visible(False)
        self.line_mean_sig, = self.ax.plot(self.t, np.zeros_like(self.t), lw=1.0, linestyle=":", alpha=0.9, label="mean(signal)")
        self.line_mean_bg,  = self.ax.plot(self.t, np.zeros_like(self.t), lw=1.0, linestyle=":", alpha=0.9, label="mean(background)")
        self.line_mean_sig.set_visible(False); self.line_mean_bg.set_visible(False)

        # editable signal
        self.line_main, = self.ax.plot(self.t, self.y, lw=1.8, label="signal")
        self.ax.legend(loc="upper right")

        # error axes
        self.ax_err.grid(True, alpha=0.3)
        self.ax_err.set_xlabel("Time (s)")
        self.ax_err.set_ylabel("Error (mV)")
        self.line_err, = self.ax_err.plot(self.t, np.zeros_like(self.t), lw=1.2, label="error = y - bg")
        self.ax_err.set_visible(False)

        # toolbar
        self.toolbar = NavToolbar(self.canvas, self); v.addWidget(self.toolbar)

        # background controls
        row_bg = QtWidgets.QHBoxLayout()
        self.btn_bg_load = QtWidgets.QPushButton("Load Background CSV")
        self.btn_bg_toggle = QtWidgets.QPushButton("Hide Background")
        self.btn_bg_apply = QtWidgets.QPushButton("기본값 = 밑그림값으로")
        row_bg.addWidget(self.btn_bg_load); row_bg.addWidget(self.btn_bg_toggle); row_bg.addWidget(self.btn_bg_apply); row_bg.addStretch(1)
        v.addLayout(row_bg)

        # options
        row_opt = QtWidgets.QHBoxLayout()
        self.chk_err = QtWidgets.QCheckBox("Show Error (y - background)")
        self.chk_metrics = QtWidgets.QCheckBox("Show Metrics (r / RMSE / SNR)")
        self.chk_means = QtWidgets.QCheckBox("Show Mean Lines")
        row_opt.addWidget(self.chk_err); row_opt.addWidget(self.chk_metrics); row_opt.addWidget(self.chk_means); row_opt.addStretch(1)
        v.addLayout(row_opt)

        # bottom actions
        row_bottom = QtWidgets.QHBoxLayout()
        self.btn_new = QtWidgets.QPushButton("New (zero)")
        self.btn_open = QtWidgets.QPushButton("Open CSV")
        self.btn_save = QtWidgets.QPushButton("Save CSV")
        self.btn_undo = QtWidgets.QPushButton("Undo")
        self.btn_redo = QtWidgets.QPushButton("Redo")
        self.lbl_metrics = QtWidgets.QLabel(""); self.lbl_metrics.setStyleSheet("color:#222; font-weight:600;")
        self.lbl_info = QtWidgets.QLabel("Ready"); self.lbl_info.setStyleSheet("color:#444;")
        row_bottom.addWidget(self.btn_new); row_bottom.addWidget(self.btn_open); row_bottom.addWidget(self.btn_save)
        row_bottom.addWidget(self.btn_undo); row_bottom.addWidget(self.btn_redo)
        row_bottom.addStretch(1); row_bottom.addWidget(self.lbl_metrics); row_bottom.addSpacing(12); row_bottom.addWidget(self.lbl_info)
        v.addLayout(row_bottom)

        # connections
        self.btn_new.clicked.connect(self.on_new)
        self.btn_open.clicked.connect(self.on_open)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_undo.clicked.connect(self.on_undo)
        self.btn_redo.clicked.connect(self.on_redo)

        self.btn_bg_load.clicked.connect(self.on_bg_load)
        self.btn_bg_toggle.clicked.connect(self.on_bg_toggle)
        self.btn_bg_apply.clicked.connect(self.on_bg_apply)

        self.chk_err.toggled.connect(self.on_toggle_error)
        self.chk_metrics.toggled.connect(lambda _: self.refresh_plot(autoscale=False))
        self.chk_means.toggled.connect(lambda _: self.refresh_plot(autoscale=False))

        # shortcuts
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_N, self, activated=self.on_new)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_O, self, activated=self.on_open)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self, activated=self.on_save)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_Z, self, activated=self.on_undo)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_Y, self, activated=self.on_redo)

        # drawing state
        self.drawing = False
        self.last_ix = None
        self.cid_press   = self.canvas.mpl_connect("button_press_event", self.on_press)
        self.cid_release = self.canvas.mpl_connect("button_release_event", self.on_release)
        self.cid_motion  = self.canvas.mpl_connect("motion_notify_event", self.on_motion)

        self.refresh_plot(autoscale=True)

    # ===== helpers =====
    def _set_heights_for_error(self, show_err: bool):
        self.gs.set_height_ratios([3, 1 if show_err else 0.0001])
        self.ax_err.set_visible(show_err)
        self.ax_err.xaxis.set_visible(show_err); self.ax_err.yaxis.set_visible(show_err)

    def refresh_plot(self, autoscale=False):
        # background
        if self.bg_y is not None and self.bg_visible:
            self.line_bg.set_visible(True)
            self.line_bg.set_data(self.t, self.bg_y)
        else:
            self.line_bg.set_visible(False)

        # main
        self.line_main.set_data(self.t, self.y)

        # mean lines
        if self.chk_means.isChecked():
            y_mean = float(np.mean(self.y)) if self.y.size else 0.0
            self.line_mean_sig.set_data(self.t, np.full_like(self.t, y_mean))
            self.line_mean_sig.set_visible(True)
            if self.bg_y is not None and self.bg_visible:
                bg_mean = float(np.mean(self.bg_y))
                self.line_mean_bg.set_data(self.t, np.full_like(self.t, bg_mean))
                self.line_mean_bg.set_visible(True)
            else:
                self.line_mean_bg.set_visible(False)
        else:
            self.line_mean_sig.set_visible(False); self.line_mean_bg.set_visible(False)

        # error plot
        show_err = self.chk_err.isChecked() and (self.bg_y is not None)
        self._set_heights_for_error(show_err)
        if show_err:
            err = self.y - self.bg_y
            self.line_err.set_data(self.t, err)
            if autoscale:
                ymin, ymax = np.min(err), np.max(err)
                pad = 0.1 * max(1e-9, ymax - ymin)
                self.ax_err.set_ylim(float(ymin - pad), float(ymax + pad))
            self.ax_err.relim(); self.ax_err.autoscale_view(scalex=False, scaley=not autoscale)

        # autoscale main
        if autoscale:
            ymin = float(np.min(self.y)); ymax = float(np.max(self.y))
            if self.line_bg.get_visible():
                ymin = min(ymin, float(np.min(self.bg_y))); ymax = max(ymax, float(np.max(self.bg_y)))
            pad = 0.1 * max(1e-9, ymax - ymin)
            self.ax.set_ylim(ymin - pad, ymax + pad); self.ax.set_xlim(float(self.t[0]), float(self.t[-1]))

        self.ax.relim(); self.ax.autoscale_view(scalex=False, scaley=False)
        self.update_metrics_label()
        self.canvas.draw_idle()

    def update_metrics_label(self):
        if not self.chk_metrics.isChecked() or self.bg_y is None:
            self.lbl_metrics.setText(""); return
        y, bg = self.y, self.bg_y
        if y.size != bg.size:
            self.lbl_metrics.setText("Metrics: N/A (size mismatch)"); return
        sx, sy = float(np.std(y)), float(np.std(bg))
        r = float("nan") if (sx < 1e-15 or sy < 1e-15) else float(np.corrcoef(y, bg)[0, 1])
        err = y - bg
        rmse = float(np.sqrt(np.mean(err*err)))
        rms_sig = float(np.sqrt(np.mean(bg*bg))); rms_err = float(np.sqrt(np.mean(err*err)))
        if rms_err < 1e-15: snr_txt = "∞"
        elif rms_sig < 1e-15: snr_txt = "−∞"
        else: snr_txt = f"{20.0*np.log10(rms_sig/rms_err):.2f}"
        if snr_txt in ("∞", "−∞"):
            self.lbl_metrics.setText(f"r={r:.4f}   RMSE={rmse:.6f} mV   SNR={snr_txt} dB")
        else:
            self.lbl_metrics.setText(f"r={r:.4f}   RMSE={rmse:.6f} mV   SNR={snr_txt} dB")

    # ===== option handlers =====
    def on_toggle_error(self, checked):
        self.refresh_plot(autoscale=True)

    # ===== mouse drawing =====
    def on_press(self, event):
        if event.inaxes != self.ax: return
        if event.button == 1:
            self.drawing = True
            self._y_before_stroke = self.y.copy()
            self.redo_stack.clear()
            self.apply_point(event.xdata, event.ydata, interpolate=False)

    def on_motion(self, event):
        if event.inaxes == self.ax and event.xdata is not None and event.ydata is not None:
            self.lbl_info.setText(f"t={event.xdata:.4f}s, y={event.ydata:.4f} mV")
        if not self.drawing: return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None: return
        self.apply_point(event.xdata, event.ydata, interpolate=True)

    def on_release(self, event):
        if not self.drawing: return
        self.drawing = False; self.last_ix = None
        if self._y_before_stroke is not None and not np.allclose(self._y_before_stroke, self.y):
            self.undo_stack.append(self._y_before_stroke)
        self._y_before_stroke = None

    def apply_point(self, xdata, ydata, interpolate=True):
        x = float(np.clip(xdata, self.t[0], self.t[-1]))
        ix = int(np.clip(int(round(x * FS)), 0, N-1))
        if interpolate and getattr(self, "last_ix", None) is not None and self.last_ix != ix:
            lo, hi = min(self.last_ix, ix), max(self.last_ix, ix)
            y0, y1 = self.y[self.last_ix], float(ydata)
            if hi > lo:
                self.y[lo:hi+1] = np.linspace(y0, y1, hi-lo+1)
        else:
            self.y[ix] = float(ydata)
        self.last_ix = ix
        self.refresh_plot(autoscale=False)

    # ===== file/edit handlers =====
    def on_new(self):
        if self.confirm_discard():
            self.push_undo()
            self.y[:] = 0.0
            self.refresh_plot(autoscale=True)

    def on_open(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV files (*.csv);;All files (*.*)")
        if not path: return
        try:
            t, y = self.load_csv(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(e)); return
        self.push_undo()
        if len(t) != len(self.t) or not np.allclose(t, self.t, atol=1e-9):
            self.y[:] = np.interp(self.t, t, y)
        else:
            self.y[:] = y
        self.refresh_plot(autoscale=True)
        self.statusBar().showMessage(f"Loaded: {os.path.basename(path)}", 3000)

    def on_save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save CSV", "signal_250sps_5s.csv", "CSV files (*.csv)")
        if not path: return
        try:
            self.save_csv(path, self.t, self.y)
            self.statusBar().showMessage(f"Saved: {os.path.basename(path)}", 3000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(e))

    def on_undo(self):
        if not self.undo_stack: return
        prev = self.undo_stack.pop()
        self.redo_stack.append(self.y.copy())
        self.y[:] = prev
        self.refresh_plot(autoscale=False)

    def on_redo(self):
        if not self.redo_stack: return
        nxt = self.redo_stack.pop()
        self.undo_stack.append(self.y.copy())
        self.y[:] = nxt
        self.refresh_plot(autoscale=False)

    def push_undo(self):
        self.undo_stack.append(self.y.copy()); self.redo_stack.clear()

    def confirm_discard(self) -> bool:
        return True  # 필요시 확인 대화상자 구현 가능

    # ===== background handlers =====
    def on_bg_load(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Background CSV", "", "CSV files (*.csv);;All files (*.*)")
        if not path: return
        try:
            t, y = self.load_csv(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Load Background failed", str(e)); return
        bg = np.interp(self.t, t, y) if (len(t) != len(self.t) or not np.allclose(t, self.t, atol=1e-9)) else y.copy()
        self.bg_y = bg; self.bg_visible = True; self.btn_bg_toggle.setText("Hide Background")
        self.refresh_plot(autoscale=True)
        self.statusBar().showMessage(f"Background: {os.path.basename(path)}", 3000)

    def on_bg_toggle(self):
        if self.bg_y is None:
            QtWidgets.QMessageBox.information(self, "Background", "먼저 배경 CSV를 불러오세요."); return
        self.bg_visible = not self.bg_visible
        self.btn_bg_toggle.setText("Hide Background" if self.bg_visible else "Show Background")
        self.refresh_plot(autoscale=False)

    def on_bg_apply(self):
        if self.bg_y is None:
            QtWidgets.QMessageBox.information(self, "Apply Background", "배경 CSV가 없습니다."); return
        self.push_undo()
        self.y[:] = self.bg_y
        self.refresh_plot(autoscale=True)
        self.statusBar().showMessage("Signal replaced with background values", 2000)

    # ===== CSV I/O =====
    @staticmethod
    def load_csv(path: str):
        # 허용 형식: header 유무 모두 OK (t_seconds, ecg_mV)
        t_list, y_list = [], []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)

            def is_float(s):
                try: float(s); return True
                except Exception: return False

            if header and (not is_float(header[0]) or not is_float(header[1])):
                pass
            else:
                if header:
                    t_list.append(float(header[0])); y_list.append(float(header[1]))

            for row in reader:
                if len(row) < 2: continue
                t_list.append(float(row[0])); y_list.append(float(row[1]))

        t = np.asarray(t_list, dtype=float); y = np.asarray(y_list, dtype=float)
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
