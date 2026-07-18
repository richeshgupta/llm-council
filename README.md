# LLM Council

An extensible local LLM Council that can ask multiple advisors for independent answers, collect peer review, and synthesize a final council response.

This implementation is provider-neutral. Advisors can be backed by APIs, local CLIs, or future local inference providers through a common adapter interface.

## What it does

For each user message, the app runs a three-stage workflow:

1. Stage 1: each enabled council advisor answers the prompt independently.
2. Stage 2: advisors review anonymized Stage 1 answers and rank them.
3. Stage 3: a configured chairman advisor synthesizes the final answer.

The UI shows all intermediate artifacts, not just the final answer.

## Provider model

Providers are implemented as advisors under:

```text
backend/advisors/adapters/
```

Current adapters:

- `openrouter.py` — API-backed OpenRouter advisor.
- `claude_cli.py` — subscription-backed Claude Code CLI advisor.
- `codex_cli.py` — subscription-backed Codex CLI advisor.

The council orchestrator calls only the provider-neutral `Advisor` interface. It does not know whether an advisor is API-backed, CLI-backed, or local.

## Subscription-backed usage

Claude Pro/Max and Codex Plus/Pro are not API credits. To use those paid subscriptions, configure CLI-backed advisors and authenticate the local tools separately:

```bash
claude auth
codex login
```

Then copy and edit the advisor config:

```bash
cp backend/advisors.json.example backend/advisors.json
```

Enable the desired advisors in `backend/advisors.json`.

Codex GPT-5.6 Terra is represented as:

```json
{
  "id": "codex-terra-cli",
  "provider": "codex_cli",
  "model": "gpt-5.6-terra"
}
```

If the local Codex CLI rejects that model slug, the adapter fails clearly instead of silently downgrading.

## API-backed usage

For OpenRouter:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

If no `backend/advisors.json` is present, the backend falls back to OpenRouter defaults from `backend/config.py`.

## Running

Backend:

```bash
python -m backend.main
```

or, if using `uv`:

```bash
uv run python -m backend.main
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Advisor endpoints

```http
GET /api/advisors
GET /api/advisors/health
```

These expose enabled advisor metadata and lightweight health state.

## Design docs

- `docs/SUBSCRIPTION_BACKED_LLM_COUNCIL_HLD.md`
- `docs/PROVIDER_INTERFACE_ORCHESTRATOR_PLAN.md`
- `docs/LLM_COUNCIL_LLD.md`

