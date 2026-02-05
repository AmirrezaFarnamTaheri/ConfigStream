with open('src/configstream/intelligence/washer/core.py', 'r') as f:
    lines = f.readlines()

with open('src/configstream/intelligence/washer/core.py', 'w') as f:
    for line in lines:
        if line.strip() == ',':
            continue
        f.write(line)
