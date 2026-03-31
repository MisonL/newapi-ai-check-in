from __future__ import annotations

from collections.abc import Callable


class LineCapture:
    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._buffer = ""

    def write(self, value: str) -> int:
        self._buffer += value
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self._callback(line)
        return len(value)

    def flush(self) -> None:
        if self._buffer:
            self._callback(self._buffer)
            self._buffer = ""
