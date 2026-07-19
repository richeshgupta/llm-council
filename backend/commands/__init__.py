"""CLI command dispatch."""

from __future__ import annotations

import argparse

from .admin import run_advisors_command, run_config_command
from .ask import run_ask_command
from .doctor import run_doctor_command
from .modes import print_modes


def dispatch(args: argparse.Namespace) -> int:
    handlers = {
        "ask": run_ask_command,
        "doctor": run_doctor_command,
        "advisors": run_advisors_command,
        "config": run_config_command,
        "modes": print_modes,
    }
    return handlers[args.command](args)
