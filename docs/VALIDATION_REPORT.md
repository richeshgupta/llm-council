# Validation Report

Date: 2026-07-19

## Static and unit validation

Executed:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
npm run lint
npm run build
.venv/bin/python -m compileall backend tests
```

Result:

- Backend/API tests: passed, 8 tests.
- Frontend lint: passed.
- Frontend production build: passed.
- Python compile check: passed.

Note:

- FastAPI emitted a Starlette deprecation warning about `httpx` vs `httpx2` in `TestClient`; this does not fail tests.
- ESLint emitted a baseline browser mapping freshness warning; this does not fail lint.

## Unit/API scenarios covered

- Root API health endpoint.
- Advisor list endpoint.
- Advisor health endpoint.
- Ranking parser.
- Aggregate ranking calculation.
- Subprocess success path.
- Subprocess timeout path.
- Provider-neutral full-council stage handoff with fake advisors.

## Live local provider scenarios

### Codex CLI

Executed direct Codex Terra smoke:

```bash
codex exec --sandbox read-only --cd /home/richesh/Desktop/projects/llm-council --model gpt-5.6-terra -
```

Prompt:

```text
Return exactly: TERRA_OK
```

Result:

```text
TERRA_OK
```

### Claude CLI

Claude CLI is installed:

```text
/home/richesh/.local/bin/claude
2.1.195 (Claude Code)
```

Current state:

```text
Not logged in
```

The adapter handles this as a provider failure/skipped advisor scenario. The council continues when at least one advisor succeeds.

## Live full-council smoke

Executed:

```bash
.venv/bin/python - <<'PY'
from backend.council import run_full_council, generate_conversation_title
...
PY
```

Prompt:

```text
Answer in one short sentence: what is 2 + 2?
```

Result summary:

```json
{
  "stage1_count": 1,
  "stage1_models": ["gpt-5.6-terra"],
  "stage2_count": 1,
  "stage3_model": "gpt-5.6-terra",
  "stage3_status": "success",
  "stage3_response": "2 + 2 = 4.",
  "metadata_keys": ["aggregate_rankings", "label_to_model"],
  "title": "Simple Addition Answer"
}
```

## Live API streaming smoke

Executed through FastAPI `TestClient`:

1. `POST /api/conversations`
2. `POST /api/conversations/{id}/message/stream`
3. `GET /api/conversations/{id}`

Prompt:

```text
Answer in one short sentence: what is 3 + 5?
```

Observed events:

- `stage1_start`
- `stage1_complete`
- `stage2_start`
- `stage2_complete`
- `stage3_start`
- `stage3_complete`
- `complete`

Result summary:

```json
{
  "message_count": 2,
  "title": "Simple Addition Answer",
  "assistant_has_stage3": true
}
```

## Final validation state

The implementation is locally validated for:

- provider-neutral advisor interface;
- dedicated adapter directory;
- Codex CLI subscription-backed advisor;
- Claude CLI installed-but-unauthenticated failure path;
- OpenRouter adapter compile/API shape;
- bounded orchestrator handoff;
- ranking and aggregation;
- frontend SSE buffering;
- follow-up chat input availability;
- API advisor metadata and health endpoints;
- parity with the three-stage council workflow.

