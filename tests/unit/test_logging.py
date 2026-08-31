import os
import tempfile

from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.services.logging.logger import ExecutionLogger


def test_logger_writes_and_reads():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as tmp:
        log_path = tmp.name

    try:
        logger = ExecutionLogger(log_path)
        obs = ExecutionObservation.create(
            start=1.0, end=2.0, status="completed",
            input_hash="abc", output_hash="def",
            logger=logger,
        )
        records = logger.read_all()
        assert len(records) == 1
        assert records[0]["run_id"] == obs.run_id
        assert records[0]["status"] == "completed"
    finally:
        os.unlink(log_path)