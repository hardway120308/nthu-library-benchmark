from datetime import UTC, datetime
from pathlib import Path


class Storage:
    def __init__(self, path: str = "storage/records.txt"):
        base_path = Path(path)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.file_path = base_path.with_name(
            f"{base_path.stem}_{timestamp}{base_path.suffix}"
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.touch(exist_ok=True)

    def record_new_line_to_file(self, data: str) -> bool:
        if not self.check_need_record(data):
            return False
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(f"{data}\n")
        return True

    def check_need_record(self, data: str) -> bool:
        return "DONE" in data
