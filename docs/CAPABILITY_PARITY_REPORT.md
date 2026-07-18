# Capability Parity Report

## Scope

This report compares the public Karpathy LLM Council concept with this repository’s implementation after the provider-interface/orchestrator work.

Karpathy’s implementation is treated as a conceptual reference, not as the base product. This repository is an original implementation with its own advisor interface, provider adapters, orchestration layer, config, and tests.

## Capability map

| Capability | Karpathy LLM Council concept | This implementation | Parity |
|---|---|---|---|
| Multi-model council | Sends one prompt to multiple configured models. | Sends one prompt to multiple enabled provider-neutral advisors. | Yes |
| Stage 1 independent answers | Collects first-pass responses from council models. | `CouncilOrchestrator.stage1_collect_responses` queries enabled council advisors. | Yes |
| Stage 2 anonymized review | Labels answers as `Response A/B/C` and asks models to rank. | `build_stage2_prompt` anonymizes successful Stage 1 answers and ranks them. | Yes |
| Stage 2 ranking parser | Parses `FINAL RANKING:` text. | `parse_ranking_from_text` supports same text format. | Yes |
| Aggregate ranking | Calculates model street-cred/average rank. | `calculate_aggregate_rankings` calculates average rank. | Yes |
| Stage 3 chairman synthesis | Chairman model synthesizes final answer. | Configured chairman advisor synthesizes final answer. | Yes |
| Streaming UX | Sends stage completion events to frontend. | Existing SSE endpoint preserved. | Yes |
| Conversation persistence | Stores conversations locally as JSON. | Existing JSON storage preserved. | Yes |
| OpenRouter API support | Uses OpenRouter directly. | OpenRouter is available through `OpenRouterAdvisor`. | Yes |
| Provider extensibility | OpenRouter-oriented. | Explicit `Advisor` interface plus adapter directory. | Exceeds |
| Claude Pro/Max subscription support | Not supported directly. | Supported through `ClaudeCliAdvisor` using `claude` CLI. | Exceeds |
| Codex paid subscription support | Not supported directly. | Supported through `CodexCliAdvisor` using `codex exec`. | Exceeds |
| GPT-5.6 Terra advisor | Not part of original implementation. | Configured as `codex-terra-cli` chairman/council advisor. | Exceeds |
| Advisor health endpoint | Not present. | `GET /api/advisors/health`. | Exceeds |
| Advisor metadata endpoint | Not present. | `GET /api/advisors`. | Exceeds |
| Bounded API/CLI concurrency | Not separated by provider mode. | Separate API and CLI concurrency limits. | Exceeds |
| CLI subprocess safety | Not applicable. | Uses read-only Codex sandbox and no shell interpolation. | Exceeds |
| Follow-up messages | Original UI pattern supports chat-like history. | Input now remains available for existing conversations. | Yes |
| Robust SSE parsing | Basic chunk parsing. | Frontend buffers SSE event chunks before JSON parse. | Exceeds |

## Validated local scenarios

Executed locally:

- Python compile for backend and tests.
- Backend unit tests for:
  - ranking parser;
  - aggregate ranking;
  - subprocess success;
  - subprocess timeout;
  - full orchestrator stage handoff with fake advisors.
- API smoke tests for:
  - root health;
  - advisor listing;
  - advisor health.
- Frontend:
  - `npm run lint`;
  - `npm run build`.
- CLI provider checks:
  - `codex` installed;
  - `claude` installed;
  - Codex Terra direct smoke returned `TERRA_OK`;
  - full live council smoke using checked-in subscription config succeeded through Codex Terra.

Observed local provider state:

- Codex CLI is authenticated and supports `gpt-5.6-terra`.
- Claude CLI is installed but not logged in; the adapter classifies this as a provider failure and the council continues with successful advisors.

## Remaining gaps

These are not blockers for parity with the original concept, but are recommended hardening items:

1. Persist failed/skipped advisor attempts alongside successful stage outputs.
2. Add UI display for skipped advisors.
3. Add structured JSON ranking output and parser.
4. Add a dedicated advisor settings page.
5. Add database-backed storage if multi-user or high-volume usage is needed.

## Conclusion

The implementation reaches parity with the core Karpathy LLM Council workflow:

```text
independent answers -> anonymized peer review -> chairman synthesis
```

It exceeds the reference concept in provider extensibility and subscription-backed execution by supporting a common advisor interface, dedicated adapter directory, Claude CLI integration, Codex CLI integration, Codex GPT-5.6 Terra configuration, advisor health endpoints, and safer CLI subprocess execution.

