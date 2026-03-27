# Quick Start Guide

## Installation (First Time)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Graphviz Binary (Optional - for FA diagrams)
**macOS:**
```bash
brew install graphviz
```

**Ubuntu/Debian:**
```bash
sudo apt-get install graphviz
```

**Windows:** 
Download from https://graphviz.org/download/ and add to PATH

### 3. Set API Keys (Optional - for Groq LLM features)
```bash
export GROQ_API_KEY="gsk-your-api-key-here"
```

## Running the Application

### Option 1: Streamlit Web UI (Recommended)
The most user-friendly browser-based interface with visualizations and Groq LLM integration.

```bash
streamlit run app.py
```

Opens automatically at http://localhost:8501

**Features:**
- 🎯 Single Pattern DFA matching
- 🔗 Multi-Pattern Aho-Corasick search
- 🤖 Natural Language queries with Groq
- 📊 Real-time FA diagrams & match plots

**Chat behavior:**
- Without genome loaded: assistant can still answer setup/usage questions.
- With genome loaded: assistant extracts pattern and runs matching.

### Option 2: PyQt6 Desktop Application
Professional desktop simulator with step-by-step DFA visualization.

```bash
python3 main.py
```

**Features:**
- Visual DFA state machine execution
- Step-by-step control (play/pause/step)
- Match position timeline
- Speed adjustment

### Option 3: Python Library (Programmatic)
Use the modules directly in your own code.

```python
from dfa import get_transition_table
from matcher import find_matches

pattern = "ATCG"
genome = "ATCGATCGATCGATCG"

delta, accept_state = get_transition_table(pattern)
matches = find_matches(genome, delta, accept_state, len(pattern))
print(f"Matches found at: {matches}")
```

## Example Workflows

### Single Pattern Search
1. Open Streamlit app: `streamlit run app.py`
2. Enter pattern: `ATCG`
3. Paste genome sequence
4. Click "Find Matches"
5. View FA diagram and match distribution

### Multi-Pattern Search
1. Switch to "Multi-Pattern (Aho-Corasick)" mode
2. Enter patterns (one per line):
   ```
   ATCG
   TGC
   AAA
   ```
3. Paste genome
4. View matches for all patterns simultaneously

### Natural Language Query
1. Switch to "Natural Language Chat"
2. Load genome sequence
3. Ask: "Find all occurrences of ATCG"
4. Groq extracts pattern and explains results

### Load Real Genomes
Place FASTA files in `sample_data/` folder and use in app:
- Click "Paste genome sequence"
- Paste your FASTA content
- Or load via Python:
  ```python
  from genome_loader import load_genome
  genome = load_genome("sample_data/my_genome.fasta")
  ```

Note: Web inputs automatically strip FASTA headers and whitespace/newlines before validation.

## Troubleshooting

**"dot not found" when generating FA diagrams:**
- Install Graphviz binary (see Installation step 2)

**"No module named 'streamlit'":**
```bash
pip install streamlit
```

**Groq API not working:**
- Set `GROQ_API_KEY`: `export GROQ_API_KEY="gsk-..."`
- Check API key is valid at https://console.groq.com/

**Port 8501 already in use:**
```bash
streamlit run app.py --server.port 8502
```

## Project Structure

```
dna-fa-matcher/
├── dfa.py                  # Core DFA engine (KMP-based)
├── matcher.py              # DFA pattern scanner
├── aho_corasick.py         # Multi-pattern matching
├── genome_loader.py        # FASTA file loader
├── visualize.py            # Graphviz + Matplotlib
├── app.py                  # Streamlit web UI
├── simulator_ui.py         # PyQt6 desktop app
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
└── sample_data/           # Example genomes
```

## API Reference

### DFA Engine
```python
from dfa import get_transition_table
delta, accept_state = get_transition_table(pattern)
```

### Pattern Matching
```python
from matcher import find_matches
matches = find_matches(genome, delta, accept_state, len(pattern))
# Returns: [1, 5, 9, 13, ...] (1-indexed positions)
```

### Multi-Pattern
```python
from aho_corasick import AhoCorasickMatcher
matcher = AhoCorasickMatcher(["ATCG", "TGC"])
results = matcher.find_all_matches(genome)
# Returns: {'ATCG': [1, 5, 9], 'TGC': [2, 6]}
```

### Genome Loading
```python
from genome_loader import load_genome
genome = load_genome("file.fasta")
```

### Visualizations
```python
from visualize import draw_fa_diagram, plot_matches

draw_fa_diagram(pattern, delta, accept_state, "output.png")
plot_matches(genome, matches, pattern, "output.png")
```

## Performance

- **Single pattern matching**: O(n) - linear time
- **Multi-pattern (5 patterns)**: O(n + z) where z = matches
- **Typical speed**: 10-50ms for 1M bp genome

## Support

For issues or questions:
1. Check README.md for detailed documentation
2. Verify all dependencies are installed
3. Ensure Python 3.10+
4. Check that required binaries (Graphviz) are on PATH

## About

**DNA FA Matcher** - Deterministic Finite Automaton based DNA pattern matching
with Aho-Corasick multi-pattern support and Groq LLM integration.

Course: CS Automata Theory Project
Team: Zainab Saeed (509170), Maryam Ubaid (511128)

