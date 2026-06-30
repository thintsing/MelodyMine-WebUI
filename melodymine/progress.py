"""Thread-safe progress queue manager for MelodyMine WebUI.

Provides ProgressManager — a queue-based pub-sub system that allows
background download threads to emit progress messages and WebSocket
endpoints to stream them to clients.
"""

import queue
import threading
import time
import uuid
from contextlib import contextmanager
from io import StringIO
import sys


class DownloadCancelled(Exception):
    """Raised when a download task is cancelled by the user."""


class ProgressManager:
    """Thread-safe progress queues + cancel support for active downloads."""

    def __init__(self):
        self._queues: dict[str, queue.Queue] = {}
        self._results: dict[str, dict] = {}
        self._cancelled: set[str] = set()
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def create_task(self) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._queues[task_id] = queue.Queue()
        return task_id

    def register_thread(self, task_id: str, thread: threading.Thread) -> None:
        with self._lock:
            self._threads[task_id] = thread

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._queues:
                return False
            self._cancelled.add(task_id)
        self.emit(task_id, "status", "cancelling")
        return True

    def is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancelled

    def emit(self, task_id: str, type_: str, data) -> None:
        """Push a progress message to the task's queue."""
        q = self._queues.get(task_id)
        if q:
            q.put({"type": type_, "data": data, "ts": time.time()})

    def set_result(self, task_id: str, result: dict) -> None:
        with self._lock:
            self._results[task_id] = result
        self.emit(task_id, "result", result)
        self.emit(task_id, "done", None)

    def get_result(self, task_id: str) -> dict | None:
        return self._results.get(task_id)

    def iter_progress(self, task_id: str, timeout: float = 300):
        """Generator yielding progress messages until DONE or timeout."""
        q = self._queues.get(task_id)
        if not q:
            return
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = q.get(timeout=0.5)
                yield msg
                if msg["type"] == "done":
                    return
            except queue.Empty:
                yield {"type": "ping", "data": None, "ts": time.time()}

    def cleanup(self, task_id: str) -> None:
        with self._lock:
            self._queues.pop(task_id, None)
            self._results.pop(task_id, None)
            self._cancelled.discard(task_id)
            self._threads.pop(task_id, None)

    # ── stdout capture (thread-safe via exclusive lock) ────────────────

    _capture_lock = threading.Lock()

    @contextmanager
    def capture_print(self, task_id: str):
        """Redirect stdout to capture print() output as progress logs.

        Uses an exclusive lock to prevent concurrent stdout hijacking.
        If another thread is already capturing, logs go to real stdout
        (server console) instead — safe and correct.
        """
        acquired = self._capture_lock.acquire(blocking=False)
        if not acquired:
            yield  # another thread is capturing; skip
            return

        pm_ref = self
        tid = task_id

        class _Tee(StringIO):
            def write(self, s):
                super().write(s)
                if s.strip():
                    sys.__stdout__.write(s)
                if pm_ref.is_cancelled(tid):
                    raise DownloadCancelled()

            def flush(self):
                super().flush()
                sys.__stdout__.flush()

        old = sys.stdout
        tee = _Tee()
        sys.stdout = tee
        try:
            yield
        except DownloadCancelled:
            pass  # cancelled — don't emit progress, just clean up
        else:
            # emit captured output as a single log block
            captured = tee.getvalue()
            if captured.strip():
                for line in captured.splitlines():
                    if line.strip():
                        self.emit(task_id, "log", line)
        finally:
            sys.stdout = old
            self._capture_lock.release()
