def build_dfa(pattern):
    alphabet = ['A', 'T', 'C', 'G']
    m = len(pattern)

    dfa = [{char: 0 for char in alphabet} for _ in range(m + 1)]

    for state in range(m + 1):
        for char in alphabet:
            prefix = pattern[:state] + char

            for k in range(min(m, state + 1), -1, -1):
                if prefix.endswith(pattern[:k]):
                    dfa[state][char] = k
                    break

    return dfa