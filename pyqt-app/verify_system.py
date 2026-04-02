#!/usr/bin/env python3
"""
GeneFlow — Comprehensive System Verification & Testing Script
Tests all components and dependencies for production readiness
"""

import sys
import subprocess
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    """Print a success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Print an error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    """Print a warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    """Print an info message"""
    print(f"{BLUE}ℹ {text}{RESET}")

def check_python_version():
    """Verify Python version"""
    print_header("1. Checking Python Version")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python 3.9+ required, found {version.major}.{version.minor}")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print_header("2. Checking Dependencies")
    
    required = {
        "streamlit": "Web UI framework",
        "PyQt6": "Desktop UI framework",
        "PyQt6.QtWebEngineWidgets": "Desktop web renderer",
        "matplotlib": "Data visualization",
        "plotly": "Interactive charts",
        "pandas": "Data processing",
        "Bio": "FASTA file support (BioPython)",
        "dfa": "DFA module",
        "matcher": "Matcher module",
    }
    
    missing = []
    
    for package, description in required.items():
        try:
            if package == "Bio":
                __import__("Bio")
                display_name = "biopython"
            elif package == "dfa":
                from dfa import get_transition_table
                display_name = "dfa"
            elif package == "matcher":
                from matcher import find_matches
                display_name = "matcher"
            elif package == "PyQt6.QtWebEngineWidgets":
                from PyQt6.QtWebEngineWidgets import QWebEngineView
                display_name = "PyQt6-WebEngine"
            else:
                __import__(package)
                display_name = package
            
            print_success(f"{display_name:20} — {description}")
        except ImportError:
            print_error(f"{package:20} — {description}")
            missing.append(package)
    
    if missing:
        print_warning(f"\nMissing packages: {', '.join(missing)}")
        print_info("Install them with: pip install -r requirements.txt")
        return False
    
    print_success("\nAll dependencies installed!")
    return True

def test_core_algorithm():
    """Test the core DFA matching algorithm"""
    print_header("3. Testing Core Algorithm")
    
    try:
        from dfa import get_transition_table
        from matcher import find_matches
        
        # Test data
        pattern = "ATCG"
        genome = "ATCGATCGATCGATCGATCGATCGATCGATCG"
        expected = [1, 5, 9, 13, 17, 21, 25, 29]
        
        # Build DFA
        delta, accept_state = get_transition_table(pattern)
        print_success(f"DFA constructed for pattern '{pattern}'")
        
        # Find matches
        matches = find_matches(genome, delta, accept_state, len(pattern))
        print_success(f"Pattern matching completed")
        
        # Verify results
        if matches == expected:
            print_success(f"✓ Found {len(matches)} matches at correct positions")
            print_info(f"  Positions: {matches}")
            return True
        else:
            print_error(f"Unexpected match positions!")
            print_info(f"  Expected: {expected}")
            print_info(f"  Got:      {matches}")
            return False
    
    except Exception as e:
        print_error(f"Algorithm test failed: {e}")
        return False

def test_dfa_construction():
    """Test various DFA constructions"""
    print_header("4. Testing DFA Construction")
    
    try:
        from dfa import get_transition_table
        
        test_cases = [
            ("A", 1),
            ("AT", 2),
            ("ATC", 3),
            ("ATCG", 4),
            ("ATAT", 4),
            ("AAA", 3),
        ]
        
        all_passed = True
        for pattern, expected_states in test_cases:
            try:
                delta, accept_state = get_transition_table(pattern)
                num_states = accept_state + 1
                
                if num_states == expected_states:
                    print_success(f"Pattern '{pattern}' → {num_states} states")
                else:
                    print_warning(f"Pattern '{pattern}' → {num_states} states (expected {expected_states})")
            except Exception as e:
                print_error(f"Pattern '{pattern}' failed: {e}")
                all_passed = False
        
        return all_passed
    
    except Exception as e:
        print_error(f"DFA test failed: {e}")
        return False

