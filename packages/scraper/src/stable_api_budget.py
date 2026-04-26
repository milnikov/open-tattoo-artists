#!/usr/bin/env python3
"""
Shared token budget for instagram-scraper-stable-api usage across scripts.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


class BudgetExhaustedError(RuntimeError):
    """Raised by retry helpers when the shared stable-API budget cannot be consumed."""


class StableApiBudget:
    def __init__(self, file_path: Path, limit: int, window_seconds: int) -> None:
        self.file_path = file_path
        self.lock_path = file_path.with_suffix(file_path.suffix + ".lock")
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def from_env() -> "StableApiBudget":
        file_path = Path(
            os.environ.get(
                "RAPIDAPI_STABLE_BUDGET_FILE",
                "packages/scraper/stable_api_budget.json",
            )
        )
        limit = int(os.environ.get("RAPIDAPI_STABLE_BUDGET_LIMIT", "50000"))
        window_seconds = int(
            os.environ.get("RAPIDAPI_STABLE_BUDGET_WINDOW_SECONDS", str(30 * 24 * 3600))
        )
        return StableApiBudget(file_path=file_path, limit=limit, window_seconds=window_seconds)

    def _load_state(self) -> dict:
        if not self.file_path.exists():
            return {"window_start": int(time.time()), "used": 0}
        try:
            state = json.loads(self.file_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                # Malformed state: reset, but warn so silent over-spend is visible.
                print(
                    f"[stable_api_budget] {self.file_path}: state is not an object; resetting window.",
                    file=sys.stderr,
                )
                return {"window_start": int(time.time()), "used": 0}
            return {
                "window_start": int(state.get("window_start", int(time.time()))),
                "used": int(state.get("used", 0)),
            }
        except Exception as exc:
            print(
                f"[stable_api_budget] {self.file_path}: cannot read state ({exc}); resetting window.",
                file=sys.stderr,
            )
            return {"window_start": int(time.time()), "used": 0}

    def _save_state(self, state: dict) -> None:
        # Unique tmp path per writer so even if a future caller skips the lock
        # we don't clobber another process's tmp file.
        tmp = self.file_path.with_suffix(f"{self.file_path.suffix}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self.file_path)

    def try_consume(self) -> bool:
        # Local import to avoid platform issues at module import time.
        import fcntl

        with open(self.lock_path, "w", encoding="utf-8") as lock_fp:
            fcntl.flock(lock_fp, fcntl.LOCK_EX)
            now = int(time.time())
            state = self._load_state()
            if now - int(state["window_start"]) >= self.window_seconds:
                state = {"window_start": now, "used": 0}
            if int(state["used"]) >= self.limit:
                fcntl.flock(lock_fp, fcntl.LOCK_UN)
                return False
            state["used"] = int(state["used"]) + 1
            self._save_state(state)
            fcntl.flock(lock_fp, fcntl.LOCK_UN)
            return True
