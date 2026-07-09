# AGENTS.md — Healthcare GEO Audit

## What this is

A **Phase 0 validation probe** — deliberately minimal — that tests one business thesis: *do AI-search answers show meaningful visibility gaps between competing local medical practices?*

The output is a ranked count of how often each tracked practice is named across a set of patient queries. A "GAP IS REAL" verdict means the full product is worth building; anything else means stop.

**Do not expand this into a full product until the probe produces a "GAP IS REAL" result in a real market.**

---

## Commands

```bash
# No dependencies — stdlib only, Python 3.9+

# Smoke test (no API key needed, deterministic mock data)
python3 probe.py --mock

# Cheap live test (3 queries instead of 10)
OPENROUTER_API_KEY=... python3 probe.py --queries 3

# Full run — default provider (Perplexity Sonar via OpenRouter, ~$0.10)
OPENROUTER_API_KEY=... python3 probe.py

# Alternative providers
ZAI_API_KEY=...    python3 probe.py --provider zai    # GLM-4.6 + web search
NVIDIA_API_KEY=... python3 probe.py --provider nvidia  # free, no web grounding

# Specific model override
OPENROUTER_API_KEY=... python3 probe.py --model perplexity/sonar-pro

# Web UI (serves on http://127.0.0.1:8765 by default)
OPENROUTER_API_KEY=... python3 server.py
python3 server.py --port 8765 --host 0.0.0.0
```

Audit JSON is written to `data/audits/probe-{provider}-{timestamp}.json` after every CLI run.

---

## Architecture

```
probe.py       Core logic — providers, mention detection, audit runner, CLI
server.py      Thin HTTP wrapper — imports probe, serves a single-page web UI
data/audits/   Raw JSON output from each run
```

**`probe.py` is intentionally a single file.** The brief explicitly says "the whole tool, deliberately one file." Do not split it unless the phase changes.

**`server.py` contains no business logic.** All audit logic lives in `probe.run_audit()`. The server just calls that function and streams the result over SSE.

---

## Control / data flow

**CLI path:**
`main()` → parses args, resolves API key → `run()` → `run_audit()` → per-query: `call_{provider}()` → `mentioned_practices_for()` → verdict logic → prints results + saves JSON.

**Web UI path:**
Browser POST `/api/audit` → `Handler.do_POST()` → `probe.run_audit(..., on_query=callback)` → SSE events streamed per query (`start` / `query` / `error` / `done`) → `renderFinal()` in `APP_JS`.

The `on_query` callback is the seam between core logic and both UIs — CLI prints lines, server pushes SSE.

---

## Key data structures

**Practice dict** (used throughout):
```python
{"name": "Forest Family Dentistry", "aliases": ["forest family dentistry", "forest family dental"]}
```
Mention detection is case-insensitive substring match against `aliases` over `answer + source titles + source content` concatenated.

**`run_audit()` return dict** — the canonical result shape shared by CLI and web UI:
```python
{
  "ranking": [{"name": str, "count": int}, ...],  # sorted desc
  "total_queries": int,
  "queries_with_any": int,
  "queries_with_none": int,
  "verdict": str,   # "GAP IS REAL — build..." | "AMBIGUOUS — ..." | "COLLAPSES — ..."
  "detail": str,
  "query_results": [...],
  "errors": [...],
  "total_cost": float,
  "provider": str,
  "model": str,
  "timestamp": str,  # UTC ISO-8601
}
```

---

## Verdict thresholds

The verdict logic (in `run_audit()`) is the decision gate — do not change thresholds casually:

- **GAP IS REAL**: `top - bottom >= 3` AND `bottom <= total_queries // 4`
- **AMBIGUOUS**: any spread that doesn't meet the above
- **COLLAPSES**: zero queries named any tracked practice

---

## Provider differences

| Provider | Web-grounded? | Source of mentions | Cost |
|---|---|---|---|
| `openrouter` (Perplexity Sonar) | Yes | answer text + `url_citation` annotations | ~$0.01/query |
| `zai` (GLM-4.6) | Yes | answer text + `web_search` tool results | ~$0.003/query (estimated) |
| `nvidia` (GLM-5.2 via NIM) | No | training data only | Free |

The OpenRouter response includes real cost in `usage.cost`. z.ai doesn't — cost is estimated from token counts using hardcoded per-token prices. NVIDIA is free.

HTTP retries use backoff `(2, 5, 12)` seconds. Billing/quota errors (HTTP 402, "insufficient balance", etc.) are **not** retried and raise immediately. `HTTP_TIMEOUT` is 300s because NVIDIA free-tier cold starts can take 2-3 minutes.

---

## Web UI internals

`server.py` is stdlib only (`http.server`). The entire HTML and JS are inlined as Python string constants (`HTML`, `APP_JS`). There are no template files, no static assets on disk, and no build step.

SSE streaming: the server calls `self.wfile.write` + `self.wfile.flush()` directly in the request handler thread. `ThreadingHTTPServer` handles concurrent requests. The browser uses `fetch()` + `ReadableStream` (not `EventSource`) to consume the stream.

The web UI's `parse_practices()` auto-generates aliases from plain-text practice names: lowercased, `&` normalized to `and`, and the first two words as a shorter alias.

---

## Gotchas

- **`--mock` uses deterministic random seeded by query MD5.** Repeated runs produce identical results, which is intentional for testing.
- **The web server only reads `OPENROUTER_API_KEY`.** There is no way to select provider or model from the web UI — it is hardcoded to OpenRouter/Perplexity Sonar. Mock mode bypasses this.
- **`data/audits/` is gitignored** — raw API responses (which may contain PII-adjacent content) are not committed.
- **`probe.py` exits with code 1** if the verdict is "COLLAPSES", 0 otherwise. This makes `--mock` useful in CI to test the pipeline.
- **`server.py` silences all HTTP request logs** (`log_message` is a no-op). Add a `print` there if you need to debug server-side traffic.
- The `run_audit()` function has an 0.8s sleep between queries to avoid rate-limit pressure on live providers. Remove it only if you're sure the provider won't throttle.
