#!/usr/bin/env python3
"""
Healthcare GEO Audit — Minimal Validation Probe (Phase 0).

Tests the single riskiest assumption in the build plan:

    Do AI answers actually show meaningful gaps between competing practices
    in the same city + specialty?

Sends 10 realistic patient questions to a web-grounded AI-search model (Perplexity
Sonar via OpenRouter, or GLM-4.6 via z.ai), then counts how often each of several
real Austin dental practices is named. The distribution answers the thesis:
        "3 practices dominate, 2 are invisible"  -> the opportunity is real.
        "all mentioned equally" / "none named"   -> stop, reassess.

Stdlib only (Python 3.9+). No pip install required.

Usage:
    OPENROUTER_API_KEY=... python3 probe.py                  # Perplexity Sonar (default, recommended)
    OPENROUTER_API_KEY=... python3 probe.py --model perplexity/sonar-pro
    ZAI_API_KEY=...        python3 probe.py --provider zai    # GLM-4.6 + web search
    python3 probe.py --mock                                    # dry run, no key
    python3 probe.py --queries 3                               # cheaper smoke test
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 120         # web-grounded calls can be slow
RETRY_BACKOFF = (2, 5, 12) # seconds between retries on transient errors

# Endpoints
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
ZAI_ENDPOINT = "https://api.z.ai/api/paas/v4/chat/completions"

# Default model per provider
DEFAULTS = {
    "openrouter": "openai/gpt-4o-mini:online",  # web-grounded via :online plugin; ~cheapest usable
    "zai": "glm-4.6",                            # web-search tool grounding
}

# 10 realistic patient questions a person in Austin would actually ask an AI.
QUERIES = [
    "best dentist in austin tx",
    "top rated dentist in austin",
    "dentist near me that takes delta dental austin",
    "affordable dentist south austin",
    "family dentist austin tx",
    "cosmetic dentist austin",
    "invisalign provider austin tx",
    "emergency dentist austin open saturday",
    "pediatric dentist austin tx",
    "dentist for crowns and implants austin",
]

# Real Austin dental practices, tuned to the actual market leaders AI surfaces.
# Derived from live Perplexity/Google results: the names that recur across
# "best dentist in Austin" recommendations. aliases = every form a practice might
# be cited as, matched case-insensitively against answer text + cited snippets.
PRACTICES = [
    {"name": "Forest Family Dentistry",
     "aliases": ["forest family dentistry", "forest family dental"]},
    {"name": "Austin Dental Spa",
     "aliases": ["austin dental spa", "mark sweeney", "austin dental"]},
    {"name": "Enamel Dentistry",
     "aliases": ["enamel dentistry"]},
    {"name": "Walden Dental",
     "aliases": ["walden dental"]},
    {"name": "Westlake Hills Dentistry",
     "aliases": ["westlake hills dentistry", "westlake hills dental"]},
    {"name": "Celebrate Dental & Braces",
     "aliases": ["celebrate dental"]},
    {"name": "ATX Family Dental",
     "aliases": ["atx family dental"]},
    {"name": "Tech Ridge Dental",
     "aliases": ["tech ridge dental"]},
    {"name": "Belterra Dental",
     "aliases": ["belterra dental"]},
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "audits")


# ---------------------------------------------------------------------------
# Shared HTTP helper (stdlib only)
# ---------------------------------------------------------------------------
def _post_json(url: str, headers: dict, payload: dict) -> dict:
    """POST JSON with retry on transient errors. Returns parsed JSON."""
    body = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt, wait in enumerate(RETRY_BACKOFF + (None,)):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            err_body = e.read().decode("utf-8", "replace")
            # Balance/quota errors are permanent until resolved — don't retry.
            low = err_body.lower()
            if e.code in (402,) or any(k in low for k in
                    ("insufficient balance", "insufficient_quota", "billing",
                     "no credit", "exceeded your current")):
                raise RuntimeError(
                    f"Provider billing/quota error (HTTP {e.code}): {err_body[:300]}. "
                    "Add credits and re-run.") from e
            # Other 429 / 5xx are transient.
            if e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {e.code}: {err_body[:300]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
        if wait is None:
            break
        time.sleep(wait)
    raise RuntimeError(f"request failed after retries: {last_err}")


# ---------------------------------------------------------------------------
# Provider: OpenRouter (Perplexity Sonar — the brief's recommended source)
# ---------------------------------------------------------------------------
def call_openrouter(query: str, api_key: str, model: str) -> dict:
    """Send one patient question to a Perplexity Sonar model via OpenRouter.

    Sonar is web-grounded and returns a cited answer. We harvest mentions from
    both the answer text and the url_citation annotations (title/url), since a
    practice may be cited via source without its name spelled out in prose.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": ("You are a helpful local-search assistant answering a patient "
                         "looking for a dental practice. Recommend specific, real "
                         "practices by name. List the best options you can verify, "
                         "with a one-line reason each.")},
            {"role": "user", "content": query},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = _post_json(OPENROUTER_ENDPOINT, headers, payload)
    if "error" in data:
        raise RuntimeError(f"OpenRouter error: {json.dumps(data['error'])[:300]}")

    answer = ""
    sources = []
    try:
        msg = data["choices"][0]["message"]
        answer = msg.get("content") or ""
        # OpenRouter/Perplexity attach url_citation annotations to the message.
        for ann in msg.get("annotations") or []:
            uc = ann.get("url_citation") or {}
            if uc:
                sources.append({
                    "title": uc.get("title", ""),
                    "link": uc.get("url", ""),
                    "content": "",
                })
    except (KeyError, IndexError):
        pass
    # Some providers also return a top-level "citations" array.
    for c in data.get("citations") or []:
        if isinstance(c, str):
            sources.append({"title": c, "link": c, "content": ""})
        elif isinstance(c, dict):
            sources.append({"title": c.get("title", ""), "link": c.get("url", ""), "content": ""})
    # OpenRouter returns the real cost of this call in usage.cost (USD).
    try:
        cost = float((data.get("usage") or {}).get("cost") or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    return {"answer": answer, "sources": sources, "cost": cost, "raw": data}


# ---------------------------------------------------------------------------
# Provider: z.ai (GLM-4.6 + web_search tool)
# ---------------------------------------------------------------------------
def call_zai(query: str, api_key: str, model: str) -> dict:
    """Send one patient question to GLM-4.6 with web-search grounding via z.ai."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": ("You are a helpful local-search assistant answering a patient "
                         "looking for a dental practice. Recommend specific, real "
                         "practices by name. List the 3-5 best options you can verify, "
                         "with a one-line reason each.")},
            {"role": "user", "content": query},
        ],
        "tools": [{"type": "web_search", "web_search": {
            "enable": True, "search_engine": "search-prime",
            "search_result": True, "count": 8}}],
        "temperature": 0.3,
        "stream": False,
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept-Language": "en-US,en",
    }
    data = _post_json(ZAI_ENDPOINT, headers, payload)
    answer = ""
    sources = []
    try:
        answer = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        pass
    for s in data.get("web_search") or []:
        sources.append({"title": s.get("title", ""), "link": s.get("link", ""),
                        "content": s.get("content", "")})
    # z.ai doesn't return a cost field, so estimate it from token usage x price.
    # GLM-4.6 pricing (https://docs.z.ai): ~$0.60/1M input, ~$2.20/1M output.
    usage = data.get("usage") or {}
    try:
        pt = float(usage.get("prompt_tokens") or 0) / 1_000_000 * 0.60
        ct = float(usage.get("completion_tokens") or 0) / 1_000_000 * 2.20
        cost = pt + ct
    except (TypeError, ValueError):
        cost = 0.0
    return {"answer": answer, "sources": sources, "cost": cost, "raw": data}


# ---------------------------------------------------------------------------
# Mention detection
# ---------------------------------------------------------------------------
def mentioned_practices(result: dict, practices=None) -> list:
    """Return the names of practices cited anywhere in this grounded answer.

    practices defaults to the module-level PRACTICES list.
    """
    practices = practices if practices is not None else PRACTICES
    haystack = (result.get("answer") or "").lower()
    for src in result.get("sources") or []:
        haystack += "\n" + (src.get("title") or "").lower()
        haystack += "\n" + (src.get("content") or "").lower()
    hits = []
    for p in practices:
        if any(a in haystack for a in p["aliases"]):
            hits.append(p["name"])
    return hits


# alias used by run_audit / the web UI
def mentioned_practices_for(result, practices):
    return mentioned_practices(result, practices)


# ---------------------------------------------------------------------------
# Mock provider — run the full pipeline on canned data with no API key
# ---------------------------------------------------------------------------
def mock_result(query: str) -> dict:
    rng = random.Random(int(hashlib.md5(query.encode()).hexdigest(), 16))  # deterministic per query
    # Simulate the "gap" the thesis predicts: 2 practices dominate, 2 invisible.
    weights = {
        "Forest Family Dentistry": 0.7,
        "Austin Dental Spa": 0.6,
        "Belterra Dental": 0.4,
        "ATX Family Dental": 0.1,
        "Tech Ridge Dental": 0.0,
    }
    answer = "Recommended: "
    cited = []
    for name, w in weights.items():
        if rng.random() < w:
            cited.append(name)
    answer += ", ".join(cited) if cited else "(no specific practices named)"
    return {"answer": answer, "sources": [], "raw": {}}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Core audit logic (shared by CLI and the web UI)
# ---------------------------------------------------------------------------
def run_audit(provider, model, api_key, queries, practices, mock=False, on_query=None, market=""):
    """Run the audit and return a structured result dict.

    queries:    list of query strings
    practices:  list of {name, aliases} dicts
    on_query:   optional callback(i, total, query, mentions, query_cost, run_cost)
                called per query (the web UI uses this to stream progress + cost)
    """
    caller = {"openrouter": call_openrouter, "zai": call_zai}[provider]
    mentioned_in = {p["name"]: 0 for p in practices}
    queries_with_any = 0
    queries_with_none = 0
    query_results = []
    errors = []
    run_cost = 0.0  # running USD total for this audit

    for i, q in enumerate(queries, 1):
        query_cost = 0.0
        if mock:
            result = mock_result(q)
        else:
            try:
                result = caller(q, api_key, model)
            except Exception as e:
                err_msg = str(e)
                errors.append({"query": q, "error": err_msg})
                if on_query:
                    on_query(i, len(queries), q, None, query_cost, run_cost)
                continue
            query_cost = float(result.get("cost") or 0.0)
            run_cost += query_cost
            time.sleep(0.8)
        hits = mentioned_practices_for(result, practices)
        for name in hits:
            mentioned_in[name] += 1
        if hits:
            queries_with_any += 1
        else:
            queries_with_none += 1
        query_results.append({
            "query": q, "mentions": hits,
            "answer": result.get("answer", ""), "sources": result.get("sources", []),
            "cost": round(query_cost, 6),
        })
        if on_query:
            on_query(i, len(queries), q, hits, query_cost, run_cost)

    total_q = len(queries)
    ranking = sorted(mentioned_in.items(), key=lambda kv: kv[1], reverse=True)
    counts = [c for _, c in ranking]

    # --- verdict logic (mirrors the brief's decision gate) -----------------
    if total_q == 0 or queries_with_any == 0:
        if total_q == 0:
            verdict, detail = "NO DATA", "no queries ran."
        else:
            verdict = "COLLAPSES — no practices named"
            detail = ("The AI named none of these practices in any query. Either the "
                      "market is too generic for AI to name anyone, or grounding isn't "
                      "surfacing local listings. The pitch has nothing to grab onto.")
    else:
        top, bottom = counts[0], counts[-1]
        if top == 0:
            verdict, detail = "COLLAPSES — nobody named", "top count is 0."
        elif top - bottom >= 3 and bottom <= (total_q // 4):
            verdict = "GAP IS REAL — build the full tool"
            detail = (f"top practice in {top}/{total_q}, bottom in {bottom}/{total_q}. "
                      "The 'some dominate, some invisible' pattern the thesis needs is here.")
        else:
            verdict = "AMBIGUOUS — investigate before building"
            detail = (f"top {top}/{total_q} vs bottom {bottom}/{total_q}. Spread is too "
                      "flat to be a clear sales wedge. Re-run with more queries / a "
                      "sharper market before committing to Phase 2.")

    return {
        "ranking": [{"name": n, "count": c} for n, c in ranking],
        "total_queries": total_q,
        "queries_with_any": queries_with_any,
        "queries_with_none": queries_with_none,
        "verdict": verdict,
        "detail": detail,
        "query_results": query_results,
        "errors": errors,
        "total_cost": round(run_cost, 6),
        "market": market or "",
        "provider": provider,
        "model": "mock" if mock else model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run(provider: str, model: str, api_key: str, limit: int, mock: bool, market: str = ""):
    """CLI entry: run the audit and print results to the terminal."""
    queries = QUERIES[:limit] if limit else QUERIES
    src_label = "MOCK (canned answers)" if mock else f"{provider}/{model}"
    if not market:
        market = f"dentists in Austin, TX"
    print(f"Healthcare GEO Audit — validation probe")
    print(f"Market: {market} | {len(PRACTICES)} practices tracked | "
          f"{len(queries)} patient queries")
    print(f"Source: {src_label}")
    print("=" * 72)

    def on_query(i, total, q, hits, query_cost=0.0, run_cost=0.0):
        if hits is None:
            status = "ERROR — API call failed"
            cost_str = ""
        elif hits:
            status = ", ".join(hits)
            cost_str = f"  [${run_cost:.4f}]" if run_cost else ""
        else:
            status = "(none of the tracked practices named)"
            cost_str = ""
        print(f"[{i:>2}/{total}] {q}")
        print(f"        -> {status}{cost_str}")

    result = run_audit(provider, model, api_key, queries, PRACTICES, mock=mock, on_query=on_query, market=market)

    total_q = result["total_queries"]
    print("\n" + "=" * 72)
    print("RANKING — how often each tracked practice is named across patient queries")
    print("-" * 72)
    for rank, row in enumerate(result["ranking"], 1):
        bar = "#" * row["count"]
        print(f"  {rank}. {row['name']:<28} {row['count']}/{total_q}  {bar}")
    print("-" * 72)
    print(f"  Queries naming ANY tracked practice:  {result['queries_with_any']}/{total_q}")
    print(f"  Queries naming NONE:                  {result['queries_with_none']}/{total_q}")
    print(f"  Total API cost:                       ${result['total_cost']:.4f}")

    if result["errors"]:
        print(f"\n  Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"    [{e['query']}] {e['error']}")

    print("\n" + "=" * 72)
    print("THESIS CHECK: is there a meaningful gap to sell?")
    print("-" * 72)
    print(f"  VERDICT: {result['verdict']}")
    print(f"  Detail:  {result['detail']}")

    # --- dump raw audit JSON ------------------------------------------------
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = os.path.join(DATA_DIR, f"probe-{provider}-{ts}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nRaw audit JSON saved to: {out}")
    except OSError as e:
        print(f"\n(could not save audit JSON: {e})")

    print("\n" + result["detail"])
    return 0 if "REAL" in result["verdict"] or "AMBIGUOUS" in result["verdict"] else 1


def main():
    ap = argparse.ArgumentParser(description="Healthcare GEO validation probe")
    ap.add_argument("--provider", choices=["openrouter", "zai"], default="openrouter",
                    help="AI-search provider (default: openrouter = Perplexity Sonar)")
    ap.add_argument("--model", default=None,
                    help="model id; defaults to perplexity/sonar (openrouter) or glm-4.6 (zai)")
    ap.add_argument("--mock", action="store_true",
                    help="use canned answers instead of the API (no key needed)")
    ap.add_argument("--queries", type=int, default=0,
                    help="run only the first N patient queries (default: all 10)")
    args = ap.parse_args()

    model = args.model or DEFAULTS[args.provider]

    if args.mock:
        return run(args.provider, model, "", args.queries, mock=True)

    if args.provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        env_name = "OPENROUTER_API_KEY"
    else:
        key = os.environ.get("ZAI_API_KEY", "").strip()
        env_name = "ZAI_API_KEY"
    if not key:
        print(f"ERROR: set {env_name}, or run with --mock.", file=sys.stderr)
        return 2
    return run(args.provider, model, key, args.queries, mock=False)


if __name__ == "__main__":
    sys.exit(main())
