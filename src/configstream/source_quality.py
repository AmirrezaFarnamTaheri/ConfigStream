import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict

logger = logging.getLogger(__name__)

@dataclass
class SourceHealth:
    url: str
    failures: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0
    status: str = "active"  # active, probation, dead

class SourceQualityTracker:
    def __init__(self, db_path: Path = Path("data/source_health.json")):
        self.db_path = db_path
        self.sources: Dict[str, SourceHealth] = self._load_db()

    def _load_db(self) -> Dict[str, SourceHealth]:
        if not self.db_path.exists():
            return {}
        try:
            data = json.loads(self.db_path.read_text())
            return {url: SourceHealth(**props) for url, props in data.items()}
        except Exception:
            return {}

    def save(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            data = {url: asdict(health) for url, health in self.sources.items()}
            self.db_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save source health db: {e}")

    def report_success(self, url: str):
        if url not in self.sources:
            self.sources[url] = SourceHealth(url=url)

        record = self.sources[url]
        record.failures = 0
        record.last_success = datetime.now(timezone.utc).timestamp()
        record.status = "active"
        self.save()

    def report_failure(self, url: str):
        if url not in self.sources:
            self.sources[url] = SourceHealth(url=url)

        record = self.sources[url]
        record.failures += 1
        record.last_failure = datetime.now(timezone.utc).timestamp()

        # LOGIC: 3 strikes = Probation, 10 strikes = Dead
        if record.failures >= 10:
            if record.status != "dead":
                record.status = "dead"
                logger.error(f"💀 Source marked DEAD: {url}")
        elif record.failures >= 3:
            if record.status != "probation":
                record.status = "probation"
                logger.warning(f"⚠️ Source on PROBATION: {url}")

        self.save()

    def should_fetch(self, url: str) -> bool:
        """Decides if a source is worthy of bandwidth."""
        if url not in self.sources:
            return True  # New source, give it a chance

        record = self.sources[url]
        if record.status == "dead":
            # Optional: Allow resurrection check every week?
            # For now, dead is dead.
            return False

        if record.status == "probation":
            # Exponential backoff: Retry once every 6 hours
            cooldown = 6 * 3600
            # If time since last failure is less than cooldown, skip
            if (datetime.now(timezone.utc).timestamp() - record.last_failure) < cooldown:
                return False

        return True
