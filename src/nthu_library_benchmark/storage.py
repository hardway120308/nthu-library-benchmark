from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

DEFAULT_RECORD_PATH = Path("storage/records.txt")
RECORD_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


class Storage:
    """Persist benchmark completion records in a timestamped text file."""

    def __init__(self, path: str | Path = DEFAULT_RECORD_PATH) -> None:
        base_path = Path(path)
        timestamp = datetime.now(UTC).strftime(RECORD_TIMESTAMP_FORMAT)
        self.file_path = base_path.with_name(
            f"{base_path.stem}_{timestamp}{base_path.suffix}"
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: str) -> None:
        """Append one record and terminate it with a newline."""
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(f"{record}\n")
