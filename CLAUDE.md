# CLAUDE.md - LLM Council CLI Notes

This repository is terminal-only. Do not add or start a web frontend unless the user explicitly asks for one.

## Primary user workflow

Install:

```bash
/home/richesh/.local/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

Ask a query:

```bash
.venv/bin/llm-council "Explain Docker in 3 bullet points."
```

Compatibility wrapper:

```bash
.venv/bin/python scripts/ask_council.py "Explain Docker in 3 bullet points."
```

## Provider smoke checks

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

## Architecture

- `backend/cli.py`: installed console entrypoint `llm-council`.
- `scripts/ask_council.py`: thin compatibility wrapper around `backend.cli`.
- `backend/council.py`: compatibility facade over the provider-neutral orchestrator.
- `backend/orchestration/`: prompt construction, ranking parsing, bounded execution, and stage handoff.
- `backend/advisors/base.py`: provider-neutral `Advisor` interface.
- `backend/advisors/registry.py`: loads enabled advisors from config.
- `backend/advisors/adapters/`: provider implementations.
  - `codex_cli.py`
  - `claude_cli.py`
  - `openrouter.py`
- `backend/advisors.json`: default runtime config.
- `.codex/skills/llm-council-cli/SKILL.md`: repo-local skill for CLI install/use.

## Default advisor config

`backend/advisors.json` enables:

- `codex-terra-cli`: council member, chairman, title generator.
- `claude-sonnet-cli`: council member.

OpenRouter exists as an adapter but is disabled by default.

## Stage flow

```text
Query
  -> Stage 1: each advisor answers independently
  -> Stage 2: successful answers are anonymized and peer-ranked
  -> Aggregate rankings
  -> Stage 3: chairman advisor synthesizes final answer
  -> CLI prints stage details and final answer
```

## Testing

```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
.venv/bin/python -m compileall backend tests scripts
```

Run a real query:

```bash
.venv/bin/llm-council --brief "What is 2 + 2?"
```

## Common gotchas

- Run commands from the repository root.
- If `llm-council` is missing, rerun `.venv/bin/python -m pip install -e .`.
- If Claude fails, run the Claude smoke check first.
- If Codex fails, run the Codex Terra smoke check first.
- If Stage 1 is empty, every enabled advisor failed; test advisors one by one.

