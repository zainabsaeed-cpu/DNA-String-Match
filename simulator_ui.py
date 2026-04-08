"""Professional PyQt6 DNA Finite-Automaton Simulator with Groq AI-powered suggestions."""

import sys
import math
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSlider, QSpacerItem, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Project imports
from dfa import get_transition_table
from matcher import find_matches, trace_dfa
from genome_loader import load_genome

try:
    from ai_insights import AIQueryHandler
    HAS_AI = True
except (ImportError, Exception):
    HAS_AI = False

# Color theme
BG, PANEL, CARD, BORDER = "#0D1117", "#161B22", "#21262D", "#30363D"
ACCENT, SUCCESS, CORAL, TEXT, MUTED = "#58A6FF", "#3FB950", "#F78166", "#E6EDF3", "#8B949E"

NUCLEOTIDE_COLORS = {"A": "#3FB950", "T": "#F78166", "C": "#58A6FF", "G": "#D2A8FF"}


class TimelineWidget(QWidget):
    """Horizontal genome timeline with colored nucleotides and match highlights."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._genome, self._matches, self._pattern_len = "", [], 0
        self._current_index, self._match_set = -1, set()
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, genome: str, matches: List[int], pattern_len: int):
        self._genome, self._matches, self._pattern_len = genome, matches, pattern_len
        self._match_set = {m - 1 + i for m in matches for i in range(pattern_len)}
        self._current_index = -1
        self.update()

    def set_current_index(self, idx: int):
        self._current_index = idx
        self.update()

    def paintEvent(self, event):
        if not self._genome:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, n = self.width(), self.height(), len(self._genome)
        cell_w = max(3, min(18, (w - 20) / max(n, 1)))
        offset_x = max(10, (w - cell_w * n) / 2)

        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawLine(int(offset_x), h - 8, int(offset_x + cell_w * n), h - 8)
        painter.setFont(QFont("JetBrains Mono", max(7, min(10, int(cell_w * 0.7)))))

        for i, ch in enumerate(self._genome):
            x = offset_x + i * cell_w
            if i in self._match_set:
                painter.fillRect(int(x), 2, int(cell_w), h - 12, QColor(SUCCESS + "30"))
            if i == self._current_index:
                painter.fillRect(int(x), 0, int(cell_w), h - 8, QColor(ACCENT + "55"))
                painter.setPen(QPen(QColor(ACCENT), 2))
                painter.drawRect(int(x), 0, int(cell_w), h - 10)
            painter.setPen(QPen(QColor(NUCLEOTIDE_COLORS.get(ch, MUTED))))
            if cell_w >= 10:
                painter.drawText(int(x), 4, int(cell_w), h - 16, Qt.AlignmentFlag.AlignCenter, ch)
            painter.setPen(QPen(QColor(BORDER), 1))
            if i % max(1, int(n / 20)) == 0:
                painter.drawLine(int(x), h - 10, int(x), h - 4)
        painter.end()


class FADiagramWidget(QWidget):
    """Custom-painted DFA graph with per-step active-state highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._pattern, self._delta, self._accept_state = "", {}, -1
        self._current_state, self._positions = -1, {}
        self._status_text, self._radius = "Run the matcher to generate a DFA diagram", 26

    def render_dfa(self, pattern: str, delta: Dict, accept_state: int):
        self._pattern, self._delta, self._accept_state = pattern, delta, accept_state
        self._current_state, self._status_text = 0, ""
        self._compute_layout()
        self.update()

    def highlight_state(self, state: int):
        self._current_state = state
        self.update()

    def clear_diagram(self):
        self._pattern, self._delta, self._accept_state = "", {}, -1
        self._current_state, self._positions = -1, {}
        self._status_text = "Run the matcher to generate a DFA diagram"
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._compute_layout()

    def _compute_layout(self):
        if not self._delta:
            self._positions = {}
            return
        n = len(self._delta)
        margin_x, y = 56, max(90, self.height() * 0.5)
        span = max(1, self.width() - margin_x * 2)
        step = min(110, max(70, span / max(1, n - 1)))
        start_x = max(margin_x, (self.width() - step * max(0, n - 1)) / 2)
        self._positions = {state: (start_x + state * step, y) for state in range(n)}

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._delta:
            painter.setPen(QColor(MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._status_text)
            return
        self._draw_edges(painter)
        self._draw_nodes(painter)

    def _draw_edges(self, painter: QPainter):
        edge_labels: Dict[tuple, List[str]] = {}
        for src, transitions in self._delta.items():
            for char, dst in transitions.items():
                edge_labels.setdefault((src, dst), []).append(char)

        for (src, dst), chars in edge_labels.items():
            sx, sy, dx, dy = self._positions[src][0], self._positions[src][1], \
                             self._positions[dst][0], self._positions[dst][1]
            label = ",".join(sorted(chars))

            if src == dst:
                loop_r = self._radius + 14
                rect_x, rect_y = sx - loop_r, sy - self._radius - loop_r - 6
                painter.setPen(QPen(QColor(MUTED), 2))
                painter.drawArc(int(rect_x), int(rect_y), int(loop_r * 2), int(loop_r * 2), 35 * 16, 290 * 16)
                painter.setPen(QColor(ACCENT))
                painter.drawText(int(sx - 22), int(rect_y - 2), 44, 18, Qt.AlignmentFlag.AlignCenter, label)
                continue

            color = QColor(SUCCESS if dst == src + 1 and src < self._accept_state else MUTED)
            painter.setPen(QPen(color, 2))
            direction = 1 if dx > sx else -1
            painter.drawLine(int(sx + direction * self._radius), int(sy), 
                           int(dx - direction * self._radius), int(dy))

            angle = math.atan2(dy - sy, (dx - direction * self._radius) - (sx + direction * self._radius))
            ah = 8
            for a_offset in [0.83, -0.83]:
                a = angle + math.pi * a_offset
                painter.drawLine(int(dx - direction * self._radius), int(dy),
                               int(dx - direction * self._radius + ah * math.cos(a)),
                               int(dy + ah * math.sin(a)))

            lx = (sx + direction * self._radius + dx - direction * self._radius) / 2
            ly = sy - 16 if abs(dx - sx) > 30 else sy + 24
            painter.setPen(QColor(ACCENT))
            painter.drawText(int(lx - 24), int(ly - 10), 48, 20, Qt.AlignmentFlag.AlignCenter, label)

        x0, y0 = self._positions[0]
        painter.setPen(QPen(QColor(ACCENT), 2))
        painter.drawLine(int(x0 - 44), int(y0), int(x0 - self._radius), int(y0))

    def _draw_nodes(self, painter: QPainter):
        font = QFont("JetBrains Mono", 10)
        font.setBold(True)
        painter.setFont(font)

        for state, (x, y) in self._positions.items():
            fill, pen = QColor(CARD), QPen(QColor(BORDER), 2)
            if state == self._accept_state:
                fill, pen = QColor("#1D4F2B"), QPen(QColor(SUCCESS), 2)
            if state == self._current_state:
                fill, pen = QColor("#1F3A5A"), QPen(QColor(ACCENT), 3)

            painter.setBrush(QBrush(fill))
            painter.setPen(pen)
            painter.drawEllipse(int(x - self._radius), int(y - self._radius), 
                               self._radius * 2, self._radius * 2)

            if state == self._accept_state:
                painter.setPen(QPen(pen.color(), 2))
                inset = 6
                painter.drawEllipse(int(x - self._radius + inset), int(y - self._radius + inset),
                                  (self._radius - inset) * 2, (self._radius - inset) * 2)

            painter.setPen(QColor(TEXT))
            painter.drawText(int(x - 20), int(y - 10), 40, 20, Qt.AlignmentFlag.AlignCenter, f"q{state}")


class MatchVisualizationWidget(QWidget):
    """Matplotlib-based match position visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_MATPLOTLIB:
            self.figure = Figure(facecolor=BG, edgecolor="none")
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        else:
            lbl = QLabel("Matplotlib not installed.\nRun: pip install matplotlib")
            lbl.setStyleSheet(f"color: {MUTED}; text-align: center;")
            layout.addWidget(lbl)

    def plot_matches(self, matches: List[int], genome_len: int, pattern_len: int):
        if not HAS_MATPLOTLIB or not matches:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(PANEL)

        if not matches:
            ax.text(0.5, 0.5, "No matches found", ha="center", va="center",
                   transform=ax.transAxes, color=MUTED, fontsize=14)
        else:
            ax.bar(matches, [1] * len(matches), width=pattern_len * 0.8,
                  color=SUCCESS, edgecolor=ACCENT, linewidth=2, alpha=0.8)
            ax.set_xlim(0, genome_len)
            ax.set_ylim(0, 1.5)
            ax.set_xlabel("Genome Position", color=TEXT, fontweight="bold")
            ax.set_ylabel("Match", color=TEXT, fontweight="bold")
            ax.set_title(f"Match Positions ({len(matches)} total)",
                        color=TEXT, fontweight="bold", fontsize=12)

        ax.tick_params(colors=MUTED)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color(BORDER)

        self.figure.tight_layout()
        self.canvas.draw()


def _card(title: str) -> tuple:
    """Create a stat card."""
    frame = QFrame()
    frame.setObjectName("card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(4)
    lbl_title = QLabel(title)
    lbl_title.setObjectName("sectionHeader")
    lay.addWidget(lbl_title)
    lbl_value = QLabel("—")
    lbl_value.setObjectName("bigNumber")
    lay.addWidget(lbl_value)
    return frame, lay, lbl_value


class DNASimulatorWindow(QMainWindow):
    """Professional DNA FA Simulator with AI assistance."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DNA Pattern Matcher - Finite Automaton Theory")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 900)

        self._pattern, self._genome, self._delta = "", "", {}
        self._accept_state, self._trace, self._matches = 0, [], []
        self._step, self._playing = -1, False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        self._build_ui()
        self._setup_shortcuts()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("headerBar")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 8, 16, 8)
        hlay.setSpacing(12)

        title = QLabel("DNA Pattern Matcher")
        title.setObjectName("appTitle")
        hlay.addWidget(title)
        hlay.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Pattern
        lbl_pat = QLabel("Pattern")
        lbl_pat.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700;")
        hlay.addWidget(lbl_pat)
        self._inp_pattern = QLineEdit("ATCG")
        self._inp_pattern.setFixedWidth(140)
        self._inp_pattern.setPlaceholderText("e.g. ATCG")
        hlay.addWidget(self._inp_pattern)

        # AI Query (if available)
        if HAS_AI:
            lbl_ai = QLabel("AI Query")
            lbl_ai.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700;")
            hlay.addWidget(lbl_ai)
            self._inp_ai_query = QLineEdit()
            self._inp_ai_query.setPlaceholderText("e.g. 'find mutation patterns'")
            self._inp_ai_query.setFixedWidth(200)
            hlay.addWidget(self._inp_ai_query)

            self._btn_suggest = QPushButton("Suggest")
            self._btn_suggest.setToolTip("Use AI to extract pattern")
            self._btn_suggest.clicked.connect(self._ai_suggest_pattern)
            hlay.addWidget(self._btn_suggest)
            self._ai_handler = AIQueryHandler()
        else:
            self._inp_ai_query, self._btn_suggest, self._ai_handler = None, None, None

        # Genome
        lbl_gen = QLabel("Genome")
        lbl_gen.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700;")
        hlay.addWidget(lbl_gen)
        self._inp_genome = QLineEdit()
        self._inp_genome.setMinimumWidth(200)
        self._inp_genome.setPlaceholderText("Paste or load FASTA…")
        hlay.addWidget(self._inp_genome, stretch=1)

        self._btn_fasta = QPushButton("Load FASTA")
        self._btn_fasta.clicked.connect(self._load_fasta)
        hlay.addWidget(self._btn_fasta)

        self._btn_run = QPushButton("Run")
        self._btn_run.setObjectName("runButton")
        self._btn_run.clicked.connect(self._run)
        hlay.addWidget(self._btn_run)

        root.addWidget(header)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setObjectName("progressTop")
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        root.addWidget(self._progress)

        # Body
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)

        # Left - DFA + Timeline
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(12, 12, 6, 8)
        left_lay.setSpacing(10)

        fa_frame = QFrame()
        fa_frame.setObjectName("panel")
        fa_lay = QVBoxLayout(fa_frame)
        fa_lay.setContentsMargins(8, 6, 8, 6)
        fa_lbl = QLabel("DFA DIAGRAM")
        fa_lbl.setObjectName("sectionHeader")
        fa_lay.addWidget(fa_lbl)
        self._fa_widget = FADiagramWidget()
        self._fa_widget.setMinimumSize(300, 200)
        self._fa_scroll = QScrollArea()
        self._fa_scroll.setWidgetResizable(True)
        self._fa_scroll.setWidget(self._fa_widget)
        fa_lay.addWidget(self._fa_scroll, stretch=1)
        left_lay.addWidget(fa_frame, stretch=3)

        tl_frame = QFrame()
        tl_frame.setObjectName("panel")
        tl_lay = QVBoxLayout(tl_frame)
        tl_lay.setContentsMargins(8, 6, 8, 6)
        tl_lbl = QLabel("GENOME TIMELINE")
        tl_lbl.setObjectName("sectionHeader")
        tl_lay.addWidget(tl_lbl)
        self._timeline = TimelineWidget()
        tl_lay.addWidget(self._timeline)
        left_lay.addWidget(tl_frame, stretch=0)

        body.addWidget(left)

        # Right - Match visualization + Log
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(6, 12, 12, 8)
        right_lay.setSpacing(10)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        c1, _, self._lbl_step = _card("CURRENT STEP")
        c2, _, self._lbl_state = _card("DFA STATE")
        c3, _, self._lbl_matches = _card("MATCHES")
        self._lbl_matches.setObjectName("matchHit")
        stats_row.addWidget(c1)
        stats_row.addWidget(c2)
        stats_row.addWidget(c3)
        right_lay.addLayout(stats_row)

        # Info card
        info_frame = QFrame()
        info_frame.setObjectName("card")
        info_lay = QHBoxLayout(info_frame)
        info_lay.setContentsMargins(14, 10, 14, 10)
        info_lay.setSpacing(24)
        self._stat_labels: Dict[str, QLabel] = {}
        for key in ("Pattern", "Genome Len", "DFA States", "Match %"):
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl_k = QLabel(key.upper())
            lbl_k.setStyleSheet(f"color:{MUTED}; font-size:10px; font-weight:700;")
            lbl_v = QLabel("—")
            lbl_v.setStyleSheet(f"color:{TEXT}; font-size:14px; font-weight:600;")
            col.addWidget(lbl_k)
            col.addWidget(lbl_v)
            info_lay.addLayout(col)
            self._stat_labels[key] = lbl_v
        right_lay.addWidget(info_frame)

        # Match visualization
        viz_frame = QFrame()
        viz_frame.setObjectName("panel")
        viz_lay = QVBoxLayout(viz_frame)
        viz_lay.setContentsMargins(8, 6, 8, 6)
        viz_lbl = QLabel("MATCH VISUALIZATION")
        viz_lbl.setObjectName("sectionHeader")
        viz_lay.addWidget(viz_lbl)
        self._match_viz = MatchVisualizationWidget()
        viz_lay.addWidget(self._match_viz, stretch=1)
        right_lay.addWidget(viz_frame, stretch=1)

        # Step log
        log_frame = QFrame()
        log_frame.setObjectName("panel")
        log_lay = QVBoxLayout(log_frame)
        log_lay.setContentsMargins(8, 6, 8, 6)
        log_lbl = QLabel("STEP LOG")
        log_lbl.setObjectName("sectionHeader")
        log_lay.addWidget(log_lbl)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Step", "Char", "From", "To", "Match"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        log_lay.addWidget(self._table)
        right_lay.addWidget(log_frame, stretch=1)

        body.addWidget(right)
        body.setStretchFactor(0, 5)
        body.setStretchFactor(1, 5)
        root.addWidget(body, stretch=1)

        # Control bar
        ctrl = QFrame()
        ctrl.setObjectName("controlBar")
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(16, 6, 16, 6)
        ctrl_lay.setSpacing(10)

        self._btn_reset = QPushButton("Reset")
        self._btn_reset.clicked.connect(self._reset)
        ctrl_lay.addWidget(self._btn_reset)

        self._btn_back = QPushButton("Back")
        self._btn_back.clicked.connect(self._step_back)
        ctrl_lay.addWidget(self._btn_back)

        self._btn_play = QPushButton("Play")
        self._btn_play.setObjectName("playButton")
        self._btn_play.clicked.connect(self._toggle_play)
        ctrl_lay.addWidget(self._btn_play)

        self._btn_step = QPushButton("Step")
        self._btn_step.clicked.connect(self._step_forward)
        ctrl_lay.addWidget(self._btn_step)

        ctrl_lay.addSpacerItem(QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        spd_lbl = QLabel("Speed")
        spd_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; font-weight:600;")
        ctrl_lay.addWidget(spd_lbl)
        self._slider_speed = QSlider(Qt.Orientation.Horizontal)
        self._slider_speed.setRange(20, 800)
        self._slider_speed.setValue(200)
        self._slider_speed.setFixedWidth(160)
        self._slider_speed.valueChanged.connect(self._speed_changed)
        ctrl_lay.addWidget(self._slider_speed)
        self._lbl_speed = QLabel("200 ms")
        self._lbl_speed.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        self._lbl_speed.setFixedWidth(54)
        ctrl_lay.addWidget(self._lbl_speed)

        ctrl_lay.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        self._lbl_step_of = QLabel("")
        self._lbl_step_of.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        ctrl_lay.addWidget(self._lbl_step_of)

        root.addWidget(ctrl)

        # Status bar
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {MUTED}; padding: 4px 8px; font-size: 11px;")
        root.addWidget(self._status_label)

        self._set_controls_enabled(False)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._run)
        QShortcut(QKeySequence("Space"), self).activated.connect(self._toggle_play)
        QShortcut(QKeySequence("Right"), self).activated.connect(self._step_forward)
        QShortcut(QKeySequence("Left"), self).activated.connect(self._step_back)

    def _update_status(self, msg: str):
        self._status_label.setText(msg)

    def _load_fasta(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open FASTA", "", "FASTA (*.fasta *.fa);;All (*)")
        if path:
            try:
                genome = load_genome(path)
                self._inp_genome.setText(genome)
                self._update_status("FASTA loaded")
            except Exception as e:
                QMessageBox.critical(self, "FASTA Error", str(e))

    def _ai_suggest_pattern(self):
        if not self._ai_handler or not self._inp_ai_query:
            return
        query = self._inp_ai_query.text().strip()
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter an AI query")
            return

        self._update_status("Analyzing query with AI...")
        QApplication.processEvents()

        success, pattern_or_error = self._ai_handler.extract_pattern(query)
        if success:
            self._inp_pattern.setText(pattern_or_error)
            self._update_status(f"AI suggested pattern: {pattern_or_error}")
        else:
            QMessageBox.warning(self, "AI Error", pattern_or_error)
            self._update_status("AI query failed")

    def _run(self):
        pattern = self._inp_pattern.text().strip().upper()
        genome = self._inp_genome.text().strip().upper()

        if not pattern:
            QMessageBox.warning(self, "Error", "Pattern cannot be empty")
            return
        if not genome:
            QMessageBox.warning(self, "Error", "Genome cannot be empty")
            return

        valid = set("ATCG")
        if not all(c in valid for c in pattern):
            QMessageBox.warning(self, "Error", "Pattern contains invalid characters")
            return

        self._stop_play()
        self._update_status("Building DFA...")
        QApplication.processEvents()

        try:
            self._delta, self._accept_state = get_transition_table(pattern)
            self._pattern, self._genome = pattern, genome
            self._matches = find_matches(genome, self._delta, self._accept_state, len(pattern))
            self._trace = trace_dfa(genome, self._delta, self._accept_state, len(pattern))
            self._step = -1

            self._fa_widget.render_dfa(pattern, self._delta, self._accept_state)
            self._timeline.set_data(genome, self._matches, len(pattern))
            self._match_viz.plot_matches(self._matches, len(genome), len(pattern))

            n_states = len(self._delta)
            match_pct = (len(self._matches) / max(len(genome), 1)) * 100
            self._stat_labels["Pattern"].setText(pattern)
            self._stat_labels["Genome Len"].setText(f"{len(genome):,}")
            self._stat_labels["DFA States"].setText(str(n_states))
            self._stat_labels["Match %"].setText(f"{match_pct:.1f}%")

            self._lbl_step.setText("0")
            self._lbl_state.setText("q0")
            self._lbl_matches.setText("0")
            self._table.setRowCount(0)
            self._progress.setMaximum(len(self._trace))
            self._progress.setValue(0)
            self._lbl_step_of.setText(f"0 / {len(self._trace)}")

            self._set_controls_enabled(True)
            self._update_status(f"DFA built: {len(self._matches)} matches found")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self._update_status("Error")

    def _toggle_play(self):
        if not self._trace:
            return
        if self._playing:
            self._stop_play()
        else:
            self._start_play()

    def _start_play(self):
        if self._step >= len(self._trace) - 1:
            self._step = -1
            self._table.setRowCount(0)
        self._playing = True
        self._btn_play.setText("Pause")
        self._btn_play.setObjectName("playButtonActive")
        self._btn_play.style().unpolish(self._btn_play)
        self._btn_play.style().polish(self._btn_play)
        self._timer.start(self._slider_speed.value())
        self._update_status("Playing animation...")

    def _stop_play(self):
        self._playing = False
        self._timer.stop()
        self._btn_play.setText("Play")
        self._btn_play.setObjectName("playButton")
        self._btn_play.style().unpolish(self._btn_play)
        self._btn_play.style().polish(self._btn_play)

    def _advance_step(self):
        if self._step >= len(self._trace) - 1:
            self._stop_play()
            self._update_status("Animation complete")
            return
        self._step += 1
        self._show_step(self._step)

    def _step_forward(self):
        if not self._trace or self._step >= len(self._trace) - 1:
            return
        self._step += 1
        self._show_step(self._step)

    def _step_back(self):
        if not self._trace or self._step <= 0:
            return
        self._table.removeRow(self._table.rowCount() - 1)
        self._step -= 1
        self._show_step(self._step, add_row=False)

    def _reset(self):
        self._stop_play()
        self._step = -1
        self._table.setRowCount(0)
        self._timeline.set_current_index(-1)
        self._lbl_step.setText("0")
        self._lbl_state.setText("q0")
        self._lbl_matches.setText("0")
        self._progress.setValue(0)
        self._lbl_step_of.setText(f"0 / {len(self._trace)}")
        if self._delta:
            self._fa_widget.highlight_state(0)
        self._update_status("Reset")

    def _speed_changed(self, val: int):
        self._lbl_speed.setText(f"{val} ms")
        if self._playing:
            self._timer.setInterval(val)

    def _set_controls_enabled(self, on: bool):
        for btn in (self._btn_reset, self._btn_back, self._btn_play, self._btn_step):
            btn.setEnabled(on)
        self._slider_speed.setEnabled(on)

    def _show_step(self, idx: int, add_row: bool = True):
        if idx < 0 or idx >= len(self._trace):
            return
        step = self._trace[idx]

        self._lbl_step.setText(str(idx + 1))
        self._lbl_state.setText(f"q{step['next_state']}")

        matches_so_far = sum(1 for t in self._trace[:idx + 1] if t["is_match"])
        self._lbl_matches.setText(str(matches_so_far))

        if step["is_match"]:
            self._lbl_matches.setStyleSheet(f"color: #FFFFFF; background-color: {SUCCESS};")
            QTimer.singleShot(500, lambda: self._lbl_matches.setStyleSheet(""))

        self._timeline.set_current_index(step["index"])
        self._fa_widget.highlight_state(step["next_state"])
        self._progress.setValue(idx + 1)
        self._lbl_step_of.setText(f"{idx + 1} / {len(self._trace)}")

        if add_row:
            row = self._table.rowCount()
            self._table.insertRow(row)
            items = [str(idx + 1), step["char"], f"q{step['prev_state']}", 
                    f"q{step['next_state']}", "MATCH" if step["is_match"] else ""]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if step["is_match"]:
                    item.setForeground(QBrush(QColor(SUCCESS)))
                self._table.setItem(row, col, item)
            self._table.scrollToBottom()


def launch():
    """Launch the app."""
    app = QApplication(sys.argv)
    qss_path = Path(__file__).parent / "assets" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text())
    window = DNASimulatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()

