"""Professional PyQt6 DNA Finite-Automaton Simulator."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ── Project imports ──────────────────────────────────────────────────────────
from dfa import get_transition_table
from matcher import find_matches, trace_dfa
from genome_loader import load_genome

# ── Constants ────────────────────────────────────────────────────────────────
BG = "#0D1117"
PANEL = "#161B22"
CARD = "#21262D"
BORDER = "#30363D"
ACCENT = "#58A6FF"
SUCCESS = "#3FB950"
CORAL = "#F78166"
TEXT = "#E6EDF3"
MUTED = "#8B949E"

NUCLEOTIDE_COLORS = {
    "A": "#3FB950",  # green
    "T": "#F78166",  # coral
    "C": "#58A6FF",  # blue
    "G": "#D2A8FF",  # purple
}


# ═════════════════════════════════════════════════════════════════════════════
#  Timeline Widget — custom QPainter genome strip
# ═════════════════════════════════════════════════════════════════════════════
class TimelineWidget(QWidget):
    """Horizontal genome timeline with colored nucleotides and match highlights."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._genome: str = ""
        self._matches: List[int] = []  # 1-indexed
        self._pattern_len: int = 0
        self._current_index: int = -1  # 0-based index of active step
        self._match_set: set = set()
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, genome: str, matches: List[int], pattern_len: int):
        self._genome = genome
        self._matches = matches
        self._pattern_len = pattern_len
        self._match_set = set()
        for m in matches:
            for i in range(pattern_len):
                self._match_set.add(m - 1 + i)  # convert 1-indexed to 0-indexed
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

        w = self.width()
        h = self.height()
        n = len(self._genome)

        # cell geometry
        cell_w = max(3, min(18, (w - 20) / max(n, 1)))
        total_w = cell_w * n
        offset_x = max(10, (w - total_w) / 2)

        # Draw ruler line
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawLine(int(offset_x), h - 8, int(offset_x + total_w), h - 8)

        font = QFont("JetBrains Mono", max(7, min(10, int(cell_w * 0.7))))
        painter.setFont(font)

        for i, ch in enumerate(self._genome):
            x = offset_x + i * cell_w

            # Background for match positions
            if i in self._match_set:
                painter.fillRect(int(x), 2, int(cell_w), h - 12, QColor(SUCCESS + "30"))

            # Current step highlight
            if i == self._current_index:
                painter.fillRect(int(x), 0, int(cell_w), h - 8, QColor(ACCENT + "55"))
                # border
                painter.setPen(QPen(QColor(ACCENT), 2))
                painter.drawRect(int(x), 0, int(cell_w), h - 10)

            # Nucleotide color
            color = NUCLEOTIDE_COLORS.get(ch, MUTED)
            painter.setPen(QPen(QColor(color)))
            if cell_w >= 10:
                painter.drawText(int(x), 4, int(cell_w), h - 16,
                                 Qt.AlignmentFlag.AlignCenter, ch)

            # Tick mark
            painter.setPen(QPen(QColor(BORDER), 1))
            if i % max(1, int(n / 20)) == 0:
                painter.drawLine(int(x), h - 10, int(x), h - 4)

        painter.end()


