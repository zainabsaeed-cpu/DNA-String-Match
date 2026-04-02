"""GeneFlow — DNA Sequencing Analysis (PyQt6 Desktop App - Modern Redesign)"""

import csv
import html
import json
import math
import sys
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QSplitter, QComboBox, QCheckBox, QScrollArea, QProgressBar,
    QFileDialog, QTabWidget, QFrame, QStyle, QSizePolicy, QGridLayout, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPointF, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPdfWriter, QPainterPath
import matplotlib
matplotlib.use('Qt5Agg')

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from Bio import SeqIO
    HAS_BIO = True
except ImportError:
    HAS_BIO = False

from dfa import get_transition_table
from matcher import find_matches, trace_dfa

try:
    from ai_insights import AIQueryHandler
    HAS_AI = True
except (ImportError, Exception):
    HAS_AI = False

# ─────────────────────────────────────────────────────────────────────────────
# THEME COLORS - Modern Professional Design
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "bg": "#070c16",
    "bg-elevated": "#0d1525",
    "bg-secondary": "#111c31",
    "card": "#161b22",
    "panel": "#16243b",
    "panel-soft": "#1b2942",
    "surface": "#18213a",
    "surface2": "#1e2a42",
    "text-primary": "#f1f6ff",
    "text-secondary": "#8ea4c7",
    "text-tertiary": "#667b9d",
    "accent": "#38d7c8",
    "teal": "#38d7c8",
    "teal2": "#5eead4",
    "accent-blue": "#4ea0ff",
    "accent-soft": "#18304b",
    "gold": "#e7be69",
    "gold2": "#f0c96a",
    "violet": "#a78bfa",
    "green": "#4ade80",
    "border": "#233552",
    "border-card": "#2d3748",
    "border-light": "#17263f",
    "success": "#35d07f",
    "warning": "#f2c465",
    "error": "#ff6f86",
}

FONTS = {
    "sans": "Outfit",
    "serif": "Cormorant Garamond",
    "mono": "JetBrains Mono",
}


