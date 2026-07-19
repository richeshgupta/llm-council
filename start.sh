#!/bin/bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: ./start.sh [options] \"your question\""
  echo "Example: ./start.sh \"Explain Docker in 3 bullet points.\""
  exit 2
fi

.venv/bin/llm-council "$@"
