# DNA String Matcher - Detailed Project Tech Stack Report

## 1. Project Overview

### Project Name
DNA Pattern Matcher / GeneFlow DNA String Matcher

### Core Purpose
This project detects DNA subsequences (patterns) inside larger genome strings using a Deterministic Finite Automaton (DFA) based matcher.

### Academic Positioning
The implementation is designed as an Automata Theory project and demonstrates:
- Formal language concepts mapped to a practical bioinformatics problem
- DFA construction and traversal
- Linear-time string matching behavior in practice
- Multi-interface software engineering (CLI launcher, desktop GUI, Streamlit web UI)

## 2. Technology Stack (At a Glance)

### Programming Language
- Python (project documents mention 3.9+, 3.10+, and 3.13 in different places)

### Core Algorithm Layer
- Custom DFA builder and matcher
- Alphabet restricted to A, T, C, G

### Desktop Application Layer
- PyQt6
- PyQt6-WebEngine
- Matplotlib embedded in Qt (FigureCanvasQTAgg)

### Web Application Layer
- Streamlit
- Plotly
- Pandas

### Bioinformatics/Data Layer
- BioPython (SeqIO for FASTA parsing)
- Custom genome file loader (plain/FASTA filtering to A/T/C/G)

### AI Layer (Optional)
- Hugging Face Router Chat Completions endpoint
- Model fallback strategy across multiple instruct models
- Environment token support through multiple variable names

### Visualization Layer
- Matplotlib (desktop and generated static visual assets)
- Plotly (interactive web charts)
- Custom SVG/Canvas DNA visuals

### Tooling and Verification
- Python test/verification scripts (custom, not pytest-based)
- Dependency verification script

## 3. Dependency List (requirements.txt)

Current declared packages:
- PyQt6>=6.7
- PyQt6-WebEngine>=6.7
- matplotlib>=3.7
- google-generativeai>=0.3.0
- biopython>=1.83
- streamlit>=1.28
- plotly>=5.17
- pandas>=2.0
- certifi>=2024.2.2

Important note:
- The active AI implementation in the code uses Hugging Face API calls, while requirements still include google-generativeai.
- This indicates migration history or mixed versions of the AI integration logic.

## 4. System Architecture

### 4.1 Layered View
1. Input Layer
- Pattern input (manual or AI-assisted)
- Genome input (manual text or FASTA upload/load)

2. Processing Layer
- DFA transition table generation from pattern
- Streaming genome scan with state transitions
- Match position extraction
- Optional transition trace for animation playback

3. Presentation Layer
- Desktop PyQt interface with custom-painted DFA visuals and timeline
- Streamlit web interfaces with HTML/CSS-heavy branded UIs and charts

4. Auxiliary Services
- AI pattern suggestion/chat
- System verification and test scripts
- Export/report features in desktop variant (CSV/PDF related imports present)

### 4.2 Execution Entry Points
- main.py: terminal launcher to pick desktop or web run mode
- app_desktop.py: starts the desktop app
- app_web.py: advanced Streamlit web experience
- app_streamlit.py: alternate Streamlit experience
- demo.py: CLI demonstration script (contains stale references)

## 5. Codebase Structure

### Root Modules (Primary)
- main.py: menu-driven launcher
- dfa.py: DFA transition table construction
- matcher.py: matching and per-step tracing
- genome_loader.py: FASTA/plain loader and DNA sanitization
- ai_insights.py: optional AI integration via Hugging Face router
- simulator_ui_geneflow.py: major desktop UI implementation
- simulator_ui.py: alternate desktop UI implementation
- app_web.py: Streamlit web app (modern branded design)
- app_streamlit.py: second Streamlit UX variant
- dna_visuals.py: SVG and matplotlib DNA visual generation
- test_suite.py: scenario and performance tests
- verify_system.py: environment/dependency/system verification

### Duplicated Subproject
- pyqt-app/: mirrored copy of most root modules, likely a packaged/exported snapshot or alternate branch copy

### Other Directories
- assets/: stylesheet assets (Qt theme)
- outputs/: generated visual outputs
- web/: currently empty

## 6. Core Algorithm and Complexity

### 6.1 DFA Construction
The transition table is built over states 0..m where m is pattern length.
For each state and each alphabet symbol, next state is computed by longest prefix/suffix compatibility.

### 6.2 Matching
Genome scan iterates once through text and updates state via transition table.
When accept state is reached, a match start position is recorded.

### 6.3 Complexity Discussion
- Matching phase is linear in genome size: O(n)
- DFA preprocessing is pattern-dependent and currently implemented via explicit prefix/suffix checks
- In project messaging, total flow is presented as linear-time scanning centered on DFA traversal

## 7. Data Handling and Validation

### 7.1 DNA Alphabet Constraints
- Valid symbols: A, T, C, G
- Patterns are uppercased and validated against alphabet
- Genome text is cleaned to valid nucleotides only

