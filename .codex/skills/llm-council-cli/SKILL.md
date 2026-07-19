---
name: llm-council-cli
description: Install, configure, smoke-test, and run this repository's terminal-only LLM Council. Use when the user asks how to install the LLM Council CLI, run a query from the command line, verify Claude/Codex local subscription-backed providers, configure advisors, troubleshoot CLI execution, or avoid/remove the web frontend.
---

# LLM Council CLI

Use this skill for this repository’s terminal-only workflow. Do not require or start the frontend.

## Install

From the repo root:

```bash
cd /home/richesh/Desktop/projects/llm-council
/home/richesh/.local/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

If `.venv` already exists, reuse it.

## Provider smoke checks

Run these before debugging the council.

Claude:

```bash
claude -p - --output-format text --no-session-persistence --tools '' <<'EOF'
Return exactly: CLAUDE_OK
EOF
```

Codex Terra:

```bash
codex exec --sandbox read-only --cd /home/richesh/Desktop/projects/llm-council --model gpt-5.6-terra - <<'EOF'
Return exactly: TERRA_OK
EOF
```

Expected outputs are `CLAUDE_OK` and `TERRA_OK`.

## Run a council query

Prefer the checked-in helper script:

```bash
.venv/bin/python scripts/ask_council.py "Explain Docker in 3 bullet points."
```

Or use the installed console command after `pip install -e .`:

```bash
.venv/bin/llm-council "Explain Docker in 3 bullet points."
```

For final answer only:

```bash
.venv/bin/llm-council --brief "What is 2 + 2?"
```

Pipe input:

```bash
echo "Summarize HTTP in one paragraph." | .venv/bin/python scripts/ask_council.py
```

## Config

Advisor config is `backend/advisors.json`.

Default intent:

- `codex-terra-cli`: enabled, council member, chairman, title generator.
- `claude-sonnet-cli`: enabled, council member.
- `openrouter-gemini`: disabled.

Use API providers only if explicitly enabled and credentials are configured.

## Troubleshooting

- `ModuleNotFoundError`: run `.venv/bin/python -m pip install -e .`.
- `claude` not found: install Claude Code and ensure it is on `PATH`.
- `codex` not found: install Codex CLI and ensure it is on `PATH`.
- Claude login failure: run Claude authentication, then rerun the smoke check.
- Codex model failure: run the direct Codex Terra smoke command; if the model slug is rejected, adjust `backend/advisors.json`.
- Empty Stage 1: all enabled advisors failed; test each provider directly first.
