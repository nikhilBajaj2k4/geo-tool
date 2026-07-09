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
    NVIDIA_API_KEY=...     python3 probe.py --provider nvidia  # free NVIDIA models (no web search)
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
from collections import Counter
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 300        # NVIDIA free tier cold starts can take 2-3 min
RETRY_BACKOFF = (2, 5, 12) # seconds between retries on transient errors

# Endpoints
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
ZAI_ENDPOINT = "https://api.z.ai/api/paas/v4/chat/completions"
NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

# Default model per provider
DEFAULTS = {
    "openrouter": "perplexity/sonar",
    "zai": "glm-4.6",                            # web-search tool grounding
    "nvidia": "z-ai/glm-5.2",                  # free, GLM via NVIDIA NIM
}

# Multi-engine models — all via OpenRouter, each web-grounded differently
MULTI_ENGINES = [
    {"id": "sonar",   "name": "Perplexity Sonar", "model": "perplexity/sonar", "provider": "openrouter"},
    {"id": "gpt4o",   "name": "ChatGPT",           "model": "openai/gpt-4o-mini:online", "provider": "openrouter"},
    {"id": "gemini",  "name": "Gemini Flash",      "model": "google/gemini-2.5-flash", "provider": "openrouter"},
]

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
# Provider: NVIDIA (free models, OpenAI-compatible, no web-search grounding)
# ---------------------------------------------------------------------------
def call_nvidia(query: str, api_key: str, model: str) -> dict:
    """Send one patient question to a free NVIDIA model.

    NVIDIA's free tier doesn't include web-search grounding, so answers come
    from training data only. Mention detection still works — it just won't be
    real-time local search results like Perplexity Sonar.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": ("You are a helpful local-search assistant answering a patient "
                         "looking for a dental practice in Austin, Texas. Recommend "
                         "specific, real practices by name. List the 3-5 best options "
                         "you can verify, with a one-line reason each.")},
            {"role": "user", "content": query},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = _post_json(NVIDIA_ENDPOINT, headers, payload)
    if "error" in data:
        raise RuntimeError(f"NVIDIA error: {json.dumps(data['error'])[:300]}")
    answer = ""
    try:
        answer = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        pass
    # NVIDIA free models don't return citations.
    # Estimate cost from token usage (free models, but track for consistency).
    usage = data.get("usage") or {}
    try:
        pt = float(usage.get("prompt_tokens") or 0) / 1_000_000 * 0.00
        ct = float(usage.get("completion_tokens") or 0) / 1_000_000 * 0.00
        cost = pt + ct
    except (TypeError, ValueError):
        cost = 0.0
    return {"answer": answer, "sources": [], "cost": cost, "raw": data}


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
# Source citation analysis (Phase 1 — explains why the gaps exist)
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> str:
    """Extract a clean domain from a URL for grouping citations."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        # strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _analyze_citations(query_results: list) -> dict:
    """Analyze all query results to extract citation patterns.

    Returns:
        {
            "source_domains": {domain: count, ...},
            "per_query_citations": [{query, sources_found, domains: [...]}, ...],
            "top_domains_ranked": [(domain, count), ...],
        }
    """
    from collections import Counter
    source_hits = Counter()
    per_query = []

    for qr in query_results:
        domains = []
        for src in qr.get("sources", []) or []:
            domain = _extract_domain(src.get("link", "") or src.get("url", ""))
            if domain:
                domains.append(domain)
                source_hits[domain] += 1

        per_query.append({
            "query": qr.get("query", ""),
            "mentions": qr.get("mentions", []),
            "domains_cited": domains,
            "source_count": len(domains),
        })

    return {
        "source_domains": dict(source_hits.most_common()),
        "per_query_citations": per_query,
        "top_domains_ranked": source_hits.most_common(15),
    }


