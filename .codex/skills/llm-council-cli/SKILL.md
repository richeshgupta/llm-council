---
name: llm-council-cli
description: Install, configure, diagnose, test, and run this repository's terminal-only LLM Council with local Claude/Codex subscriptions or provider adapters. Use for CLI setup, council queries, provider health checks, advisor configuration, structured output, and troubleshooting. No frontend is required.
---

# LLM Council CLI

Use this skill for the repository's terminal-only workflow. Do not start or require a frontend.

## Install

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Reuse an existing `.venv` when present.

## Diagnose providers

Run a passive check first:

```bash
llm-council --doctor
```

If binaries are present but a real run fails, verify authentication and model access:

```bash
llm-council --doctor --probe
```

Warn the user that `--probe` sends a minimal request and may consume subscription usage.

## Run a council query

Full answers, critiques, rankings, and synthesis:

```bash
llm-council "Explain Docker in 3 bullet points."
```

Final answer only:

```bash
llm-council --output final "What is 2 + 2?"
```

Machine-readable result:

```bash
llm-council --output json "Review this design" > result.json
```

Piped request:

```bash
printf '%s\n' "Summarize HTTP in one paragraph" | llm-council --output final
```

## Configure advisors

The packaged default is `backend/advisors.json`. Override it with either:

```bash
llm-council --config /path/to/advisors.json "Your question"
```

or:

```bash
export LLM_COUNCIL_CONFIG=/path/to/advisors.json
```

Keep each provider adapter in `backend/advisors/adapters/`. Implement the `Advisor` interface and register its factory with `AdvisorRegistry.register_provider()`.

## Troubleshoot

- Exit `2`: inspect configuration syntax and validation output.
- Exit `1`: read provider diagnostics on stderr, then run `--doctor --probe`.
- Missing command: install the relevant provider CLI and ensure it is on `PATH`.
- Authentication failure: log in through that provider's CLI and rerun the probe.
- Model unavailable: update the advisor's `model` in the selected config.
- Partial failure: successful providers still complete the council; warnings identify degraded stages.

## Validate changes

```bash
python -m unittest discover -s tests -p 'test*.py' -v
python -m compileall -q backend tests scripts
```
