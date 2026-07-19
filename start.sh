#!/bin/bash
set -euo pipefail

QUERY="${*:-}"

if [ -z "$QUERY" ]; then
  echo "Usage: ./start.sh \"your question\""
  echo "Example: ./start.sh \"Explain Docker in 3 bullet points.\""
  exit 2
fi

.venv/bin/python scripts/ask_council.py "$QUERY"