def _competitor_gap_analysis(query_results: list, practices: list) -> list:
    """For each query where competitors won and the tracked practice didn't,
    show exactly what sources the AI cited. Returns per-practice gap insights."""
    gaps = {}
    for practice in practices:
        name = practice["name"]
        aliases = [a.lower() for a in practice.get("aliases", [])]
        gaps[name] = {"present_in": 0, "missing_from": 0, "gap_queries": []}

    for qr in query_results:
        query = qr.get("query", "")
        mentioned = [m.lower() for m in qr.get("mentions", [])]
        sources = qr.get("sources", []) or []
        source_domains = [_extract_domain(s.get("link", "") or s.get("url", "")) for s in sources]
        source_domains = [d for d in source_domains if d]

        for p in practices:
            name = p["name"]
            aliases = [a.lower() for a in p.get("aliases", [])]
            was_mentioned = any(m in name.lower() or any(a in name.lower() for a in aliases) for m in mentioned)
            # also check if any alias is directly in mentioned
            if not was_mentioned:
                was_mentioned = any(name.lower() in m or m in name.lower() for m in mentioned)

            if was_mentioned:
                gaps[name]["present_in"] += 1
            else:
                gaps[name]["missing_from"] += 1
                if mentioned and source_domains:
                    gaps[name]["gap_queries"].append({
                        "query": query,
                        "competitors_mentioned": mentioned,
                        "sources_cited": [{
                            "title": s.get("title", ""),
                            "domain": _extract_domain(s.get("link", "") or s.get("url", "")),
                            "link": s.get("link", "") or s.get("url", ""),
                        } for s in sources][:5],
                        "dominant_domain": max(set(source_domains), key=source_domains.count) if source_domains else "",
                    })

    return [{"practice": name, **data} for name, data in gaps.items()]


# Common recommendation rules for local medical practices
RECOMMENDATION_RULES = [
    {"domain_keywords": ["google.com"], "action": "Google Business Profile",
     "detail": "AI models frequently cite Google Maps listings. Ensure your profile is claimed, has recent photos, and accurate hours.",
     "priority": 5},
    {"domain_keywords": ["yelp.com"], "action": "Yelp Listing",
     "detail": "Your Yelp presence is being ignored. Claim your listing and actively request reviews.",
     "priority": 4},
    {"domain_keywords": ["healthgrades.com"], "action": "Healthgrades Profile",
     "detail": "Healthgrades is a top-cited medical directory. Create or update your profile with specialties and patient reviews.",
     "priority": 4},
    {"domain_keywords": ["zocdoc.com"], "action": "Zocdoc Listing",
     "detail": "Zocdoc drives AI citations. List your practice with availability and accepted insurance.",
     "priority": 4},
    {"domain_keywords": ["reddit.com"], "action": "Reddit Presence",
     "detail": "Reddit threads influence AI recommendations. Monitor r/[yourcity] and engage authentically.",
     "priority": 3},
    {"domain_keywords": ["facebook.com"], "action": "Facebook Page",
     "detail": "Social proof matters. Keep your Facebook page active with updates and reviews.",
     "priority": 2},
    {"domain_keywords": ["instagram.com"], "action": "Instagram Presence",
     "detail": "Visual social proof helps AI recommendations. Post before/after photos and patient stories.",
     "priority": 2},
    {"domain_keywords": ["justdial.com"], "action": "Justdial Listing",
     "detail": "Justdial is a critical local directory in India. Ensure your listing has reviews, photos, and accurate contact info.",
     "priority": 4},
    {"domain_keywords": ["practo.com"], "action": "Practo Profile",
     "detail": "Practo is the leading healthcare directory in India. Create a complete profile with services and patient feedback.",
     "priority": 4},
]


