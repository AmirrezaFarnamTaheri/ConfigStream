import os
import subprocess
import sys
from pathlib import Path


def test_validator_dependencies_resolvable():
    """Verify that validate_frontend_placeholders can be imported cleanly without missing dependencies."""
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "validate_frontend_placeholders.py"
    assert script_path.exists(), "validate_frontend_placeholders.py missing"

    env = dict(os.environ)
    src_dir = str(root / "src")
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing_pp}" if existing_pp else src_dir

    result = subprocess.run(
        [sys.executable, "-c", "import configstream.security_validator; import pydantic_settings"],
        capture_output=True,
        text=True,
        cwd=str(root),
        env=env,
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"


def test_live_pages_smoke_receives_candidate_identity_and_public_key() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "deploy-pages.yml").read_text(
        encoding="utf-8"
    )
    assert "--expected-commit \"$EXPECTED_SOURCE_SHA\"" in workflow
    assert "--expected-run-id \"$EXPECTED_SOURCE_RUN_ID\"" in workflow
    assert "--expected-digest \"$manifest_digest\"" in workflow
    assert "CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}" in workflow
    assert "CS_PUBLIC_KEY is required to verify the signed deployed artifact" in workflow
