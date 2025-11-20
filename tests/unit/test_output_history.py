import json
from pathlib import Path
from configstream.output import save_history


def test_save_history(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    counts = {"2023-10-01": 100, "2023-10-02": 150}

    save_history(counts, output_dir)

    history_file = output_dir / "history.json"
    assert history_file.exists()

    data = json.loads(history_file.read_text())
    assert data == counts
