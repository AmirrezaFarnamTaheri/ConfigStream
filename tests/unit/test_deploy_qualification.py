import subprocess
import sys
from pathlib import Path


def test_validator_dependencies_resolvable():
    """Verify that validate_frontend_placeholders can be imported cleanly without missing dependencies."""
    script_path = Path("scripts/validate_frontend_placeholders.py")
    assert script_path.exists(), "validate_frontend_placeholders.py missing"

    result = subprocess.run(
        [sys.executable, "-c", "import configstream.security_validator; import pydantic_settings"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"
