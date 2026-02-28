from matcher import dfa_match

def main():
    genome = "GATCGATCGGATCG"
    pattern = "ATCG"

    matches = dfa_match(genome, pattern)

    print("Pattern found at positions:", matches)

if __name__ == "__main__":
    main()