### 7.2 File Handling
- FASTA support through BioPython in web flows
- Plain/FASTA parsing through custom loader in desktop flows

### 7.3 Match Index Convention
- Primary matcher returns 1-indexed positions
- Compatibility helper in matcher.py includes 0-index conversion for legacy calls

## 8. UI and UX Technology Details

### Desktop (PyQt)
- Custom-painted DFA graph with active state highlighting
- Genome timeline rendering with nucleotide colors and match overlays
- Optional animation controls via transition trace
- Embedded charting with Matplotlib
- Rich theme variables and branded styling

### Web (Streamlit)
- Heavy custom CSS typography and branding
- Custom HTML blocks for transitions, bars, and sequence highlighting
- Plotly charts and metric panels
- Session state driven analysis workflow

### Visual Design Notes
- The project includes multiple visual systems (dark neon, editorial serif themes, and desktop palettes), indicating iterative design evolution.

## 9. AI Integration Details

### Functional Role
- Extract DNA patterns from natural language prompts
- Provide assistant-style replies with context in desktop chat workflows
- Offer motif suggestions through k-mer frequency logic

### Runtime Behavior
- Uses HTTP calls to Hugging Face Router endpoint
- Supports model fallback list for resiliency
- Includes friendly error normalization (quota/auth/loading/network)

### Configuration
- Reads tokens from environment and optionally .env
- Supports multiple variable names including HF and Google-style names for compatibility

## 10. Testing and Quality Assurance

### 10.1 test_suite.py Coverage Themes
- Basic correctness tests
- Bioinformatics-inspired motifs (start/stop codons, promoter-like patterns)
- Edge cases (overlaps, boundaries, empty/invalid patterns)
- Performance checks (large genome processing)
- Validation checks (case handling, exact position verification)

### 10.2 verify_system.py Coverage Themes
- Python version checks
- Dependency import checks
- Algorithm smoke tests
- UI dependency checks (desktop + web)
- Required file structure checks

### 10.3 Test Framework Style
- Script-driven functional checks (manual runner)
- No formal pytest/unittest harness currently detected

## 11. Known Inconsistencies and Technical Debt

1. AI provider mismatch
- requirements and quick docs mention Google/Gemini paths, but active AI module calls Hugging Face APIs

2. Demo script stale imports
- demo.py imports modules not present in this workspace (aho_corasick, visualize) and references app.py

3. Multi-version duplication
- Entire pyqt-app mirror duplicates root code, increasing maintenance overhead and divergence risk

4. Version statement inconsistency
- Project docs/scripts mention different minimum Python versions

5. Potential backend mismatch in desktop plotting
- Desktop module sets matplotlib Qt5Agg backend while using PyQt6

## 12. Runtime and Deployment Notes

### Local Development
Typical workflow:
1. Create/activate venv
2. Install requirements
3. Run main.py and choose desktop/web

### Web Run
- streamlit run app_web.py

### Desktop Run
- python3 app_desktop.py

### Optional Environment Variables
- Hugging Face token variable(s)
- Historical docs also reference GOOGLE_API_KEY

## 13. Security and Reliability Notes

- API keys are sourced from environment/.env and should never be hardcoded
- Network calls for AI include timeout and error handling
- Input sanitation is implemented for DNA character filtering
- Missing/invalid FASTA handling includes explicit exceptions

## 14. Suggested Slide Deck (PPT) Outline

1. Problem Statement and Domain Context
2. Automata Theory to Bioinformatics Mapping
3. End-to-End Architecture
4. Tech Stack by Layer
5. DFA Algorithm Walkthrough
6. UI Systems (Desktop + Web)
7. AI-Assisted Pattern Discovery
8. Testing Strategy and Results
9. Limitations and Technical Debt
10. Future Work and Roadmap

## 15. Suggested LaTeX Report Structure

Recommended sections:
- Abstract
- Introduction
- Background (DFA and DNA Pattern Matching)
- System Architecture
- Implementation Details
- Experimental Validation
- Discussion (Trade-offs and Limitations)
- Conclusion and Future Work
- References
- Appendix (Screenshots, Transition Tables, Test Outputs)

## 16. Future Improvement Roadmap

1. Consolidate duplicate codebases (root vs pyqt-app)
2. Standardize AI provider and clean dependencies/docs
3. Replace stale demo dependencies or remove deprecated paths
4. Introduce formal automated testing (pytest + CI)
5. Normalize Python version policy across docs and scripts
6. Add packaging/release strategy (single distributable for desktop/web)

## 17. Summary

The project is a feature-rich academic-to-practical DNA matching platform built around DFA-based pattern matching, with both desktop and web experiences, optional AI support, and strong visual storytelling. The architecture is modular and presentation-friendly, but would benefit from consistency cleanup (AI provider, duplicated code, and stale demo artifacts) before final production or publication.