def _generate_recommendations(citation_data: dict, practices: list, ranking: list) -> dict:
    """Generate actionable recommendations based on what AI models are citing.

    Two types of recommendations:
    1. "Cited domains you're missing" — domains the AI cites but your practice isn't on
    2. "Volume gaps" — your practice has fewer reviews/signals than competitors
    """
    top_domains = citation_data.get("top_domains_ranked", [])
    recommendations = []

    # 1. Map domains to recommended actions
    mentioned_domains = set()
    for domain, count in top_domains:
        for rule in RECOMMENDATION_RULES:
            if any(kw in domain for kw in rule["domain_keywords"]):
                if rule["action"] not in [r["action"] for r in recommendations]:
                    recommendations.append({
                        "action": rule["action"],
                        "detail": rule["detail"],
                        "domain": domain,
                        "citation_count": count,
                        "priority": rule["priority"],
                    })
                mentioned_domains.add(domain)

    # 2. Add "review gap" recommendation if the leader has significant mentions
    if ranking and len(ranking) >= 2:
        top_count = ranking[0]["count"]
        bottom_count = ranking[-1]["count"]
        if top_count > 0 and top_count - bottom_count >= 3:
            recommendations.append({
                "action": "Google Reviews",
                "detail": f"Your top competitor appears in {top_count}/10 queries. AI models prioritize review count and rating. Aim for 50+ Google reviews with recent activity.",
                "domain": "google.com",
                "citation_count": top_count,
                "priority": 5,
            })

    # 3. If no domains cited at all, suggest basic web presence
    if not top_domains:
        recommendations.append({
            "action": "Basic Web Presence",
            "detail": "No cited sources were found. Create a website with structured data (schema.org/LocalBusiness), claim your Google Business Profile, and get listed on major directories.",
            "domain": "",
            "citation_count": 0,
            "priority": 5,
        })

    # Sort by priority descending
    recommendations.sort(key=lambda r: r["priority"], reverse=True)
    # Deduplicate by action name
    seen = set()
    unique = []
    for r in recommendations:
        if r["action"] not in seen:
            seen.add(r["action"])
            unique.append(r)

    return {
        "recommendations": unique,
        "top_cited_domains": top_domains[:10],
        "total_unique_domains": len(top_domains),
    }


