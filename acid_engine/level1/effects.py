"""Observed effects of a run. ContextVar collector, not a proof of purity."""
from __future__ import annotations

from contextvars import ContextVar, Token

_current: ContextVar[EffectCollector | None] = ContextVar(
    "acid_effect_collector", default=None
)


class EffectCollector:
    """Collect effects_observed for one run."""

    __slots__ = ("_effects", "_token")

    def __init__(self) -> None:
        self._effects: list[str] = []
        self._token: Token[EffectCollector | None] | None = None

    def __enter__(self) -> EffectCollector:
        self._token = _current.set(self)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._token is not None:
            _current.reset(self._token)
        self._token = None

    def record(self, effect: str) -> None:
        self._effects.append(effect)

    @property
    def effects(self) -> tuple[str, ...]:
        return tuple(self._effects)


def record_effect(effect: str) -> None:
    """Record an effect if a collector is active. Else no-op."""
    collector = _current.get()
    if collector is not None:
        collector.record(effect)
