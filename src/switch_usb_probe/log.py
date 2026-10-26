"""Small JSONL logger with redaction at the boundary."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, TextIO

from .redact import redact_mapping

LEVELS = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
}


class JsonlLogger:
    """Write one JSON object per line to a stream.

    Logs go to stderr (or a file), never stdout, so ``--json`` output remains
    machine-readable.  Every field is passed through ``redact_mapping``.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        *,
        level: str = "info",
        clock: Any = time.time,
    ) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.level = level.lower()
        if self.level not in LEVELS:
            raise ValueError(f"unknown log level: {level}")
        self.clock = clock

    def enabled(self, level: str) -> bool:
        return LEVELS[level.lower()] >= LEVELS[self.level]

    def log(self, event: str, *, level: str = "info", **fields: Any) -> None:
        normalized = level.lower()
        if normalized not in LEVELS:
            raise ValueError(f"unknown log level: {level}")
        if not self.enabled(normalized):
            return
        timestamp = datetime.fromtimestamp(
            float(self.clock()), tz=timezone.utc
        ).isoformat(timespec="milliseconds")
        record = {
            "ts": timestamp.replace("+00:00", "Z"),
            "level": normalized,
            "event": event,
            **redact_mapping(fields),
        }
        try:
            print(
                json.dumps(record, sort_keys=True, ensure_ascii=False),
                file=self.stream,
                flush=True,
            )
        except (BrokenPipeError, ValueError):
            # Logging must never turn a successful inspection into a failure.
            return

    def debug(self, event: str, **fields: Any) -> None:
        self.log(event, level="debug", **fields)

    def info(self, event: str, **fields: Any) -> None:
        self.log(event, level="info", **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.log(event, level="warning", **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log(event, level="error", **fields)


class NullLogger(JsonlLogger):
    """Logger that discards records; useful for pure tests."""

    def __init__(self) -> None:
        super().__init__(stream=sys.stderr, level="error")

    def log(self, event: str, *, level: str = "info", **fields: Any) -> None:
        return
