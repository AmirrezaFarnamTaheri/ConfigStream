import sys
import re

def minify_html(content):
    # Remove comments
    content = re.sub(r'<!--(.*?)-->', '', content, flags=re.DOTALL)
    # Remove whitespace between tags
    content = re.sub(r'>\s+<', '><', content)
    # Collapse multiple spaces
    content = re.sub(r'\s+', ' ', content)
    return content.strip()

def minify_css(content):
    # Remove comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove whitespace
    content = re.sub(r'\s*([:;{}])\s*', r'\1', content)
    return content.strip()

def main():
    if len(sys.argv) < 2:
        print("Usage: python minify_frontend.py <file>")
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath, 'r') as f:
        content = f.read()

    if filepath.endswith('.html'):
        minified = minify_html(content)
    elif filepath.endswith('.css'):
        minified = minify_css(content)
    else:
        minified = content

    with open(filepath, 'w') as f:
        f.write(minified)

if __name__ == "__main__":
    main()
