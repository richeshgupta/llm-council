<p align="center">
  <img src="assets/llm-council-banner.png" alt="Six AI advisor nodes converging into one LLM Council synthesis" width="920">
</p>

<h1 align="center">LLM Council CLI</h1>

<p align="center">
  <a href="https://github.com/richeshgupta/llm-council/actions/workflows/ci.yml"><img src="https://github.com/richeshgupta/llm-council/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/interface-CLI-4B32C3" alt="CLI interface">
</p>

LLM Council is a terminal-first brainstorming tool for developers. It asks several independently configured LLM advisors for answers, has them anonymously critique and rank the candidate answers, then asks a chairman model to synthesize the council's best result.

It supports local subscription-backed CLIs such as Codex and Claude Code, plus API-backed providers through adapters. No frontend is required.

## How it works

1. **Independent answers** — every enabled council member answers the same request in parallel.
2. **Anonymous peer review** — members evaluate responses labeled `Response A`, `Response B`, and so on.
3. **Synthesis** — the configured chairman uses the answers, critiques, and valid aggregate rankings to produce one final answer.

Provider failures are isolated. Partial failures are reported on stderr, chairman candidates fail over in configured order, and a run exits nonzero if it cannot produce a synthesized answer.

## Install

Prerequisites: Python 3.10+, plus authenticated `codex` and/or `claude` commands for the default configuration.

```bash
git clone https://github.com/richeshgupta/llm-council.git
cd llm-council
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Verify the local setup without consuming model usage:

```bash
llm-council doctor
```

Verify authentication and model access with a minimal real request to every enabled provider:

```bash
llm-council doctor --probe
```

`--probe` may count against provider subscription usage.

## Ask the council

```bash
llm-council ask --mode brainstorm \
  "Propose three architectures for a webhook delivery system and compare them."
```

The default output includes independent answers, full peer critiques, aggregate rankings, and final synthesis. Progress and provider warnings go to stderr, keeping stdout usable in pipelines.

Final answer only:

```bash
llm-council ask --mode decision --output final \
  "What are the tradeoffs between REST and gRPC here?"
```

Structured output:

```bash
llm-council ask --mode review --output json \
  "Review this migration plan" > council-result.json
```

Pipe a request:

```bash
printf '%s\n' "Ways to reduce CI time" | \
  llm-council ask --mode brainstorm --output final
```

List the generic modes and inspect the active runtime configuration:

```bash
llm-council modes
llm-council advisors
llm-council config path
llm-council config show
llm-council config validate
```

For compatibility, `llm-council "question"`, `--brief`, and the legacy `--doctor` flag still work. New integrations should use explicit commands.

## Configuration

The shipped configuration enables:

- Codex GPT-5.6 Terra as council member, chairman, and title generator.
- Claude Sonnet through Claude Code as a council member.
- OpenRouter support, disabled by default.

Configuration precedence is:

1. `--config /path/to/advisors.json`
2. `LLM_COUNCIL_CONFIG`
3. The packaged `backend/advisors.json`

The same packaged configuration is used from any working directory. A missing explicit configuration is an error; the CLI never silently switches provider families.

Codex runs in an isolated temporary directory by default and receives only essential CLI/auth/network environment variables. To intentionally give it read access to a repository, set `options.cwd` on that advisor explicitly.

Use [backend/advisors.json.example](backend/advisors.json.example) as a starting point. New providers implement the `Advisor` interface in `backend/advisors/base.py`, live in their own adapter module under `backend/advisors/adapters/`, and register a factory with `AdvisorRegistry.register_provider()`.

## Exit behavior

- `0`: synthesis succeeded, including runs with non-fatal advisor failures.
- `1`: providers were unavailable or synthesis could not complete.
- `2`: command usage or configuration error.
- `130`: interrupted by the user.

## Optional local API

The CLI is the primary interface. A local-only FastAPI server is available for programmatic integrations:

```bash
python -m backend.main
```

It binds to `127.0.0.1:8001` by default. Conversation data is stored under the platform data directory, configurable with `LLM_COUNCIL_DATA_DIR`.

## Test

```bash
python -m unittest discover -s tests -p 'test*.py' -v
```

GitHub Actions runs the suite on Python 3.10–3.14, compiles the source, checks installed dependencies, builds both distributions, and smoke-tests the installed wheel from outside the checkout. Built distributions are retained as workflow artifacts for seven days.

Authenticated Claude and Codex calls are deliberately excluded from hosted CI because they require local paid-subscription sessions.

Real-provider checks are intentionally separate because they consume subscription usage:

```bash
llm-council doctor --probe
llm-council ask --output final "Reply with exactly COUNCIL_OK"
```

See [docs/CLI_VALIDATION_REPORT.md](docs/CLI_VALIDATION_REPORT.md) for the latest validation results.
