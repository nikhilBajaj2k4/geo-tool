# GeoAudit — Build Log

**Date**: July 9-10, 2026  
**Repository**: [github.com/nikhilBajaj2k4/geo-tool](https://github.com/nikhilBajaj2k4/geo-tool)

---

## What This Is

GeoAudit measures how often local medical practices appear in AI search answers (ChatGPT, Perplexity, Gemini) when patients search for their specialty. It identifies visibility gaps between competing practices and prescribes specific actions to close them.

---

## Architecture

```
geo-tool/
├── probe.py          Core engine — providers, mention detection, citation analysis,
│                     multi-engine audit, gap analysis, recommendations
├── server.py         Web UI — SaaS dashboard, SSE streaming, PDF reports
├── report.py         White-label PDF report generator (print-to-PDF)
├── test_runner.py    CLI test suite — runs multiple markets in sequence
├── ftest.py          Standalone render verification test
├── check_render.py   UI render debug helper
├── quick_test.py     DOM render test harness
├── data/
│   ├── audits/       CLI audit output (probe-{provider}-{timestamp}.json)
│   └── test-runs/    Multi-market test results + summary.json
├── .env.example      API key template
├── .gitignore         Excludes audits, .env, __pycache__, screenshots
└── docs/
    └── gaston.md     Architecture notes
```

### Control Flow

```
Browser (POST /api/audit) or CLI (main() → run())
        │
        ▼
  run_audit() / run_multi_audit()
        │
        ├── call_openrouter()  → Perplexity Sonar / ChatGPT / Gemini Flash
        ├── mentioned_practices_for()  → case-insensitive alias match
        ├── _analyze_citations()      → domain extraction & counting
        ├── _competitor_gap_analysis() → per-practice invisibility tracking
        └── _generate_recommendations() → priority-scored actions
                │
                ▼
        Structured result dict → JSON file + SSE stream + rendered dashboard
```

---

## Phase 0 — Mention Tracking & Verdict Logic

### probe.py

- `QUERIES`: 10 hardcoded patient questions (Austin dentists)
- `PRACTICES`: 9 real Austin dental practices with alias lists
- `mentioned_practices()`: Case-insensitive substring match across answer text + source titles + source content
- `run_audit()`: Orchestrates query loop, counts mentions, computes verdict
- Verdict logic:
  - **GAP IS REAL**: `top - bottom >= 3` AND `bottom <= total_queries // 4`
  - **AMBIGUOUS**: Spread exists but too flat
  - **COLLAPSES**: Zero practices named across all queries

### server.py

- Stdlib HTTP server on `127.0.0.1:8765`
- HTML/JS inlined as Python strings
- SSE streaming via `ReadableStream` (POST-based, not EventSource)
- Live progress bar + cost tracking
- Results: ranking bars, per-query detail with expandable AI answers
- History tab with localStorage persistence

### Fixes Applied

- **Mock determinism**: `hash()` → `hashlib.md5` (Python 3.3+ PYTHONHASHSEED)
- **Error visibility**: Failed API calls now print "ERROR" instead of silent "(none)"
- **Web UI `parse_practices()`**: Removed single-word alias generation (false positives)
- **README**: Synced to actual defaults (OpenRouter, not z.ai)
- **`.gitignore`**: Excludes audit JSONs, `.env`, `__pycache__`
- **ID collision**: `#queries` textarea vs results container → renamed to `#queryDetails`

---

## Phase 1 — Source Citation + Recommendations

### probe.py additions

```python
_extract_domain(url)          # Parse URL → clean domain
_analyze_citations(results)    # Counter of cited domains per query
_generate_recommendations()    # Map domains → priority-scored actions
```

#### RECOMMENDATION_RULES

| Domain Keyword | Action | Priority |
|---|---|---|
| google.com | Google Reviews | 5 |
| healthgrades.com | Healthgrades Profile | 4 |
| zocdoc.com | Zocdoc Listing | 4 |
| yelp.com | Yelp Listing | 4 |
| reddit.com | Reddit Presence | 3 |
| justdial.com | Justdial Listing (India) | 4 |
| practo.com | Practo Profile (India) | 4 |
| facebook.com | Facebook Page | 2 |

New output fields: `source_analysis`, `recommendations`, `top_cited_domains`

### server.py — SaaS Dashboard v1

- Indigo accent, clean cards, gradient progress bar
- 3 KPI cards: queries with mentions, domains cited, practices invisible
- **Recommended Actions** section with priority-scored cards
- **Top Cited Sources** pill tags
- Per-query domain chips + collapsible source/answer

### Verified

Live run on Austin dentists: `deltadental.com 3×`, `reddit.com 3×`, `zocdoc.com 2×`, `localpicks.ai 2×` → recommendations: "Zocdoc Listing", "Reddit Presence"

---

## Phase 2 — Multi-Engine + Gap Analysis + PDF Reports

### Multi-Engine (probe.py)

```python
MULTI_ENGINES = [
    {"id": "sonar",   "name": "Perplexity Sonar", "model": "perplexity/sonar"},
    {"id": "gpt4o",   "name": "ChatGPT",           "model": "openai/gpt-4o-mini:online"},
    {"id": "gemini",  "name": "Gemini Flash",      "model": "google/gemini-2.5-flash"},
]
```

`run_multi_audit()`: Runs same queries across all engines, aggregates results.
Per-engine breakdowns in output: ranking, cost, verdict, citation domains per engine.

Live test results (Austin dentists, 2 queries):

| Engine | Queries with mentions | Top Practice | Cost |
|---|---|---|---|
| Perplexity Sonar | 2/2 | Austin Dental Spa (2) | $0.0106 |
| ChatGPT | 2/2 | Austin Dental Spa (2) | $0.0112 |
| Gemini Flash | 2/2 | Austin Dental Spa (2) | $0.0008 |

### Competitor Gap Analysis (probe.py)

`_competitor_gap_analysis()`: For each query where a competitor won but the practice was invisible:

- Which competitors were mentioned
- What domains the AI cited
- The dominant source domain
- Per-practice: `present_in`, `missing_from`, `gap_queries` arrays

### PDF Reports (report.py)

`generate_report()`: Clean HTML report — scorecard, ranking bars, per-engine breakdown cards, competitor gap analysis, priority-scored recommendations, top cited sources. Print-to-PDF ready with `@page` media queries.

### server.py additions

- Engine selector pills (Sonar / GPT / Gemini) with per-engine query counts
- 4 KPI cards with engine count
- Visibility scatter plot
- Competitor Gap Analysis section
- "Download Report" button → opens printer-friendly HTML in new tab
- `/api/report` POST endpoint

---

## Phase 2b — Terminal Theme Overhaul

Full CSS rewrite:

- **Palette**: `#0a0c11` background, `#00ff88` neon green accent
- **Typography**: JetBrains Mono everywhere
- **Effects**: Scanline overlay (`repeating-linear-gradient`), CRT flicker animation
- **Form labels**: `> specialty` terminal prompt style
- **Section cards**: `// config` comment-style labels
- **Topbar**: `$ new_audit` prompt-style heading
- **Nav**: lowercase_monospace naming convention
- **Buttons**: Squared corners, green glow on hover
- **Engine dots**: Colored indicators (green/blue/amber)

---

## Test Suite

### test_runner.py

Runs multiple market configs in sequence, saves individual results + summary.

```
dentist-austin:     GAP IS REAL (8/10, $0.0543) — Perplexity Sonar
dentist-kota:       GAP IS REAL (4/10, $0.0546) — Jaiswal Dental Clinic 4/10
dermatologist-london: GAP IS REAL (7/10, $0.0553) — 3-way tie at 3/10
```

All results saved to `data/test-runs/`.

### ftest.py

Standalone UI render test — loads the exact server HTML + JS, injects multi-engine audit data, verifies all cards render. Confirmed: **PASS: 5 ranks, 4 KPIs**

---

## How to Run

```bash
# 1. Set your API key
export OPENROUTER_API_KEY="your-key-here"

# 2. CLI (single engine)
python3 probe.py                     # full run, Perplexity Sonar
python3 probe.py --mock              # dry run, no key needed
python3 probe.py --queries 3         # quick 3-query smoke test

# 3. Web dashboard
python3 server.py                    # http://127.0.0.1:8765
python3 server.py --port 8080        # custom port

# 4. Multi-market test suite
python3 test_runner.py

# 5. PDF report from CLI audit
python3 report.py data/audits/probe-openrouter-{timestamp}.json
```

---

## Key Data Structures

### Audit Result (from `run_audit()`)

```python
{
    "ranking": [{"name": str, "count": int}, ...],
    "total_queries": int,
    "queries_with_any": int,
    "queries_with_none": int,
    "verdict": str,          # "GAP IS REAL — ..." | "AMBIGUOUS — ..." | "COLLAPSES — ..."
    "detail": str,
    "query_results": [{query, mentions, answer, sources, cost, ...}, ...],
    "errors": [...],
    "total_cost": float,
    "market": str,
    "provider": str,
    "model": str,
    "timestamp": str,        # UTC ISO-8601
    "source_analysis": {
        "source_domains": {domain: count},
        "per_query_citations": [{query, domains_cited, ...}],
        "top_domains_ranked": [(domain, count), ...]
    },
    "recommendations": [{action, detail, domain, citation_count, priority}, ...],
    "top_cited_domains": [(domain, count), ...],
    "gap_analysis": [{practice, present_in, missing_from, gap_queries}, ...],
    "engines": {            # multi-engine only
        "sonar": {name, ranking, queries_with_any, total_cost, verdict, ...},
        "gpt4o": {...},
        "gemini": {...}
    }
}
```

---

## Git History

```
fb77bce Complete terminal theme overhaul — dark CRT aesthetic
5983231 Ref issue: restart server to clear cached UI
35873f7 Fix UI rendering — RF is now window.RF, verified working
2b3cbcd Fix UI rendering — remove setTimeout race condition
8a12207 Complete UI overhaul — production SaaS dashboard
d8a2a90 Phase 2: Competitor gap analysis + white-label PDF reports
19394cc Phase 2: Multi-engine coverage — Sonar + ChatGPT + Gemini
a81a906 Fix SSE reader pump — done frame processing
a26ff48 Phase 1: Source citation analysis + recommendations
241a9e8 Add test runner + 3 test runs
61c806c SaaS dashboard redesign — sidebar nav, history
31605fc Remove screenshots from repo
be3b647 Full UI overhaul — dark terminal-style redesign
266329e Fix ID collision in web UI
c460ef2 Initial commit
```

---

## Next Steps

| Priority | Feature | Impact |
|---|---|---|
| P1 | Scheduled recurring audits + trend lines | Subscription hook |
| P1 | Crawlability audit (schema, reviews, site health) | Hyper-specific recs |
| P2 | Prompt discovery (what patients actually ask) | Expand query coverage |
| P2 | Multi-location support (franchise/chain) | Enterprise use |
| P3 | Google Search Console + Analytics integration | ROI measurement |
| P3 | Agency white-label (custom domain, branding) | Agency go-to-market |

---

## Total API Cost (All Tests)

| Test | Queries | Engines | Cost |
|---|---|---|---|
| Austin dentist (mock) | 10 | 3 | $0.00 |
| Austin dentist (live) | 10 | 1 | $0.05 |
| Kota dentist (live) | 10 | 1 | $0.05 |
| London dermatologist (live) | 10 | 1 | $0.06 |
| Multi-engine test (live) | 2 | 3 | $0.02 |
| **Total spent** | | | **~$0.18** |
