import sys
from pathlib import Path

def setup_python_path():
    root_dir = Path(__file__).parent.parent.parent
    src_dir = str(root_dir / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    return root_dir
