# CLI Validation Report

This repository is terminal-only. The frontend has been removed.

## Primary command paths

Install:

```bash
/home/richesh/.local/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

Run query:

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

## Automated tests

```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
```

Latest local result:

```text
Ran 8 tests
OK
```

## Real query smoke tests

Installed console command:

```bash
.venv/bin/llm-council --brief "Answer in one short sentence: what is 2 + 2?"
```

Result:

```text
2 + 2 = 4.
```

Compatibility wrapper:

```bash
.venv/bin/python scripts/ask_council.py --brief "Answer in one short sentence: what is the capital of France?"
```

Result:

```text
Paris.
```
