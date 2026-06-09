# PPT Submission Blueprint (As Per Professor Model)

Deadline: 15 April 2026
Submission mode: LMS
Mandatory: PPT file submission (no PPT = -3 marks)
Mandatory: Built around proposal (else -3 marks)

---

## 1. Slide-by-Slide Structure (Use This Exact Order)

### Slide 1: Title + Team Details
Title:
DNA Pattern Matcher using Finite Automata (DFA)

Subtitle:
Theory of Automata Course Project

Team details block:
- Team Name: [Your Team Name]
- Member 1: [Name] | [Roll No] | [Email]
- Member 2: [Name] | [Roll No] | [Email]
- Member 3: [Name] | [Roll No] | [Email]
- Mentor/Section (if required): [Details]

Footer:
Submission Date: 15 April 2026

---

### Slide 2: Problem Statement
Use this wording:
- DNA sequences are very large and manual motif/pattern discovery is slow and error-prone.
- We need a fast and explainable method to find a DNA pattern (A/T/C/G) in genome text.
- Existing beginner-level tools often do not visually explain automata transitions.

Add one concise objective line:
Objective: Build an educational and practical DFA-based DNA matcher with visualization and real-time insights.

---

### Slide 3: Proposal Alignment (Important for Marks)
Title:
How This Work Matches Our Proposal

Create a 2-column table:
- Column A: Proposal Commitments
- Column B: Implemented Evidence

Recommended rows:
- DFA-based matching algorithm -> Implemented in dfa.py + matcher.py
- Interactive UI -> Desktop + web interfaces implemented
- FASTA support -> Genome loading and parsing completed
- Visualization -> DFA state view, timeline, match plot available
- Optional AI assistance -> Natural language to DNA pattern flow added

Note:
This slide prevents the proposal-related penalty.

---

### Slide 4: High-Level Solution Overview
Title:
Proposed Solution

Content bullets:
- Input: DNA pattern + genome sequence (text or FASTA)
- Processing: DFA construction and single-pass scanning
- Output: Match positions, statistics, transition visualization
- Optional AI: pattern suggestion from natural language query

Add your own architecture diagram (self-made):
Input -> Preprocessing -> DFA Builder -> Matcher Engine -> Visualization + Metrics

---

### Slide 5: Diagram 1 (System Architecture) [Self-Created]
Must be original (no copied internet images).

Diagram blocks to draw in PPT/diagrams.net:
- User Layer: Student/Researcher
- Interface Layer: Desktop UI, Web UI
- Logic Layer: DFA Constructor, Matcher, Trace Generator
- Data Layer: FASTA Loader, DNA Cleaner
- Optional Service: AI Query Handler

Tip:
Use your own color theme and labels from your project terminology.

---

### Slide 6: Diagram 2 (DFA Working)
Title:
How DFA Matching Works

Include:
- States q0 to qm for pattern length m
- Transition examples for A/T/C/G
- Accept state highlighted
- Match reported when accept state reached

Small complexity note:
Scan step is linear with respect to genome length (single left-to-right pass).

---

### Slide 7: Implementation Highlights
Show screenshots from your own app:
- Pattern input and genome input panel
- DFA diagram panel
- Match timeline/chart
- Stats panel (match count, state count, etc.)

Text bullets:
- Supports DNA alphabet validation
- Handles FASTA-based workflows
- Provides animation/trace of transitions
- Includes optional AI assistance

---

### Slide 8: Results / Demo Cases
Add at least 2 concrete test cases.

Case A:
- Pattern: ATCG
- Genome: ATCGATCGATCGATCGATCGATCGATCGATCG
- Result: 8 matches

Case B (biological motif example):
- Pattern: TATA
- Genome: [your sample]
- Result: [your observed count]

Include a simple comparison table:
Pattern | Genome Length | Matches | Runtime (if measured)

---

### Slide 9: Self-Explanatory Demo Video (YouTube)
Title:
Demo Video

Must include:
- YouTube video link (public or unlisted)
- QR code (optional but recommended)
- Video duration: 3 to 6 minutes ideal

Video should clearly show:
1. Problem and objective (20-30 sec)
2. Running the app (desktop/web)
3. Enter pattern and genome
4. FASTA upload demo
5. Visualization and match outputs
6. Brief conclusion

Important:
Narration should be clear enough that professor can understand without live explanation.

---

### Slide 10: GitHub Repository (Public)
Title:
Project Repository

Include:
- Public GitHub URL
- Repo QR code (optional)
- Key folders/files screenshot

Checklist text:
- Repository is public
- README is updated with run steps
- Requirements file is present
- Team members visible in commits/contributors

---

### Slide 11: Conclusion + Future Work
Suggested bullets:
- Successfully implemented proposal-driven DFA DNA matcher
- Delivered explainable visualization and practical genome handling
- Demonstrated working prototype via video + public repo

Future work:
- Multi-pattern matching extension
- Better biological dataset integration
- CI-based automated testing pipeline

---

### Slide 12: Thank You / Q&A
Include:
- Team names
- Contact emails
- GitHub and demo links again

---

## 2. Diagram Rules (To Avoid Penalty)
Use only self-made diagrams. Do not paste architecture figures from websites/articles.

Safe options:
- Draw shapes directly in PPT
- Use diagrams.net and export your own PNG
- Use your own screenshots from your app

For each diagram, add tiny footer:
Source: Created by project team

---

## 3. Demo Video Recording Script (Ready to Use)

Opening:
"This project solves DNA pattern matching using deterministic finite automata."

Flow:
1. "We input a DNA pattern and genome sequence."
2. "System builds DFA transition table for the pattern."
3. "Genome is scanned left to right and matches are recorded."
4. "We visualize transitions, match locations, and summary metrics."
5. "We can also load FASTA and optionally use AI-assisted pattern extraction."

Closing:
"This implementation is aligned with our proposal and demonstrates automata theory in a real bioinformatics workflow."

---

## 4. Final Submission Checklist (LMS)

Before upload, verify all below:
- PPT file created and finalized
- Team details slide included
- Problem slide included
- Solution with original diagrams included
- Proposal alignment slide included
- Demo video uploaded on YouTube and link added
- Public GitHub link added
- PPT exported with working hyperlinks
- File name follows class format (if specified)
- Submission done before 15 April 2026 deadline

---

## 5. Suggested PPT File Name
TEAM_<TeamName>_DNA_DFA_Project_Apr15_2026.pptx

---

## 6. Optional Add-On (If You Have Time)
Add one backup slide named "Technical Appendix" with:
- DFA transition table snapshot
- One trace snippet (state transitions)
- One test summary screenshot

This helps during viva questions.
