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

Current state after re-test:

```text
CLAUDE_OK
```

The direct CLI smoke and adapter smoke both passed after local Claude authentication was completed.

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

## Live full-council smoke with Codex Terra and Claude

Prompt:

```text
Answer in one short sentence: what is the capital of France?
```

Result summary:

```json
{
  "stage1_count": 2,
  "stage1_advisors": [
    {
      "advisor_id": "codex-terra-cli",
      "model": "gpt-5.6-terra",
      "provider": "codex_cli",
      "status": "success",
      "response": "Paris."
    },
    {
      "advisor_id": "claude-sonnet-cli",
      "model": "sonnet",
      "provider": "claude_cli",
      "status": "success",
      "response": "Paris."
    }
  ],
  "stage2_count": 2,
  "stage3_model": "gpt-5.6-terra",
  "stage3_status": "success",
  "stage3_response": "Paris.",
  "title": "France Capital"
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

## Live API streaming multi-turn smoke with Codex Terra and Claude

Executed through FastAPI `TestClient`:

1. Created a conversation.
2. Sent a streamed first prompt.
3. Sent a streamed follow-up prompt in the same conversation.
4. Re-loaded the saved conversation.

Observed:

```json
{
  "first_events_present": {
    "stage1_start": true,
    "stage1_complete": true,
    "stage2_start": true,
    "stage2_complete": true,
    "stage3_start": true,
    "stage3_complete": true,
    "complete": true
  },
  "second_events_present": {
    "stage1_start": true,
    "stage1_complete": true,
    "stage2_start": true,
    "stage2_complete": true,
    "stage3_start": true,
    "stage3_complete": true,
    "complete": true
  },
  "message_count": 4,
  "roles": ["user", "assistant", "user", "assistant"],
  "assistant_stage_counts": [
    {
      "stage1": 2,
      "stage2": 2,
      "has_stage3": true,
      "stage3_response": "10 - 3 = 7."
    },
    {
      "stage1": 2,
      "stage2": 2,
      "has_stage3": true,
      "stage3_response": "6 × 7 = 42."
    }
  ]
}
```

## Final validation state

The implementation is locally validated for:

- provider-neutral advisor interface;
- dedicated adapter directory;
- Codex CLI subscription-backed advisor;
- Claude CLI authenticated success path;
- OpenRouter adapter compile/API shape;
- bounded orchestrator handoff;
- ranking and aggregation;
- frontend SSE buffering;
- follow-up chat input availability;
- API advisor metadata and health endpoints;
- parity with the three-stage council workflow.
