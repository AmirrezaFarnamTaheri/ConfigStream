# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path


def test_server_exposes_separate_liveness_and_readiness_contracts() -> None:
    source = Path("src/configstream/server/__init__.py").read_text(encoding="utf-8")
    assert "from pathlib import Path" in source
    assert '@app.get("/live")' in source
    assert '@app.get("/ready")' in source
    assert "evaluate_runtime_health" in source
    assert "status_code=status_code" in source
    assert "asyncio.to_thread" in source


def test_render_uses_process_liveness_not_artifact_readiness() -> None:
    blueprint = Path("render.yaml").read_text(encoding="utf-8")
    assert "healthCheckPath: /live" in blueprint


def test_server_package_has_an_executable_container_entrypoint() -> None:
    source = Path("src/configstream/server/__main__.py").read_text(encoding="utf-8")
    assert 'uvicorn.run(' in source
    assert '"configstream.server:app"' in source
    assert 'os.getenv("PORT", "8000")' in source
    assert 'if __name__ == "__main__":' in source
