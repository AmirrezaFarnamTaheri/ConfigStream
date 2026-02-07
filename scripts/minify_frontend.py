#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import logging

try:
    import rjsmin
    import rcssmin
except ImportError:
    print("Error: rjsmin and rcssmin are required. Install with: pip install rjsmin rcssmin")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def minify_frontend(frontend_dir: Path):
    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found: {frontend_dir}")
        return

    assets_dir = frontend_dir / "assets"
    if not assets_dir.exists():
        logger.error(f"Assets directory not found: {assets_dir}")
        return

    logger.info(f"Minifying assets in {assets_dir}")

    # Minify JS
    for js_file in assets_dir.rglob("*.js"):
        if js_file.name.endswith(".min.js"):
            continue

        try:
            content = js_file.read_text(encoding="utf-8")
            minified = rjsmin.jsmin(content)
            # Overwrite original file for deployment
            js_file.write_text(minified, encoding="utf-8")
            logger.info(f"Minified JS: {js_file.relative_to(frontend_dir)}")
        except Exception as e:
            logger.error(f"Failed to minify {js_file}: {e}")

    # Minify CSS
    for css_file in assets_dir.rglob("*.css"):
        if css_file.name.endswith(".min.css"):
            continue

        try:
            content = css_file.read_text(encoding="utf-8")
            minified = rcssmin.cssmin(content)
            css_file.write_text(minified, encoding="utf-8")
            logger.info(f"Minified CSS: {css_file.relative_to(frontend_dir)}")
        except Exception as e:
            logger.error(f"Failed to minify {css_file}: {e}")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    frontend_path = base_dir / "frontend"
    minify_frontend(frontend_path)