# ---------------------------------------------------------------------------
# Multi-engine audit (Phase 2 — compare visibility across AI platforms)
# ---------------------------------------------------------------------------
def run_multi_audit(api_key, queries, practices, engines=None, mock=False, on_query=None, market=""):
    """Run the audit across multiple AI engines and produce a per-engine breakdown.

    Returns same shape as run_audit() plus:
        "engines": {engine_id: {ranking, queries_with_any, total_cost, query_results, ...}, ...}
    """
    engines = engines or MULTI_ENGINES
    per_engine = {}
    all_practices_mentioned = {p["name"]: 0 for p in practices}
    total_queries = 0
    total_any = 0
    total_none = 0
    total_cost = 0.0
    all_query_results = []
    all_errors = []
    all_source_domains = Counter()
    all_recommendations = []

    for engine in engines:
        if mock:
            result = run_audit(
                engine["provider"], engine["model"], api_key,
                queries, practices, mock=True, market=market
            )
        else:
            result = run_audit(
                engine["provider"], engine["model"], api_key,
                queries, practices, market=market,
                on_query=lambda i, total, q, hits, qc, rc: on_query(
                    i, total, q, hits, qc, rc, engine["id"]
                ) if on_query else None,
            )

        per_engine[engine["id"]] = {
            "name": engine["name"],
            "ranking": result["ranking"],
            "queries_with_any": result["queries_with_any"],
            "queries_with_none": result["queries_with_none"],
            "total_cost": result["total_cost"],
            "verdict": result["verdict"],
            "query_results": result["query_results"],
            "top_cited_domains": result.get("top_cited_domains", []),
            "recommendations": result.get("recommendations", []),
        }

        # Aggregate across engines
        for row in result["ranking"]:
            all_practices_mentioned[row["name"]] += row["count"]
        total_queries = max(total_queries, result["total_queries"])
        total_cost += result["total_cost"]
        all_errors.extend(result.get("errors", []))
        all_query_results.extend(result.get("query_results", []))
        for dm, ct in result.get("top_cited_domains", []):
            all_source_domains[dm] += ct
        all_recommendations.extend(result.get("recommendations", []))

    total_any = sum(1 for c in all_practices_mentioned.values() if c > 0)

    # Compute aggregate ranking
    ranking = sorted(all_practices_mentioned.items(), key=lambda kv: kv[1], reverse=True)
    counts = [c for _, c in ranking]

    # Verdict
    total_queries_all = total_queries * len(engines)
    if total_any == 0:
        verdict = "COLLAPSES — no practices named"
        detail = "Not a single practice appeared in any engine across any query."
    else:
        top, bottom = counts[0], counts[-1]
        if top - bottom >= (len(engines) * 3) and bottom <= (total_queries_all // 4):
            verdict = "GAP IS REAL — build the full tool"
            detail = f"Top practice at {top}/{total_queries_all}, bottom at {bottom}/{total_queries_all}. Consistent gap across {len(engines)} engines."
        elif bottom > (total_queries_all // 4):
            verdict = "AMBIGUOUS — investigate before building"
            detail = f"Top {top}/{total_queries_all} vs bottom {bottom}/{total_queries_all}. Too flat across {len(engines)} engines."
        else:
            verdict = "GAP IS REAL — build the full tool"
            detail = f"Top practice at {top}/{total_queries_all}, bottom at {bottom}/{total_queries_all}. Significant gap found."

    # Dedupe recommendations
    seen_recs = set()
    unique_recs = []
    for r in all_recommendations:
        if r["action"] not in seen_recs:
            seen_recs.add(r["action"])
            unique_recs.append(r)
    unique_recs.sort(key=lambda r: r["priority"], reverse=True)

    return {
        "ranking": [{"name": n, "count": c} for n, c in ranking],
        "total_queries": total_queries,
        "total_queries_all": total_queries_all,
        "queries_with_any": total_any,
        "queries_with_none": len(practices) - total_any,
        "verdict": verdict,
        "detail": detail,
        "query_results": all_query_results,
        "errors": all_errors,
        "total_cost": round(total_cost, 6),
        "market": market or "",
        "provider": "multi",
        "model": f"{len(engines)} engines",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_analysis": _analyze_citations(all_query_results),
        "recommendations": unique_recs,
        "top_cited_domains": [(d, c) for d, c in all_source_domains.most_common(15)],
        "engines": per_engine,
        # Phase 2: competitor gap analysis (aggregate)
        "gap_analysis": _competitor_gap_analysis(all_query_results, practices),
    }


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
    caller = {"openrouter": call_openrouter, "zai": call_zai, "nvidia": call_nvidia}[provider]
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

    # Phase 1: citation analysis + recommendations
    ranked_list = [{"name": n, "count": c} for n, c in ranking]
    source_data = _analyze_citations(query_results)
    recs = _generate_recommendations(source_data, practices, ranked_list)
    gap_data = _competitor_gap_analysis(query_results, practices)

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
        # Phase 1: citation insights
        "source_analysis": source_data,
        "recommendations": recs["recommendations"],
        "top_cited_domains": recs["top_cited_domains"],
        # Phase 2: competitor gap analysis
        "gap_analysis": gap_data,
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
    ap.add_argument("--provider", choices=["openrouter", "zai", "nvidia"], default="openrouter",
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
    elif args.provider == "zai":
        key = os.environ.get("ZAI_API_KEY", "").strip()
        env_name = "ZAI_API_KEY"
    else:
        key = os.environ.get("NVIDIA_API_KEY", "").strip()
        env_name = "NVIDIA_API_KEY"
    if not key:
        print(f"ERROR: set {env_name}, or run with --mock.", file=sys.stderr)
        return 2
    return run(args.provider, model, key, args.queries, mock=False)


if __name__ == "__main__":
    sys.exit(main())
