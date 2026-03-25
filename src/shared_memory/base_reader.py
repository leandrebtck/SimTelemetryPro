"""Base shared memory reader with polling thread."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

from ..telemetry.data_models import TelemetryFrame

FILE_MAP_READ = 0x0004
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.OpenFileMappingW.restype = wintypes.HANDLE
kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]

kernel32.MapViewOfFile.restype = ctypes.c_void_p
kernel32.MapViewOfFile.argtypes = [
    wintypes.HANDLE, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t,
]

kernel32.UnmapViewOfFile.restype = wintypes.BOOL
kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def open_shared_memory(name: str) -> tuple[Optional[int], Optional[int]]:
    """Open a named shared memory mapping. Returns (handle, ptr) or (None, None)."""
    handle = kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
    if not handle:
        return None, None
    ptr = kernel32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
    if not ptr:
        kernel32.CloseHandle(handle)
        return None, None
    return handle, ptr


def close_shared_memory(handle: Optional[int], ptr: Optional[int]) -> None:
    if ptr:
        kernel32.UnmapViewOfFile(ptr)
    if handle:
        kernel32.CloseHandle(handle)


class BaseReader(ABC):
    """Abstract base class for simulator shared memory readers."""

    SIM_NAME: str = "Unknown"

    def __init__(self, poll_hz: int = 60):
        self._poll_hz = poll_hz
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[TelemetryFrame], None]] = []
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def add_callback(self, cb: Callable[[TelemetryFrame], None]) -> None:
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[TelemetryFrame], None]) -> None:
        self._callbacks.discard(cb) if hasattr(self._callbacks, "discard") else None
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        interval = 1.0 / self._poll_hz
        while self._running:
            t_start = time.perf_counter()
            try:
                frame = self.read_frame()
                if frame is not None:
                    self._connected = True
                    for cb in self._callbacks:
                        cb(frame)
                else:
                    self._connected = False
            except Exception:
                self._connected = False
            elapsed = time.perf_counter() - t_start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    @abstractmethod
    def read_frame(self) -> Optional[TelemetryFrame]:
        """Read current telemetry. Returns None if sim not running."""
        ...
