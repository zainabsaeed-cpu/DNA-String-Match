from dfa import build_dfa

def dfa_match(text, pattern):
    dfa = build_dfa(pattern)
    state = 0
    positions = []

    for i in range(len(text)):
        state = dfa[state].get(text[i], 0)

        if state == len(pattern):
            positions.append(i - len(pattern) + 1)

    return positions