class LiveGenomeReaderWidget(QWidget):
    """Live genome sequence reader showing current scanning position."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._genome = ""
        self._current_index = -1
        self.setMinimumHeight(100)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_data(self, genome: str, current_index: int):
        self._genome = genome
        self._current_index = current_index
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(14, 12, -14, -12)

        painter.fillRect(self.rect(), QColor(COLORS["bg-secondary"]))

        if not self._genome:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(COLORS["accent"]))
            painter.drawEllipse(int(rect.center().x() - 7), int(rect.center().y() - 28), 14, 14)
            painter.setPen(QColor(COLORS["text-tertiary"]))
            painter.setFont(QFont(FONTS["mono"], 12, QFont.Weight.Bold))
            painter.drawText(rect.adjusted(0, 0, 0, -10), Qt.AlignmentFlag.AlignCenter, "Load genome to see live scan")
            return

        # Show context around current position
        context_size = 20
        start = max(0, self._current_index - context_size)
        end = min(len(self._genome), self._current_index + context_size + 1)
        visible_genome = self._genome[start:end]
        
        # Draw genome sequence
        painter.setPen(QColor(COLORS["text-primary"]))
        painter.setFont(QFont(FONTS["mono"], 14, QFont.Weight.Bold))
        
        # Highlight current position
        current_local_pos = self._current_index - start
        for i, base in enumerate(visible_genome):
            x = rect.left() + 20 + i * 18
            color = QColor(COLORS["warning"]) if i == current_local_pos else QColor(COLORS["accent"])
            painter.setPen(color)
            painter.drawText(int(x), int(rect.top() + 30), 16, 20, Qt.AlignmentFlag.AlignCenter, base)
        
        # Draw position indicator
        if 0 <= current_local_pos < len(visible_genome):
            painter.setPen(QPen(QColor(COLORS["warning"]), 2))
            x = rect.left() + 20 + current_local_pos * 18
            painter.drawRect(int(x) - 2, int(rect.top() + 28), 20, 24)
        
        # Show position info
        info_text = f"Position: {self._current_index + 1} / {len(self._genome)}"
        painter.setPen(QColor(COLORS["text-secondary"]))
        painter.setFont(QFont(FONTS["mono"], 11))
        painter.drawText(rect.left() + 20, int(rect.top() + 70), info_text)


class GenomeTimelineWidget(QWidget):
    """Live genome scanner strip with highlighted current state and matches."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._genome = ""
        self._matches = []
        self._pattern_len = 0
        self._current_index = -1
        self._match_positions = set()
        self.setMinimumHeight(126)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_data(self, genome: str, matches: list[int], pattern_len: int):
        self._genome = genome
        self._matches = matches
        self._pattern_len = pattern_len
        self._match_positions = {m - 1 + i for m in matches for i in range(pattern_len)}
        self._current_index = -1
        self.update()

    def set_current_index(self, index: int):
        self._current_index = index
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLORS["bg-secondary"]))

        if not self._genome:
            painter.setPen(QColor(COLORS["text-secondary"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Run an analysis to populate the genome scan.")
            return

        left = 16
        top = 18
        width = self.width() - 32
        cell_width = max(12, min(26, width / max(1, len(self._genome))))
        row_height = 34
        columns = max(1, int(width / cell_width))

        painter.setFont(QFont(FONTS["mono"], 10, QFont.Weight.Bold))
        for index, base in enumerate(self._genome):
            row = index // columns
            col = index % columns
            x = left + col * cell_width
            y = top + row * row_height

            if y + row_height > self.height() - 16:
                break

            rect = (int(x), int(y), int(cell_width - 4), int(row_height - 6))
            color = QColor({"A": "#35d07f", "T": "#f2c465", "C": "#4ea0ff", "G": "#bf7cff"}.get(base, COLORS["text-secondary"]))
            bg = QColor(COLORS["panel-soft"])

            if index in self._match_positions:
                bg = QColor("#1c4c3a")
            if index == self._current_index:
                bg = QColor("#183d5c")

            painter.setPen(QPen(QColor(COLORS["border-light"]), 1))
            painter.setBrush(QBrush(bg))
            painter.drawRoundedRect(*rect, 6, 6)
            painter.setPen(color)
            painter.drawText(rect[0], rect[1], rect[2], rect[3], Qt.AlignmentFlag.AlignCenter, base)


class FADiagramWidget(QWidget):
    """Custom painted DFA diagram with active-state highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern = ""
        self._delta = {}
        self._accept_state = -1
        self._current_state = 0
        self._status_text = "Run analysis to generate the DFA diagram."
        self._positions = {}
        self._radius = 28
        self.setMinimumHeight(320)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def render_dfa(self, pattern: str, delta: dict, accept_state: int):
        self._pattern = pattern
        self._delta = delta
        self._accept_state = accept_state
        self._current_state = 0
        self._status_text = ""
        self._compute_layout()
        self.update()

    def highlight_state(self, state: int, message: str = ""):
        self._current_state = state
        if message:
            self._status_text = message
        self.update()

    def clear_diagram(self):
        self._pattern = ""
        self._delta = {}
        self._accept_state = -1
        self._current_state = 0
        self._status_text = "Run analysis to generate the DFA diagram."
        self._positions = {}
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._compute_layout()

    def _compute_layout(self):
        if not self._delta:
            self._positions = {}
            return
        states = len(self._delta)
        if states == 1:
            self._positions = {0: (self.width() / 2, self.height() / 2)}
            return
        margin = 72
        usable = max(1, self.width() - margin * 2)
        step = max(130, min(180, usable / max(1, states - 1)))
        start_x = max(margin, (self.width() - step * (states - 1)) / 2)
        y = max(124, self.height() * 0.58)
        self._positions = {state: (start_x + state * step, y) for state in range(states)}

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLORS["bg-elevated"]))

        if not self._delta:
            painter.setPen(QColor(COLORS["text-secondary"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._status_text)
            return

        self._draw_edges(painter)
        self._draw_nodes(painter)

        painter.setPen(QColor(COLORS["text-secondary"]))
        painter.setFont(QFont(FONTS["mono"], 12, QFont.Weight.Bold))
        painter.drawText(16, 24, self._status_text or f"Live state: q{self._current_state}")

    def _draw_edges(self, painter: QPainter):
        edge_labels = {}
        for source, transitions in self._delta.items():
            for char, destination in transitions.items():
                edge_labels.setdefault((source, destination), []).append(char)

        def draw_arrow_head(tip_x, tip_y, angle, color, size=11):
            left = QPointF(
                tip_x - size * math.cos(angle - 0.55),
                tip_y - size * math.sin(angle - 0.55),
            )
            right = QPointF(
                tip_x - size * math.cos(angle + 0.55),
                tip_y - size * math.sin(angle + 0.55),
            )
            head = QPainterPath()
            head.moveTo(QPointF(tip_x, tip_y))
            head.lineTo(left)
            head.lineTo(right)
            head.closeSubpath()
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            painter.drawPath(head)
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        for (source, destination), chars in edge_labels.items():
            sorted_chars = sorted(chars)
            label = ",".join(sorted_chars[:2]) + (f"+{len(sorted_chars) - 2}" if len(sorted_chars) > 2 else "")
            sx, sy = self._positions[source]
            dx, dy = self._positions[destination]

            if source == destination:
                loop_r = self._radius + 14
                rect = QRectF(sx - loop_r, sy - self._radius - loop_r - 22, loop_r * 2, loop_r * 2)
                painter.setPen(QPen(QColor(COLORS["accent"]), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                painter.drawArc(rect, 25 * 16, 320 * 16)
                end_deg = 25 + 320
                end_rad = math.radians(end_deg)
                cx = rect.x() + rect.width() / 2
                cy = rect.y() + rect.height() / 2
                arrow_tip_x = cx + loop_r * math.cos(end_rad)
                arrow_tip_y = cy - loop_r * math.sin(end_rad)
                prev_rad = math.radians(end_deg - 8)
                prev_x = cx + loop_r * math.cos(prev_rad)
                prev_y = cy - loop_r * math.sin(prev_rad)
                arrow_angle = math.atan2(arrow_tip_y - prev_y, arrow_tip_x - prev_x)
                draw_arrow_head(arrow_tip_x, arrow_tip_y, arrow_angle, QColor(COLORS["accent"]), size=10)
                painter.setPen(QColor(COLORS["accent-blue"] if source == self._current_state else COLORS["text-primary"]))
                painter.setFont(QFont(FONTS["mono"], 11, QFont.Weight.Bold))
                painter.drawText(int(rect.x() - 26), int(rect.y() - 22), int(rect.width() + 52), 20, Qt.AlignmentFlag.AlignCenter, label)
                continue

            direction = 1 if dx > sx else -1
            start_x = sx + direction * (self._radius + 4)
            end_x = dx - direction * (self._radius + 8)
            edge_color = QColor(COLORS["success"] if destination == self._accept_state else COLORS["text-secondary"])
            painter.setPen(QPen(edge_color, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

            span = abs(destination - source)
            if source < destination:
                control_y = sy - (52 + (span - 1) * 18)
                label_y = control_y - 24
            else:
                control_y = sy + (52 + (span - 1) * 18)
                label_y = control_y + 8

            control_x = (start_x + end_x) / 2
            path = QPainterPath(QPointF(start_x, sy))
            path.quadTo(QPointF(control_x, control_y), QPointF(end_x, dy))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPath(path)

            tx = end_x - control_x
            ty = dy - control_y
            angle = math.atan2(ty, tx)
            draw_arrow_head(end_x, dy, angle, edge_color, size=10)

            painter.setPen(QColor(COLORS["text-primary"]))
            painter.setFont(QFont(FONTS["mono"], 11, QFont.Weight.Bold))
            painter.drawText(int(control_x - 42), int(label_y - 10), 84, 20, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_nodes(self, painter: QPainter):
        painter.setFont(QFont(FONTS["mono"], 12, QFont.Weight.Bold))
        for state, (x, y) in self._positions.items():
            if state == self._accept_state:
                fill = QColor("#0f2f26")
                pen = QPen(QColor(COLORS["success"]), 3)
            else:
                fill = QColor(COLORS["panel"])
                pen = QPen(QColor(COLORS["border"]), 3)

            if state == self._current_state:
                fill = QColor("#103b52")
                pen = QPen(QColor(COLORS["accent"]), 4)

            painter.setBrush(QBrush(fill))
            painter.setPen(pen)
            painter.drawEllipse(int(x - self._radius), int(y - self._radius), self._radius * 2, self._radius * 2)

            if state == self._accept_state:
                painter.setPen(QPen(pen.color(), 1))
                inset = 6
                painter.drawEllipse(
                    int(x - self._radius + inset),
                    int(y - self._radius + inset),
                    int((self._radius - inset) * 2),
                    int((self._radius - inset) * 2),
                )

            painter.setPen(QColor(COLORS["text-primary"]))
            painter.setFont(QFont(FONTS["mono"], 13, QFont.Weight.Bold))
            painter.drawText(int(x - 22), int(y - 10), 44, 20, Qt.AlignmentFlag.AlignCenter, f"q{state}")


class MatchPlotWidget(QWidget):
    """Matplotlib-based match distribution widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._empty = QLabel()
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setTextFormat(Qt.TextFormat.RichText)
        self._empty.setStyleSheet(f"color: {COLORS['text-secondary']}; padding: 24px; line-height: 1.4;")
        self._empty.setText(
            f"<div style='text-align:center;'>"
            f"<div style='font-size:24px; color:{COLORS['accent']}; margin-bottom:8px;'>◌</div>"
            f"<div>Match chart appears here after running analysis.</div>"
            f"</div>"
        )
        layout.addWidget(self._empty)

        self.figure = None
        self.canvas = None
        if HAS_MATPLOTLIB:
            self.figure = Figure(facecolor=COLORS["bg-secondary"], edgecolor="none")
            self.canvas = FigureCanvas(self.figure)
            self.canvas.hide()
            layout.addWidget(self.canvas)

    def plot_matches(self, matches: list[int], genome_len: int, pattern_len: int):
        if not HAS_MATPLOTLIB:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(COLORS["bg-secondary"])
        if not matches:
            ax.text(0.5, 0.5, "No matches found", ha="center", va="center", transform=ax.transAxes, color=COLORS["text-secondary"], fontsize=13)
        else:
            ax.bar(matches, [1] * len(matches), width=max(1, pattern_len * 0.8), color=COLORS["accent"], alpha=0.85, edgecolor=COLORS["accent-blue"], linewidth=1.6)
            ax.set_xlim(0, max(1, genome_len + 1))
            ax.set_ylim(0, 1.6)
            ax.set_xlabel("Genome position", color=COLORS["text-primary"], fontweight="bold")
            ax.set_ylabel("Match", color=COLORS["text-primary"], fontweight="bold")
            ax.set_title(f"Match Positions ({len(matches)} total)", color=COLORS["text-primary"], fontweight="bold")

        ax.tick_params(colors=COLORS["text-secondary"])
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color(COLORS["border"])

        self._empty.hide()
        self.canvas.show()
        self.figure.tight_layout()
        self.canvas.draw()


class AIWorker(QThread):
    """Runs Gemini requests off the UI thread."""

    result_ready = pyqtSignal(str, bool, str)

    def __init__(self, handler, action: str, message: str, context: Optional[dict] = None):
        super().__init__()
        self.handler = handler
        self.action = action
        self.message = message
        self.context = context or {}

    def run(self):
        try:
            if self.action == "chat":
                success, payload = self.handler.chat(self.message, self.context)
            elif self.action == "extract":
                success, payload = self.handler.extract_pattern(self.message)
            else:
                success, payload = False, "Unsupported AI action."
        except Exception as exc:  # pragma: no cover
            success, payload = False, str(exc)
        self.result_ready.emit(self.action, success, payload)

class GeneFlowApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pattern = ""
        self.genome = ""
        self.matches = []
        self.dfa_table = {}
        self._ai_handler = None
        self._ai_thread = None
        self._ai_panel_collapsed = False
        self._top_splitter = None
        self._ai_panel_body = None
        self._ai_toggle_btn = None
        self._kpi_labels = {}
        self._dfa_search_input = None
        self._dfa_base_filter = None
        self._dfa_accept_only = None
        self._nav_labels = []
        self._header_tagline = None
        self._header_right_tag = None
        self._accept_state = 0
        self._trace = []
        self._step_index = -1
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._advance_playback)
        self._example_genomes = {
            "Short Demo": "ATCGATCGATGGATCG",
            "Mutation-like": "ATCGGATCATCGTTTATCGATCG",
            "Repeats": "ATATATCGATATATCGATAT",
        }
        self._scan_progress = None
        self._scan_status = None
        self._state_diagram = None
        self._state_meta = None
        self._speed_combo = None
        self._timeline_widget = None
        self._match_plot_widget = None
        self._live_genome_reader = None
        self._export_format_combo = None
        self._export_btn = None
        self._history_text = None
        self._right_tabs = None
        self._status_left = None
        self._status_center = None
        self._status_right = None
        self._nav_buttons = {}
        self._panel_matcher = None
        self._panel_results = None
        self._panel_dfa = None
        self._panel_ai = None
        self.session_history = []

        self.app_shell = None
        
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("GeneFlow - DNA Sequencing Analysis")
        self.setWindowIcon(self.create_icon())
        self.setGeometry(100, 100, 1400, 900)

        self.app_shell = self.create_shell()
        self.setCentralWidget(self.app_shell)

    def create_shell(self):
        shell = QWidget()
        shell.setObjectName("appShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        shell_layout.addWidget(self.create_titlebar())

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        workbench = QWidget()
        workbench_layout = QHBoxLayout(workbench)
        workbench_layout.setContentsMargins(0, 0, 0, 0)
        workbench_layout.setSpacing(0)

        self.sidebar_widget = self.create_sidebar()
        workbench_layout.addWidget(self.sidebar_widget)

        center_stack = QWidget()
        center_layout = QVBoxLayout(center_stack)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.create_topbar())

        self.center_scroll = QScrollArea()
        self.center_scroll.setWidgetResizable(True)
        self.center_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.center_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.center_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.center_scroll.setWidget(self.create_center_content())
        center_layout.addWidget(self.center_scroll, 1)
        workbench_layout.addWidget(center_stack, 1)

        self._right_tabs = self.create_right_tabs()
        workbench_layout.addWidget(self._right_tabs)

        self._wire_sidebar_navigation()

        body_layout.addWidget(workbench, 1)
        body_layout.addWidget(self.create_statusbar())
        shell_layout.addWidget(body, 1)

        return shell

    def create_titlebar(self):
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"background: {COLORS['bg-elevated']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        left_pad = QWidget()
        left_pad.setFixedWidth(8)
        layout.addWidget(left_pad)

        title = QLabel("GeneFlow Desktop  v2.1  —  DNA Pattern Matcher")
        title.setFont(QFont(FONTS["mono"], 10))
        title.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 1px;")
        layout.addWidget(title)

        layout.addStretch()

        logo = QLabel("GeneFlow")
        logo.setFont(QFont(FONTS["serif"], 15, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(logo)

        layout.addStretch()

        status = QLabel("LIVE ANALYSIS")
        status.setStyleSheet(
            f"color: {COLORS['gold']}; background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 10px; font-family: '{FONTS['mono']}'; font-size: 9px;"
        )
        layout.addWidget(status)

        return bar

    def _nav_icon(self, kind: str):
        style = self.style()
        mapping = {
            "matcher": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "diagram": QStyle.StandardPixmap.SP_ArrowRight,
            "results": QStyle.StandardPixmap.SP_DialogApplyButton,
            "data": QStyle.StandardPixmap.SP_DirIcon,
            "export": QStyle.StandardPixmap.SP_DialogSaveButton,
            "history": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "config": QStyle.StandardPixmap.SP_FileDialogInfoView,
            "ai": QStyle.StandardPixmap.SP_MessageBoxInformation,
        }
        return style.standardIcon(mapping.get(kind, QStyle.StandardPixmap.SP_FileIcon))

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background: {COLORS['bg-elevated']}; border-right: 1px solid {COLORS['border']};")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 18, 0, 18)
        layout.setSpacing(6)

        def add_section(label_text):
            lbl = QLabel(label_text)
            lbl.setFont(QFont(FONTS["mono"], 9))
            lbl.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 2px; padding: 12px 20px 6px;")
            layout.addWidget(lbl)

        add_section("Analysis")
        self._nav_buttons["matcher"] = self._make_nav_button("DFA Matcher", "matcher", active=True)
        self._nav_buttons["diagram"] = self._make_nav_button("FA Diagram", "diagram")
        self._nav_buttons["results"] = self._make_nav_button("Match Plot", "results")
        for btn in (self._nav_buttons["matcher"], self._nav_buttons["diagram"], self._nav_buttons["results"]):
            layout.addWidget(btn)

        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {COLORS['border']}; margin: 10px 20px;")
        layout.addWidget(line)

        add_section("Data")
        self._nav_buttons["data"] = self._make_nav_button("Load FASTA", "data")
        self._nav_buttons["export"] = self._make_nav_button("Export Results", "export")
        self._nav_buttons["history"] = self._make_nav_button("History", "history")
        for btn in (self._nav_buttons["data"], self._nav_buttons["export"], self._nav_buttons["history"]):
            layout.addWidget(btn)

        line2 = QWidget()
        line2.setFixedHeight(1)
        line2.setStyleSheet(f"background: {COLORS['border']}; margin: 10px 20px;")
        layout.addWidget(line2)

        add_section("System")
        self._nav_buttons["config"] = self._make_nav_button("Config", "config")
        layout.addWidget(self._nav_buttons["config"])

        layout.addStretch()

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(20, 0, 20, 0)
        bottom_layout.setSpacing(10)

        self.sidebar_match_stat = self._sidebar_stat_card("Session Matches", "84", "across 2 analyses")
        self.sidebar_genome_stat = self._sidebar_stat_card("Genome Length", "300", "bases loaded", gold=True)
        bottom_layout.addWidget(self.sidebar_match_stat)
        bottom_layout.addWidget(self.sidebar_genome_stat)
        layout.addWidget(bottom)
        return sidebar

    def _make_nav_button(self, text, kind, active=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setIcon(self._nav_icon(kind))
        btn.setIconSize(QSize(16, 16))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _checked=False, key=kind: self._activate_sidebar(key))
        btn.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                padding: 10px 18px;
                border: none;
                border-left: 2px solid transparent;
                background: transparent;
                color: {COLORS['text-secondary']};
                font-family: '{FONTS['sans']}';
                font-size: 13px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.03); color: {COLORS['text-primary']}; }}
            QPushButton:checked {{
                background: rgba(45,212,191,0.06);
                border-left-color: {COLORS['accent']};
                color: {COLORS['accent']};
            }}
            """
        )
        return btn

    def _wire_sidebar_navigation(self):
        self._activate_sidebar("matcher")

    def _activate_sidebar(self, key: str):
        for nav_key, button in self._nav_buttons.items():
            button.setChecked(nav_key == key)

        self._focus_section_for_key(key)

        if self._right_tabs is None:
            return
        if key in {"matcher", "diagram", "results"}:
            self._right_tabs.setCurrentIndex(0)
        elif key in {"data", "export"}:
            self._right_tabs.setCurrentIndex(2)
        elif key in {"history", "config"}:
            self._right_tabs.setCurrentIndex(3)

    def _focus_section_for_key(self, key: str):
        target = None
        if key in {"matcher", "data"}:
            target = self._panel_matcher
        elif key == "diagram":
            target = self._panel_dfa
        elif key == "results":
            target = self._panel_results
        elif key == "export":
            target = self._panel_results
        elif key in {"history", "config"}:
            target = self._panel_ai

        if target is None:
            return

        if self.center_scroll is not None:
            self.center_scroll.ensureWidgetVisible(target, 24, 24)

        self._flash_panel_focus(target)

    def _flash_panel_focus(self, panel: QWidget):
        base_style = panel.styleSheet() or ""
        flash_style = (
            base_style
            + f" border: 2px solid {COLORS['accent']};"
            + " border-radius: 12px;"
        )
        panel.setStyleSheet(flash_style)
        QTimer.singleShot(700, lambda p=panel, s=base_style: p.setStyleSheet(s))

    def _sidebar_stat_card(self, label, value, sub, gold=False):
        card = QWidget()
        card.setStyleSheet(f"background: {COLORS['bg-secondary']}; border: 1px solid {COLORS['border-light']}; border-radius: 12px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)
        dot = QLabel("●")
        dot.setFont(QFont(FONTS["mono"], 10, QFont.Weight.Bold))
        dot.setStyleSheet(f"color: {COLORS['gold'] if gold else COLORS['accent']};")
        top_row.addWidget(dot)
        badge = QLabel(label.upper())
        badge.setFont(QFont(FONTS["mono"], 8, QFont.Weight.Bold))
        badge.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 1px;")
        top_row.addWidget(badge)
        top_row.addStretch()
        layout.addLayout(top_row)

        lab = QLabel(label)
        lab.setFont(QFont(FONTS["sans"], 10, QFont.Weight.DemiBold))
        lab.setStyleSheet(f"color: {COLORS['text-secondary']};")
        layout.addWidget(lab)
        val = QLabel("—" if not value else value)
        val.setFont(QFont(FONTS["mono"], 22, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {COLORS['gold'] if gold else COLORS['accent']}; padding: 2px 0; line-height: 1;")
        layout.addWidget(val)
        sub_lab = QLabel(sub)
        sub_lab.setStyleSheet(f"color: {COLORS['text-tertiary']}; font-family: '{FONTS['mono']}'; font-size: 10px;")
        layout.addWidget(sub_lab)
        return card

    def create_topbar(self):
        bar = QWidget()
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"background: {COLORS['bg-elevated']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("ATCG")
        self.pattern_input.setMinimumWidth(160)
        self.pattern_input.setMaximumWidth(220)

        self.genome_source_input = QLineEdit()
        self.genome_source_input.setPlaceholderText("sequence.fasta")
        self.genome_source_input.setReadOnly(True)
        self.genome_source_input.setMinimumWidth(220)
        self.genome_source_input.setMaximumWidth(320)

        self.load_btn = QPushButton("Browse")
        self.load_btn.clicked.connect(self.load_fasta)
        self.load_btn.setMinimumWidth(92)
        self.load_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.clicked.connect(self.run_matcher)
        self.run_btn.setMinimumWidth(150)
        self.run_btn.setMinimumHeight(40)
        self.run_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        self.clear_btn.setMinimumWidth(92)
        self.clear_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.export_quick_btn = QPushButton()
        self.export_quick_btn.setIcon(self._nav_icon("export"))
        self.export_quick_btn.setFixedSize(32, 32)
        self.export_quick_btn.clicked.connect(self.export_results)

        self.config_quick_btn = QPushButton()
        self.config_quick_btn.setIcon(self._nav_icon("config"))
        self.config_quick_btn.setFixedSize(32, 32)

        self.pattern_input.setStyleSheet(self._field_style(120))
        self.genome_source_input.setStyleSheet(self._field_style(220))
        self.load_btn.setStyleSheet(self._ghost_button_style())
        self.clear_btn.setStyleSheet(self._ghost_button_style())
        self.run_btn.setStyleSheet(self._primary_button_style())
        self.export_quick_btn.setStyleSheet(self._icon_button_style())
        self.config_quick_btn.setStyleSheet(self._icon_button_style())

        group1 = QWidget()
        g1 = QHBoxLayout(group1)
        g1.setContentsMargins(0, 0, 0, 0)
        g1.setSpacing(10)
        label1 = QLabel("PATTERN")
        label1.setFont(QFont(FONTS["mono"], 11))
        label1.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 2px;")
        g1.addWidget(label1)
        g1.addWidget(self.pattern_input)
        layout.addWidget(group1)

        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(sep)

        group2 = QWidget()
        g2 = QHBoxLayout(group2)
        g2.setContentsMargins(0, 0, 0, 0)
        g2.setSpacing(10)
        label2 = QLabel("GENOME SOURCE")
        label2.setFont(QFont(FONTS["mono"], 11))
        label2.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 2px;")
        g2.addWidget(label2)
        g2.addWidget(self.genome_source_input)
        g2.addWidget(self.load_btn)
        layout.addWidget(group2, 1)

        layout.addWidget(self.run_btn)
        layout.addWidget(self.clear_btn)
        layout.addWidget(self.export_quick_btn)
        layout.addWidget(self.config_quick_btn)
        layout.addStretch()
        return bar

    def _field_style(self, width):
        return f"background: {COLORS['card']}; border: 1px solid {COLORS['border-card']}; border-radius: 6px; padding: 8px 12px; color: {COLORS['teal2'] if 'teal2' in COLORS else COLORS['accent']}; font-family: '{FONTS['mono']}'; font-size: 13px; min-height: 18px;"

    def _primary_button_style(self):
        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLORS['accent']}, stop:1 {COLORS['teal2']});
            color: #03131a;
            border: 1px solid {COLORS['border-card']};
            border-radius: 8px;
            padding: 10px 18px;
            font-family: '{FONTS['mono']}';
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.4px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLORS['teal2']}, stop:1 {COLORS['accent']});
        }}
        QPushButton:pressed {{
            background: {COLORS['accent']};
        }}
        """

    def _ghost_button_style(self):
        return f"background: transparent; color: {COLORS['text-secondary']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 9px 14px; font-family: '{FONTS['mono']}'; font-size: 10px;"

    def _icon_button_style(self):
        return f"background: {COLORS['surface'] if 'surface' in COLORS else COLORS['bg-secondary']}; color: {COLORS['text-secondary']}; border: 1px solid {COLORS['border']}; border-radius: 6px;"

    def create_center_content(self):
        body = QWidget()
        body.setStyleSheet(f"background: {COLORS['bg']};")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        genome_input_panel = QWidget()
        genome_input_panel.setStyleSheet(f"")
        gip_layout = QVBoxLayout(genome_input_panel)
        gip_layout.setContentsMargins(16, 16, 16, 16)
        gip_layout.setSpacing(10)
        input_header = QHBoxLayout()
        title = QLabel("Genome Input")
        title.setFont(QFont(FONTS["serif"], 18, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        input_header.addWidget(title)
        input_header.addStretch()
        self.example_selector = QComboBox()
        self.example_selector.addItems(list(self._example_genomes.keys()))
        self.example_selector.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border-card']}; border-radius: 6px; padding: 6px 10px; font-family: '{FONTS['mono']}';")
        input_header.addWidget(self.example_selector)
        self.example_btn = QPushButton("Load Example")
        self.example_btn.clicked.connect(self.load_example_genome)
        self.example_btn.setStyleSheet(self._ghost_button_style())
        input_header.addWidget(self.example_btn)
        gip_layout.addLayout(input_header)

        self.genome_input = QTextEdit()
        self.genome_input.setPlaceholderText("Paste genome sequence here or load a FASTA file.")
        self.genome_input.setMinimumHeight(150)
        self.genome_input.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border-card']}; border-radius: 8px; padding: 10px; font-family: '{FONTS['mono']}'; font-size: 10px;")
        gip_layout.addWidget(self.genome_input)

        layout.addWidget(genome_input_panel)

        layout.addWidget(self.create_metrics_row())

        lgr_panel = QWidget()
        lgr_panel.setStyleSheet(f"")
        lgr_layout = QVBoxLayout(lgr_panel)
        lgr_layout.setContentsMargins(16, 16, 16, 16)
        lgr_layout.setSpacing(8)
        lgr_header = QHBoxLayout()
        lgr_title = QLabel("Live Genome Reader")
        lgr_title.setFont(QFont(FONTS["serif"], 18, QFont.Weight.DemiBold))
        lgr_title.setStyleSheet(f"color: {COLORS['text-primary']};")
        lgr_header.addWidget(lgr_title)
        lgr_header.addStretch()
        lgr_tag = QLabel("REAL-TIME")
        lgr_tag.setStyleSheet(f"color: {COLORS['gold']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 10px; font-family: '{FONTS['mono']}'; font-size: 10px;")
        lgr_header.addWidget(lgr_tag)
        lgr_layout.addLayout(lgr_header)
        self._live_genome_reader = LiveGenomeReaderWidget()
        self._live_genome_reader.setMinimumHeight(120)
        lgr_layout.addWidget(self._live_genome_reader)
        layout.addWidget(lgr_panel)

        genome_panel = QWidget()
        genome_panel.setStyleSheet(f"")
        g_layout = QVBoxLayout(genome_panel)
        g_layout.setContentsMargins(16, 16, 16, 16)
        g_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Genome Sequence Viewer")
        title.setFont(QFont(FONTS["serif"], 18, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        header.addWidget(title)
        header.addStretch()
        g_layout.addLayout(header)

        self._match_plot_widget = MatchPlotWidget()
        self._match_plot_widget.setMinimumHeight(150)
        g_layout.addWidget(self._match_plot_widget)

        self.genome_display = QTextEdit()
        self.genome_display.setReadOnly(True)
        self.genome_display.setMinimumHeight(120)
        self.genome_display.setStyleSheet(f"background: {COLORS['card']}; border: 1px solid {COLORS['border-card']}; border-radius: 8px; color: {COLORS['text-secondary']}; padding: 12px; font-family: '{FONTS['mono']}'; font-size: 13px;")
        g_layout.addWidget(self.genome_display)

        progress_row = QWidget()
        p_layout = QVBoxLayout(progress_row)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(6)
        self._scan_progress = QProgressBar()
        self._scan_progress.setRange(0, 100)
        self._scan_progress.setValue(0)
        self._scan_progress.setFormat("pos %v / %m")
        p_layout.addWidget(self._scan_progress)
        g_layout.addWidget(progress_row)

        controls = QHBoxLayout()
        self.play_btn = self._icon_control_button("▶")
        self.play_btn.clicked.connect(self.start_playback)
        self.pause_btn = self._icon_control_button("❚❚")
        self.pause_btn.clicked.connect(self.pause_playback)
        self.step_btn = self._icon_control_button("▸")
        self.step_btn.clicked.connect(self.step_forward)
        self.reset_btn = self._icon_control_button("↺")
        self.reset_btn.clicked.connect(self.reset_playback)
        for btn in (self.play_btn, self.pause_btn, self.step_btn, self.reset_btn):
            controls.addWidget(btn)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Slow", "Normal", "Fast"])
        self.speed_combo.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border-card']}; border-radius: 6px; padding: 6px 12px; font-family: '{FONTS['mono']}';")
        controls.addWidget(self.speed_combo)
        controls.addStretch()
        g_layout.addLayout(controls)
        layout.addWidget(genome_panel)

        return body

    def create_metrics_row(self):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.stat_labels = {}
        cards = [
            ("Matches Found", "teal"),
            ("Match Density", "gold"),
            ("DFA States", "violet"),
            ("Genome Length", "green"),
        ]
        for label, color in cards:
            card = QWidget()
            card.setStyleSheet(f"background: {COLORS['card']}; border: 1px solid {COLORS['border-card']}; border-radius: 10px;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 18, 18, 18)
            cl.setSpacing(6)
            lab = QLabel(label.upper())
            lab.setFont(QFont(FONTS["mono"], 9))
            lab.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 2px;")
            cl.addWidget(lab)
            val = QLabel("—")
            val.setFont(QFont("Syne", 28, QFont.Weight.Bold))
            val.setStyleSheet(f"color: {COLORS[color if color in COLORS else 'accent']}; line-height: 1;")
            cl.addWidget(val)
            sub = QLabel("")
            sub.setStyleSheet(f"color: {COLORS['text-tertiary']}; font-family: '{FONTS['mono']}'; font-size: 10px;")
            cl.addWidget(sub)
            layout.addWidget(card, 1)
            key_map = {
                "Matches Found": "Matches",
                "Match Density": "Density",
                "DFA States": "DFA States",
                "Genome Length": "Genome Length",
            }
            self.stat_labels[key_map[label]] = val
        return row

    def _icon_control_button(self, glyph):
        btn = QPushButton(glyph)
        btn.setFixedSize(36, 36)
        btn.setStyleSheet(f"background: {COLORS['accent']}; color: {COLORS['bg']}; border: none; border-radius: 8px; font-family: '{FONTS['mono']}'; font-weight: 700;")
        return btn

    def create_right_tabs(self):
        tabs = QTabWidget()
        tabs.setMinimumWidth(400)
        tabs.setMaximumWidth(470)
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {COLORS['bg-elevated']};
                border: 1px solid {COLORS['border']};
                border-top: none;
            }}
            QTabBar::tab {{
                background: {COLORS['bg-secondary']};
                color: {COLORS['text-tertiary']};
                min-width: 100px;
                padding: 11px 14px;
                margin-right: 2px;
                font-family: '{FONTS['mono']}';
                font-size: 10px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QTabBar::tab:selected {{
                background: {COLORS['bg-elevated']};
                color: {COLORS['accent']};
                border-bottom: 3px solid {COLORS['accent']};
                font-weight: 700;
            }}
        """)
        tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
        tabs.tabBar().setExpanding(True)
        tabs.tabBar().setUsesScrollButtons(True)
        tabs.addTab(self.create_dfa_right_tab(), "DFA Live")
        tabs.addTab(self.create_ai_right_tab(), "AI")
        tabs.addTab(self.create_export_right_tab(), "Export")
        tabs.addTab(self.create_info_tab(), "History")
        return tabs

    def create_statusbar(self):
        bar = QWidget()
        bar.setFixedHeight(28)
        bar.setStyleSheet(f"background: {COLORS['bg-elevated']}; border-top: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(18)

        self._status_left = QLabel("Ready - DFA scanning active")
        self._status_left.setStyleSheet(f"color: {COLORS['success']}; font-family: '{FONTS['mono']}'; font-size: 10px; font-weight: 700;")
        self._status_center = QLabel('Pattern: "" | 0 states | Genome: not loaded')
        self._status_center.setStyleSheet(f"color: {COLORS['text-tertiary']}; font-family: '{FONTS['mono']}'; font-size: 10px;")
        self._status_right = QLabel("GeneFlow v2.1")
        self._status_right.setStyleSheet(f"color: {COLORS['text-tertiary']}; font-family: '{FONTS['mono']}'; font-size: 10px;")
        layout.addWidget(self._status_left)
        layout.addWidget(self._status_center)
        layout.addStretch()
        layout.addWidget(self._status_right)
        return bar

    def send_quick_prompt(self, prompt: str):
        if hasattr(self, "chat_input"):
            self.chat_input.setPlainText(prompt)
            if self._ensure_ai_handler():
                self.send_chat_message()

    def quick_export(self, label: str):
        if label == "FA Diagram":
            file_path, _ = QFileDialog.getSaveFileName(self, "Save FA Diagram", "fa_diagram.png", "PNG Images (*.png)")
            if file_path and self._state_diagram is not None:
                self._render_widget_png(self._state_diagram, file_path)
        elif label == "Match Plot":
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Match Plot", "match_plot.png", "PNG Images (*.png)")
            if file_path and self._match_plot_widget is not None:
                self._render_widget_png(self._match_plot_widget, file_path)
        elif label == "CSV Report":
            file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV Report", "results.csv", "CSV Files (*.csv)")
            if file_path:
                self._export_csv(file_path)
        elif label == "PDF Report":
            file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "results.pdf", "PDF Files (*.pdf)")
            if file_path:
                self._export_pdf(file_path)

    def _export_pdf(self, file_path: str):
        writer = QPdfWriter(file_path)
        writer.setResolution(96)
        painter = QPainter(writer)
        self.app_shell.render(painter)
        painter.end()

    def _render_widget_png(self, widget: QWidget, file_path: str):
        if widget is None:
            return
        pixmap = QPixmap(widget.size())
        pixmap.fill(QColor(COLORS["bg-secondary"]))
        widget.render(pixmap)
        pixmap.save(file_path, "PNG")

    def create_dfa_right_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._state_diagram = FADiagramWidget()
        self._state_diagram.setMinimumHeight(380)
        layout.addWidget(self._state_diagram)

        self._state_meta = QLabel("Live State: q0")
        self._state_meta.setStyleSheet(f"color: {COLORS['text-secondary']}; font-family: '{FONTS['mono']}'; font-size: 11px; letter-spacing: 0.2px;")
        self._state_meta.setWordWrap(True)
        layout.addWidget(self._state_meta)

        table_wrap = QWidget()
        table_wrap.setStyleSheet(f"background: {COLORS['bg-secondary']}; border: 1px solid {COLORS['border-light']}; border-radius: 12px;")
        twl = QVBoxLayout(table_wrap)
        twl.setContentsMargins(12, 12, 12, 12)
        tbl_title = QLabel("Transition Table")
        tbl_title.setFont(QFont(FONTS["serif"], 15, QFont.Weight.DemiBold))
        tbl_title.setStyleSheet(f"color: {COLORS['text-primary']};")
        twl.addWidget(tbl_title)
        self.dfa_table_widget = QTableWidget()
        self.dfa_table_widget.verticalHeader().setVisible(False)
        self.dfa_table_widget.setHorizontalHeaderLabels(["State", "A", "T", "C", "G"])
        self.dfa_table_widget.setAlternatingRowColors(True)
        self.dfa_table_widget.horizontalHeader().setStretchLastSection(True)
        self.dfa_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dfa_table_widget.setMinimumHeight(220)
        self.dfa_table_widget.setStyleSheet(f"""
            QTableWidget {{
                background: {COLORS['bg']};
                color: {COLORS['text-primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border']};
                font-family: '{FONTS['mono']}';
                font-size: 10px;
            }}
            QHeaderView::section {{
                background: {COLORS['bg-elevated']};
                color: {COLORS['text-primary']};
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid {COLORS['accent']};
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QTableWidget::item {{
                padding: 6px;
            }}
        """)
        twl.addWidget(self.dfa_table_widget)
        layout.addWidget(table_wrap, 1)
        return page

    def create_ai_right_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QWidget()
        header.setStyleSheet(f"background: {COLORS['bg-secondary']}; border: 1px solid {COLORS['border-light']}; border-radius: 10px;")
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 12, 12, 12)
        a = QLabel("AI Assistant")
        a.setFont(QFont(FONTS["serif"], 16, QFont.Weight.DemiBold))
        a.setStyleSheet(f"color: {COLORS['text-primary']};")
        h.addWidget(a)
        h.addStretch()
        icon = QLabel("◼")
        icon.setStyleSheet(f"color: {COLORS['accent']};")
        h.addWidget(icon)
        layout.addWidget(header)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(190)
        self.chat_history.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border-card']}; border-radius: 8px; padding: 10px; font-family: '{FONTS['mono']}'; font-size: 10px;")
        layout.addWidget(self.chat_history)

        quick = QWidget()
        ql = QGridLayout(quick)
        ql.setContentsMargins(0, 0, 0, 0)
        ql.setHorizontalSpacing(6)
        ql.setVerticalSpacing(6)
        self.ai_quick_buttons = []
        prompts = [
            "Explain state",
            "Why matches",
            "Suggest motif",
            "Summarize run",
        ]
        for idx, prompt in enumerate(prompts):
            btn = QPushButton(prompt)
            btn.setMinimumHeight(30)
            btn.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['accent']}; border: 1px solid {COLORS['border-card']}; border-radius: 4px; padding: 5px 8px; font-family: '{FONTS['mono']}'; font-size: 9px;")
            full_prompt = {
                "Explain state": "Explain current DFA state and transitions",
                "Why matches": "Why did this genome produce this many matches?",
                "Suggest motif": "Suggest a new DNA pattern to test next",
                "Summarize run": "Summarize this run for a report",
            }[prompt]
            btn.clicked.connect(lambda _, p=full_prompt: self.send_quick_prompt(p))
            self.ai_quick_buttons.append(btn)
            ql.addWidget(btn, idx // 2, idx % 2)
        layout.addWidget(quick)

        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Ask about your results...")
        self.chat_input.setFixedHeight(72)
        self.chat_input.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border-card']}; padding: 8px; font-family: '{FONTS['mono']}'; font-size: 10px;")
        layout.addWidget(self.chat_input)

        btn_row = QHBoxLayout()
        self.send_chat_btn = QPushButton("Send")
        self.send_chat_btn.clicked.connect(self.send_chat_message)
        self.send_chat_btn.setMinimumHeight(34)
        self.send_chat_btn.setMinimumWidth(100)
        self.send_chat_btn.setStyleSheet(self._primary_button_style())
        btn_row.addWidget(self.send_chat_btn)
        self.extract_pattern_btn = QPushButton("Use As Pattern")
        self.extract_pattern_btn.clicked.connect(self.suggest_pattern_from_chat)
        self.extract_pattern_btn.setMinimumHeight(34)
        self.extract_pattern_btn.setMinimumWidth(130)
        self.extract_pattern_btn.setStyleSheet(self._ghost_button_style())
        btn_row.addWidget(self.extract_pattern_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._append_chat_message("assistant", "Hi, I am your GeneFlow AI assistant. Ask me to explain results or suggest a DNA pattern.")
        if not HAS_AI:
            self.ai_status.setText("Gemini SDK not installed. Install: pip install google-generativeai")
            self.send_chat_btn.setEnabled(False)
            self.extract_pattern_btn.setEnabled(False)
        return page

    def create_export_right_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Quick Export")
        title.setFont(QFont(FONTS["serif"], 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(title)

        self._export_format_combo = QComboBox()
        self._export_format_combo.addItems(["CSV Report", "JSON Report", "Text Summary", "HTML Report", "PNG Snapshot", "PDF Report"])
        self._export_format_combo.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['card']};
                color: {COLORS['text-primary']};
                border: 1px solid {COLORS['border-card']};
                border-radius: 8px;
                padding: 8px 10px;
                font-family: '{FONTS['mono']}';
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 1px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
        """)
        layout.addWidget(self._export_format_combo)

        grid = QWidget()
        gl = QVBoxLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(8)
        for label, kind in [("FA Diagram", "diagram"), ("Match Plot", "results"), ("CSV Report", "export"), ("PDF Report", "export")]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['card']};
                    color: {COLORS['text-primary']};
                    border: 1px solid {COLORS['border-card']};
                    border-left: 3px solid transparent;
                    border-radius: 10px;
                    padding: 10px 14px;
                    text-align: left;
                    font-family: '{FONTS['mono']}';
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg-secondary']};
                    border: 1px solid {COLORS['accent']};
                    border-left: 3px solid {COLORS['accent']};
                    color: {COLORS['accent']};
                }}
                QPushButton:pressed {{
                    background: {COLORS['accent-soft']};
                    border-left: 3px solid {COLORS['teal2']};
                    color: {COLORS['teal2']};
                }}
            """)
            btn.clicked.connect(lambda _, l=label: self.quick_export(l))
            gl.addWidget(btn)
        layout.addWidget(grid)
        return page

    def create_info_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Session History")
        title.setFont(QFont(FONTS["serif"], 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(title)

        self._history_text = QTextEdit()
        self._history_text.setReadOnly(True)
        self._history_text.setStyleSheet(f"color: {COLORS['text-primary']}; font-family: '{FONTS['mono']}'; font-size: 10px;")
        layout.addWidget(self._history_text)

        info = QLabel("Pattern, matches, and DFA summary for the last 5 runs are preserved here.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS['text-secondary']}; font-family: '{FONTS['mono']}'; font-size: 10px;")
        layout.addWidget(info)
        return page
    
    def create_header(self):
        """Modern header with branding and navigation"""
        header = QHBoxLayout()
        header.setContentsMargins(40, 16, 40, 16)
        header.setSpacing(32)
        
        # Logo + Branding
        logo_label = QLabel("🧬")
        logo_label.setFont(QFont(FONTS["sans"], 20, QFont.Weight.Bold))
        header.addWidget(logo_label)
        
        brand_label = QLabel("GeneFlow")
        brand_label.setFont(QFont(FONTS["serif"], 20, QFont.Weight.DemiBold))
        brand_label.setStyleSheet(f"color: {COLORS['text-primary']}; font-style: italic;")
        header.addWidget(brand_label)
        
        tagline = QLabel("DNA Sequencing Analysis")
        tagline.setFont(QFont(FONTS["mono"], 9))
        tagline.setStyleSheet(f"color: {COLORS['gold']}; letter-spacing: 2px;")
        header.addWidget(tagline)
        
        # Navigation
        header.addSpacing(32)
        
        nav_items = ["Matcher", "DFA Viewer", "Results", "Documentation"]
        for item in nav_items:
            nav_btn = QLabel(item)
            nav_btn.setFont(QFont(FONTS["sans"], 11, QFont.Weight.Medium))
            nav_btn.setStyleSheet(f"color: {COLORS['text-secondary']}; padding: 0 12px;")
            header.addWidget(nav_btn)
            self._nav_labels.append(nav_btn)
        
        header.addStretch()

        right_tag = QLabel("DFA DNA MATCHER")
        right_tag.setFont(QFont(FONTS["mono"], 9))
        right_tag.setStyleSheet(f"color: {COLORS['gold']}; letter-spacing: 2px;")
        header.addWidget(right_tag)
        self._header_right_tag = right_tag

        header.addSpacing(16)
        
        # CTA Button
        cta_btn = QPushButton("Get Started")
        cta_btn.setFont(QFont(FONTS["mono"], 10, QFont.Weight.Bold))
        cta_btn.setMinimumSize(100, 36)
        cta_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #1a2640;
            }}
        """)
        header.addWidget(cta_btn)
        
        wrapper = QWidget()
        wrapper.setLayout(header)
        wrapper.setStyleSheet(f"border-bottom: 1px solid {COLORS['border']};")

        self._header_tagline = tagline
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(wrapper)
        return layout
    
    def create_hero(self):
        """Hero section with DNA visualization"""
        wrapper = QWidget()
        wrapper.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLORS['bg-elevated']}, stop:0.55 {COLORS['bg-secondary']}, stop:1 {COLORS['bg']}); border: 1px solid {COLORS['border']}; border-radius: 18px;"
        )

        hero_layout = QHBoxLayout(wrapper)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(10)

        title = QLabel("Live DNA pattern discovery")
        title.setFont(QFont(FONTS["serif"], 28, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        left.addWidget(title)

        subtitle = QLabel("Match genome sequences, inspect the DFA in motion, and export a polished report from the same run.")
        subtitle.setWordWrap(True)
        subtitle.setFont(QFont(FONTS["sans"], 11))
        subtitle.setStyleSheet(f"color: {COLORS['text-secondary']};")
        left.addWidget(subtitle)

        chips = QHBoxLayout()
        for text, color in [("Live DFA", COLORS["accent"]), ("AI Assistant", COLORS["gold"]), ("Export Ready", COLORS["success"])]:
            pill = QLabel(text)
            pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pill.setFont(QFont(FONTS["mono"], 9, QFont.Weight.Bold))
            pill.setStyleSheet(f"color: {color}; background: {COLORS['card']}; border: 1px solid {COLORS['border-card']}; border-radius: 11px; padding: 5px 10px;")
            chips.addWidget(pill)
        chips.addStretch()
        left.addLayout(chips)

        actions = QHBoxLayout()
        self.hero_start_btn = QPushButton("Run Analysis")
        self.hero_start_btn.clicked.connect(self.run_matcher)
        self.hero_start_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #03131a; border: none; border-radius: 8px; padding: 10px 16px; font-weight: 700;")
        actions.addWidget(self.hero_start_btn)

        self.hero_export_btn = QPushButton("Export Report")
        self.hero_export_btn.clicked.connect(self.export_results)
        self.hero_export_btn.setStyleSheet(f"background: {COLORS['card']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border-card']}; border-radius: 8px; padding: 10px 16px; font-weight: 700;")
        actions.addWidget(self.hero_export_btn)
        actions.addStretch()
        left.addLayout(actions)
        left.addStretch()

        hero_layout.addLayout(left, 2)

        right = QWidget()
        right.setStyleSheet(f"background: {COLORS['card']}; border: 1px solid {COLORS['border-card']}; border-radius: 14px;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        helix_title = QLabel("Genome Helix")
        helix_title.setFont(QFont(FONTS["mono"], 10, QFont.Weight.Bold))
        helix_title.setStyleSheet(f"color: {COLORS['gold']}; letter-spacing: 1px;")
        right_layout.addWidget(helix_title)

        self._helix_widget = HelixWidget()
        right_layout.addWidget(self._helix_widget)

        scan_tag = QLabel("Animated pulse indicates the active scan window.")
        scan_tag.setWordWrap(True)
        scan_tag.setStyleSheet(f"color: {COLORS['text-secondary']}; font-size: 11px;")
        right_layout.addWidget(scan_tag)

        hero_layout.addWidget(right, 1)

        return wrapper
    
    def create_content(self):
        """Main dashboard layout with resizable analysis panels."""
        dashboard = QWidget()
        root = QVBoxLayout(dashboard)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        root.addWidget(self.create_hero())

        title = QLabel("Dashboard")
        title.setFont(QFont(FONTS["serif"], 22, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        root.addWidget(title)

        root.addWidget(self.create_kpi_strip())

        vertical_split = QSplitter(Qt.Orientation.Vertical)
        vertical_split.setChildrenCollapsible(True)

        top_row = QSplitter(Qt.Orientation.Horizontal)
        top_row.setChildrenCollapsible(True)
        self._panel_matcher = self.create_matcher_tab()
        self._panel_ai = self.create_ai_panel()
        top_row.addWidget(self._panel_matcher)
        top_row.addWidget(self._panel_ai)
        top_row.setSizes([760, 500])
        top_row.setStretchFactor(0, 3)
        top_row.setStretchFactor(1, 2)
        self._top_splitter = top_row

        bottom_row = QSplitter(Qt.Orientation.Horizontal)
        bottom_row.setChildrenCollapsible(True)
        self._panel_results = self.create_results_tab()
        self._panel_dfa = self.create_dfa_tab()
        bottom_row.addWidget(self._panel_results)
        bottom_row.addWidget(self._panel_dfa)
        bottom_row.setSizes([760, 500])
        bottom_row.setStretchFactor(0, 3)
        bottom_row.setStretchFactor(1, 2)

        vertical_split.addWidget(top_row)
        vertical_split.addWidget(bottom_row)
        vertical_split.setSizes([430, 350])

        root.addWidget(vertical_split, 1)
        return dashboard

    def create_kpi_strip(self):
        """Top KPI row for quick-glance dashboard metrics."""
        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card_meta = {
            "Matches": ("●", COLORS["accent"], "MATCHES"),
            "Density": ("◌", COLORS["gold"], "RATE"),
            "DFA States": ("▣", COLORS["violet"], "DFA"),
            "Genome Length": ("▦", COLORS["green"], "GENOME"),
        }
        for key in ["Matches", "Density", "DFA States", "Genome Length"]:
            card = QWidget()
            card.setStyleSheet(
                f"background: {COLORS['bg-secondary']}; border: 1px solid {COLORS['border-light']}; border-radius: 14px;"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(4)

            icon_text, icon_color, tag_text = card_meta[key]
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(6)
            icon = QLabel(icon_text)
            icon.setFont(QFont(FONTS["mono"], 11, QFont.Weight.Bold))
            icon.setStyleSheet(f"color: {icon_color};")
            header_row.addWidget(icon)
            tag = QLabel(tag_text)
            tag.setFont(QFont(FONTS["mono"], 8, QFont.Weight.Bold))
            tag.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 1px;")
            header_row.addWidget(tag)
            header_row.addStretch()
            card_layout.addLayout(header_row)

            val = QLabel("—")
            val.setFont(QFont(FONTS["mono"], 22, QFont.Weight.Bold))
            val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet(f"color: {icon_color}; padding: 2px 0;")
            card_layout.addWidget(val)

            lbl = QLabel(key.upper())
            lbl.setFont(QFont(FONTS["sans"], 10, QFont.Weight.DemiBold))
            lbl.setStyleSheet(f"color: {COLORS['text-secondary']}; letter-spacing: 0.6px;")
            card_layout.addWidget(lbl)

            layout.addWidget(card, 1)
            self._kpi_labels[key] = val

        return strip

    def create_ai_panel(self):
        """Wrap the AI section in a collapsible dashboard panel."""
        panel = QWidget()
        panel.setStyleSheet(
            f"background: {COLORS['bg-secondary']}; border: 1px solid {COLORS['border-light']}; border-radius: 10px;"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header_label = QLabel("AI Assistant")
        header_label.setFont(QFont(FONTS["sans"], 12, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {COLORS['text-primary']};")
        header.addWidget(header_label)
        header.addStretch()

        self._ai_toggle_btn = QPushButton("Hide")
        self._ai_toggle_btn.setCheckable(True)
        self._ai_toggle_btn.setFixedHeight(30)
        self._ai_toggle_btn.clicked.connect(self.toggle_ai_panel)
        self._ai_toggle_btn.setStyleSheet(
            f"background: {COLORS['bg']}; color: {COLORS['text-primary']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 4px 10px;"
        )
        header.addWidget(self._ai_toggle_btn)
        layout.addLayout(header)

        self._ai_panel_body = self.create_ai_chat_tab()
        layout.addWidget(self._ai_panel_body, 1)
        return panel

    def toggle_ai_panel(self):
        """Collapse or expand the AI panel while preserving dashboard usability."""
        self._ai_panel_collapsed = not self._ai_panel_collapsed
        if self._ai_panel_body is not None:
            self._ai_panel_body.setVisible(not self._ai_panel_collapsed)
        if self._ai_toggle_btn is not None:
            self._ai_toggle_btn.setText("Show" if self._ai_panel_collapsed else "Hide")
        if self._top_splitter is not None:
            total = max(1, self._top_splitter.width())
            if self._ai_panel_collapsed:
                self._top_splitter.setSizes([int(total * 0.86), int(total * 0.14)])
            else:
                self._top_splitter.setSizes([int(total * 0.60), int(total * 0.40)])

    def create_ai_chat_tab(self):
        """Gemini assistant chat tab."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel("Gemini AI Assistant")
        title.setFont(QFont(FONTS["serif"], 18, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(title)

        subtitle = QLabel("Ask about DNA matching, DFA interpretation, or suggest a pattern from plain language.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {COLORS['text-secondary']};")
        layout.addWidget(subtitle)

        self.ai_status = QLabel()
        self.ai_status.setStyleSheet(f"color: {COLORS['text-secondary']}; font-size: 12px;")
        layout.addWidget(self.ai_status)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(170)
        self.chat_history.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['card']};
                border: 1px solid {COLORS['border-card']};
                border-radius: 8px;
                padding: 10px;
                color: {COLORS['text-primary']};
            }}
        """)
        layout.addWidget(self.chat_history)

        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Ask Gemini something about your DNA analysis...")
        self.chat_input.setMinimumHeight(74)
        self.chat_input.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['card']};
                border: 1px solid {COLORS['border-card']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {COLORS['text-primary']};
            }}
            QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        layout.addWidget(self.chat_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.send_chat_btn = QPushButton("Send to Gemini")
        self.send_chat_btn.setMinimumHeight(42)
        self.send_chat_btn.clicked.connect(self.send_chat_message)
        self.send_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #0052a3;
            }}
            QPushButton:disabled {{
                background: {COLORS['border']};
                color: {COLORS['text-tertiary']};
            }}
        """)
        btn_row.addWidget(self.send_chat_btn)

        self.extract_pattern_btn = QPushButton("Extract Pattern")
        self.extract_pattern_btn.setMinimumHeight(42)
        self.extract_pattern_btn.clicked.connect(self.suggest_pattern_from_chat)
        self.extract_pattern_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg']};
                color: {COLORS['text-primary']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['border-light']};
            }}
            QPushButton:disabled {{
                color: {COLORS['text-tertiary']};
            }}
        """)
        btn_row.addWidget(self.extract_pattern_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._append_chat_message(
            "assistant",
            "Hi, I am your GeneFlow AI assistant. Ask me to explain results or suggest a DNA pattern.",
        )

        if HAS_AI:
            self.ai_status.setText("Gemini ready. Uses GOOGLE_API_KEY from your environment.")
        else:
            self.ai_status.setText("Gemini SDK not installed. Install: pip install google-generativeai")
            self.send_chat_btn.setEnabled(False)
            self.extract_pattern_btn.setEnabled(False)

        layout.addStretch()
        container.setLayout(layout)
        return container
    
    def create_matcher_tab(self):
        """Matcher input tab"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)
        
        # Pattern input
        pattern_label = QLabel("DNA Pattern")
        pattern_label.setFont(QFont(FONTS["serif"], 14, QFont.Weight.DemiBold))
        pattern_label.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(pattern_label)
        
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("e.g., ATCGATCG")
        self.pattern_input.setMinimumHeight(40)
        self.pattern_input.setFont(QFont("Courier New", 11))
        self.pattern_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg-secondary']};
                border: 2px solid {COLORS['border-light']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {COLORS['text-primary']};
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        layout.addWidget(self.pattern_input)
        
        # Genome input
        genome_label = QLabel("Genome Sequence")
        genome_label.setFont(QFont(FONTS["serif"], 14, QFont.Weight.DemiBold))
        genome_label.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(genome_label)
        
        self.genome_input = QTextEdit()
        self.genome_input.setPlaceholderText("Paste genome sequence (FASTA or raw)...")
        self.genome_input.setMinimumHeight(130)
        self.genome_input.setFont(QFont("Courier New", 10))
        self.genome_input.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['card']};
                border: 1px solid {COLORS['border-card']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {COLORS['text-primary']};
            }}
            QTextEdit:focus {{
                border: 1px solid {COLORS['accent']};
            }}
        """)
        layout.addWidget(self.genome_input)

        example_row = QHBoxLayout()
        example_row.setSpacing(10)
        ex_label = QLabel("Example Genome")
        ex_label.setStyleSheet(f"color: {COLORS['text-secondary']};")
        example_row.addWidget(ex_label)
        self.example_selector = QComboBox()
        self.example_selector.addItems(self._example_genomes.keys())
        self.example_selector.setMinimumWidth(170)
        example_row.addWidget(self.example_selector)
        self.example_btn = QPushButton("Load Example Genome")
        self.example_btn.clicked.connect(self.load_example_genome)
        example_row.addWidget(self.example_btn)
        example_row.addStretch()
        layout.addLayout(example_row)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.run_btn = QPushButton("▶ Run Analysis")
        self.run_btn.setFont(QFont(FONTS["mono"], 11, QFont.Weight.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.clicked.connect(self.run_matcher)
        self.run_btn.setStyleSheet(self._primary_button_style())
        btn_layout.addWidget(self.run_btn)
        
        self.load_btn = QPushButton("📂 Load FASTA")
        self.load_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.load_btn.setMinimumHeight(44)
        self.load_btn.clicked.connect(self.load_fasta)
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg']};
                color: {COLORS['text-primary']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['border-light']};
            }}
        """)
        btn_layout.addWidget(self.load_btn)
        
        self.clear_btn = QPushButton("🔄 Clear")
        self.clear_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.clear_btn.setMinimumHeight(44)
        self.clear_btn.clicked.connect(self.clear_all)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg']};
                color: {COLORS['text-primary']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['border-light']};
            }}
        """)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)

        playback_row = QHBoxLayout()
        playback_row.setSpacing(10)
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.start_playback)
        playback_row.addWidget(self.play_btn)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_playback)
        playback_row.addWidget(self.pause_btn)
        self.step_btn = QPushButton("Step")
        self.step_btn.clicked.connect(self.step_forward)
        playback_row.addWidget(self.step_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_playback)
        playback_row.addWidget(self.reset_btn)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Slow", "Normal", "Fast"])
        self.speed_combo.setCurrentText("Normal")
        self.speed_combo.currentTextChanged.connect(self._set_playback_speed)
        playback_row.addWidget(self.speed_combo)
        playback_row.addStretch()
        layout.addLayout(playback_row)

        export_row = QHBoxLayout()
        export_row.setSpacing(10)
        export_label = QLabel("Export Format")
        export_label.setStyleSheet(f"color: {COLORS['text-secondary']};")
        export_row.addWidget(export_label)
        self._export_format_combo = QComboBox()
        self._export_format_combo.addItems(["CSV Report", "JSON Report", "Text Summary", "HTML Report", "PNG Snapshot"])
        export_row.addWidget(self._export_format_combo)
        self._export_btn = QPushButton("Export Data")
        self._export_btn.clicked.connect(self.export_results)
        export_row.addWidget(self._export_btn)
        export_row.addStretch()
        layout.addLayout(export_row)

        self._scan_status = QLabel("Run analysis to start live genome scan.")
        self._scan_status.setStyleSheet(f"color: {COLORS['text-secondary']};")
        layout.addWidget(self._scan_status)

        self._scan_progress = QProgressBar()
        self._scan_progress.setRange(0, 100)
        self._scan_progress.setValue(0)
        layout.addWidget(self._scan_progress)

        layout.addStretch()
        
        container.setLayout(layout)
        return container
    
    def create_dfa_tab(self):
        """DFA visualization tab"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        
        title = QLabel("DFA Transition Table")
        title.setFont(QFont(FONTS["sans"], 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._dfa_search_input = QLineEdit()
        self._dfa_search_input.setPlaceholderText("Search state or transition...")
        self._dfa_search_input.setFixedHeight(30)
        self._dfa_search_input.textChanged.connect(self.apply_dfa_table_filters)
        controls.addWidget(self._dfa_search_input, 1)

        self._dfa_base_filter = QComboBox()
        self._dfa_base_filter.addItems(["All Bases", "A", "T", "C", "G"])
        self._dfa_base_filter.setFixedHeight(30)
        self._dfa_base_filter.currentTextChanged.connect(self.apply_dfa_table_filters)
        controls.addWidget(self._dfa_base_filter)

        self._dfa_accept_only = QCheckBox("Accept-related")
        self._dfa_accept_only.setStyleSheet(f"color: {COLORS['text-secondary']};")
        self._dfa_accept_only.toggled.connect(self.apply_dfa_table_filters)
        controls.addWidget(self._dfa_accept_only)

        clear_filters = QPushButton("Reset")
        clear_filters.setFixedHeight(30)
        clear_filters.clicked.connect(self.reset_dfa_filters)
        controls.addWidget(clear_filters)

        layout.addLayout(controls)
        
        self.dfa_table_widget = QTableWidget()
        self.dfa_table_widget.setMinimumHeight(220)
        self.dfa_table_widget.verticalHeader().setDefaultSectionSize(28)
        self.dfa_table_widget.setStyleSheet(f"""
            QTableWidget {{
                background: {COLORS['bg-secondary']};
                border: 1px solid {COLORS['border-light']};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background: {COLORS['bg']};
                color: {COLORS['text-primary']};
                padding: 6px;
                border: none;
                border-bottom: 2px solid {COLORS['border']};
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {COLORS['border-light']};
            }}
            QTableWidget::item:selected {{
                background: {COLORS['accent-soft']};
            }}
        """)
        layout.addWidget(self.dfa_table_widget)
        
        layout.addStretch()
        container.setLayout(layout)
        return container
    
    def create_results_tab(self):
        """Results display tab"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)
        
        title = QLabel("Analysis Results")
        title.setFont(QFont(FONTS["serif"], 18, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(title)
        
        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.stat_labels = {}
        for stat_name in ["Matches", "Density", "DFA States", "Genome Length"]:
            stat_widget = self.create_stat_card(stat_name)
            stats_layout.addWidget(stat_widget)
            self.stat_labels[stat_name] = stat_widget.findChild(QLabel, f"{stat_name}_value")
        
        layout.addLayout(stats_layout)

        timeline_title = QLabel("Live Genome Scan")
        timeline_title.setFont(QFont(FONTS["serif"], 14, QFont.Weight.DemiBold))
        timeline_title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(timeline_title)

        self._timeline_widget = GenomeTimelineWidget()
        layout.addWidget(self._timeline_widget)

        plot_title = QLabel("Match Distribution")
        plot_title.setFont(QFont(FONTS["serif"], 14, QFont.Weight.DemiBold))
        plot_title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(plot_title)

        self._match_plot_widget = MatchPlotWidget()
        self._match_plot_widget.setMinimumHeight(210)
        layout.addWidget(self._match_plot_widget)
        
        # Genome display
        genome_title = QLabel("Genome with Matches")
        genome_title.setFont(QFont(FONTS["serif"], 14, QFont.Weight.DemiBold))
        genome_title.setStyleSheet(f"color: {COLORS['text-primary']};")
        layout.addWidget(genome_title)
        
        self.genome_display = QTextEdit()
        self.genome_display.setReadOnly(True)
        self.genome_display.setFont(QFont("Courier New", 9))
        self.genome_display.setMinimumHeight(110)
        self.genome_display.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['card']};
                border: 1px solid {COLORS['border-card']};
                border-radius: 8px;
                padding: 8px;
                color: {COLORS['text-secondary']};
            }}
        """)
        layout.addWidget(self.genome_display)
        
        layout.addStretch()
        container.setLayout(layout)
        return container
    
    def create_stat_card(self, label):
        """Create a statistics card widget"""
        widget = QWidget()
        widget.setObjectName("statCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        icon_map = {
            "Matches": ("●", COLORS["accent"]),
            "Density": ("◌", COLORS["gold"]),
            "DFA States": ("▣", COLORS["violet"]),
            "Genome Length": ("▦", COLORS["green"]),
        }
        icon_text, icon_color = icon_map.get(label, ("●", COLORS["accent"]))

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)
        icon = QLabel(icon_text)
        icon.setFont(QFont(FONTS["mono"], 11, QFont.Weight.Bold))
        icon.setStyleSheet(f"color: {icon_color};")
        top_row.addWidget(icon)
        hint = QLabel(label.upper())
        hint.setFont(QFont(FONTS["mono"], 8, QFont.Weight.Bold))
        hint.setStyleSheet(f"color: {COLORS['text-tertiary']}; letter-spacing: 1px;")
        top_row.addWidget(hint)
        top_row.addStretch()
        layout.addLayout(top_row)
        
        value_label = QLabel("—")
        value_label.setObjectName(f"{label}_value")
        value_label.setFont(QFont(FONTS["mono"], 24, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {icon_color}; padding: 2px 0;")
        layout.addWidget(value_label)
        
        label_widget = QLabel(label)
        label_widget.setFont(QFont(FONTS["sans"], 10, QFont.Weight.DemiBold))
        label_widget.setStyleSheet(f"color: {COLORS['text-secondary']}; letter-spacing: 0.4px;")
        layout.addWidget(label_widget)
        
        widget.setLayout(layout)
        widget.setStyleSheet(f"""
            QWidget#statCard {{
                background: {COLORS['bg-secondary']};
                border: 1px solid {COLORS['border-light']};
                border-radius: 14px;
            }}
        """)
        return widget
    
    def create_footer(self):
        """Footer"""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(40, 20, 40, 20)
        
        footer_text = QLabel("GeneFlow v2.0 — Advanced DNA Pattern Matching using Finite Automata Theory")
        footer_text.setFont(QFont("Arial", 10))
        footer_text.setStyleSheet(f"color: {COLORS['text-secondary']};")
        footer_layout.addWidget(footer_text)
        
        footer_layout.addStretch()
        
        wrapper = QWidget()
        wrapper.setLayout(footer_layout)
        wrapper.setStyleSheet(f"border-top: 1px solid {COLORS['border-light']};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(wrapper)
        return layout
    
    def run_matcher(self):
        """Run the pattern matcher"""
        pattern = self.pattern_input.text().upper().strip()
        genome = "".join(ch for ch in self.genome_input.toPlainText().upper() if ch in {"A", "T", "C", "G"})
        if hasattr(self, "genome_source_input") and not self.genome_source_input.text().strip():
            self.genome_source_input.setText("pasted sequence")
        
        if not pattern or not genome:
            print("Please enter both pattern and genome")
            return
        
        try:
            delta, accept_state = get_transition_table(pattern)
            pattern_len = len(pattern)
            matches = find_matches(genome, delta, accept_state, pattern_len)
            trace = trace_dfa(genome, delta, accept_state, pattern_len)
            
            self.pattern = pattern
            self.genome = genome
            self.matches = matches
            self.dfa_table = delta
            self._accept_state = accept_state
            self._trace = trace
            self._step_index = -1
            self.pause_playback()
            
            self.display_results()
            self.reset_playback()
            self._record_session()
            print(f"✓ Found {len(matches)} matches")
        except Exception as e:
            print(f"Error: {e}")
    
    def display_results(self):
        """Display analysis results"""
        if not self.pattern or not self.genome:
            return
        
        # Update stats
        match_count = len(self.matches)
        density = (match_count / len(self.genome) * 100)
        self._set_metric_values(match_count, density)
        self._update_status_bar()
        
        if self._state_diagram is not None:
            self._state_diagram.render_dfa(self.pattern, self.dfa_table, self._accept_state)
        if self._timeline_widget is not None:
            self._timeline_widget.set_data(self.genome, self.matches, len(self.pattern))
        if self._match_plot_widget is not None:
            self._match_plot_widget.plot_matches(self.matches, len(self.genome), len(self.pattern))

        if hasattr(self, "pattern_info_badge"):
            self.pattern_info_badge.setText(f'P = "{self.pattern}"')
        if hasattr(self, "range_info_badge"):
            self.range_info_badge.setText(f'T[0..{max(0, len(self.genome) - 1)}]')

        if hasattr(self, "match_positions_view"):
            if self.matches:
                self.match_positions_view.setText("  ".join(f"pos {m}" for m in self.matches))
            else:
                self.match_positions_view.setText("No matches found.")

        # Update genome display
        self.display_genome()
        
        # Update DFA table
        self.display_dfa_table()

    def _set_metric_values(self, match_count: int, density: float):
        if "Matches" in self.stat_labels:
            self.stat_labels["Matches"].setText(str(match_count))
        if "Density" in self.stat_labels:
            self.stat_labels["Density"].setText(f"{density:.1f}%")
        if "DFA States" in self.stat_labels:
            self.stat_labels["DFA States"].setText(str(len(self.pattern) + 1))
        if "Genome Length" in self.stat_labels:
            self.stat_labels["Genome Length"].setText(str(len(self.genome)))

    def _update_status_bar(self):
        if self._status_left is not None:
            if not self.pattern or not self.genome:
                self._status_left.setText("Input missing - load a pattern and genome")
                self._status_left.setStyleSheet(f"color: {COLORS['error']}; font-family: '{FONTS['mono']}'; font-size: 10px; font-weight: 700;")
            elif self._step_index >= 0 and self._step_index < len(self._trace):
                self._status_left.setText("Scanning in progress")
                self._status_left.setStyleSheet(f"color: {COLORS['warning']}; font-family: '{FONTS['mono']}'; font-size: 10px; font-weight: 700;")
            else:
                self._status_left.setText("Ready - DFA scanning active")
                self._status_left.setStyleSheet(f"color: {COLORS['success']}; font-family: '{FONTS['mono']}'; font-size: 10px; font-weight: 700;")
        if self._status_center is not None:
            self._status_center.setText(f'Pattern: "{self.pattern}" | {len(self.pattern) + 1} states | Genome: {len(self.genome)} bp')
        if self._status_right is not None:
            self._status_right.setText(f"pos {self.current_scan_position()} / {len(self.genome) if self.genome else 0}")

    def current_scan_position(self):
        if self._step_index < 0:
            return 0
        if self._step_index >= len(self._trace):
            return len(self.genome)
        return self._trace[self._step_index]["index"] + 1

    def _record_session(self):
        entry = {
            "pattern": self.pattern,
            "matches": len(self.matches),
            "density": f"{(len(self.matches) / len(self.genome) * 100):.1f}%" if self.genome else "0%",
            "states": len(self.pattern) + 1,
            "genome_length": len(self.genome),
        }
        self.session_history.insert(0, entry)
        self.session_history = self.session_history[:5]
        self._refresh_history_view()

    def _refresh_history_view(self):
        if self._history_text is None:
            return
        lines = []
        if not self.session_history:
            lines.append("No sessions yet.")
        for index, item in enumerate(self.session_history, start=1):
            lines.append(
                f"{index}. {item['pattern']} | {item['matches']} matches | {item['density']} | {item['states']} states | {item['genome_length']} bp"
            )
        self._history_text.setPlainText("\n".join(lines))
    
    def display_genome(self):
        """Display genome with match highlights"""
        current_genome_index = -1
        if 0 <= self._step_index < len(self._trace):
            current_genome_index = self._trace[self._step_index]["index"]
        elif self._step_index >= len(self._trace) and self._trace:
            current_genome_index = self._trace[-1]["index"]

        html = (
            '<html><body style="font-family: Courier New; font-size: 13px; line-height: 1.8; '
            f'background: {COLORS["bg"]}; color: {COLORS["text-primary"]}; padding: 8px;">'
        )
        
        match_pos = set()
        for m in self.matches:
            for i in range(m - 1, min(m - 1 + len(self.pattern), len(self.genome))):
                match_pos.add(i)
        
        base_colors = {'A': '#ef4444', 'T': '#f59e0b', 'C': '#0066cc', 'G': '#8b5cf6'}
        
        for i, base in enumerate(self.genome):
            if i == current_genome_index:
                html += f'<span style="background: {COLORS["warning"]}; color: {COLORS["bg"]}; padding: 0 2px; border-radius: 2px; font-weight: bold;">{base}</span>'
            elif i in match_pos:
                html += f'<span style="background: {COLORS["accent-soft"]}; padding: 0 2px; border-radius: 2px; font-weight: bold;">{base}</span>'
            else:
                color = base_colors.get(base, COLORS['text-secondary'])
                html += f'<span style="color: {color};">{base}</span>'
            
            if (i + 1) % 60 == 0:
                html += '<br/>'
        
        html += '</body></html>'
        self.genome_display.setHtml(html)
    
    def display_dfa_table(self):
        """Display DFA transition table"""
        bases = ['A', 'T', 'C', 'G']
        items = self.get_filtered_dfa_rows()
        self.dfa_table_widget.setColumnCount(len(bases) + 1)
        self.dfa_table_widget.setHorizontalHeaderLabels(['State'] + bases)
        self.dfa_table_widget.setRowCount(len(items))
        
        for row, (state, trans) in enumerate(items):
            # State column
            item = QTableWidgetItem(str(state))
            item.setFont(QFont("Courier New", 12))
            if state == self.current_state():
                item.setBackground(QColor(COLORS["accent-soft"]))
            self.dfa_table_widget.setItem(row, 0, item)
            
            # Transition columns
            for col, base in enumerate(bases):
                next_state = trans.get(base, 0)
                item = QTableWidgetItem(str(next_state))
                item.setFont(QFont("Courier New", 12))
                if next_state == len(self.pattern):
                    item.setForeground(QColor(COLORS['success']))
                if state == self.current_state():
                    item.setBackground(QColor(COLORS["accent-soft"]))
                self.dfa_table_widget.setItem(row, col + 1, item)

    def current_state(self):
        if self._step_index < 0:
            return 0
        if self._step_index >= len(self._trace):
            return self._trace[-1]["next_state"] if self._trace else 0
        return self._trace[self._step_index]["next_state"]

    def render_state_diagram(self):
        if self._state_diagram is None:
            return
        if not self.pattern:
            self._state_diagram.clear_diagram()
            if self._state_meta is not None:
                self._state_meta.setText("Live State: q0")
            return

        curr = self.current_state()
        prev = 0
        ch = "-"
        if 0 <= self._step_index < len(self._trace):
            prev = self._trace[self._step_index]["prev_state"]
            ch = self._trace[self._step_index]["char"]

        nodes = []
        for state in range(len(self.pattern) + 1):
            if state == curr:
                nodes.append(
                    f"<span style='background:{COLORS['accent']};color:{COLORS['bg']};padding:2px 7px;border-radius:10px;'>q{state}</span>"
                )
            elif state == self._accept_state:
                nodes.append(
                    f"<span style='color:{COLORS['success']};border:1px solid {COLORS['success']};padding:2px 6px;border-radius:10px;'>q{state}</span>"
                )
            else:
                nodes.append(f"<span style='color:{COLORS['text-secondary']};'>q{state}</span>")

        self._state_diagram.highlight_state(curr, f"Live State: q{curr} | Last transition: q{prev} --{ch}--> q{curr}")
        if self._state_meta is not None:
            self._state_meta.setText(f"Live State: q{curr} | Last transition: q{prev} --{ch}--> q{curr}")

    def _set_playback_speed(self, speed: str):
        delay = {"Slow": 700, "Normal": 350, "Fast": 120}.get(speed, 350)
        self._play_timer.setInterval(delay)

    def start_playback(self):
        if not self._trace:
            return
        self._set_playback_speed(self.speed_combo.currentText() if self.speed_combo else "Normal")
        if self._step_index >= len(self._trace) - 1:
            self._step_index = -1
        self._play_timer.start()

    def pause_playback(self):
        self._play_timer.stop()

    def _advance_playback(self):
        if self._step_index >= len(self._trace) - 1:
            self.pause_playback()
            return
        self.step_forward()

    def step_forward(self):
        if not self._trace:
            return
        self._step_index = min(self._step_index + 1, len(self._trace) - 1)
        self._refresh_live_scan()

    def reset_playback(self):
        self.pause_playback()
        self._step_index = -1
        self._refresh_live_scan()

    def _refresh_live_scan(self):
        if not self.genome:
            return
        if self._step_index < 0:
            if self._scan_status is not None:
                self._scan_status.setText("Ready: press Play to run genome scan through DFA states.")
            if self._scan_progress is not None:
                self._scan_progress.setValue(0)
            if self._timeline_widget is not None:
                self._timeline_widget.set_current_index(-1)
            if self._live_genome_reader is not None:
                self._live_genome_reader.set_data(self.genome, -1)
        else:
            step = self._trace[self._step_index]
            if self._scan_status is not None:
                self._scan_status.setText(
                    f"Index {step['index'] + 1}/{len(self.genome)} | Base {step['char']} | q{step['prev_state']} -> q{step['next_state']}"
                )
            if self._scan_progress is not None:
                pct = int(((step['index'] + 1) / max(1, len(self.genome))) * 100)
                self._scan_progress.setValue(pct)
            if self._timeline_widget is not None:
                self._timeline_widget.set_current_index(step["index"])
            if self._live_genome_reader is not None:
                self._live_genome_reader.set_data(self.genome, step["index"])

        self.render_state_diagram()
        self.display_genome()
        self.display_dfa_table()

    def get_filtered_dfa_rows(self):
        """Apply compact table filters to DFA rows."""
        rows = list(self.dfa_table.items())
        if not rows:
            return rows

        query = self._dfa_search_input.text().strip().lower() if self._dfa_search_input else ""
        selected_base = self._dfa_base_filter.currentText() if self._dfa_base_filter else "All Bases"
        accept_only = self._dfa_accept_only.isChecked() if self._dfa_accept_only else False
        accept_state = len(self.pattern)

        filtered = []
        for state, trans in rows:
            if accept_only:
                has_accept_transition = any(next_state == accept_state for next_state in trans.values())
                if state != accept_state and not has_accept_transition:
                    continue

            if selected_base != "All Bases" and selected_base in trans:
                state_text = f"{state} {selected_base}->{trans[selected_base]}"
            else:
                transitions = " ".join(f"{base}->{next_state}" for base, next_state in trans.items())
                state_text = f"{state} {transitions}"

            if query and query not in state_text.lower():
                continue
            filtered.append((state, trans))

        return filtered

    def apply_dfa_table_filters(self):
        if self.dfa_table:
            self.display_dfa_table()

    def reset_dfa_filters(self):
        if self._dfa_search_input is not None:
            self._dfa_search_input.clear()
        if self._dfa_base_filter is not None:
            self._dfa_base_filter.setCurrentIndex(0)
        if self._dfa_accept_only is not None:
            self._dfa_accept_only.setChecked(False)
        if self.dfa_table:
            self.display_dfa_table()
    
    def load_fasta(self):
        """Load FASTA file"""
        if not HAS_BIO:
            print("BioPython not installed")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(self, "Load FASTA", "", "FASTA Files (*.fasta *.fa)")
        
        if filename:
            try:
                seqs = []
                for record in SeqIO.parse(filename, "fasta"):
                    seqs.append(str(record.seq).upper())
                self.genome_input.setText("".join(seqs))
                if hasattr(self, "genome_source_input"):
                    self.genome_source_input.setText(Path(filename).name)
            except Exception as e:
                print(f"Error loading FASTA: {e}")

    def load_example_genome(self):
        name = self.example_selector.currentText() if hasattr(self, "example_selector") else ""
        genome = self._example_genomes.get(name, "")
        if genome:
            self.genome_input.setPlainText(genome)
            if hasattr(self, "genome_source_input"):
                self.genome_source_input.setText(f"example:{name}")

    def focus_run_controls(self):
        if hasattr(self, "pattern_input"):
            self.pattern_input.setFocus()

    def export_results(self):
        if not self.pattern or not self.genome:
            QMessageBox.information(self, "Nothing to export", "Run an analysis before exporting results.")
            return

        selected = self._export_format_combo.currentText() if self._export_format_combo is not None else "JSON Report"
        filter_map = {
            "CSV Report": "CSV Files (*.csv)",
            "JSON Report": "JSON Files (*.json)",
            "Text Summary": "Text Files (*.txt)",
            "HTML Report": "HTML Files (*.html)",
            "PNG Snapshot": "PNG Images (*.png)",
            "PDF Report": "PDF Files (*.pdf)",
        }
        default_suffix = {
            "CSV Report": ".csv",
            "JSON Report": ".json",
            "Text Summary": ".txt",
            "HTML Report": ".html",
            "PNG Snapshot": ".png",
            "PDF Report": ".pdf",
        }[selected]
        file_path, _ = QFileDialog.getSaveFileName(self, "Export GeneFlow Results", f"geneflow_report{default_suffix}", filter_map[selected])
        if not file_path:
            return

        try:
            if selected == "CSV Report":
                self._export_csv(file_path)
            elif selected == "JSON Report":
                self._export_json(file_path)
            elif selected == "Text Summary":
                self._export_text(file_path)
            elif selected == "HTML Report":
                self._export_html(file_path)
            elif selected == "PDF Report":
                self._export_pdf(file_path)
            else:
                self._export_png(file_path)
            QMessageBox.information(self, "Export complete", f"Saved report to:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _export_payload(self):
        return {
            "pattern": self.pattern,
            "genome_length": len(self.genome),
            "matches": self.matches,
            "dfa_states": len(self.dfa_table),
            "accept_state": self._accept_state,
            "transition_table": {str(state): trans for state, trans in self.dfa_table.items()},
            "trace_steps": self._trace,
        }

    def _export_csv(self, file_path: str):
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["metric", "value"])
            writer.writerow(["pattern", self.pattern])
            writer.writerow(["genome_length", len(self.genome)])
            writer.writerow(["match_count", len(self.matches)])
            writer.writerow(["dfa_states", len(self.dfa_table)])
            writer.writerow([])
            writer.writerow(["match_positions"])
            for position in self.matches:
                writer.writerow([position])
            writer.writerow([])
            writer.writerow(["state", "A", "T", "C", "G"])
            for state, trans in self.dfa_table.items():
                writer.writerow([state, trans.get("A", 0), trans.get("T", 0), trans.get("C", 0), trans.get("G", 0)])

    def _export_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(self._export_payload(), handle, indent=2)

    def _export_text(self, file_path: str):
        summary = [
            "GeneFlow DNA Pattern Matching Report",
            f"Pattern: {self.pattern}",
            f"Genome length: {len(self.genome)}",
            f"Match count: {len(self.matches)}",
            f"Matches: {', '.join(map(str, self.matches)) if self.matches else 'None'}",
            f"DFA states: {len(self.dfa_table)}",
            "",
            "Transition table:",
        ]
        for state, trans in self.dfa_table.items():
            summary.append(f"q{state}: A->{trans.get('A', 0)} T->{trans.get('T', 0)} C->{trans.get('C', 0)} G->{trans.get('G', 0)}")
        Path(file_path).write_text("\n".join(summary), encoding="utf-8")

    def _export_html(self, file_path: str):
        rows = []
        for state, trans in self.dfa_table.items():
            rows.append(
                f"<tr><td>q{state}</td><td>{trans.get('A', 0)}</td><td>{trans.get('T', 0)}</td><td>{trans.get('C', 0)}</td><td>{trans.get('G', 0)}</td></tr>"
            )
        match_badges = ''.join(f"<span class='pill'>pos {m}</span>" for m in self.matches) if self.matches else '<p>No matches found.</p>'

        html_doc = f"""
        <html><head><meta charset='utf-8'><title>GeneFlow Report</title>
        <style>
        body {{ background:#070c16; color:#f1f6ff; font-family:Arial,sans-serif; padding:32px; }}
        .card {{ background:#111c31; border:1px solid #233552; border-radius:16px; padding:20px; margin-bottom:18px; }}
        table {{ width:100%; border-collapse:collapse; }}
        th, td {{ padding:8px 10px; border-bottom:1px solid #233552; text-align:left; }}
        .pill {{ display:inline-block; padding:4px 10px; border-radius:999px; margin:4px 6px 0 0; background:#16243b; border:1px solid #233552; }}
        </style></head><body>
        <div class='card'><h1>GeneFlow Report</h1><p>Pattern: {self.pattern}</p><p>Genome length: {len(self.genome)}</p><p>Match count: {len(self.matches)}</p></div>
        <div class='card'><h2>Matches</h2>{match_badges}</div>
        <div class='card'><h2>DFA Table</h2><table><tr><th>State</th><th>A</th><th>T</th><th>C</th><th>G</th></tr>{''.join(rows)}</table></div>
        </body></html>
        """
        Path(file_path).write_text(html_doc, encoding="utf-8")

    def _export_png(self, file_path: str):
        target = self._state_diagram if self._state_diagram is not None and self._state_diagram.isVisible() else self.app_shell
        self._render_widget_png(target, file_path)
    
    def clear_all(self):
        """Clear all inputs"""
        self.pattern_input.clear()
        self.genome_input.clear()
        if hasattr(self, "genome_source_input"):
            self.genome_source_input.clear()
        self.genome_display.clear()
        self.matches = []
        self.dfa_table = {}
        self._trace = []
        self._step_index = -1
        self.pause_playback()
        self.reset_dfa_filters()
        self.dfa_table_widget.setRowCount(0)
        if self._state_diagram is not None:
            self._state_diagram.clear_diagram()
        if self._state_meta is not None:
            self._state_meta.setText("Live State: q0")
        if self._scan_status is not None:
            self._scan_status.setText("Run analysis to start live genome scan.")
        if self._scan_progress is not None:
            self._scan_progress.setValue(0)
        for label in self.stat_labels.values():
            label.setText("—")
        self._update_status_bar()
        print("Cleared all inputs")

    def _append_chat_message(self, role: str, message: str):
        role_labels = {
            "assistant": "Gemini",
            "user": "You",
            "system": "System",
        }
        role_color = {
            "assistant": COLORS["accent"],
            "user": COLORS["text-primary"],
            "system": COLORS["text-secondary"],
        }
        label = role_labels.get(role, "System")
        color = role_color.get(role, COLORS["text-secondary"])
        safe_message = html.escape(message).replace("\n", "<br/>")
        self.chat_history.append(
            f'<div style="margin: 6px 0;"><b style="color:{color};">{label}:</b> {safe_message}</div>'
        )

    def _ensure_ai_handler(self) -> bool:
        if not HAS_AI:
            QMessageBox.warning(self, "Gemini Unavailable", "Install google-generativeai to enable AI chat.")
            return False
        if self._ai_handler is not None:
            return True
        try:
            self._ai_handler = AIQueryHandler()
            return True
        except Exception as exc:
            QMessageBox.warning(self, "Gemini Setup Error", str(exc))
            self.ai_status.setText("Gemini setup failed. Check GOOGLE_API_KEY and internet access.")
            return False

    def _ai_context(self) -> dict:
        return {
            "pattern": self.pattern or "not set",
            "genome_length": str(len(self.genome)) if self.genome else "0",
            "matches": str(len(self.matches)),
            "dfa_states": str(len(self.dfa_table)) if self.dfa_table else "0",
        }

    def _start_ai_worker(self, action: str, message: str):
        if self._ai_thread and self._ai_thread.isRunning():
            self.ai_status.setText("Gemini is still processing your previous request...")
            return

        self.send_chat_btn.setEnabled(False)
        self.extract_pattern_btn.setEnabled(False)
        self.ai_status.setText("Gemini is thinking...")

        self._ai_thread = AIWorker(self._ai_handler, action, message, self._ai_context())
        self._ai_thread.result_ready.connect(self._on_ai_result)
        self._ai_thread.start()

    def send_chat_message(self):
        message = self.chat_input.toPlainText().strip()
        if not message:
            QMessageBox.information(self, "Empty Message", "Type a message before sending to Gemini.")
            return
        if not self._ensure_ai_handler():
            return

        self._append_chat_message("user", message)
        self.chat_input.clear()
        self._start_ai_worker("chat", message)

    def suggest_pattern_from_chat(self):
        message = self.chat_input.toPlainText().strip()
        if not message:
            QMessageBox.information(self, "Empty Message", "Enter your natural language request first.")
            return
        if not self._ensure_ai_handler():
            return

        self._append_chat_message("user", f"Suggest DNA pattern from: {message}")
        self._start_ai_worker("extract", message)

    def _on_ai_result(self, action: str, success: bool, payload: str):
        self.send_chat_btn.setEnabled(HAS_AI)
        self.extract_pattern_btn.setEnabled(HAS_AI)

        if action == "extract":
            if success:
                self.pattern_input.setText(payload)
                self._append_chat_message("assistant", f"I extracted this DNA pattern: {payload}")
                self.ai_status.setText(f"Pattern updated to {payload}")
            else:
                self._append_chat_message("system", payload)
                self.ai_status.setText("Pattern extraction failed.")
            return

        if success:
            self._append_chat_message("assistant", payload)
            self.ai_status.setText("Gemini response received.")
        else:
            self._append_chat_message("system", payload)
            self.ai_status.setText("Gemini request failed.")
    
    def apply_styles(self):
        """Apply global styles"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {COLORS['bg']};
                color: {COLORS['text-primary']};
            }}
            QWidget {{
                background: {COLORS['bg']};
                font-family: '{FONTS['sans']}';
            }}
            QLineEdit, QTextEdit, QTableWidget {{
                font-family: '{FONTS['mono']}';
            }}
            QScrollArea {{
                border: none;
                background: {COLORS['bg']};
            }}
            QProgressBar {{
                background: {COLORS['bg-secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                text-align: center;
                color: {COLORS['text-primary']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 5px;
            }}
        """)

    def resizeEvent(self, event):
        """Adapt header visibility for smaller window widths to prevent clipping."""
        super().resizeEvent(event)
        width = self.width()

        show_nav = width >= 1240
        show_tags = width >= 1060
        show_tagline = width >= 980

        for label in self._nav_labels:
            label.setVisible(show_nav)
        if self._header_right_tag is not None:
            self._header_right_tag.setVisible(show_tags)
        if self._header_tagline is not None:
            self._header_tagline.setVisible(show_tagline)
    
    def create_icon(self):
        """Create window icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(COLORS['accent']))
        return QIcon(pixmap)

def main():
    app = QApplication(sys.argv)
    window = GeneFlowApp()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

