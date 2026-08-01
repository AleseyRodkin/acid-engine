"""Execution modes: normal vs light."""
from __future__ import annotations
from enum import Enum


class ExecutionMode(str, Enum):
    NORMAL = "normal"   # full observation + hashing
    LIGHT = "light"     # reduced observations (still deterministic)