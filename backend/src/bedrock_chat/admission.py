"""Process-local inference admission; one app instance per worker."""
from contextlib import contextmanager
from threading import BoundedSemaphore
from time import monotonic


class AdmissionRejected(Exception):
    pass


class InferenceAdmission:
    def __init__(self):
        self._slot = BoundedSemaphore(1)
        self._tokens = 2.0
        self._updated = monotonic()

    @contextmanager
    def slot(self):
        if not self._slot.acquire(blocking=False):
            raise AdmissionRejected
        try:
            now = monotonic()
            self._tokens = min(2.0, self._tokens + now - self._updated)
            self._updated = now
            if self._tokens < 1:
                raise AdmissionRejected
            self._tokens -= 1
            yield
        finally:
            self._slot.release()
