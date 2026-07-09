#!/usr/bin/env python3
"""PDF report generator for GeoAudit — white-label CMO-ready deliverables.

Stdlib only — generates a clean HTML report that browsers can print to PDF.
"""
import json
import os
from datetime import datetime, timezone


def generate_report(data: dict, output_path: str = None) -> str:
    """Generate a white-label HTML report from audit data. Returns HTML string."""
    market = data.get("market", "Local Healthcare Market")
    ts = datetime.now(timezone.utc).strftime("%B %d, %Y")
    verdict = data.get("verdict", "Unknown")
    ranking = data.get("ranking", [])
    total_q = data.get("total_queries", 0)
    total_any = data.get("queries_with_any", 0)
    recs = data.get("recommendations", [])
    domains = data.get("top_cited_domains", [])
    gaps = data.get("gap_analysis", [])
    engines = data.get("engines", {})
    total_cost = data.get("total_cost", 0)
    total_queries_all = data.get("total_queries_all", total_q)

    verdict_cls = "good" if "REAL" in verdict else "warn" if "AMBIGUOUS" in verdict else "bad"
    verdict_icon = {"good": "✓", "warn": "⚠", "bad": "✗"}.get(verdict_cls, "!")

    # Build the ranking table
    rank_rows = ""
    for i, row in enumerate(ranking[:15]):
        count = row["count"]
        pct = (count / max(total_q, 1)) * 100
        bar_fill = min(pct, 100)
        rank_rows += f"""<tr>
<td class="pos">#{i+1}</td>
<td class="name">{row['name']}</td>
<td class="bar-cell"><div class="bar-track"><div class="bar-fill" style="width:{bar_fill}%"></div></div></td>
<td class="count">{count}/{total_q if total_queries_all == 0 else total_queries_all}</td>
</tr>"""

    # Build recommendations
    rec_html = ""
    for r in recs[:8]:
        rec_html += f"""<div class="rec-item">
<div class="rec-prio p{r['priority']}">{r['priority']}</div>
<div class="rec-body">
<div class="rec-title">{r['action']}</div>
<div class="rec-detail">{r['detail']}</div>
{r.get('domain', '') and f'<div class="rec-src">Source: {r["domain"]} ({r.get("citation_count", 0)}×)</div>' or ''}
</div>
</div>"""

    # Build domain tags
    domain_html = ""
    for d, ct in domains[:12]:
        domain_html += f'<span class="dom-tag">{d} <b>{ct}×</b></span>\n'

    # Build gap analysis
    gap_html = ""
    gaps_with_data = [g for g in (gaps or []) if g.get("gap_queries")]
    for g in gaps_with_data[:5]:
        gap_html += f'<div class="gap-section"><h4>{g["practice"]}</h4>'
        gap_html += f'<p>This practice was <span class="bad">invisible</span> in {g["missing_from"]}/{g["present_in"]+g["missing_from"]} queries while competitors won.</p>'
        for gq in g.get("gap_queries", [])[:3]:
            gap_html += f"""<div class="gap-query">
<div class="gap-qtext">Query: <em>"{gq['query']}"</em></div>
<div class="gap-comp">Competitors mentioned: <strong>{', '.join(gq.get('competitors_mentioned', []))}</strong></div>
<div class="gap-srcs">Sources cited: {', '.join(s['domain'] for s in gq.get('sources_cited', [])[:3])}</div>
</div>"""
        gap_html += '</div>'

    # Engine breakdown
    eng_html = ""
    if engines:
        eng_html = '<h3>Per-Engine Breakdown</h3><div class="engine-grid">'
        for eid, eng in engines.items():
            eng_html += f"""<div class="engine-card">
<div class="eng-name">{eng['name']}</div>
<div class="eng-metric">{eng['queries_with_any']}/{total_q} queries</div>
<div class="eng-metric">${eng['total_cost']:.4f}</div>
</div>"""
        eng_html += '</div>'

    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><title>GeoAudit Report — {market}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif;font-size:11px;line-height:1.5;color:#1a1c20;max-width:780px;margin:0 auto;padding:36px 32px}}
