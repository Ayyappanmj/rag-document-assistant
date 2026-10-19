"""Runs one evaluation at a time in a background thread and reports progress."""
import logging
import threading
from datetime import datetime, timezone
from typing import Callable

from app.rag.generator import LLMError

logger = logging.getLogger(__name__)

Runner = Callable[[Callable[[int, int], None]], None]


class EvaluationJobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = self._idle()

    @staticmethod
    def _idle() -> dict:
        return {"state": "idle", "completed": 0, "total": 0, "error": None, "started_at": None}

    def status(self) -> dict:
        with self._lock:
            return dict(self._state)

    def reset(self) -> None:
        with self._lock:
            self._state = self._idle()

    def start(self, runner: Runner, total: int) -> bool:
        """Returns False if a run is already in progress."""
        with self._lock:
            if self._state["state"] == "running":
                return False
            self._state = {
                "state": "running", "completed": 0, "total": total, "error": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        threading.Thread(target=self._run, args=(runner,), daemon=True, name="evaluation-run").start()
        return True

    def _progress(self, done: int, total: int) -> None:
        with self._lock:
            self._state.update(completed=done, total=total)

    def _run(self, runner: Runner) -> None:
        try:
            runner(self._progress)
            with self._lock:
                self._state["state"] = "completed"
        except Exception as exc:  # report a safe message, log the details
            logger.exception("evaluation_run_failed")
            message = str(exc) if isinstance(exc, LLMError) else "The evaluation run failed. Check the server logs."
            with self._lock:
                self._state.update(state="failed", error=message)


job_manager = EvaluationJobManager()
