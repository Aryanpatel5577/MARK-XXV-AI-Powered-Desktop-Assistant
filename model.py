from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar,
)


# ==========================================
# FILE PATHS AND CONSTANTS
# ==========================================

def get_base_directory() -> Path:
    """Returns the base directory of the running script or executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_directory()
CONFIG_DIR = BASE_DIR / "config"
API_FILE = CONFIG_DIR / "api_keys.json"

DEFAULT_WIDTH = 980
DEFAULT_HEIGHT = 700
MIN_WIDTH = 820
MIN_HEIGHT = 580
LEFT_PANEL_WIDTH = 148
RIGHT_PANEL_WIDTH = 340

CURRENT_OS = platform.system()  # "Windows", "Darwin" (macOS), or "Linux"


# Color Palette class
class Colors:
    BG = "#00060a"
    PANEL = "#010d14"
    PANEL2 = "#010f18"
    BORDER = "#0d3347"
    BORDER_B = "#1a5c7a"
    BORDER_A = "#0f4060"
    PRIMARY = "#00d4ff"
    PRIMARY_DIM = "#007a99"
    PRIMARY_GHOST = "#001f2e"
    ACCENT = "#ff6b00"
    ACCENT2 = "#ffcc00"
    GREEN = "#00ff88"
    GREEN_DARK = "#00aa55"
    RED = "#ff3355"
    MUTED = "#ff3366"
    TEXT = "#8ffcff"
    TEXT_DIM = "#3a8a9a"
    TEXT_MED = "#5ab8cc"
    WHITE = "#d8f8ff"
    DARK = "#000d14"
    BAR_BG = "#011520"


def make_color(hex_code: str, alpha: int = 255) -> QColor:
    """Helper function to create a QColor object from a hex string and alpha."""
    color = QColor(hex_code)
    color.setAlpha(alpha)
    return color


# ==========================================
# SYSTEM METRICS THREAD
# ==========================================

class SystemMetrics:
    """Monitors CPU, Memory, Network, GPU, and Temperature in a background thread."""

    def __init__(self):
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.network_usage = 0.0
        self.gpu_usage = -1.0
        self.temperature = -1.0

        self._lock = threading.Lock()
        self._last_network_stats = psutil.net_io_counters()
        self._last_network_time = time.time()
        self._is_running = True

        # Start monitoring background thread
        background_thread = threading.Thread(target=self._update_loop, daemon=True)
        background_thread.start()

    def _update_loop(self):
        while self._is_running:
            try:
                self._collect_metrics()
            except Exception:
                pass
            time.sleep(1.5)

    def _collect_metrics(self):
        # CPU & Memory
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        # Network speed calculation
        net_counters = psutil.net_io_counters()
        now = time.time()
        time_diff = now - self._last_network_time

        if time_diff > 0:
            bytes_sent = net_counters.bytes_sent - self._last_network_stats.bytes_sent
            bytes_recv = net_counters.bytes_recv - self._last_network_stats.bytes_recv
            net_mb = (bytes_sent + bytes_recv) / time_diff / (1024 * 1024)
        else:
            net_mb = 0.0

        self._last_network_stats = net_counters
        self._last_network_time = now

        # GPU and Temperature
        gpu = self._get_gpu_usage()
        temp = self._get_cpu_temperature()

        # Update thread-safe variables
        with self._lock:
            self.cpu_usage = cpu
            self.memory_usage = mem
            self.network_usage = net_mb
            self.gpu_usage = gpu
            self.temperature = temp

    def _get_gpu_usage(self) -> float:
        # Check NVIDIA GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                values = [float(val.strip()) for val in result.stdout.strip().split("\n") if val.strip()]
                if values:
                    return sum(values) / len(values)
        except Exception:
            pass

        # Check Linux AMD / Intel
        if CURRENT_OS == "Linux":
            try:
                result = subprocess.run(["rocm-smi", "--showuse", "--csv"], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        parts = line.split(",")
                        if len(parts) >= 2:
                            try:
                                return float(parts[1].strip().replace("%", ""))
                            except ValueError:
                                pass
            except Exception:
                pass

            try:
                result = subprocess.run(["intel_gpu_top", "-J", "-s", "500"], capture_output=True, text=True, timeout=1)
                if result.returncode == 0 and "Render/3D" in result.stdout:
                    import re
                    match = re.search(r'"busy":\s*([\d.]+)', result.stdout)
                    if match:
                        return float(match.group(1))
            except Exception:
                pass

        # Check macOS powermetrics
        if CURRENT_OS == "Darwin":
            try:
                result = subprocess.run(
                    ["sudo", "-n", "powermetrics", "-n", "1", "-i", "500", "--samplers", "gpu_power"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0 and "GPU" in result.stdout:
                    import re
                    match = re.search(r'GPU\s+Active:\s+([\d.]+)%', result.stdout)
                    if match:
                        return float(match.group(1))
            except Exception:
                pass

        return -1.0

    def _get_cpu_temperature(self) -> float:
        try:
            temperatures = psutil.sensors_temperatures()
            candidates = ["coretemp", "k10temp", "cpu_thermal", "acpitz", "cpu-thermal", "zenpower", "it8688"]
            for name in candidates:
                if name in temperatures and temperatures[name]:
                    return temperatures[name][0].current
            for entries in temperatures.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass

        if CURRENT_OS == "Darwin":
            try:
                result = subprocess.run(["osx-cpu-temp"], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    import re
                    match = re.search(r"([\d.]+)", result.stdout)
                    if match:
                        return float(match.group(1))
            except Exception:
                pass

        if CURRENT_OS == "Windows":
            try:
                cmd = "(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi).CurrentTemperature"
                result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    raw = float(result.stdout.strip().split("\n")[0])
                    return (raw / 10.0) - 273.15
            except Exception:
                pass

        return -1.0

    def snapshot(self) -> dict:
        """Returns a snapshot of current system metrics."""
        with self._lock:
            return {
                "cpu": self.cpu_usage,
                "mem": self.memory_usage,
                "net": self.network_usage,
                "gpu": self.gpu_usage,
                "tmp": self.temperature,
            }


system_metrics = SystemMetrics()


# ==========================================
# ANIMATED HUD CANVAS WIDGET
# ==========================================

class HudCanvas(QWidget):
    """Draws the central HUD animation, ARC reactor visualizer, and status text."""

    def __init__(self, face_image_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted = False
        self.speaking = False
        self.state = "INITIALISING"

        self.tick_counter = 0
        self.current_scale = 1.0
        self.target_scale = 1.0
        self.halo_radius = 55.0
        self.target_halo = 55.0
        self.last_update_time = time.time()
        self.scanner_angle_1 = 0.0
        self.scanner_angle_2 = 180.0
        self.ring_angles = [0.0, 120.0, 240.0]
        self.pulse_radii: list[float] = [0.0, 50.0, 100.0]
        self.blink_state = True
        self.blink_counter = 0
        self.particles: list[list[float]] = []
        self.face_pixmap: QPixmap | None = None

        self._load_face_image(face_image_path)

        # Animation Loop Timer (60 FPS approx)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animation_step)
        self.timer.start(16)

    def _load_face_image(self, image_path: str):
        """Loads and crops the target avatar image into a circle."""
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(image_path).convert("RGBA")
            min_dim = min(img.size)
            img = img.resize((min_dim, min_dim), Image.LANCZOS)

            mask = Image.new("L", (min_dim, min_dim), 0)
            ImageDraw.Draw(mask).ellipse((2, 2, min_dim - 2, min_dim - 2), fill=255)
            img.putalpha(mask)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            self.face_pixmap = pixmap
        except Exception:
            self.face_pixmap = None

    def _animation_step(self):
        self.tick_counter += 1
        now = time.time()

        interval = 0.12 if self.speaking else 0.5
        if now - self.last_update_time > interval:
            if self.speaking:
                self.target_scale = random.uniform(1.06, 1.14)
                self.target_halo = random.uniform(145, 190)
            elif self.muted:
                self.target_scale = random.uniform(0.998, 1.002)
                self.target_halo = random.uniform(15, 28)
            else:
                self.target_scale = random.uniform(1.001, 1.008)
                self.target_halo = random.uniform(48, 68)
            self.last_update_time = now

        speed = 0.38 if self.speaking else 0.15
        self.current_scale += (self.target_scale - self.current_scale) * speed
        self.halo_radius += (self.target_halo - self.halo_radius) * speed

        ring_speeds = [1.3, -0.9, 2.0] if self.speaking else [0.55, -0.35, 0.9]
        for idx, spd in enumerate(ring_speeds):
            self.ring_angles[idx] = (self.ring_angles[idx] + spd) % 360

        self.scanner_angle_1 = (self.scanner_angle_1 + (3.0 if self.speaking else 1.3)) % 360
        self.scanner_angle_2 = (self.scanner_angle_2 + (-2.0 if self.speaking else -0.75)) % 360

        frame_size = min(self.width(), self.height())
        pulse_limit = frame_size * 0.74
        pulse_speed = 4.2 if self.speaking else 2.0

        updated_pulses = []
        for pulse in self.pulse_radii:
            new_r = pulse + pulse_speed
            if new_r < pulse_limit:
                updated_pulses.append(new_r)
        self.pulse_radii = updated_pulses

        chance_new_pulse = 0.07 if self.speaking else 0.025
        if len(self.pulse_radii) < 3 and random.random() < chance_new_pulse:
            self.pulse_radii.append(0.0)

        # Particle creation when speaking
        if self.speaking and random.random() < 0.28:
            cx, cy = self.width() / 2, self.height() / 2
            angle = random.uniform(0, 2 * math.pi)
            start_r = frame_size * 0.28
            self.particles.append([
                cx + math.cos(angle) * start_r,
                cy + math.sin(angle) * start_r,
                math.cos(angle) * random.uniform(0.9, 2.4),
                math.sin(angle) * random.uniform(0.9, 2.4) - 0.4,
                1.0,  # alpha life
            ])

        # Particle updates
        new_particles = []
        for p in self.particles:
            px, py, vx, vy, alpha = p
            alpha -= 0.028
            if alpha > 0:
                new_particles.append([px + vx, py + vy, vx * 0.97, vy * 0.97, alpha])
        self.particles = new_particles

        # Text blinking
        self.blink_counter += 1
        if self.blink_counter >= 38:
            self.blink_state = not self.blink_state
            self.blink_counter = 0

        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), make_color(Colors.BG))

        width, height = self.width(), self.height()
        center_x, center_y = width / 2, height / 2
        frame_dim = min(width, height)

        # Background Grid Dots
        painter.setPen(QPen(make_color(Colors.PRIMARY_GHOST), 1))
        for x in range(0, width, 48):
            for y in range(0, height, 48):
                painter.drawPoint(x, y)

        face_radius = frame_dim * 0.31

        # Halo Glow Effect
        for i in range(10):
            r = face_radius * (1.8 - i * 0.08)
            fraction = 1.0 - i / 10
            alpha = max(0, min(255, int(self.halo_radius * 0.085 * fraction)))
            color = make_color(Colors.MUTED if self.muted else Colors.PRIMARY, alpha)
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center_x - r, center_y - r, r * 2, r * 2))

        # Pulse Rings
        for pulse in self.pulse_radii:
            alpha = max(0, int(230 * (1.0 - pulse / (frame_dim * 0.74))))
            color = make_color(Colors.MUTED if self.muted else Colors.PRIMARY, alpha)
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center_x - pulse, center_y - pulse, pulse * 2, pulse * 2))

        # Spinning Arc Rings
        arcs_config = [(0.48, 3, 115, 78), (0.40, 2, 78, 55), (0.32, 1, 56, 40)]
        for idx, (r_frac, width_r, arc_len, gap) in enumerate(arcs_config):
            ring_r = frame_dim * r_frac
            base_angle = self.ring_angles[idx]
            alpha = max(0, min(255, int(self.halo_radius * (1.0 - idx * 0.18))))
            color = make_color(Colors.MUTED if self.muted else Colors.PRIMARY, alpha)
            painter.setPen(QPen(color, width_r))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            angle = base_angle
            rect = QRectF(center_x - ring_r, center_y - ring_r, ring_r * 2, ring_r * 2)
            while angle < base_angle + 360:
                painter.drawArc(rect, int(angle * 16), int(arc_len * 16))
                angle += arc_len + gap

        # Scanners
        scan_r = frame_dim * 0.50
        scan_alpha = min(255, int(self.halo_radius * 1.5))
        extent = 75 if self.speaking else 44

        painter.setPen(QPen(make_color(Colors.MUTED if self.muted else Colors.PRIMARY, scan_alpha), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        scan_rect = QRectF(center_x - scan_r, center_y - scan_r, scan_r * 2, scan_r * 2)
        painter.drawArc(scan_rect, int(self.scanner_angle_1 * 16), int(extent * 16))

        painter.setPen(QPen(make_color(Colors.ACCENT, scan_alpha // 2), 1.5))
        painter.drawArc(scan_rect, int(self.scanner_angle_2 * 16), int(extent * 16))

        # Tick Marks
        tick_out = frame_dim * 0.497
        tick_in = frame_dim * 0.474
        painter.setPen(QPen(make_color(Colors.PRIMARY, 140), 1))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inner = tick_in if deg % 30 == 0 else tick_in + 6
            painter.drawLine(
                QPointF(center_x + tick_out * math.cos(rad), center_y - tick_out * math.sin(rad)),
                QPointF(center_x + inner * math.cos(rad), center_y - inner * math.sin(rad)),
            )

        # Crosshair Lines
        cross_r = frame_dim * 0.51
        gap_h = frame_dim * 0.16
        painter.setPen(QPen(make_color(Colors.PRIMARY, int(self.halo_radius * 0.5)), 1))
        painter.drawLine(QPointF(center_x - cross_r, center_y), QPointF(center_x - gap_h, center_y))
        painter.drawLine(QPointF(center_x + gap_h, center_y), QPointF(center_x + cross_r, center_y))
        painter.drawLine(QPointF(center_x, center_y - cross_r), QPointF(center_x, center_y - gap_h))
        painter.drawLine(QPointF(center_x, center_y + gap_h), QPointF(center_x, center_y + cross_r))

        # Corner Brackets
        bracket_len = 24
        bracket_col = make_color(Colors.PRIMARY, 210)
        h_left, h_right = center_x - frame_dim // 2, center_x + frame_dim // 2
        h_top, h_bottom = center_y - frame_dim // 2, center_y + frame_dim // 2
        painter.setPen(QPen(bracket_col, 2))

        corners = [
            (h_left, h_top, 1, 1),
            (h_right, h_top, -1, 1),
            (h_left, h_bottom, 1, -1),
            (h_right, h_bottom, -1, -1),
        ]
        for bx, by, dx, dy in corners:
            painter.drawLine(QPointF(bx, by), QPointF(bx + dx * bracket_len, by))
            painter.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bracket_len))

        # Face Avatar / Orb
        if self.face_pixmap:
            face_size = int(frame_dim * 0.62 * self.current_scale)
            scaled_face = self.face_pixmap.scaled(
                face_size, face_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(int(center_x - face_size / 2), int(center_y - face_size / 2), scaled_face)
        else:
            orb_r = int(frame_dim * 0.27 * self.current_scale)
            orb_color = (200, 0, 50) if self.muted else (0, 60, 110)
            for i in range(8, 0, -1):
                r2 = int(orb_r * i / 8)
                frac = i / 8
                a = max(0, min(255, int(self.halo_radius * 1.1 * frac)))
                painter.setBrush(QBrush(QColor(int(orb_color[0] * frac), int(orb_color[1] * frac), int(orb_color[2] * frac), a)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(center_x - r2, center_y - r2, r2 * 2, r2 * 2))

            painter.setPen(QPen(make_color(Colors.PRIMARY, min(255, int(self.halo_radius * 2))), 1))
            painter.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
            painter.drawText(QRectF(center_x - 80, center_y - 14, 160, 28), Qt.AlignmentFlag.AlignCenter, "J.A.R.V.I.S")

        # Active Particles
        for pt in self.particles:
            alpha = max(0, min(255, int(pt[4] * 255)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(make_color(Colors.PRIMARY, alpha)))
            painter.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # Status Indicator Text
        status_y = center_y + frame_dim * 0.40
        if self.muted:
            text, color = "⊘  MUTED", make_color(Colors.MUTED)
        elif self.speaking:
            text, color = "●  SPEAKING", make_color(Colors.ACCENT)
        elif self.state == "THINKING":
            symbol = "◈" if self.blink_state else "◇"
            text, color = f"{symbol}  THINKING", make_color(Colors.ACCENT2)
        elif self.state == "PROCESSING":
            symbol = "▷" if self.blink_state else "▶"
            text, color = f"{symbol}  PROCESSING", make_color(Colors.ACCENT2)
        elif self.state == "LISTENING":
            symbol = "●" if self.blink_state else "○"
            text, color = f"{symbol}  LISTENING", make_color(Colors.GREEN)
        else:
            symbol = "●" if self.blink_state else "○"
            text, color = f"{symbol}  {self.state}", make_color(Colors.PRIMARY)

        painter.setPen(QPen(color, 1))
        painter.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        painter.drawText(QRectF(0, status_y, width, 26), Qt.AlignmentFlag.AlignCenter, text)

        # Audio Waveform Visualizer
        wave_y = status_y + 30
        num_bars, bar_width = 36, 8
        start_x = (width - num_bars * bar_width) / 2

        for i in range(num_bars):
            if self.muted:
                bar_h, bar_color = 2, make_color(Colors.MUTED)
            elif self.speaking:
                bar_h = random.randint(3, 20)
                bar_color = make_color(Colors.PRIMARY) if bar_h > 12 else make_color(Colors.PRIMARY_DIM)
            else:
                bar_h = int(3 + 2 * math.sin(self.tick_counter * 0.09 + i * 0.6))
                bar_color = make_color(Colors.BORDER_B)

            painter.fillRect(QRectF(start_x + i * bar_width, wave_y + 20 - bar_h, bar_width - 1, bar_h), bar_color)


# ==========================================
# METRIC BAR WIDGET
# ==========================================

class MetricBar(QWidget):
    """Displays a custom progress bar for CPU, Memory, GPU metrics."""

    def __init__(self, label: str, color: str = Colors.PRIMARY, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.bar_color_hex = color
        self.value_percent = 0.0
        self.display_text = "--"

        self.setFixedHeight(38)
        self.setMinimumWidth(80)

    def set_value(self, percent: float, text: str):
        self.value_percent = max(0.0, min(100.0, percent))
        self.display_text = text
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()

        # Background Frame
        painter.setBrush(QBrush(make_color(Colors.PANEL2)))
        painter.setPen(QPen(make_color(Colors.BORDER_A), 1))
        painter.drawRoundedRect(QRectF(1, 1, width - 2, height - 2), 4, 4)

        bar_h = 4
        bar_y = height - bar_h - 5
        bar_w = width - 12
        bar_x = 6
        fill_w = int(bar_w * self.value_percent / 100)

        # Bar background track
        painter.setBrush(QBrush(make_color(Colors.BAR_BG)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        # Color fill based on value intensity
        if self.value_percent > 85:
            active_color = make_color(Colors.RED)
        elif self.value_percent > 65:
            active_color = make_color(Colors.ACCENT)
        else:
            active_color = make_color(self.bar_color_hex)

        if fill_w > 0:
            painter.setBrush(QBrush(active_color))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        # Label Text
        painter.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        painter.setPen(QPen(make_color(Colors.TEXT_DIM), 1))
        painter.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.label_text)

        # Percentage Text
        painter.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        text_color = active_color if self.display_text != "--" else make_color(Colors.TEXT_DIM)
        painter.setPen(QPen(text_color, 1))
        painter.drawText(QRectF(0, 4, width - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.display_text)


# ==========================================
# ANIMATED TYPEWRITER LOG WIDGET
# ==========================================

class LogWidget(QTextEdit):
    """Text console widget with animated typewriter output effect."""
    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {Colors.PANEL};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {Colors.PRIMARY_GHOST};
            }}
            QScrollBar:vertical {{
                background: {Colors.BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)

        self.message_queue: list[str] = []
        self.is_typing = False
        self.current_text = ""
        self.character_index = 0
        self.sender_tag = "sys"

        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self._type_next_char)
        self.log_signal.connect(self._enqueue_log)

    def append_log(self, text: str):
        self.log_signal.emit(text)

    def _enqueue_log(self, text: str):
        self.message_queue.append(text)
        if not self.is_typing:
            self._start_next_message()

    def _start_next_message(self):
        if not self.message_queue:
            self.is_typing = False
            return

        self.is_typing = True
        self.current_text = self.message_queue.pop(0)
        self.character_index = 0

        text_lower = self.current_text.lower()
        if text_lower.startswith("you:"):
            self.sender_tag = "you"
        elif text_lower.startswith("jarvis:"):
            self.sender_tag = "ai"
        elif text_lower.startswith("file:"):
            self.sender_tag = "file"
        elif "err" in text_lower:
            self.sender_tag = "err"
        else:
            self.sender_tag = "sys"

        self.typing_timer.start(6)

    def _type_next_char(self):
        if self.character_index < len(self.current_text):
            char = self.current_text[self.character_index]
            cursor = self.textCursor()
            char_format = cursor.charFormat()

            tag_colors = {
                "you": make_color(Colors.WHITE),
                "ai": make_color(Colors.PRIMARY),
                "err": make_color(Colors.RED),
                "file": make_color(Colors.GREEN),
                "sys": make_color(Colors.ACCENT2),
            }
            color = tag_colors.get(self.sender_tag, make_color(Colors.TEXT))
            char_format.setForeground(QBrush(color))

            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(char, char_format)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

            self.character_index += 1
        else:
            self.typing_timer.stop()
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText("\n")
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._start_next_message)


# ==========================================
# FILE DROP ZONE WIDGETS
# ==========================================

FILE_ICONS = {
    "image": ("🖼", "#00d4ff"),
    "video": ("🎬", "#ff6b00"),
    "audio": ("🎵", "#cc44ff"),
    "pdf": ("📄", "#ff4444"),
    "word": ("📝", "#4488ff"),
    "excel": ("📊", "#44bb44"),
    "code": ("💻", "#ffcc00"),
    "archive": ("📦", "#ff8844"),
    "pptx": ("📊", "#ff6622"),
    "text": ("📃", "#aaaaaa"),
    "data": ("🔧", "#88ddff"),
    "unknown": ("📎", "#888888"),
}

EXTENSION_CATEGORIES = {
    **dict.fromkeys(["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg", "ico"], "image"),
    **dict.fromkeys(["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v"], "video"),
    **dict.fromkeys(["mp3", "wav", "ogg", "m4a", "aac", "flac", "wma", "opus"], "audio"),
    **dict.fromkeys(["pdf"], "pdf"),
    **dict.fromkeys(["doc", "docx"], "word"),
    **dict.fromkeys(["xls", "xlsx", "ods"], "excel"),
    **dict.fromkeys(["ppt", "pptx"], "pptx"),
    **dict.fromkeys(["py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c", "cpp", "cs", "go", "rs", "rb", "php", "swift", "kt", "sh", "sql", "lua"], "code"),
    **dict.fromkeys(["zip", "rar", "tar", "gz", "7z", "bz2", "xz"], "archive"),
    **dict.fromkeys(["txt", "md", "rst", "log"], "text"),
    **dict.fromkeys(["csv", "tsv", "json", "xml"], "data"),
}


def get_file_category(file_path: Path) -> str:
    ext = file_path.suffix.lower().lstrip(".")
    return EXTENSION_CATEGORIES.get(ext, "unknown")


def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 ** 2:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 ** 3:
        return f"{size_in_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 ** 3):.1f} GB"


class FileDropZone(QWidget):
    """Container widget supporting Drag-and-Drop or Click-to-Browse file upload."""
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)

        self._file_path: str | None = None
        self.is_hovering = False
        self.is_drag_over = False
        self.dash_offset = 0.0

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_border)
        self.anim_timer.start(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.canvas = DropZoneCanvas(self)
        layout.addWidget(self.canvas)

    def _animate_border(self):
        self.dash_offset = (self.dash_offset + 0.8) % 20
        self.canvas.update()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.is_drag_over = True
            self.canvas.update()

    def dragLeaveEvent(self, event):
        self.is_drag_over = False
        self.canvas.update()

    def dropEvent(self, event: QDropEvent):
        self.is_drag_over = False
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self.set_file(path)
        self.canvas.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse_file()

    def enterEvent(self, event):
        self.is_hovering = True
        self.canvas.update()

    def leaveEvent(self, event):
        self.is_hovering = False
        self.canvas.update()

    def current_file(self) -> str | None:
        return self._file_path

    def clear_file(self):
        self._file_path = None
        self.canvas.update()

    def _browse_file(self):
        file_filter = (
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)"
        )
        selected_path, _ = QFileDialog.getOpenFileName(
            self, "Select a file for JARVIS", str(Path.home()), file_filter
        )
        if selected_path:
            self.set_file(selected_path)

    def set_file(self, path: str):
        self._file_path = path
        self.canvas.update()
        self.file_selected.emit(path)


class DropZoneCanvas(QWidget):
    """Custom paint canvas for rendering the File Drop Zone UI."""

    def __init__(self, drop_zone: FileDropZone):
        super().__init__(drop_zone)
        self.drop_zone = drop_zone

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        zone = self.drop_zone
        width, height = self.width(), self.height()
        padding = 6
        rect = QRectF(padding, padding, width - padding * 2, height - padding * 2)

        if zone.is_drag_over:
            bg_color = make_color("#001a24")
        elif zone.is_hovering:
            bg_color = make_color("#001218")
        else:
            bg_color = make_color(Colors.PANEL)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 6, 6)

        # Border color selection
        if zone.current_file():
            border_color = make_color(Colors.GREEN, 200)
        elif zone.is_drag_over:
            border_color = make_color(Colors.PRIMARY, 230)
        elif zone.is_hovering:
            border_color = make_color(Colors.BORDER_B, 200)
        else:
            border_color = make_color(Colors.BORDER, 160)

        pen = QPen(border_color, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(zone.dash_offset)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)

        # Draw content states
        if zone.current_file():
            self._draw_file_info(painter, width, height)
        elif zone.is_drag_over:
            self._draw_drag_over_state(painter, width, height)
        else:
            self._draw_idle_state(painter, width, height, zone.is_hovering)

    def _draw_idle_state(self, painter: QPainter, width: float, height: float, is_hovering: bool):
        center_x, center_y = width / 2, height / 2
        color = make_color(Colors.PRIMARY if is_hovering else Colors.PRIMARY_DIM)

        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(center_x, center_y - 14), QPointF(center_x, center_y + 4))
        painter.drawLine(QPointF(center_x - 8, center_y - 6), QPointF(center_x, center_y - 14))
        painter.drawLine(QPointF(center_x + 8, center_y - 6), QPointF(center_x, center_y - 14))
        painter.drawLine(QPointF(center_x - 14, center_y + 4), QPointF(center_x + 14, center_y + 4))

        painter.setFont(QFont("Courier New", 8))
        painter.setPen(QPen(make_color(Colors.TEXT if is_hovering else Colors.PRIMARY_DIM), 1))
        painter.drawText(QRectF(0, center_y + 8, width, 16), Qt.AlignmentFlag.AlignCenter, "Drop file here  or  Click to Browse")

        painter.setFont(QFont("Courier New", 7))
        painter.setPen(QPen(make_color("#1a4a5a"), 1))
        painter.drawText(QRectF(0, center_y + 24, width, 14), Qt.AlignmentFlag.AlignCenter, "Images · Video · Audio · PDF · Docs · Code · Data")

    def _draw_drag_over_state(self, painter: QPainter, width: float, height: float):
        center_x, center_y = width / 2, height / 2
        painter.setFont(QFont("Courier New", 20))
        painter.setPen(QPen(make_color(Colors.PRIMARY), 1))
        painter.drawText(QRectF(0, center_y - 24, width, 32), Qt.AlignmentFlag.AlignCenter, "⬇")

        painter.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        painter.setPen(QPen(make_color(Colors.PRIMARY), 1))
        painter.drawText(QRectF(0, center_y + 12, width, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _draw_file_info(self, painter: QPainter, width: float, height: float):
        file_path = Path(self.drop_zone.current_file())
        category = get_file_category(file_path)
        icon_str, icon_color = FILE_ICONS.get(category, FILE_ICONS["unknown"])

        size_text = format_file_size(file_path.stat().st_size)
        ext_text = file_path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        font_family = "Segoe UI Emoji" if CURRENT_OS == "Windows" else "Arial"
        painter.setFont(QFont(font_family, 22))
        painter.setPen(QPen(make_color(icon_color), 1))
        painter.drawText(QRectF(block_x, 0, block_w, height), Qt.AlignmentFlag.AlignCenter, icon_str)

        text_x = block_x + block_w + 6
        text_w = width - text_x - 38

        painter.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        painter.setPen(QPen(make_color(Colors.WHITE), 1))
        display_name = file_path.name if len(file_path.name) <= 34 else file_path.name[:31] + "..."
        painter.drawText(QRectF(text_x, height * 0.18, text_w, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display_name)

        painter.setFont(QFont("Courier New", 7))
        painter.setPen(QPen(make_color(Colors.TEXT_DIM), 1))
        painter.drawText(QRectF(text_x, height * 0.18 + 18, text_w, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{ext_text}  ·  {size_text}")

        painter.setFont(QFont("Courier New", 6))
        painter.setPen(QPen(make_color("#1e5c6a"), 1))
        parent_dir = str(file_path.parent)
        if len(parent_dir) > 42:
            parent_dir = "…" + parent_dir[-41:]
        painter.drawText(QRectF(text_x, height * 0.18 + 34, text_w, 12), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, parent_dir)

        # Draw close icon '✕'
        painter.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        painter.setPen(QPen(make_color(Colors.RED, 180), 1))
        painter.drawText(QRectF(width - 34, 0, 28, height), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, event):
        zone = self.drop_zone
        if zone.current_file() and event.pos().x() > self.width() - 34:
            zone.clear_file()
        else:
            zone.mousePressEvent(event)


# ==========================================
# SETUP OVERLAY WIDGET
# ==========================================

class SetupOverlay(QWidget):
    """First-time system setup screen asking for API keys and OS."""
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {Colors.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected_os = {"darwin": "mac", "windows": "windows"}.get(CURRENT_OS.lower(), "linux")
        self.selected_os = detected_os

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def create_label(text, font_size=9, bold=False, color=Colors.PRIMARY, align=Qt.AlignmentFlag.AlignCenter):
            lbl = QLabel(text)
            lbl.setAlignment(align)
            lbl.setFont(QFont("Courier New", font_size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
            lbl.setStyleSheet(f"color: {color}; background: transparent;")
            return lbl

        layout.addWidget(create_label("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(create_label("Configure J.A.R.V.I.S. before first boot.", 9, color=Colors.PRIMARY_DIM))
        layout.addSpacing(6)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(separator)
        layout.addSpacing(4)

        # Gemini API Key Input
        layout.addWidget(create_label("GEMINI API KEY", 8, color=Colors.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        self.gemini_input = QLineEdit()
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("AIza…")
        self.gemini_input.setFont(QFont("Courier New", 10))
        self.gemini_input.setFixedHeight(32)
        self.gemini_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {Colors.PRIMARY}; }}
        """)
        layout.addWidget(self.gemini_input)
        layout.addSpacing(8)

        # OpenRouter API Key Input
        layout.addWidget(create_label("OPENROUTER API KEY", 8, color=Colors.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        self.openrouter_input = QLineEdit()
        self.openrouter_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_input.setPlaceholderText("sk-or-…")
        self.openrouter_input.setFont(QFont("Courier New", 10))
        self.openrouter_input.setFixedHeight(32)
        self.openrouter_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {Colors.ACCENT2}; }}
        """)
        layout.addWidget(self.openrouter_input)

        layout.addSpacing(12)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(separator2)
        layout.addSpacing(4)

        # OS Selection
        layout.addWidget(create_label("OPERATING SYSTEM", 8, color=Colors.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        detected_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected_os]
        layout.addWidget(create_label(f"Auto-detected: {detected_name}", 8, color=Colors.ACCENT2, align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout()
        os_row.setSpacing(6)
        self.os_buttons: dict[str, QPushButton] = {}

        for os_key, os_label in [("windows", "⊞  Windows"), ("mac", "  macOS"), ("linux", "🐧  Linux")]:
            btn = QPushButton(os_label)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, key=os_key: self._select_os(key))
            os_row.addWidget(btn)
            self.os_buttons[os_key] = btn

        layout.addLayout(os_row)
        self._select_os(detected_os)
        layout.addSpacing(12)

        # Initialize Button
        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {Colors.PRIMARY_GHOST}; border: 1px solid {Colors.PRIMARY};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _select_os(self, os_key: str):
        self.selected_os = os_key
        palette = {
            "windows": (Colors.PRIMARY, "#001a22"),
            "mac": (Colors.ACCENT2, "#1a1400"),
            "linux": (Colors.GREEN, "#001a0d")
        }

        for k, btn in self.os_buttons.items():
            if k == os_key:
                fg, bg = palette[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {Colors.TEXT_DIM};
                        border: 1px solid {Colors.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {Colors.TEXT}; border: 1px solid {Colors.BORDER_B}; }}
                """)

    def _submit(self):
        gemini_key = self.gemini_input.text().strip()
        openrouter_key = self.openrouter_input.text().strip()

        if not gemini_key:
            self.gemini_input.setStyleSheet(self.gemini_input.styleSheet() + f" QLineEdit {{ border: 1px solid {Colors.RED}; }}")
            return
        if not openrouter_key:
            self.openrouter_input.setStyleSheet(self.openrouter_input.styleSheet() + f" QLineEdit {{ border: 1px solid {Colors.RED}; }}")
            return

        self.done.emit(gemini_key, openrouter_key, self.selected_os)