# ═════════════════════════════════════════════════════════════════════════════
#  FA Diagram Widget — renders DFA graph via graphviz into a QPixmap
# ═════════════════════════════════════════════════════════════════════════════
class FADiagramWidget(QLabel):
    """Renders the DFA diagram through Graphviz and shows it in a QLabel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")
        self._pixmap: Optional[QPixmap] = None
        self._current_state: int = -1
        self._accept_state: int = -1

    def render_dfa(self, pattern: str, delta: Dict, accept_state: int):
        """Render the DFA using graphviz to a temp PNG and load it."""
        import shutil
        if shutil.which("dot") is None:
            self.setText("Graphviz 'dot' not found.\nInstall from graphviz.org")
            self._pixmap = None
            return

        from graphviz import Digraph

        self._accept_state = accept_state
        dot = Digraph(comment="DNA Pattern DFA", format="png")
        dot.attr(rankdir="LR", bgcolor="transparent", dpi="150")
        dot.attr("node", fontname="JetBrains Mono", fontsize="11",
                 color=BORDER, fontcolor=TEXT, style="filled")
        dot.attr("edge", fontname="JetBrains Mono", fontsize="9",
                 color=MUTED, fontcolor=ACCENT)

        for state in delta:
            if state == accept_state:
                dot.node(f"q{state}", f"q{state}",
                         shape="doublecircle", fillcolor="#238636", fontcolor="#FFFFFF")
            elif state == 0:
                dot.node(f"q{state}", f"q{state}",
                         shape="circle", fillcolor=CARD)
            else:
                dot.node(f"q{state}", f"q{state}",
                         shape="circle", fillcolor=CARD)

        # Invisible start arrow
        dot.node("__start__", "", shape="none", width="0", height="0")
        dot.edge("__start__", "q0", style="bold", color=ACCENT)

        # Group edge labels
        edge_labels: Dict[tuple, List[str]] = {}
        for state, transitions in delta.items():
            for char, next_state in transitions.items():
                if state == next_state == 0 and char != pattern[0]:
                    continue
                edge_labels.setdefault((state, next_state), []).append(char)

        for (src, dst), chars in edge_labels.items():
            label = ",".join(sorted(chars))
            style = "bold" if dst == src + 1 and src < accept_state else ""
            edge_color = SUCCESS if dst == src + 1 and src < accept_state else MUTED
            dot.edge(f"q{src}", f"q{dst}", label=label, style=style, color=edge_color)

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fa_diagram")
            dot.render(path, cleanup=True)
            png_path = path + ".png"
            if os.path.exists(png_path):
                self._pixmap = QPixmap(png_path)
                self._update_display()

    def _update_display(self):
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def highlight_state(self, state: int):
        """Placeholder — re-rendering the whole graph for each step is too slow.
        Instead we show current state in the stats panel."""
        self._current_state = state


# ═════════════════════════════════════════════════════════════════════════════
#  Stat Card Helpers
# ═════════════════════════════════════════════════════════════════════════════
def _card(title: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
    """Create a dark stat card with a title and a value label."""
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
    lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft)
    lay.addWidget(lbl_value)

    return frame, lay, lbl_value


# ═════════════════════════════════════════════════════════════════════════════
#  Main Window
# ═════════════════════════════════════════════════════════════════════════════
class DNASimulatorWindow(QMainWindow):
    """Professional PyQt6 DNA FA Simulator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DNA Finite Automaton Simulator")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 860)

        # ── State ────────────────────────────────────────────────────────
        self._pattern: str = ""
        self._genome: str = ""
        self._delta: Dict = {}
        self._accept_state: int = 0
        self._trace: List[Dict] = []
        self._matches: List[int] = []
        self._step: int = -1  # current trace index (-1 = not started)
        self._playing: bool = False

        # ── Timer ────────────────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        # ── Build UI ─────────────────────────────────────────────────────
        self._build_ui()
        self._setup_shortcuts()

    # ─────────────────────────────────────────────────────────────────────
    #  Build UI
    # ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header Bar ───────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("headerBar")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 8, 16, 8)
        hlay.setSpacing(12)

        title = QLabel("DNA FA Simulator")
        title.setObjectName("appTitle")
        hlay.addWidget(title)

        hlay.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Pattern input
        lbl_pat = QLabel("Pattern")
        lbl_pat.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700;")
        hlay.addWidget(lbl_pat)
        self._inp_pattern = QLineEdit("ATCG")
        self._inp_pattern.setFixedWidth(180)
        self._inp_pattern.setPlaceholderText("e.g. ATCG")
        hlay.addWidget(self._inp_pattern)

        # Genome input
        lbl_gen = QLabel("Genome")
        lbl_gen.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700;")
        hlay.addWidget(lbl_gen)
        self._inp_genome = QLineEdit()
        self._inp_genome.setMinimumWidth(240)
        self._inp_genome.setPlaceholderText("Paste genome or load FASTA…")
        hlay.addWidget(self._inp_genome, stretch=1)

        # Load FASTA button
        self._btn_fasta = QPushButton("Load FASTA")
        self._btn_fasta.setToolTip("Load genome from a FASTA file")
        self._btn_fasta.clicked.connect(self._load_fasta)
        hlay.addWidget(self._btn_fasta)

        # Run button
        self._btn_run = QPushButton("▶  Run")
        self._btn_run.setObjectName("runButton")
        self._btn_run.setToolTip("Build DFA and find matches (Ctrl+R)")
        self._btn_run.clicked.connect(self._run)
        hlay.addWidget(self._btn_run)

        root.addWidget(header)

        # ── Progress bar (thin, below header) ────────────────────────────
        self._progress = QProgressBar()
        self._progress.setObjectName("progressTop")
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setValue(0)
        root.addWidget(self._progress)

        # ── Body Splitter ────────────────────────────────────────────────
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)
        body.setStyleSheet("QSplitter::handle { background-color: #30363D; }")

        # ── LEFT PANEL — FA Diagram + Timeline ──────────────────────────
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(12, 12, 6, 8)
        left_lay.setSpacing(10)

        # FA Diagram
        fa_frame = QFrame()
        fa_frame.setObjectName("panel")
        fa_lay = QVBoxLayout(fa_frame)
        fa_lay.setContentsMargins(8, 6, 8, 6)
        fa_lbl = QLabel("FINITE AUTOMATON DIAGRAM")
        fa_lbl.setObjectName("sectionHeader")
        fa_lay.addWidget(fa_lbl)

        self._fa_scroll = QScrollArea()
        self._fa_scroll.setWidgetResizable(True)
        self._fa_widget = FADiagramWidget()
        self._fa_widget.setMinimumSize(300, 200)
        self._fa_scroll.setWidget(self._fa_widget)
        fa_lay.addWidget(self._fa_scroll, stretch=1)
        left_lay.addWidget(fa_frame, stretch=3)

        # Timeline
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

        # ── RIGHT PANEL — Stats + Step Log ──────────────────────────────
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(6, 12, 12, 8)
        right_lay.setSpacing(10)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        # Card 1 — Current Step
        c1, _, self._lbl_step = _card("CURRENT STEP")
        stats_row.addWidget(c1)

        # Card 2 — DFA State
        c2, _, self._lbl_state = _card("DFA STATE")
        stats_row.addWidget(c2)

        # Card 3 — Matches
        c3, c3_lay, self._lbl_matches = _card("MATCHES")
        self._lbl_matches.setObjectName("matchHit")
        stats_row.addWidget(c3)

        right_lay.addLayout(stats_row)

        # Card 4 — Statistics summary
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

        # Step Log Table
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
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        log_lay.addWidget(self._table)

        right_lay.addWidget(log_frame, stretch=1)
        body.addWidget(right)

        body.setStretchFactor(0, 5)
        body.setStretchFactor(1, 4)
        root.addWidget(body, stretch=1)

        # ── Control Bar ──────────────────────────────────────────────────
        ctrl = QFrame()
        ctrl.setObjectName("controlBar")
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(16, 6, 16, 6)
        ctrl_lay.setSpacing(10)

        self._btn_reset = QPushButton("⟲  Reset")
        self._btn_reset.setToolTip("Reset animation (R)")
        self._btn_reset.clicked.connect(self._reset)
        ctrl_lay.addWidget(self._btn_reset)

        self._btn_back = QPushButton("◂  Back")
        self._btn_back.setToolTip("Step backward (←)")
        self._btn_back.clicked.connect(self._step_back)
        ctrl_lay.addWidget(self._btn_back)

        self._btn_play = QPushButton("▶  Play")
        self._btn_play.setObjectName("playButton")
        self._btn_play.setToolTip("Play / Pause animation (Space)")
        self._btn_play.clicked.connect(self._toggle_play)
        ctrl_lay.addWidget(self._btn_play)

        self._btn_step = QPushButton("Step  ▸")
        self._btn_step.setToolTip("Step forward (→)")
        self._btn_step.clicked.connect(self._step_forward)
        ctrl_lay.addWidget(self._btn_step)

        ctrl_lay.addSpacerItem(QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Speed slider
        spd_lbl = QLabel("Speed")
        spd_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; font-weight:600;")
        ctrl_lay.addWidget(spd_lbl)
        self._slider_speed = QSlider(Qt.Orientation.Horizontal)
        self._slider_speed.setRange(20, 800)
        self._slider_speed.setValue(200)
        self._slider_speed.setFixedWidth(160)
        self._slider_speed.setToolTip("Animation speed (ms per step)")
        self._slider_speed.valueChanged.connect(self._speed_changed)
        ctrl_lay.addWidget(self._slider_speed)
        self._lbl_speed = QLabel("200 ms")
        self._lbl_speed.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        self._lbl_speed.setFixedWidth(54)
        ctrl_lay.addWidget(self._lbl_speed)

        # Step indicator
        ctrl_lay.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        self._lbl_step_of = QLabel("")
        self._lbl_step_of.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        ctrl_lay.addWidget(self._lbl_step_of)

        root.addWidget(ctrl)

        # initial disabled state
        self._set_controls_enabled(False)

    # ─────────────────────────────────────────────────────────────────────
    #  Shortcuts
    # ─────────────────────────────────────────────────────────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._run)
        QShortcut(QKeySequence("Space"), self).activated.connect(self._toggle_play)
        QShortcut(QKeySequence("Right"), self).activated.connect(self._step_forward)
        QShortcut(QKeySequence("Left"), self).activated.connect(self._step_back)
        QShortcut(QKeySequence("R"), self).activated.connect(self._reset)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._load_fasta)

    # ─────────────────────────────────────────────────────────────────────
    #  Load FASTA
    # ─────────────────────────────────────────────────────────────────────
    def _load_fasta(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open FASTA File", "",
            "FASTA Files (*.fasta *.fa *.fna);;All Files (*)"
        )
        if path:
            try:
                genome = load_genome(path)
                self._inp_genome.setText(genome)
            except Exception as e:
                QMessageBox.critical(self, "FASTA Error", str(e))

    # ─────────────────────────────────────────────────────────────────────
    #  Run — build DFA, compute trace & matches
    # ─────────────────────────────────────────────────────────────────────
    def _run(self):
        pattern = self._inp_pattern.text().strip().upper()
        genome = self._inp_genome.text().strip().upper()

        if not pattern:
            QMessageBox.warning(self, "Input Error", "Pattern cannot be empty.")
            return
        if not genome:
            QMessageBox.warning(self, "Input Error",
                                "Genome is empty. Paste a sequence or load a FASTA file.")
            return
        # Validate alphabet
        valid = set("ATCG")
        bad_p = set(pattern) - valid
        if bad_p:
            QMessageBox.warning(self, "Invalid Pattern",
                                f"Pattern contains invalid characters: {bad_p}\nOnly A, T, C, G allowed.")
            return
        bad_g = set(genome) - valid
        if bad_g:
            genome = "".join(c for c in genome if c in valid)
            self._inp_genome.setText(genome)

        self._stop_play()

        # Build DFA
        try:
            self._delta, self._accept_state = get_transition_table(pattern)
        except Exception as e:
            QMessageBox.critical(self, "DFA Error", str(e))
            return

        self._pattern = pattern
        self._genome = genome
        self._matches = find_matches(genome, self._delta, self._accept_state, len(pattern))
        self._trace = trace_dfa(genome, self._delta, self._accept_state, len(pattern))
        self._step = -1

        # Update FA diagram
        self._fa_widget.render_dfa(pattern, self._delta, self._accept_state)

        # Update timeline
        self._timeline.set_data(genome, self._matches, len(pattern))

        # Update statistics
        n_states = len(self._delta)
        match_pct = (len(self._matches) / max(len(genome), 1)) * 100
        self._stat_labels["Pattern"].setText(pattern)
        self._stat_labels["Genome Len"].setText(f"{len(genome):,}")
        self._stat_labels["DFA States"].setText(str(n_states))
        self._stat_labels["Match %"].setText(f"{match_pct:.1f}%")

        # Reset cards
        self._lbl_step.setText("0")
        self._lbl_state.setText("q0")
        self._lbl_matches.setText("0")

        # Clear table
        self._table.setRowCount(0)

        # Progress bar
        self._progress.setMaximum(len(self._trace))
        self._progress.setValue(0)
        self._lbl_step_of.setText(f"0 / {len(self._trace)}")

        # Enable controls
        self._set_controls_enabled(True)

    # ─────────────────────────────────────────────────────────────────────
    #  Animation Controls
    # ─────────────────────────────────────────────────────────────────────
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
        self._btn_play.setText("⏸  Pause")
        self._btn_play.setObjectName("playButtonActive")
        self._btn_play.style().unpolish(self._btn_play)
        self._btn_play.style().polish(self._btn_play)
        self._timer.start(self._slider_speed.value())

    def _stop_play(self):
        self._playing = False
        self._timer.stop()
        self._btn_play.setText("▶  Play")
        self._btn_play.setObjectName("playButton")
        self._btn_play.style().unpolish(self._btn_play)
        self._btn_play.style().polish(self._btn_play)

    def _advance_step(self):
        """Called by QTimer or manual step."""
        if self._step >= len(self._trace) - 1:
            self._stop_play()
            return
        self._step += 1
        self._show_step(self._step)

    def _step_forward(self):
        if not self._trace:
            return
        if self._step >= len(self._trace) - 1:
            return
        self._step += 1
        self._show_step(self._step)

    def _step_back(self):
        if not self._trace or self._step <= 0:
            return
        # Remove last row from table
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

    def _speed_changed(self, val: int):
        self._lbl_speed.setText(f"{val} ms")
        if self._playing:
            self._timer.setInterval(val)

    def _set_controls_enabled(self, on: bool):
        for btn in (self._btn_reset, self._btn_back, self._btn_play, self._btn_step):
            btn.setEnabled(on)
        self._slider_speed.setEnabled(on)

    # ─────────────────────────────────────────────────────────────────────
    #  Show a specific step
    # ─────────────────────────────────────────────────────────────────────
    def _show_step(self, idx: int, add_row: bool = True):
        if idx < 0 or idx >= len(self._trace):
            return
        step = self._trace[idx]

        # Cards
        self._lbl_step.setText(str(idx + 1))
        self._lbl_state.setText(f"q{step['next_state']}")

        # Count matches so far
        matches_so_far = sum(1 for t in self._trace[:idx + 1] if t["is_match"])
        self._lbl_matches.setText(str(matches_so_far))

        # Flash match highlight
        if step["is_match"]:
            self._lbl_matches.setStyleSheet(f"color: #FFFFFF; background-color: {SUCCESS}; border-radius: 6px; padding: 2px 6px;")
            QTimer.singleShot(500, lambda: self._lbl_matches.setStyleSheet(""))

        # Timeline
        self._timeline.set_current_index(step["index"])

        # Progress
        self._progress.setValue(idx + 1)
        self._lbl_step_of.setText(f"{idx + 1} / {len(self._trace)}")

        # Table row
        if add_row:
            row = self._table.rowCount()
            self._table.insertRow(row)

            items = [
                str(idx + 1),
                step["char"],
                f"q{step['prev_state']}",
                f"q{step['next_state']}",
                "✓ MATCH" if step["is_match"] else "",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if step["is_match"]:
                    item.setForeground(QBrush(QColor(SUCCESS)))
                elif col == 1:
                    color = NUCLEOTIDE_COLORS.get(step["char"], TEXT)
                    item.setForeground(QBrush(QColor(color)))
                self._table.setItem(row, col, item)

            self._table.scrollToBottom()


# ═════════════════════════════════════════════════════════════════════════════
#  Entry Helper
# ═════════════════════════════════════════════════════════════════════════════
def launch():
    """Launch the simulator application."""
    app = QApplication(sys.argv)

    # Load stylesheet
    qss_path = Path(__file__).parent / "assets" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text())

    window = DNASimulatorWindow()
    window.show()

    # Pre-load sample FASTA if available
    sample = Path(__file__).parent / "sample_data" / "sample_genome.fasta"
    if sample.exists():
        try:
            genome = load_genome(str(sample))
            window._inp_genome.setText(genome)
        except Exception:
            pass

    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