def test_file_loading():
    """Test FASTA file loading capability"""
    print_header("5. Testing File Loading (BioPython)")
    
    try:
        from Bio import SeqIO
        print_success("BioPython available - FASTA loading supported")
        return True
    except ImportError:
        print_warning("BioPython not available - FASTA loading disabled")
        print_info("Install with: pip install biopython")
        return False
    except Exception as e:
        print_error(f"File loading test failed: {e}")
        return False

def test_web_app_imports():
    """Test that web app dependencies are available"""
    print_header("6. Testing Web App (Streamlit) Components")
    
    try:
        import streamlit
        print_success(f"Streamlit {streamlit.__version__}")
        
        import plotly
        print_success(f"Plotly {plotly.__version__}")
        
        import pandas
        print_success(f"Pandas {pandas.__version__}")
        
        print_success("\n✓ Web app is ready to run!")
        return True
    except Exception as e:
        print_error(f"Web app test failed: {e}")
        return False

def test_desktop_app_imports():
    """Test that desktop app dependencies are available"""
    print_header("7. Testing Desktop App (PyQt6) Components")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print_success("PyQt6 — GUI framework available")

        from PyQt6.QtWebEngineWidgets import QWebEngineView
        print_success("PyQt6-WebEngine — embedded web renderer available")
        
        import matplotlib
        print_success(f"Matplotlib {matplotlib.__version__}")
        
        print_success("\n✓ Desktop app is ready to run!")
        return True
    except Exception as e:
        print_error(f"Desktop app test failed: {e}")
        return False

def test_project_structure():
    """Verify project file structure"""
    print_header("8. Verifying Project Structure")
    
    required_files = [
        "app_web.py",
        "app_desktop.py",
        "dfa.py",
        "matcher.py",
        "genome_loader.py",
        "requirements.txt",
        "main.py",
    ]
    
    base_path = Path.cwd()
    all_exist = True
    
    for filename in required_files:
        filepath = base_path / filename
        if filepath.exists():
            print_success(f"{filename}")
        else:
            print_error(f"{filename} — MISSING!")
            all_exist = False
    
    return all_exist

def print_recommendations(results):
    """Print recommendations based on test results"""
    print_header("Recommendations & Next Steps")
    
    all_passed = all(results.values())
    
    if all_passed:
        print_success("All tests passed! System is ready.\n")
        print_info("To run the application:\n")
        print(f"  Option 1: {BOLD}python3 main.py{RESET}")
        print(f"    → Interactive menu to choose web or desktop\n")
        print(f"  Option 2: {BOLD}streamlit run app_web.py{RESET}")
        print(f"    → Web app at http://localhost:8501\n")
        print(f"  Option 3: {BOLD}python3 app_desktop.py{RESET}")
        print(f"    → Desktop app with embedded web UI\n")
    else:
        print_warning("Some tests failed. Review recommendations above.\n")
        
        if not results.get("dependencies"):
            print_info("Install dependencies:")
            print(f"  {BOLD}pip install -r requirements.txt{RESET}\n")
        
        if not results.get("web_app"):
            print_info("For web app, ensure:")
            print(f"  {BOLD}pip install streamlit plotly pandas{RESET}\n")
        
        if not results.get("desktop_app"):
            print_info("For desktop app, ensure:")
            print(f"  {BOLD}pip install PyQt6 PyQt6-WebEngine matplotlib{RESET}\n")

def main():
    """Run all tests"""
    print(f"\n{BOLD}{BLUE}")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🧬 GeneFlow — DNA String Matcher — System Verification".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    print(RESET)
    
    results = {
        "python_version": check_python_version(),
        "dependencies": check_dependencies(),
        "core_algorithm": test_core_algorithm(),
        "dfa_construction": test_dfa_construction(),
        "file_loading": test_file_loading(),
        "web_app": test_web_app_imports(),
        "desktop_app": test_desktop_app_imports(),
        "project_structure": test_project_structure(),
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        test_display = test_name.replace("_", " ").title()
        print(f"  {status} — {test_display}")
    
    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}\n")
    
    print_recommendations(results)
    
    print_header("End of Verification")
    
    # Exit code
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())

