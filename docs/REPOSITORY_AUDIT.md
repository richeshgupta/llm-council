# Repository Intent and Gap Audit

Date: 2026-07-19

## Derived product intent

LLM Council is a developer tool for structured multi-model thinking. Its value is not merely asking several models the same question; it is the handoff:

1. Diverse advisors reason independently, reducing anchoring and exposing alternatives.
2. Advisors inspect anonymized peer answers, making critique less dependent on provider identity.
3. Valid ballots reveal consensus and disagreement.
4. A chairman combines strong majority ideas with useful minority observations.

The primary use cases are architecture brainstorming, design review, tradeoff analysis, debugging hypotheses, planning, and iterative refinement. Local Claude/Codex adapters let developers use authenticated paid subscriptions without requiring API keys, while the provider interface supports API or future local adapters.

## Council capability matrix

| Council capability | Status |
|---|---|
| Parallel independent answers | Complete |
| Anonymous peer critique | Complete |
| Peer ranking | Complete with strict ballot validation |
| Aggregate ranking | Complete, keyed by advisor identity |
| Chairman synthesis | Complete with failover and degraded fallback |
| Shared run correlation ID | Complete |
| Partial-provider failure handling | Complete with stage diagnostics |
| Multi-turn refinement | Complete through optional conversation API |
| Stage streaming | Complete through SSE; token streaming is not implemented |
| Conversation title generation | Complete through optional API |
| Subscription-backed Claude/Codex | Complete and authenticated locally |
| API-backed providers | OpenRouter adapter complete and opt-in |
| Third-party provider extension | Interface and runtime factory registration complete |
| Web UI | Intentionally out of scope; repository is terminal-first |

## Gaps found and resolved

| Area | Gap | Resolution |
|---|---|---|
| Packaging | Installed CLI changed providers outside the repo | Config is packaged and resolved independently of CWD; missing explicit config fails safely |
| CLI UX | Silent multi-minute runs | Stage progress goes to stderr |
| CLI UX | Critiques hidden | Full output now includes peer-review text |
| Automation | Failed runs exited 0 | Defined exit statuses 0/1/2/130 |
| Automation | No structured output | Added versioned JSON output with run ID and diagnostics |
| Setup | Health checks had no CLI surface | Added passive `--doctor` and active `--doctor --probe` |
| Reliability | One adapter exception aborted a stage | Exceptions and deadlines are isolated per advisor |
| Reliability | Provider failures disappeared | Stage-specific failure metadata and stderr warnings are retained |
| Reliability | Primary chairman had no fallback | Ordered chairman/council-member failover plus degraded best-answer fallback |
| Reliability | Configured stage timeout was unused | Orchestrator enforces per-attempt deadlines |
| Reliability | Concurrent runs exceeded configured limits | Semaphores are shared within each orchestrator across concurrent runs |
| Process safety | Cancellation could orphan CLI processes | Process groups are terminated on timeout and cancellation |
| Prompt parity | CLI providers lost system messages | Structured roles are rendered into CLI prompts |
| Correctness | Empty outputs counted as success | Empty provider responses are normalized as failures |
| Correctness | Prose, duplicate, or partial ballots corrupted ranking | Only complete, unique ballots in `FINAL RANKING` are aggregated |
| Correctness | Labels failed after Z | Spreadsheet-style labels scale to AA, AB, and beyond |
| Correctness | Same-model adapters collapsed | Ranking identity uses stable advisor IDs |
| Security | Intermediate answers could act as instructions | Prompts mark advisor content as untrusted data |
| Security | Codex inherited the project directory and unrelated secrets | Codex uses an isolated temporary working directory and allowlisted environment by default |
| API parity | Streaming omitted aggregate rankings and continued after total failure | Streaming passes aggregates and stops after empty Stage 1 |
| Conversations | Stored history was ignored | Recent user/council turns are included in follow-up council queries |
| API safety | Server exposed all interfaces by default | Direct server entrypoint binds to localhost |
| Storage | Direct JSON writes could be observed partially | Writes use atomic replacement and in-process locking |
| Extensibility | Provider factory was a hardcoded branch | Providers can register factories with `AdvisorRegistry.register_provider()` |
| Maintenance | Removed-frontend and duplicate client artifacts remained | Removed header image, frontend ignores, hello entrypoint, and legacy OpenRouter client |

## Remaining limitations

These are explicit follow-on items rather than hidden defects:

- CLI output is stage-based, not token-streaming.
- Provider output is bounded after capture; true streaming bounded buffers would further reduce memory risk from a malicious executable.
- JSON conversation locking is in-process. Multi-worker API deployments should use SQLite/PostgreSQL transactions.
- The optional API is localhost-only by default but has no authentication if deliberately exposed on another interface.
- Prompt budgeting uses bounded conversation history, but large councils still need model-aware token budgeting and intermediate summarization.
- Adapter registration is programmatic; Python package entry-point discovery would support third-party plug-ins without import-time registration.
- Real-provider integration checks consume subscription usage and therefore remain an explicit validation step rather than part of every unit-test run.

## Release assessment

The original proof-of-concept happy path is now a usable developer CLI with observable execution, deterministic configuration, structured output, graceful degradation, validated ranking, and tested Claude/Codex subscription flows. The remaining items are scaling and deployment hardening concerns, not blockers for local developer brainstorming.
