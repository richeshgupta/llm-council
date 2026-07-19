"""Shared command helpers."""

from __future__ import annotations

from ..advisors.config import load_advisors_config
from ..advisors.registry import AdvisorRegistry


def create_registry(config_path: str | None) -> AdvisorRegistry:
    return AdvisorRegistry(load_advisors_config(config_path))
