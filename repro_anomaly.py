# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.anomaly import AnomalyDetector
from pathlib import Path


def test():
    if Path("test_anomaly.db").exists():
        Path("test_anomaly.db").unlink()

    d = AnomalyDetector(Path("test_anomaly.db"))
    url = "http://test"
    for i in range(10):
        d.record(url, 100)

    res = d.is_safe(url, 1000)
    print(f"Result: {res}")


test()
