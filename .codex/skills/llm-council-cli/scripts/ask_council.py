#!/usr/bin/env python3
"""Compatibility wrapper for the installed LLM Council CLI."""

from backend.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

