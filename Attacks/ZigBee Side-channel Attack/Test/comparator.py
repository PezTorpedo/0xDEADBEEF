def generate_mask(samples):
    if not samples:
        return ""

    # Check: all strings must have the same length
    length = len(samples[0])
    if any(len(s) != length for s in samples):
        raise ValueError("All strings must have the same length")

    mask = ""

    for i in range(length):
        # Take all characters at position i
        chars = {s[i] for s in samples}
        
        # If all equal → X, otherwise → 0
        mask += "X" if len(chars) == 1 else "0"

    return mask


# Example usage
samples = [
    '6188a090f6d7915a144802d7915a141ea6282e2553032e305e0501881700008bd409ad37155f9adcbc3e3a6f5b4ab61e8f68db767e9591',
    '6188b490f6d7915a144802d7915a141ebb28422553032e305e050188170000a3c774d1f7b8f4398976b688bb8bdad6a410b715caebad5d',
    '6188cb90f6d7915a144802d7915a141ed228592553032e305e0501881700009e959a8f447ee91f6026f3ba55a4b1e0a49078cca9a1aebf'
]
print(generate_mask(samples))  # Output: 0X0