# ==========================================
# MAIN APPLICATION WINDOW
# ==========================================

class MainWindow(QMainWindow):
    """Main Application Window displaying all modules, side panels, and footer."""
    log_signal = pyqtSignal(str)
    state_signal = pyqtSignal(str)

    def __init__(self, face_image_path: str):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S — MARK XXXIX")
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        # Center Window on primary screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - DEFAULT_WIDTH) // 2,
            (screen.height() - DEFAULT_HEIGHT) // 2,
        )

        self.on_text_command = None
        self._muted = False
        self._current_file: str | None = None

        # Main Layout Structure
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background: {Colors.BG};")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_header())

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.left_panel = self._build_left_panel()
        body_layout.addWidget(self.left_panel, stretch=0)

        self.hud = HudCanvas(face_image_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body_layout.addWidget(self.hud, stretch=5)

        self.right_panel = self._build_right_panel()
        body_layout.addWidget(self.right_panel, stretch=0)

        root_layout.addLayout(body_layout, stretch=1)
        root_layout.addWidget(self._build_footer())

        # Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        self.metric_timer = QTimer(self)
        self.metric_timer.timeout.connect(self._update_metrics)
        self.metric_timer.start(2000)
        self._update_metrics()

        # Connect Signals
        self.log_signal.connect(self._log_widget.append_log)
        self.state_signal.connect(self._apply_state)

        # Setup Overlay handling
        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config_file()
        if not self._ready:
            self._show_setup_overlay()

        # Shortcuts
        mute_shortcut = QShortcut(QKeySequence("F4"), self)
        mute_shortcut.activated.connect(self._toggle_mute)
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width() - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snapshot = system_metrics.snapshot()

        # CPU
        cpu = snapshot["cpu"]
        self.cpu_bar.set_value(cpu, f"{cpu:.0f}%")

        # Memory
        mem = snapshot["mem"]
        self.memory_bar.set_value(mem, f"{mem:.0f}%")

        # Network
        net = snapshot["net"]
        net_str = f"{net * 1024:.0f}KB/s" if net < 1.0 else f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)
        self.network_bar.set_value(net_pct, net_str)

        # GPU
        gpu = snapshot["gpu"]
        if gpu >= 0:
            self.gpu_bar.set_value(gpu, f"{gpu:.0f}%")
        else:
            self.gpu_bar.set_value(0, "N/A")

        # Temperature
        tmp = snapshot["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, (tmp / 100) * 100)
            self.temp_bar.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            self.temp_bar.set_value(0, "N/A")

        # Uptime
        try:
            boot_time = psutil.boot_time()
            elapsed_seconds = time.time() - boot_time
            hours = int(elapsed_seconds // 3600)
            minutes = int((elapsed_seconds % 3600) // 60)
            self.uptime_label.setText(f"UP  {hours:02d}:{minutes:02d}")
        except Exception:
            self.uptime_label.setText("UP  --:--")

        # Process Count
        try:
            process_count = len(psutil.pids())
            self.process_label.setText(f"PROC  {process_count}")
        except Exception:
            self.process_label.setText("PROC  --")

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(54)
        header.setStyleSheet(f"background: {Colors.DARK}; border-bottom: 1px solid {Colors.BORDER_B};")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        badge_label = QLabel("MARK XXXIX")
        badge_label.setFont(QFont("Courier New", 8))
        badge_label.setStyleSheet(f"color: {Colors.PRIMARY_DIM}; background: transparent;")
        layout.addWidget(badge_label)
        layout.addStretch()

        center_title_col = QVBoxLayout()
        center_title_col.setSpacing(1)

        title = QLabel("J.A.R.V.I.S")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Courier New", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.PRIMARY}; background: transparent;")
        center_title_col.addWidget(title)

        subtitle = QLabel("Just A Rather Very Intelligent System")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Courier New", 7))
        subtitle.setStyleSheet(f"color: {Colors.PRIMARY_DIM}; background: transparent;")
        center_title_col.addWidget(subtitle)

        layout.addLayout(center_title_col)
        layout.addStretch()

        right_time_col = QVBoxLayout()
        right_time_col.setSpacing(2)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        self.clock_label.setStyleSheet(f"color: {Colors.PRIMARY}; background: transparent;")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_time_col.addWidget(self.clock_label)

        self.date_label = QLabel("")
        self.date_label.setFont(QFont("Courier New", 7))
        self.date_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; background: transparent;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_time_col.addWidget(self.date_label)

        layout.addLayout(right_time_col)
        return header

    def _update_clock(self):
        self.clock_label.setText(time.strftime("%H:%M:%S"))
        self.date_label.setText(time.strftime("%a %d %b %Y"))

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(LEFT_PANEL_WIDTH)
        panel.setStyleSheet(f"background: {Colors.DARK}; border-right: 1px solid {Colors.BORDER};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(6)

        header = QLabel("◈ SYS MONITOR")
        header.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        header.setStyleSheet(
            f"color: {Colors.PRIMARY}; background: transparent; "
            f"border-bottom: 1px solid {Colors.BORDER}; padding-bottom: 4px;"
        )
        layout.addWidget(header)
        layout.addSpacing(2)

        self.cpu_bar = MetricBar("CPU", Colors.PRIMARY)
        self.memory_bar = MetricBar("MEM", Colors.ACCENT2)
        self.network_bar = MetricBar("NET", Colors.GREEN)
        self.gpu_bar = MetricBar("GPU", Colors.ACCENT)
        self.temp_bar = MetricBar("TMP", "#ff6688")

        for bar in [self.cpu_bar, self.memory_bar, self.network_bar, self.gpu_bar, self.temp_bar]:
            layout.addWidget(bar)

        layout.addSpacing(4)

        info_panel = QWidget()
        info_panel.setStyleSheet(f"background: {Colors.PANEL2}; border: 1px solid {Colors.BORDER}; border-radius: 4px;")

        ip_layout = QVBoxLayout(info_panel)
        ip_layout.setContentsMargins(6, 5, 6, 5)
        ip_layout.setSpacing(3)

        self.uptime_label = QLabel("UP  --:--")
        self.uptime_label.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.uptime_label.setStyleSheet(f"color: {Colors.GREEN}; background: transparent; border: none;")
        ip_layout.addWidget(self.uptime_label)

        self.process_label = QLabel("PROC  --")
        self.process_label.setFont(QFont("Courier New", 8))
        self.process_label.setStyleSheet(f"color: {Colors.TEXT_MED}; background: transparent; border: none;")
        ip_layout.addWidget(self.process_label)

        os_display_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(CURRENT_OS, CURRENT_OS.upper())
        os_label = QLabel(f"OS  {os_display_name}")
        os_label.setFont(QFont("Courier New", 8))
        os_label.setStyleSheet(f"color: {Colors.ACCENT2}; background: transparent; border: none;")
        ip_layout.addWidget(os_label)

        layout.addWidget(info_panel)
        layout.addStretch()

        status_badges = [
            ("AI CORE\nACTIVE", Colors.GREEN),
            ("SEC\nCLEARED", Colors.PRIMARY),
            ("PROTOCOL\nXXXVIII", Colors.TEXT_DIM),
        ]
        for text, color in status_badges:
            lbl = QLabel(text)
            lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {color}; background: {Colors.PANEL2}; "
                f"border: 1px solid {Colors.BORDER_A}; border-radius: 3px; padding: 4px;"
            )
            layout.addWidget(lbl)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(RIGHT_PANEL_WIDTH)
        panel.setStyleSheet(f"background: {Colors.DARK}; border-left: 1px solid {Colors.BORDER};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        def create_section_header(text: str):
            lbl = QLabel(f"▸ {text}")
            lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {Colors.TEXT_MED}; background: transparent;")
            return lbl

        layout.addWidget(create_section_header("ACTIVITY LOG"))
        self._log_widget = LogWidget()
        layout.addWidget(self._log_widget, stretch=1)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"color: {Colors.BORDER}; margin: 2px 0;")
        layout.addWidget(sep1)

        layout.addWidget(create_section_header("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Courier New", 7))
        self._file_hint.setStyleSheet(f"color: {Colors.TEXT_MED}; background: transparent;")
        self._file_hint.setWordWrap(True)
        layout.addWidget(self._file_hint)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {Colors.BORDER}; margin: 2px 0;")
        layout.addWidget(sep2)

        layout.addWidget(create_section_header("COMMAND INPUT"))
        layout.addLayout(self._build_input_row())

        self.mute_button = QPushButton("🎙  MICROPHONE ACTIVE")
        self.mute_button.setFixedHeight(30)
        self.mute_button.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.mute_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_button.clicked.connect(self._toggle_mute)
        self._update_mute_button_style()
        layout.addWidget(self.mute_button)

        fullscreen_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fullscreen_btn.setFixedHeight(26)
        fullscreen_btn.setFont(QFont("Courier New", 7))
        fullscreen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fullscreen_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {Colors.TEXT_MED};
                border: 1px solid {Colors.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {Colors.PRIMARY}; border: 1px solid {Colors.BORDER_B};
            }}
        """)
        fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        layout.addWidget(fullscreen_btn)

        return panel

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(5)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Type a command or question…")
        self.command_input.setFont(QFont("Courier New", 9))
        self.command_input.setFixedHeight(30)
        self.command_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d14; color: {Colors.WHITE};
                border: 1px solid {Colors.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {Colors.PRIMARY}; }}
        """)
        self.command_input.returnPressed.connect(self._send_command)
        row.addWidget(self.command_input)

        send_btn = QPushButton("▸")
        send_btn.setFixedSize(30, 30)
        send_btn.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.PANEL}; color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {Colors.PRIMARY_GHOST}; border: 1px solid {Colors.PRIMARY}; }}
        """)
        send_btn.clicked.connect(self._send_command)
        row.addWidget(send_btn)

        return row

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(22)
        footer.setStyleSheet(f"background: {Colors.DARK}; border-top: 1px solid {Colors.BORDER};")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(14, 0, 14, 0)

        def create_footer_label(text, color=Colors.TEXT_MED):
            lbl = QLabel(text)
            lbl.setFont(QFont("Courier New", 7))
            lbl.setStyleSheet(f"color: {color}; background: transparent;")
            return lbl

        layout.addWidget(create_footer_label("[F4] Mute  ·  [F11] Fullscreen"))
        layout.addStretch()
        layout.addWidget(create_footer_label("FatihMakes Industries  ·  MARK XXXIX  ·  CLASSIFIED"))
        layout.addStretch()
        layout.addWidget(create_footer_label("© STARK INDUSTRIES", Colors.PRIMARY_DIM))
        return footer

    def _on_file_selected(self, path: str):
        self._current_file = path
        file_path = Path(path)
        category = get_file_category(file_path)
        icon_str, _ = FILE_ICONS.get(category, FILE_ICONS["unknown"])
        size_str = format_file_size(file_path.stat().st_size)

        self._file_hint.setText(f"{icon_str}  {file_path.name}  ·  {size_str}  ·  Tell JARVIS what to do with it")
        self._log_widget.append_log(f"FILE: {file_path.name} ({size_str}) loaded")

        if self.on_text_command:
            message = (
                f"[FILE_UPLOADED] path={path} | name={file_path.name} | "
                f"type={file_path.suffix.lstrip('.')} | size={size_str} | "
                f"Briefly tell the user you can see the file '{file_path.name}' "
                f"({size_str}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(message,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._update_mute_button_style()

        if self._muted:
            self._apply_state("MUTED")
            self._log_widget.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log_widget.append_log("SYS: Microphone active.")

    def _update_mute_button_style(self):
        if self._muted:
            self.mute_button.setText("🔇  MICROPHONE MUTED")
            self.mute_button.setStyleSheet(f"""
                QPushButton {{
                    background: #140006; color: {Colors.MUTED};
                    border: 1px solid {Colors.MUTED}; border-radius: 3px;
                }}
            """)
        else:
            self.mute_button.setText("🎙  MICROPHONE ACTIVE")
            self.mute_button.setStyleSheet(f"""
                QPushButton {{
                    background: #00140a; color: {Colors.GREEN};
                    border: 1px solid {Colors.GREEN}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #001f10; }}
            """)

    def _send_command(self):
        text = self.command_input.text().strip()
        if not text:
            return
        self.command_input.clear()
        self._log_widget.append_log(f"You: {text}")

        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state = state
        self.hud.speaking = (state == "SPEAKING")

    def _check_config_file(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            return (
                bool(data.get("gemini_api_key")) and
                bool(data.get("openrouter_api_key")) and
                bool(data.get("os_system"))
            )
        except Exception:
            return False

    def _show_setup_overlay(self):
        overlay = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 430
        overlay.setGeometry(
            (cw.width() - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        overlay.done.connect(self._on_setup_completed)
        overlay.show()
        self._overlay = overlay

    def _on_setup_completed(self, gemini_key: str, openrouter_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        config_data = {
            "gemini_api_key": gemini_key,
            "openrouter_api_key": openrouter_key,
            "os_system": os_name,
        }
        API_FILE.write_text(json.dumps(config_data, indent=4), encoding="utf-8")

        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None

        self._apply_state("LISTENING")
        self._log_widget.append_log(f"SYS: Initialised. OS={os_name.upper()}. JARVIS online.")


# Shim class for external framework compatibility
class RootShim:
    def __init__(self, app: QApplication):
        self._app = app

    def mainloop(self):
        self._app.exec()

    def protocol(self, *args):
        pass


# ==========================================
# PUBLIC JARVIS UI INTERFACE
# ==========================================

class JarvisUI:
    """Public Wrapper Class used to control the JARVIS Interface."""

    def __init__(self, face_image_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_image_path)
        self._win.show()
        self.root = RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, value: bool):
        if value != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, callback):
        self._win.on_text_command = callback

    def set_state(self, state: str):
        self._win.state_signal.emit(state)

    def write_log(self, text: str):
        self._win.log_signal.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")