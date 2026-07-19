# LLM Council CLI

Terminal-only LLM Council that asks multiple local/provider advisors for independent answers, collects peer review, and synthesizes a final response.

Default providers:

- Codex GPT-5.6 Terra through local `codex exec`
- Claude Sonnet through local `claude -p`
- OpenRouter adapter available but disabled by default

## Install

```bash
cd /home/richesh/Desktop/projects/llm-council
/home/richesh/.local/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

## Verify providers

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

## Ask a query

```bash
.venv/bin/python scripts/ask_council.py "Explain Docker in 3 bullet points."
```

Final answer only:

```bash
.venv/bin/python scripts/ask_council.py --brief "What is 2 + 2?"
```

Pipe input:

```bash
echo "Summarize HTTP in one paragraph." | .venv/bin/python scripts/ask_council.py
```

## Configuration

Edit:

```text
backend/advisors.json
```

Current defaults:

- `codex-terra-cli`: enabled, council member, chairman, title generator
- `claude-sonnet-cli`: enabled, council member
- `openrouter-gemini`: disabled

## Optional API server

The CLI is the primary interface. The FastAPI server remains available for programmatic use:

```bash
.venv/bin/python -m backend.main
```

Useful endpoints:

```text
GET /api/advisors
GET /api/advisors/health
POST /api/conversations
POST /api/conversations/{conversation_id}/message
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
```

## Skill

Repo-local Codex skill:

```text
.codex/skills/llm-council-cli/SKILL.md
```

Use it when asking Codex to install, configure, smoke-test, or run this project from terminal.

## Validation

See:

```text
docs/CLI_VALIDATION_REPORT.md
```
