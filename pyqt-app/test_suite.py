#!/usr/bin/env python3
"""
GeneFlow — Advanced Testing Suite
Complete test coverage with real bioinformatics examples
"""

import sys
import time
from pathlib import Path

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_test(name, desc=""):
    """Print test header"""
    print(f"\n{BOLD}{BLUE}TEST: {name}{RESET}")
    if desc:
        print(f"  Description: {desc}")

def test_result(passed, message):
    """Print test result"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} — {message}")
    return passed

# ============================================================================
# TEST SUITE 1: BASIC FUNCTIONALITY
# ============================================================================

def test_single_base():
    """Test matching single base"""
    print_test("Single Base Matching", "Find all 'A' bases")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "A"
    genome = "ATCGATCGATCGATCGATCG"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 5
    return test_result(len(matches) == expected, 
                       f"Found {len(matches)} 'A' bases (expected {expected})")

def test_two_base_pattern():
    """Test matching 2-base pattern"""
    print_test("Two-Base Pattern", "Find all 'AT' patterns")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "AT"
    genome = "ATATATATAT"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 5
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} 'AT' patterns (expected {expected})")

def test_no_matches():
    """Test pattern with no matches"""
    print_test("No Matches Test", "Pattern that doesn't exist")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "GGG"
    genome = "ATCATCATCATCATCATC"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    return test_result(len(matches) == 0,
                       f"Found {len(matches)} matches (expected 0)")

# ============================================================================
# TEST SUITE 2: REAL BIOINFORMATICS PATTERNS
# ============================================================================

def test_tata_box():
    """Test TATA box detection (promoter region)"""
    print_test("TATA Box Detection", "Find TATA box promoter patterns")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "TATA"
    # Simulated promoter regions
    genome = "ATCGATAGCCGTATAATGCGATACGTATAAGC"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 2
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} TATA boxes (expected {expected})")

def test_start_codon():
    """Test ATG start codon detection"""
    print_test("Start Codon Detection", "Find ATG start codons")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "ATG"
    # Multiple start codons
    genome = "ATGATGATGATGATGATGATGC"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 7
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} ATG codons (expected {expected})")

def test_stop_codon():
    """Test TAA stop codon detection"""
    print_test("Stop Codon Detection", "Find TAA stop codons")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "TAA"
    # Multiple stop codons
    genome = "ATATAATAATAATAACGAT"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 3
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} TAA codons (expected {expected})")

# ============================================================================
# TEST SUITE 3: EDGE CASES
# ============================================================================

def test_pattern_at_boundaries():
    """Test pattern at genome boundaries"""
    print_test("Boundary Pattern Detection", "Pattern at start and end")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "ATC"
    genome = "ATCGATCGATCGATC"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    # Should find at positions 1, 5, 9, 13
    expected = 4
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} matches (expected {expected})")

def test_overlapping_patterns():
    """Test overlapping pattern matches"""
    print_test("Overlapping Pattern Test", "Patterns with overlap")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "AA"
    genome = "AAAAAA"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 5
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} overlapping 'AA' (expected {expected})")

def test_repeat_pattern():
    """Test highly repetitive pattern"""
    print_test("Repeat Pattern Test", "Pattern that repeats")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "ATCG"
    genome = "ATCGATCGATCGATCGATCGATCGATCG"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    expected = 7
    return test_result(len(matches) == expected,
                       f"Found {len(matches)} ATCG repeats (expected {expected})")

# ============================================================================
# TEST SUITE 4: PERFORMANCE TESTS
# ============================================================================

def test_large_genome_performance():
    """Test performance on large genome"""
    print_test("Large Genome Performance", "1MB genome matching")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "ATCG"
    # Create 1MB genome
    base_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    genome = base_sequence * (1_000_000 // len(base_sequence))
    
    start = time.time()
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    elapsed = time.time() - start
    
    result = test_result(elapsed < 5.0,
                         f"Processed {len(genome):,} bases in {elapsed:.3f}s")
    print(f"  Matches found: {len(matches):,}")
    return result

def test_dfa_construction_performance():
    """Test DFA construction speed"""
    print_test("DFA Construction Performance", "Build DFA for long pattern")
    
    from dfa import get_transition_table
    
    patterns = [
        ("A", 1),
        ("AT", 2),
        ("ATC", 3),
        ("ATCG", 4),
        ("ATCGAT", 6),
        ("ATCGATCG", 8),
    ]
    
    all_fast = True
    for pattern, length in patterns:
        start = time.time()
        delta, accept = get_transition_table(pattern)
        elapsed = time.time() - start
        
        fast = elapsed < 0.1
        all_fast = all_fast and fast
        status = "✓" if fast else "⚠"
        print(f"  {status} Pattern {pattern:10} ({length} bases): {elapsed*1000:.2f}ms")
    
    return test_result(all_fast, "All DFA constructions are fast")

# ============================================================================
# TEST SUITE 5: CORRECTNESS VALIDATION
# ============================================================================

def test_match_positions_correct():
    """Verify match positions are accurate"""
    print_test("Match Position Accuracy", "Verify each match is correct")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    pattern = "ATCG"
    genome = "CATCGATCGATCGATCGATCG"
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    # Verify each match
    all_correct = True
    for match_pos in matches:
        # Extract substring at match position (1-indexed)
        start = match_pos - 1
        end = start + len(pattern)
        substring = genome[start:end]
        if substring != pattern:
            all_correct = False
            print(f"  ✗ Position {match_pos}: expected '{pattern}', got '{substring}'")
    
    return test_result(all_correct,
                       f"All {len(matches)} matches verified correct")

def test_complete_coverage():
    """Test that all occurrences are found"""
    print_test("Complete Match Coverage", "Find every occurrence")
    
    pattern = "AT"
    genome = "ATATATATATAT"
    
    # Manual count
    expected_count = 0
    for i in range(len(genome) - len(pattern) + 1):
        if genome[i:i+len(pattern)] == pattern:
            expected_count += 1
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    delta, accept = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept, len(pattern))
    
    return test_result(len(matches) == expected_count,
                       f"Found {len(matches)} matches (manual count: {expected_count})")

# ============================================================================
# TEST SUITE 6: INPUT VALIDATION
# ============================================================================

def test_invalid_dna_bases():
    """Test handling of invalid DNA bases"""
    print_test("Invalid DNA Base Handling", "Pattern with invalid characters")
    
    from dfa import get_transition_table
    
    try:
        pattern = "ATXG"  # X is invalid
        delta, accept = get_transition_table(pattern)
        return test_result(False, "Should have raised error for invalid base")
    except ValueError as e:
        return test_result(True, f"Correctly rejected invalid base: {e}")
    except Exception as e:
        return test_result(False, f"Wrong error type: {e}")

def test_empty_pattern():
    """Test handling of empty pattern"""
    print_test("Empty Pattern Handling", "Pattern with no bases")
    
    from dfa import get_transition_table
    
    try:
        pattern = ""
        delta, accept = get_transition_table(pattern)
        return test_result(False, "Should have raised error for empty pattern")
    except ValueError:
        return test_result(True, "Correctly rejected empty pattern")
    except Exception as e:
        return test_result(False, f"Wrong error type: {e}")

def test_case_insensitivity():
    """Test that lowercase input is handled"""
    print_test("Case Insensitivity", "Lowercase input conversion")
    
    from dfa import get_transition_table
    from matcher import find_matches
    
    try:
        pattern = "atcg"  # lowercase
        genome = "ATCGATCGATCG"
        delta, accept = get_transition_table(pattern)
        matches = find_matches(genome.upper(), delta, accept, len(pattern))
        return test_result(len(matches) > 0, "Lowercase pattern handled correctly")
    except Exception as e:
        return test_result(False, f"Error: {e}")

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run complete test suite"""
    
    print(f"\n{BOLD}{BLUE}")
    print("╔" + "="*70 + "╗")
    print("║" + " "*70 + "║")
    print("║" + "  🧬 GeneFlow — Advanced Testing Suite".center(70) + "║")
    print("║" + " "*70 + "║")
    print("╚" + "="*70 + "╝")
    print(RESET)
    
    results = {}
    
    # Basic Functionality Tests
    print(f"\n{BOLD}{BLUE}SUITE 1: Basic Functionality{RESET}")
    results["Single Base"] = test_single_base()
    results["Two Bases"] = test_two_base_pattern()
    results["No Matches"] = test_no_matches()
    
    # Bioinformatics Tests
    print(f"\n{BOLD}{BLUE}SUITE 2: Real Bioinformatics Patterns{RESET}")
    results["TATA Box"] = test_tata_box()
    results["Start Codon"] = test_start_codon()
    results["Stop Codon"] = test_stop_codon()
    
    # Edge Cases
    print(f"\n{BOLD}{BLUE}SUITE 3: Edge Cases{RESET}")
    results["Boundaries"] = test_pattern_at_boundaries()
    results["Overlapping"] = test_overlapping_patterns()
    results["Repeating"] = test_repeat_pattern()
    
    # Performance
    print(f"\n{BOLD}{BLUE}SUITE 4: Performance{RESET}")
    results["Large Genome"] = test_large_genome_performance()
    results["DFA Speed"] = test_dfa_construction_performance()
    
    # Correctness
    print(f"\n{BOLD}{BLUE}SUITE 5: Correctness Validation{RESET}")
    results["Position Accuracy"] = test_match_positions_correct()
    results["Coverage"] = test_complete_coverage()
    
    # Input Validation
    print(f"\n{BOLD}{BLUE}SUITE 6: Input Validation{RESET}")
    results["Invalid Bases"] = test_invalid_dna_bases()
    results["Empty Pattern"] = test_empty_pattern()
    results["Case Insensitivity"] = test_case_insensitivity()
    
    # Summary
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}Test Summary{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status} — {test_name}")
    
    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{BOLD}✓ All tests passed! System is fully functional.{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{BOLD}✗ Some tests failed. Review output above.{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())

