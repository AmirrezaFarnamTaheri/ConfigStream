import os

def redistribute():
    sources_dir = 'sources'
    batch_4_path = os.path.join(sources_dir, 'batch_4.txt')

    with open(batch_4_path, 'r') as f:
        lines = f.readlines()
        lines = [l.strip() for l in lines if l.strip()]

    if len(lines) < 33:
        print(f"Error: Batch 4 only has {len(lines)} lines, cannot remove 33.")
        return

    to_move = lines[:33]
    remaining = lines[33:]

    print(f"Moving {len(to_move)} sources from Batch 4.")

    # Update Batch 4
    with open(batch_4_path, 'w') as f:
        f.write('\n'.join(remaining) + '\n')

    # Distribution Plan
    # 8 -> 11
    # 4 -> 2, 3, 5, 6, 8
    # 1 -> 1, 7, 9, 10
    # 1 -> 11 (extra)

    distribution = {
        'batch_11.txt': 8,
        'batch_2.txt': 4,
        'batch_3.txt': 4,
        'batch_5.txt': 4,
        'batch_6.txt': 4,
        'batch_8.txt': 4,
        'batch_1.txt': 1,
        'batch_7.txt': 1,
        'batch_9.txt': 1,
        'batch_10.txt': 1
    }

    # We have 33 sources.
    # Sum of distribution: 8+4+4+4+4+4+1+1+1+1 = 32.
    # One left. Add to batch 11.
    distribution['batch_11.txt'] += 1 # Now 9

    current_idx = 0

    for filename, count in distribution.items():
        chunk = to_move[current_idx : current_idx + count]
        current_idx += count

        path = os.path.join(sources_dir, filename)

        # Read existing to ensure newline
        existing_content = ""
        if os.path.exists(path):
            with open(path, 'r') as f:
                existing_content = f.read()

        with open(path, 'a') as f:
            if existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            f.write('\n'.join(chunk) + '\n')

        print(f"Appended {len(chunk)} sources to {filename}")

    if current_idx != 33:
        print(f"Warning: Distributed {current_idx} out of 33 sources.")
    else:
        print("Successfully distributed all 33 sources.")

if __name__ == '__main__':
    redistribute()
