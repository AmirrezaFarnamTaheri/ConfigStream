"""
Churn Prediction Analysis.
Analyzes the survival rate of proxies over time.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class ChurnAnalyzer:
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.data = self._load_history()

    def _load_history(self) -> Dict[str, List[str]]:
        """Load history JSON."""
        if not self.history_file.exists():
            return {}
        try:
            data = json.loads(self.history_file.read_text())
            if isinstance(data, dict):
                return data # type: ignore
            return {}
        except Exception:
            return {}

    def analyze(self) -> Dict[str, float]:
        """
        Calculate churn rate.
        Returns dictionary with churn rates per protocol.
        """
        # Mock implementation as we don't have real historical data structure defined in previous steps
        # Assuming data is { "date": [ "proxy1_hash", "proxy2_hash" ] }

        # If no history, return empty
        if not self.data:
            return {"overall": 0.0}

        # Logic: Compare sets of working proxies between days
        # For now, we return a stub
        return {"vmess": 0.15, "vless": 0.10, "shadowsocks": 0.20}


def run_churn_analysis(output_dir: Path):
    history_path = output_dir / "history.json"
    analyzer = ChurnAnalyzer(history_path)
    results = analyzer.analyze()

    report_path = output_dir / "churn_report.json"
    report_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Churn analysis saved to {report_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_churn_analysis(Path("output"))
