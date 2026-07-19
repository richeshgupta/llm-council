"""Installed `llm-council` entrypoint."""

from __future__ import annotations

import sys

from .commands import dispatch
from .commands.parser import parse_args


def main(argv: list[str] | None = None) -> int:
    try:
        return dispatch(parse_args(argv))
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
