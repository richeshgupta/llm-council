# CLI Validation Report

Date: 2026-07-19

## Result

The CLI-only LLM Council passed automated, packaging, failure-path, and authenticated-provider validation.

## Automated suite

Command:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
```

Result: **27 tests passed**.

Covered scenarios include:

- Three-stage happy-path handoff.
- Provider exception isolation.
- Partial and all-provider failure metadata.
- Chairman failover.
- Orchestration-level timeout enforcement.
- Shared concurrency limits across simultaneous runs.
- Subprocess success and timeout cleanup.
- Configuration loading outside the repository root.
- Missing config, duplicate advisor IDs, and invalid concurrency.
- Provider/config mode mismatch validation.
- Complete CLI role rendering for system/user messages.
- Strict ranking parsing and malformed ballot rejection.
- Anonymous labels beyond 26 candidates.
- JSON output and nonzero failure exit status.
- API health, deterministic advisor metadata, empty-body conversation creation, input validation, follow-up context, and streaming aggregate parity.

The FastAPI tests emit a non-failing upstream Starlette/httpx deprecation warning.

## Packaging

A wheel was built, installed into a clean Python 3.11 environment, and invoked from `/tmp`.

Verified:

- `backend/advisors.json` and `backend/advisors.json.example` are present in the wheel.
- Running outside the checkout loads `codex_cli` and `claude_cli`.
- The CLI does not silently switch to OpenRouter.
- `llm-council --doctor` resolves the packaged configuration and finds both local commands.

## Provider authentication

Command:

```bash
.venv/bin/llm-council --doctor --probe
```

Result:

- Codex GPT-5.6 Terra: `LLM_COUNCIL_OK`
- Claude Sonnet via Claude Code: `LLM_COUNCIL_OK`
- Exit status: `0`

## Real council flow

A real architecture-brainstorming query ran through all stages with JSON output.

- Run ID: `9260ab28-06f6-418b-b641-b1d94cae3995`
- Stage 1: 2/2 advisor answers.
- Stage 2: 2/2 peer reviews with complete ballots.
- Aggregate ranking: 2 candidates, 2 votes each.
- Stage 3: Codex chairman synthesis succeeded.
- Provider failures: none.
- Exit status: `0`.

An additional piped-stdin compatibility run returned exactly `COUNCIL_STDIN_OK` through `--brief` with exit status `0`.

## Failure semantics

Using a temporary configuration whose Claude and Codex command names did not exist:

- Both provider-specific errors were printed to stderr.
- The final status was failed.
- Exit status was `1`.

Using a missing explicit config:

- A concise configuration error was printed to stderr.
- Exit status was `2`.

## Other checks

- `compileall`: passed.
- `pip check`: passed.
- `git diff --check`: passed.
- Repo-local Codex skill validation: passed.
