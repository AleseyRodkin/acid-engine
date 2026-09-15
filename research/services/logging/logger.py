"""Structured execution logging."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from acid_engine.level3.container.observation import ExecutionObservation


class ExecutionLogger:
    """Write execution records to a JSON file (one line per run)."""

    def __init__(self, log_path: str | Path = "execution_log.jsonl"):
        self.log_path = Path(log_path)

    def log(self, obs: ExecutionObservation, extra: dict[str, Any] | None = None) -> None:
        entry = {
            "run_id": obs.run_id,
            "timestamp": time.time(),
            "status": obs.status,
            "latency_ms": round(obs.latency_ms, 3),
            "input_hash": obs.input_hash,
            "output_hash": obs.output_hash,
            "trace": list(obs.trace),
        }
        if extra:
            entry["extra"] = extra
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        records = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records