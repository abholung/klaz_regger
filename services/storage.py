import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

from services.registration import RegistrationResult


STATE_FILE = Path("state/progress.json")


def save_state(results: Iterable[RegistrationResult]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(result) for result in results]
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> List[RegistrationResult]:
    if not STATE_FILE.exists():
        return []
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return [RegistrationResult(**item) for item in data]


def export_results_csv(path: Path, results: Iterable[RegistrationResult]) -> None:
    results = list(results)
    if not results:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].__dict__.keys())
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)
