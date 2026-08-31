"""Представление живого исполняемого кода (уровень 0)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class LiveCodeView:
    """Обёртка над живой Python-функцией."""
    def __init__(self, func: Callable[[Any], Any]):
        self.func = func

    def execute(self, input_data: Any) -> Any:
        return self.func(input_data)

    def __call__(self, input_data: Any) -> Any:
        return self.execute(input_data)