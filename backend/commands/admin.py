"""Advisor and configuration inspection commands."""

from __future__ import annotations

import argparse
import json

from ..advisors.config import load_advisors_config, resolve_advisors_config_path
from .common import create_registry


def run_advisors_command(args: argparse.Namespace) -> int:
    registry = create_registry(args.config)
    advisors = registry.get_enabled_advisors()
    rows = [
        {
            "id": advisor.id,
            "display_name": advisor.display_name,
            "provider": advisor.provider,
            "mode": advisor.mode.value,
            "roles": sorted(role.value for role in advisor.roles),
        }
        for advisor in advisors
    ]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(
            f"{row['id']:24} {row['provider']:12} {row['mode']:5} "
            f"{','.join(row['roles'])}"
        )
    return 0


def run_config_command(args: argparse.Namespace) -> int:
    path = resolve_advisors_config_path(args.config).resolve()
    if args.action == "path":
        print(path)
        return 0
    config = load_advisors_config(args.config)
    if args.action == "show":
        print(json.dumps(config.model_dump(mode="json"), indent=2))
    else:
        create_registry(args.config)
        print(f"Configuration is valid: {path}")
    return 0
