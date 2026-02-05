# SPDX-License-Identifier: AGPL-3.0-or-later
"""
HTML Smuggling Tool: Embeds proxy configs in HTML files for distribution.

This tool hides configs inside legitimate-looking HTML pages to evade
automated text scanners that detect base64 strings or JSON files.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Site Maintenance</title>
    <meta name="csrf-token" content="{BASE64_CONFIG}">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }}
        .container {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 500px;
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 1rem;
        }}
        p {{
            color: #666;
            line-height: 1.6;
        }}
        button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            margin-top: 1rem;
            transition: background 0.3s;
        }}
        button:hover {{
            background: #5568d3;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>System Maintenance</h1>
        <p>Our engineers are updating the server. Please check back later.</p>
        <button onclick="copyConfig()">Copy Reference ID</button>
        <p id="status" class="hidden" style="color: green; margin-top: 1rem;"></p>
    </div>
    <script>
        function copyConfig() {{
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (!meta) {{
                alert('Reference ID not found');
                return;
            }}
            const cfg = meta.content;
            try {{
                // Decode base64
                const decoded = atob(cfg);
                navigator.clipboard.writeText(decoded).then(() => {{
                    const status = document.getElementById('status');
                    status.textContent = 'Reference ID copied to clipboard!';
                    status.classList.remove('hidden');
                    setTimeout(() => {{
                        status.classList.add('hidden');
                    }}, 3000);
                }}).catch(err => {{
                    // Fallback for older browsers
                    const textarea = document.createElement('textarea');
                    textarea.value = decoded;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    const status = document.getElementById('status');
                    status.textContent = 'Reference ID copied!';
                    status.classList.remove('hidden');
                    setTimeout(() => {{
                        status.classList.add('hidden');
                    }}, 3000);
                }});
            }} catch (e) {{
                alert('Failed to decode reference ID');
            }}
        }}
    </script>
</body>
</html>
"""


def create_html_smuggled_config(
    config_content: str,
    output_path: Path,
    template: Optional[str] = None,
) -> Path:
    """
    Create an HTML file with embedded config.

    Args:
        config_content: The config content to embed (JSON, base64, etc.)
        output_path: Path where the HTML file should be written
        template: Optional custom HTML template (uses default if None)

    Returns:
        Path to the created HTML file
    """
    # Encode config as base64
    encoded = base64.b64encode(config_content.encode("utf-8")).decode("utf-8")

    # Use provided template or default
    html_content = (template or HTML_TEMPLATE).format(BASE64_CONFIG=encoded)

    # Write HTML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

    logger.info(f"Created HTML smuggled config at {output_path}")
    return output_path


def extract_config_from_html(html_path: Path) -> Optional[str]:
    """
    Extract config from an HTML file.

    Args:
        html_path: Path to the HTML file

    Returns:
        Decoded config content or None if extraction fails
    """
    try:
        html_content = html_path.read_text(encoding="utf-8")
        
        # Try to find base64 in meta tag
        import re
        match = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', html_content)
        if match:
            encoded = match.group(1)
            decoded = base64.b64decode(encoded).decode("utf-8")
            return decoded
        
        logger.warning(f"Could not find config in HTML file: {html_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to extract config from HTML: {e}")
        return None

