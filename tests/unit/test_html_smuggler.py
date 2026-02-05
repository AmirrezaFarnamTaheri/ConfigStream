# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for HTML smuggler."""

import pytest
import base64
import tempfile
from pathlib import Path
from configstream.tools.html_smuggler import (
    create_html_smuggled_config,
    extract_config_from_html,
)


class TestHTMLSmuggler:
    """Test HTML smuggling functionality."""

    def test_create_html_smuggled_config(self):
        """Test creating HTML with embedded config."""
        config_content = '{"test": "config"}'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.html"
            result_path = create_html_smuggled_config(
                config_content,
                output_path,
            )
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Verify HTML contains base64 encoded config
            html_content = output_path.read_text()
            assert "csrf-token" in html_content
            assert "System Maintenance" in html_content
            
            # Verify config is base64 encoded
            import re
            match = re.search(r'content="([^"]+)"', html_content)
            if match:
                encoded = match.group(1)
                decoded = base64.b64decode(encoded).decode("utf-8")
                assert decoded == config_content

    def test_extract_config_from_html(self):
        """Test extracting config from HTML."""
        config_content = '{"test": "config"}'
        encoded = base64.b64encode(config_content.encode("utf-8")).decode("utf-8")
        
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta name="csrf-token" content="{encoded}">
</head>
<body></body>
</html>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_path = Path(f.name)
        
        try:
            result = extract_config_from_html(temp_path)
            assert result == config_content
        finally:
            temp_path.unlink()

    def test_extract_config_not_found(self):
        """Test extraction when config not found."""
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>No Config</title>
</head>
<body></body>
</html>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_path = Path(f.name)
        
        try:
            result = extract_config_from_html(temp_path)
            assert result is None
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