h1{{font-size:1.6rem;font-weight:800;letter-spacing:-.02em;margin-bottom:4px}}
h2{{font-size:1.15rem;font-weight:700;margin:28px 0 10px;padding-top:18px;border-top:2px solid #e8eaed;color:#1a1c20}}
h3{{font-size:.95rem;font-weight:700;margin:18px 0 8px;color:#555a62}}
h4{{font-size:.85rem;font-weight:700;margin:12px 0 4px}}
.subtitle{{color:#808791;font-size:.85rem;margin-bottom:22px}}
.verdict{{padding:16px 20px;border-radius:8px;margin:16px 0;font-size:1rem;font-weight:700}}
.verdict.good{{background:#ecfdf5;color:#059669;border:1.5px solid #a7f3d0}}
.verdict.warn{{background:#fffbeb;color:#d97706;border:1.5px solid #fde68a}}
.verdict.bad{{background:#fef2f2;color:#dc2626;border:1.5px solid #fecaca}}
.meta{{font-size:.82rem;color:#555a62;margin-bottom:10px}}
table{{width:100%;border-collapse:collapse;margin:10px 0 16px}}
th{{text-align:left;font-size:.7rem;color:#808791;text-transform:uppercase;letter-spacing:.06em;padding:6px 8px;border-bottom:1px solid #e8eaed}}
td{{padding:6px 8px;border-bottom:1px solid #e8eaed;font-size:.82rem}}
.bar-cell{{width:120px}}
.bar-track{{background:#e8eaed;border-radius:3px;height:10px;overflow:hidden}}
.bar-fill{{background:linear-gradient(90deg,#6366f1,#8b5cf6);height:100%;border-radius:3px}}
.pos{{font-weight:700;color:#808791;width:30px}}
.count{{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}}
.rec-item{{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #e8eaed;align-items:flex-start}}
.rec-prio{{width:22px;height:22px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:.6rem;font-weight:700;color:#fff;flex-shrink:0}}
.p5{{background:#059669}}.p4{{background:#6366f1}}.p3{{background:#0891b2}}.p2{{background:#808791}}
.rec-title{{font-weight:600;font-size:.82rem}}.rec-detail{{font-size:.76rem;color:#555a62;margin-top:2px}}
.rec-src{{font-size:.7rem;color:#6366f1;margin-top:3px}}
.dom-tag{{display:inline-block;padding:2px 8px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:99px;font-size:.7rem;margin:2px 4px 2px 0;font-family:'SF Mono',monospace}}
.gap-section{{margin:12px 0;padding:10px 14px;background:#fef2f2;border-radius:6px;border-left:3px solid #dc2626}}
.gap-comp{{font-size:.8rem;margin:4px 0}}
.gap-qtext{{font-size:.82rem}}
.gap-srcs{{font-size:.76rem;color:#555a62;margin-top:3px}}
.engine-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:8px 0}}
.engine-card{{background:#f7f8fa;border:1px solid #e8eaed;border-radius:8px;padding:12px;text-align:center}}
.eng-name{{font-weight:700;font-size:.8rem;margin-bottom:4px}}
.eng-metric{{font-size:.75rem;color:#555a62}}
.bad{{color:#dc2626;font-weight:600}}
.good{{color:#059669}}
.warn{{color:#d97706}}
.footer{{margin-top:30px;padding-top:14px;border-top:1px solid #e8eaed;font-size:.7rem;color:#a5aab3;text-align:center}}
@page{{size:A4;margin:15mm}}
@media print{{body{{padding:0}}}}
</style></head><body>
<h1>GeoAudit Report</h1>
<div class="subtitle">{market} — {ts}</div>

<div class="verdict {verdict_cls}">{verdict_icon} {verdict}</div>
<div class="meta">
{total_any}/{total_q} queries named a tracked practice across {len(engines) or 1} engine{"" if (len(engines) or 1) == 1 else "s"}.
{"All values aggregated across engines." if len(engines) > 1 else ""}
Total API cost: ${total_cost:.4f}
</div>

{eng_html}

{('<h2>Visibility Ranking</h2><table><thead><tr><th>#</th><th>Practice</th><th>Visibility</th><th>Mentions</th></tr></thead><tbody>' + rank_rows + '</tbody></table>') if rank_rows else ''}

{('<h2>Competitor Gap Analysis</h2><p class="meta" style="margin-bottom:12px">Where your tracked practices were invisible but competitors were mentioned — and exactly what sources the AI cited.</p>' + gap_html) if gaps_with_data else '<h2>Competitor Gap Analysis</h2><p class="meta">No gap data available — all practices mentioned equally.</p>'}

{('<h2>Recommended Actions</h2>' + rec_html) if recs else ''}

{('<h2>Top Cited Sources</h2><div style="margin:8px 0 16px">' + domain_html + '</div>') if domains else ''}

<div class="footer">
Generated by GeoAudit — AI Visibility Intelligence. Report for informational purposes only.
</div></body></html>"""

    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html


# CLI: python3 report.py <audit-json-path>
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 report.py data/audits/probe-*.json [output.html]")
        sys.exit(1)

    json_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else json_path.replace(".json", "-report.html")

    with open(json_path) as f:
        data = json.load(f)

    html = generate_report(data, out_path)
    print(f"Report saved to: {out_path}")
    print(f"Size: {len(html)} bytes")
