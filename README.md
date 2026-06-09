# DNA Pattern Matcher — Finite Automaton Theory Project

A professional PyQt6 desktop application for DNA sequence pattern matching using Deterministic Finite Automata (DFA), with AI-powered pattern suggestions and interactive step-by-step animation.

## 🎯 Features

- **DFA Construction**: Automatically builds a transition table for DNA patterns (A/T/C/G alphabet).
- **Interactive Visualization**: 
  - Custom-painted DFA state diagram with active-state highlighting per step
  - Color-coded genome timeline showing match positions
  - Matplotlib-based match position bar chart
- **Step-by-Step Animation**: Play, pause, step forward/backward through the DFA trace.
- **AI Pattern Suggestions** (Optional): Use Groq AI to extract DNA patterns from natural language queries.
- **FASTA File Loading**: Load genome sequences from standard FASTA files.
- **Professional Dark Theme**: Modern, cohesive UI with GitHub-inspired colors.
- **Status Bar & Metrics**: Real-time progress, match count, DFA state count, and match percentage.

## 📋 Requirements

- Python 3.10+
- PyQt6 (GUI framework)
- Matplotlib (match visualization)
- Groq API key (optional, for AI pattern suggestions)
- BioPython (optional, for advanced FASTA handling)

## 🚀 Setup & Run

### 1. Clone & Install Dependencies

```bash
cd /path/to/dna-fa-matcher
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up AI (Optional)

If you want to use the AI pattern suggestion feature:

```bash
export GROQ_API_KEY="your-api-key-here"
```

Or set it in your environment before running the app.

### 3. Launch the Application

```bash
python3 main.py
```

The application will open a desktop window.

## 💻 Usage

### Basic Workflow

1. **Enter Pattern**: Type a DNA pattern (e.g., `ATCG`) in the "Pattern" field.
2. **Load Genome**: Either paste a genome sequence or click "Load FASTA" to open a file.
3. **Run Matcher**: Click "Run" to build the DFA and find all matches.
4. **Visualize**: 
   - **DFA Diagram** (left): Shows state transitions; active state is highlighted in blue.
   - **Genome Timeline** (left): Colored nucleotides; match regions are highlighted.
   - **Match Visualization** (right): Bar chart of match positions.
5. **Animate**: Use Play/Pause, Step, Back, or Speed controls to trace through the DFA step-by-step.

### Quick FASTA Test File

Use the included sample FASTA file for a fast test:

- `samples/demo_genome.fasta`

Desktop app test flow:

1. Enter a pattern like `TATA` or `ATG`.
2. Click **Load FASTA**.
3. Select `samples/demo_genome.fasta`.
4. Click **Run** to see matches and DFA animation.

### AI Pattern Suggestion (if enabled)

1. In the "AI Query" field, type a natural language description:
   - *"Find GC-rich regions"*
   - *"Detect mutation patterns"*
   - *"Common promoter sequences"*
2. Click "Suggest".
3. The AI will extract a DNA pattern and auto-fill the Pattern field.
4. Click "Run" to execute.

## 📂 Project Structure

```
dna-fa-matcher/
├── main.py                  # Entry point
├── simulator_ui.py          # PyQt6 desktop GUI
├── dfa.py                   # DFA construction
├── matcher.py               # Pattern matching & tracing
├── genome_loader.py         # FASTA file loading
├── ai_insights.py           # AI pattern extraction (Anthropic)
├── samples/
│   └── demo_genome.fasta    # Ready-to-use FASTA test file
├── assets/
│   └── style.qss            # Qt stylesheet (dark theme)
├── requirements.txt         # Dependencies
└── README.md                # This file
```

## 🧬 Algorithm

**Knuth-Morris-Pratt (KMP) DFA**:
- Builds transition table with O(m) preprocessing (m = pattern length)
- Scans genome with O(n) time complexity (n = genome length)
- Total: **O(n + m)** — linear time pattern matching

## 🎓 For Professors

This project demonstrates:
- Finite Automata theory applied to practical bioinformatics
- DFA state construction and traversal
- Time complexity analysis (linear-time scanning)
- Professional software engineering practices (modular design, error handling, UI polish)
- Optional: AI integration for exploratory research

## 📝 Command-Line Demo (Optional)

For a quick CLI demo without the GUI:

```bash
python3 demo.py
```

## 🔧 Troubleshooting

**"matplotlib not installed"**: Run `pip install matplotlib`

**"Anthropic API key not found"**: The AI feature gracefully disables. Set `GROQ_API_KEY` or use the app without AI.

**"FASTA file not found"**: Ensure the file path is correct and readable.

## 📄 License

Educational project for Automata Theory coursework.


