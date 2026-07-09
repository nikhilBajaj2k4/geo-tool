#!/usr/bin/env python3
"""
Minimal local web UI for the Healthcare GEO Audit probe.

Stdlib only (http.server). One page: pick city/specialty/practices, hit Run,
see the ranking + verdict. Reuses probe.run_audit() so the logic is identical
to the CLI.

Usage:
    OPENROUTER_API_KEY=... python3 server.py        # then open the printed URL
    python3 server.py --port 8765
    python3 server.py                               # works with --mock from the page
"""
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import probe

HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GeoAudit — Healthcare Visibility Intelligence</title>
<style>
  :root {
    --bg:#f8fafc; --surface:#fff; --surface-2:#f1f5f9; --surface-3:#e2e8f0; --surface-4:#cbd5e1;
    --border:#e2e8f0; --border-strong:#cbd5e1;
    --text:#0f172a; --text-2:#475569; --text-3:#64748b; --muted:#94a3b8;
    --accent:#6366f1; --accent-hover:#4f46e5; --accent-soft:#eef2ff; --accent-10:rgba(99,102,241,.1);
    --good:#059669; --good-soft:#ecfdf5; --good-border:#a7f3d0;
    --warn:#d97706; --warn-soft:#fffbeb; --warn-border:#fde68a;
    --bad:#dc2626; --bad-soft:#fef2f2; --bad-border:#fecaca;
    --gradient:linear-gradient(135deg,#6366f1,#8b5cf6,#a855f7);
    --shadow-sm:0 1px 2px rgba(0,0,0,.05);
    --shadow:0 1px 3px rgba(0,0,0,.1),0 1px 2px rgba(0,0,0,.06);
    --shadow-md:0 4px 6px -1px rgba(0,0,0,.1),0 2px 4px -2px rgba(0,0,0,.05);
    --shadow-lg:0 10px 15px -3px rgba(0,0,0,.1),0 4px 6px -4px rgba(0,0,0,.05);
    --radius:12px; --radius-sm:8px; --radius-xs:6px;
  }
  * { box-sizing:border-box; }
  @media (prefers-reduced-motion:reduce) { *,::before,::after { animation-duration:0s!important; transition-duration:0s!important; } }
  body {
    margin:0; background:var(--bg); color:var(--text); overflow-x:hidden;
    font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',system-ui,sans-serif;
    font-size:14px; line-height:1.6; -webkit-font-smoothing:antialiased;
  }
  ::selection { background:var(--accent-10); color:var(--accent); }

  /* --- layout --- */
  .app { display:flex; min-height:100vh; }
  .sidebar { width:240px; background:var(--surface); border-right:1px solid var(--border);
    display:flex; flex-direction:column; flex-shrink:0; position:sticky; top:0; height:100vh;
    z-index:10; }
  .sidebar-header { padding:24px 20px 20px; border-bottom:1px solid var(--border); }
  .sidebar-header .logo { font-size:1.1rem; font-weight:800; color:var(--text);
    letter-spacing:-.02em; display:flex; align-items:center; gap:10px; }
  .sidebar-header .logo-icon { width:32px; height:32px; background:var(--gradient);
    border-radius:var(--radius-sm); display:flex; align-items:center; justify-content:center;
    color:#fff; font-size:.85rem; box-shadow:0 2px 8px rgba(99,102,241,.3); }
  .sidebar-header .badge { font-size:.65rem; font-weight:600; color:var(--accent);
    background:var(--accent-soft); padding:2px 8px; border-radius:99px;
    letter-spacing:.04em; }
  .sidebar-nav { padding:12px 12px; flex:1; }
  .sidebar-nav a { display:flex; align-items:center; gap:10px; padding:8px 12px;
    border-radius:var(--radius-xs); font-size:.85rem; font-weight:500; color:var(--text-2);
    text-decoration:none; cursor:pointer; transition:all .15s; margin-bottom:2px; }
  .sidebar-nav a:hover { background:var(--surface-2); color:var(--text); }
  .sidebar-nav a.active { background:var(--accent-soft); color:var(--accent); font-weight:600; }
  .sidebar-nav a .nav-icon { font-size:1rem; width:20px; text-align:center; }
  .sidebar-footer { padding:12px 20px; border-top:1px solid var(--border); font-size:.72rem;
    color:var(--muted); }
  .sidebar-footer span { display:block; }
  .sidebar-footer .model { color:var(--accent); font-weight:600; }

  .main { flex:1; min-width:0; }
  .topbar { background:var(--surface); border-bottom:1px solid var(--border);
    padding:16px 28px; display:flex; align-items:center; justify-content:space-between; }
  .topbar h2 { margin:0; font-size:1.1rem; font-weight:700; color:var(--text); letter-spacing:-.01em; }
  .topbar .stats { display:flex; gap:20px; }
  .topbar .stat { text-align:right; }
  .topbar .stat .val { font-size:1.1rem; font-weight:700; color:var(--text); font-variant-numeric:tabular-nums; }
  .topbar .stat .lbl { font-size:.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
  .content { padding:28px; max-width:1100px; }

  /* --- tabs --- */
  .tab { display:none; }
  .tab.active { display:block; animation:fadeIn .25s ease; }
  @keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }

  /* --- cards --- */
  .card { background:var(--surface); border:1px solid var(--border);
    border-radius:var(--radius); padding:24px; margin-bottom:20px;
    box-shadow:var(--shadow-sm); transition:box-shadow .2s; }
  .card:hover { box-shadow:var(--shadow); }
  .card-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }
  .card-title { font-size:.72rem; font-weight:700; color:var(--text-3); text-transform:uppercase;
    letter-spacing:.07em; }
  .card-row { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  @media (max-width:768px) { .card-row { grid-template-columns:1fr; } }

  /* --- form --- */
  .field { margin-bottom:16px; }
  .field:last-child { margin-bottom:0; }
  .field label { display:block; font-size:.78rem; font-weight:600; color:var(--text-2);
    margin-bottom:6px; }
  .field label .opt { color:var(--muted); font-weight:400; }
  .field input, .field textarea {
    width:100%; background:var(--surface); color:var(--text); font-family:inherit;
    border:1.5px solid var(--border); border-radius:var(--radius-sm);
    padding:10px 14px; font-size:.88rem; line-height:1.55;
    transition:border-color .15s, box-shadow .15s;
  }
  .field input::placeholder, .field textarea::placeholder { color:var(--muted); }
  .field input:focus, .field textarea:focus { outline:none; border-color:var(--accent);
    box-shadow:0 0 0 3px var(--accent-10); }
  .field input:disabled, .field textarea:disabled {
    background:var(--surface-2); color:var(--muted); border-color:var(--border);
    cursor:not-allowed; }
  .field textarea { min-height:100px; resize:vertical; }
  .field input { height:40px; }

  .actions { display:flex; align-items:center; gap:12px; margin-top:20px; flex-wrap:wrap; }
  .btn {
    padding:10px 20px; font-size:.85rem; font-weight:600; border-radius:var(--radius-sm);
    cursor:pointer; display:inline-flex; align-items:center; gap:7px; border:0;
    font-family:inherit; transition:all .15s; white-space:nowrap;
  }
  .btn-primary { background:var(--accent); color:#fff; box-shadow:0 1px 3px rgba(99,102,241,.3); }
  .btn-primary:hover:not(:disabled) { background:var(--accent-hover); box-shadow:0 4px 12px rgba(99,102,241,.35); transform:translateY(-1px); }
  .btn-primary:active:not(:disabled) { transform:translateY(0); }
  .btn-primary:disabled { opacity:.5; cursor:not-allowed; transform:none; }
  .btn-ghost { background:transparent; color:var(--text-2); border:1.5px solid var(--border); }
  .btn-ghost:hover:not(:disabled) { background:var(--surface-2); border-color:var(--surface-4); }
  .btn-danger { background:var(--bad-soft); color:var(--bad); border:1.5px solid var(--bad-border); }
  .btn-danger:hover:not(:disabled) { background:var(--bad); color:#fff; border-color:var(--bad); }
  .spinner { width:16px; height:16px; border:2px solid rgba(255,255,255,.3);
    border-top-color:#fff; border-radius:50%; animation:spin .6s linear infinite; display:none; }
  .running .spinner { display:block; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .toggle { display:flex; align-items:center; gap:8px; font-size:.82rem; color:var(--text-2);
    cursor:pointer; user-select:none; }
  .toggle input { width:32px; height:18px; appearance:none; background:var(--surface-3);
    border-radius:99px; cursor:pointer; position:relative; transition:background .2s; }
  .toggle input::after { content:''; width:14px; height:14px; background:#fff; border-radius:50%;
    position:absolute; top:2px; left:2px; transition:transform .2s; box-shadow:0 1px 2px rgba(0,0,0,.1); }
  .toggle input:checked { background:var(--accent); }
  .toggle input:checked::after { transform:translateX(14px); }
  .status-line { color:var(--bad); font-size:.82rem; min-height:1.2em; }

  /* --- running overlay --- */
  .run-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
    padding:20px 24px; margin-bottom:20px; box-shadow:var(--shadow-sm); }
  .run-progress { display:flex; align-items:center; gap:14px; margin-bottom:14px; }
  .run-track { flex:1; height:6px; background:var(--surface-3); border-radius:3px; overflow:hidden; }
  .run-fill { height:100%; width:0%; background:var(--gradient); border-radius:3px;
    transition:width .3s ease; }
  .run-label { font-size:.8rem; font-weight:600; color:var(--text-2); min-width:52px;
    text-align:right; font-variant-numeric:tabular-nums; }
  .run-log { background:var(--surface-2); border-radius:var(--radius-sm); padding:10px 14px;
    max-height:300px; overflow-y:auto; font-size:.78rem; line-height:1.7; font-family:'SF Mono','Fira Code',monospace; }
  .run-log .r-hit { color:var(--good); }
  .run-log .r-miss { color:var(--muted); }
  .run-log .r-err { color:var(--bad); }
  .run-log .r-meta { color:var(--text-3); }
  .run-footer { display:flex; justify-content:space-between; align-items:center;
    margin-top:12px; font-size:.76rem; color:var(--text-3); }
  .run-footer .cost { color:var(--good); font-weight:600; }

  /* --- results --- */
  .result-verdict { padding:20px 24px; border-radius:var(--radius); margin-bottom:20px;
    display:flex; align-items:center; gap:14px; font-weight:700; font-size:.95rem; }
  .result-verdict.good { background:var(--good-soft); color:var(--good); border:1px solid var(--good-border); }
  .result-verdict.warn { background:var(--warn-soft); color:var(--warn); border:1px solid var(--warn-border); }
  .result-verdict.bad { background:var(--bad-soft); color:var(--bad); border:1px solid var(--bad-border); }
  .result-verdict .vicon { font-size:1.3rem; }
  .result-meta { font-size:.82rem; color:var(--text-3); margin-bottom:20px; }

  /* --- ranking --- */
  .rank-list { margin-top:8px; }
  .rank-item { display:grid; grid-template-columns:24px 1fr 80px 64px; gap:12px; align-items:center;
    padding:10px 0; border-bottom:1px solid var(--border); font-size:.85rem; }
  @media (max-width:768px) { .rank-item { grid-template-columns:24px 1fr 64px; } .rank-item .rank-bar-wrap { display:none; } }
  .rank-item:last-child { border-bottom:0; }
  .rank-pos { font-weight:700; color:var(--muted); font-size:.78rem; text-align:right; }
  .rank-name { font-weight:600; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .rank-bar-wrap { min-width:0; }
  .rank-bar-track { height:8px; background:var(--surface-3); border-radius:4px; overflow:hidden; }
  .rank-bar-fill { height:100%; border-radius:4px; transition:width .6s cubic-bezier(.4,0,.2,1); }
  .rank-bar-fill.hi { background:var(--accent); }
  .rank-bar-fill.md { background:var(--accent); opacity:.5; }
  .rank-bar-fill.lo { background:var(--muted); opacity:.3; }
  .rank-count { text-align:right; font-weight:700; color:var(--text); font-variant-numeric:tabular-nums; }
  .rank-count .of { font-weight:400; color:var(--muted); }

  /* --- query list --- */
  .query-item { padding:12px 0; border-bottom:1px solid var(--border); }
  .query-item:last-child { border-bottom:0; }
  .query-head { display:flex; align-items:center; gap:10px; }
  .query-head .q-dot { width:20px; height:20px; border-radius:50%; display:flex;
    align-items:center; justify-content:center; font-size:.65rem; flex-shrink:0; }
  .query-head .q-dot.hit { background:var(--good-soft); color:var(--good); }
  .query-head .q-dot.miss { background:var(--surface-2); color:var(--muted); }
  .query-head .q-text { font-size:.85rem; font-weight:500; flex:1; word-break:break-word; }
  .query-head .q-cost { font-size:.72rem; color:var(--muted); font-family:'SF Mono','Fira Code',monospace; }
  .query-mentions { margin:4px 0 0 30px; font-size:.78rem; }
  .query-mentions.hit { color:var(--good); }
  .query-mentions.miss { color:var(--muted); }
  .query-answer { margin:8px 0 0 30px; font-size:.78rem; }
  .query-answer summary { cursor:pointer; color:var(--accent); font-weight:500; list-style:none;
    font-size:.76rem; }
  .query-answer summary::-webkit-details-marker { display:none; }
  .query-answer summary::before { content:'Show answer \u2192'; }
  .query-answer[open] summary::before { content:'Hide answer \u2191'; }
  .query-answer .ans-body { margin-top:8px; padding:14px; background:var(--surface-2);
    border-radius:var(--radius-sm); border-left:3px solid var(--accent);
    white-space:pre-wrap; line-height:1.65; max-height:280px; overflow:auto;
    font-size:.8rem; color:var(--text-2); }

  /* --- history --- */
  .history-empty { text-align:center; padding:60px 20px; color:var(--muted); font-size:.9rem; }
  .history-item { display:flex; align-items:center; gap:14px; padding:14px 0;
    border-bottom:1px solid var(--border); cursor:pointer; transition:background .1s; }
  .history-item:hover { background:var(--surface-2); margin:0 -24px; padding:14px 24px; }
  .history-item .h-verdict { font-size:.7rem; font-weight:700; padding:3px 8px; border-radius:99px;
    white-space:nowrap; }
  .history-item .h-verdict.real { background:var(--good-soft); color:var(--good); }
  .history-item .h-verdict.amb { background:var(--warn-soft); color:var(--warn); }
  .history-item .h-verdict.col { background:var(--bad-soft); color:var(--bad); }
  .history-item .h-info { flex:1; min-width:0; }
  .history-item .h-market { font-weight:600; font-size:.85rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .history-item .h-meta { font-size:.72rem; color:var(--muted); }
  .history-item .h-cost { font-size:.78rem; color:var(--text-2); font-family:'SF Mono','Fira Code',monospace; }
  .clear-btn { font-size:.78rem; color:var(--bad); cursor:pointer; background:none; border:0;
    padding:4px 0; margin-top:12px; }
  .clear-btn:hover { text-decoration:underline; }

  .empty-state { text-align:center; padding:48px 20px; }
  .empty-state .icon { font-size:2.5rem; margin-bottom:12px; opacity:.3; }
  .empty-state h3 { font-size:1rem; font-weight:600; margin:0 0 6px; }
  .empty-state p { font-size:.82rem; color:var(--muted); margin:0; }

  @media (max-width:768px) {
    .sidebar { display:none; }
    .topbar { padding:14px 16px; }
    .topbar .stats { gap:14px; }
    .content { padding:16px; }
    .card { padding:16px; }
  }
</style></head><body><div class="app">
<aside class="sidebar">
  <div class="sidebar-header">
    <div class="logo"><span class="logo-icon">&#9670;</span> GeoAudit <span class="badge">PROBE</span></div>
  </div>
  <nav class="sidebar-nav">
    <a data-tab="audit" class="active"><span class="nav-icon">&#9654;</span> New Audit</a>
    <a data-tab="history"><span class="nav-icon">&#9776;</span> History <span id="historyCount" style="margin-left:auto;font-size:.7rem;color:var(--muted)"></span></a>
  </nav>
  <div class="sidebar-footer">
    <span>Model:</span>
    <span class="model">Perplexity Sonar</span>
    <span style="margin-top:4px">via OpenRouter</span>
  </div>
</aside>

<main class="main">
  <div class="topbar">
    <h2 id="pageTitle">New Audit</h2>
    <div class="stats">
      <div class="stat"><div class="val" id="statTotal">0</div><div class="lbl">Total runs</div></div>
      <div class="stat"><div class="val" id="statLastV">—</div><div class="lbl">Last verdict</div></div>
    </div>
  </div>
  <div class="content">

    <!-- tab: New Audit -->
    <div id="tab-audit" class="tab active">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Audit Configuration</span>
        </div>
        <div class="card-row">
          <div class="field"><label>Specialty</label><input id="spec" placeholder="e.g. dentist, dermatologist" value="dentist"></div>
          <div class="field"><label>City / Region</label><input id="city" placeholder="e.g. Austin, TX" value="Austin, TX"></div>
        </div>
        <div class="field"><label>Practices to track <span class="opt">— one per line</span></label>
          <textarea id="practices" placeholder="Practice Name 1&#10;Practice Name 2&#10;...">Forest Family Dentistry
Austin Dental Spa
Enamel Dentistry
Walden Dental
Westlake Hills Dentistry
Celebrate Dental & Braces
ATX Family Dental
Tech Ridge Dental
Belterra Dental</textarea></div>
        <div class="field"><label>Patient queries <span class="opt">— one per line</span></label>
          <textarea id="queries" placeholder="best dentist in austin tx&#10;top rated dentist in austin&#10;...">best dentist in austin tx
top rated dentist in austin
dentist near me that takes delta dental austin
affordable dentist south austin
family dentist austin tx
cosmetic dentist austin
invisalign provider austin tx
emergency dentist austin open saturday
pediatric dentist austin tx
dentist for crowns and implants austin</textarea></div>
        <div class="actions">
          <button id="runBtn" class="btn btn-primary"><span class="spinner"></span> Run Audit</button>
          <button id="cancelBtn" class="btn btn-danger" style="display:none">Cancel</button>
          <label class="toggle"><input type="checkbox" id="mockToggle"><span>Mock mode</span></label>
          <button id="loadExBtn" class="btn btn-ghost">Load example</button>
          <span id="status" class="status-line" role="alert"></span>
        </div>
      </div>

      <div id="running" style="display:none">
        <div class="run-card">
          <div class="run-progress">
            <div class="run-track"><div id="runFill" class="run-fill"></div></div>
            <div id="runLabel" class="run-label">0 / 0</div>
          </div>
          <div id="runLog" class="run-log"></div>
          <div class="run-footer">
            <span id="runElapsed">0.0s</span>
            <span id="runCost" class="cost"></span>
          </div>
        </div>
      </div>

      <div id="result" style="display:none">
        <div id="verdict" class="result-verdict"></div>
        <div id="summary" class="result-meta"></div>
        <div class="card">
          <div class="card-title">Visibility Ranking</div>
          <div id="ranking" class="rank-list"></div>
        </div>
        <div class="card">
          <div class="card-title">Query Details</div>
          <div id="queryDetails"></div>
        </div>
      </div>
    </div>

    <!-- tab: History -->
    <div id="tab-history" class="tab">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Past Audits</span>
          <button class="clear-btn" onclick="clearHistory()">Clear all</button>
        </div>
        <div id="historyList"><div class="empty-state"><div class="icon">&#9670;</div><h3>No audits yet</h3><p>Run your first audit to see results here.</p></div></div>
      </div>
    </div>

  </div>
</main>
</div>
<script src="/app.js"></script>
</body></html>"""


APP_JS = r"""// GeoAudit — SaaS dashboard client
const $ = (id) => document.getElementById(id);
let evtSource = null, runningCost = 0, auditStart = 0;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>]/g, (c) =>
    c === "&" ? "&amp;" : c === "<" ? "&lt;" : "&gt;"
  );
}
function fmtCost(c) { return "$" + Number(c || 0).toFixed(4); }
function elapsed() { return ((Date.now() - auditStart) / 1000).toFixed(1) + "s"; }

// --- tabs ---
document.querySelectorAll(".sidebar-nav a").forEach((a) => {
  a.addEventListener("click", () => switchTab(a.dataset.tab));
});

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".sidebar-nav a").forEach((a) => a.classList.remove("active"));
  $("tab-" + name).classList.add("active");
  document.querySelector('[data-tab="' + name + '"]').classList.add("active");
  $("pageTitle").textContent = name === "history" ? "Audit History" : "New Audit";
  if (name === "history") refreshHistory();
}

// --- history / localStorage ---
function loadHistory() {
  try { return JSON.parse(localStorage.getItem("geoaudit_history") || "[]"); }
  catch (e) { return []; }
}
function saveHistory(arr) {
  localStorage.setItem("geoaudit_history", JSON.stringify(arr));
}
function addToHistory(d) {
  const h = loadHistory();
  h.unshift({
    ts: new Date().toISOString(),
    market: d.market || (($("spec").value || "dentist") + " in " + ($("city").value || "")),
    verdict: d.verdict,
    total_queries: d.total_queries,
    queries_with_any: d.queries_with_any,
    total_cost: d.total_cost,
    ranking: d.ranking,
    provider: d.provider, model: d.model,
    query_results: d.query_results
  });
  if (h.length > 50) h.length = 50;
  saveHistory(h);
  updateStats();
}
function clearHistory() {
  if (confirm("Delete all saved audits?")) {
    saveHistory([]); refreshHistory(); updateStats();
  }
}
function updateStats() {
  const h = loadHistory();
  $("statTotal").textContent = h.length;
  const hc = $("historyCount");
  hc.textContent = h.length || "";
  hc.style.display = h.length ? "" : "none";
  if (h.length) {
    const v = h[0].verdict;
    $("statLastV").textContent = v.indexOf("REAL") !== -1 ? "Gap" : v.indexOf("AMBIGUOUS") !== -1 ? "?" : "None";
    $("statLastV").style.color = v.indexOf("REAL") !== -1 ? "var(--good)" : v.indexOf("AMBIGUOUS") !== -1 ? "var(--warn)" : "var(--bad)";
  } else {
    $("statLastV").textContent = "\u2014"; $("statLastV").style.color = "";
  }
}
function refreshHistory() {
  const h = loadHistory();
  const el = $("historyList");
  if (!h.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">\u25c6</div><h3>No audits yet</h3><p>Run your first audit to see results here.</p></div>';
    return;
  }
  el.innerHTML = h
    .map((r) => {
      const vcls = r.verdict.indexOf("REAL") !== -1 ? "real" : r.verdict.indexOf("AMBIGUOUS") !== -1 ? "amb" : "col";
      const vtxt = r.verdict.indexOf("REAL") !== -1 ? "GAP" : r.verdict.indexOf("AMBIGUOUS") !== -1 ? "AMBIGUOUS" : "COLLAPSED";
      const d = new Date(r.ts);
      const ts = d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      return (
        '<div class="history-item" onclick="viewHistory(' + h.indexOf(r) + ')">' +
        '<span class="h-verdict ' + vcls + '">' + vtxt + "</span>" +
        '<div class="h-info"><div class="h-market">' + esc(r.market) + "</div>" +
        '<div class="h-meta">' + r.queries_with_any + "/" + r.total_queries + " queries named a practice &middot; " + ts + "</div></div>" +
        '<span class="h-cost">' + (r.model === "mock" ? "mock" : fmtCost(r.total_cost)) + "</span>" +
        "</div>"
      );
    })
    .join("");
}
function viewHistory(idx) {
  const r = loadHistory()[idx];
  if (!r) return;
  // load into the audit tab
  switchTab("audit");
  // set form
  const parts = (r.market || "").split(" in ");
  if (parts.length === 2) {
    $("spec").value = parts[0]; $("city").value = parts[1];
  }
  // load practices and queries from stored results
  $("practices").value = (r.ranking || []).map((p) => p.name).join("\n");
  $("queries").value = (r.query_results || []).map((q) => q.query).join("\n");
  // show the result
  $("result").style.display = "block";
  $("running").style.display = "none";
  renderFinal(r);
  $("result").scrollIntoView({ behavior: "smooth" });
}

// --- load example ---
$("loadExBtn").addEventListener("click", () => {
  $("spec").value = "dentist";
  $("city").value = "Austin, TX";
  $("practices").value = "Forest Family Dentistry\nAustin Dental Spa\nEnamel Dentistry\nWalden Dental\nWestlake Hills Dentistry\nCelebrate Dental & Braces\nATX Family Dental\nTech Ridge Dental\nBelterra Dental";
  $("queries").value = "best dentist in austin tx\ntop rated dentist in austin\ndentist near me that takes delta dental austin\naffordable dentist south austin\nfamily dentist austin tx\ncosmetic dentist austin\ninvisalign provider austin tx\nemergency dentist austin open saturday\npediatric dentist austin tx\ndentist for crowns and implants austin";
});

// --- audit ---
function setRunState(running) {
  ["spec", "city", "practices", "queries", "mockToggle"].forEach((id) => { $(id).disabled = running; });
  $("runBtn").style.display = running ? "none" : "";
  $("cancelBtn").style.display = running ? "" : "none";
  $("loadExBtn").style.display = running ? "none" : "";
}

function startAudit() {
  if (evtSource) { evtSource.close(); evtSource = null; }
  setRunState(true);
  $("status").textContent = "";
  $("result").style.display = "none";
  $("running").style.display = "block";
  runningCost = 0;
  auditStart = Date.now();
  $("runFill").style.width = "0%";
  $("runLabel").textContent = "0 / 0";
  $("runLog").innerHTML = "";
  $("runElapsed").textContent = "0.0s";
  $("runCost").textContent = "";

  const practices = $("practices").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const queries = $("queries").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const mock = $("mockToggle").checked;
  const body = {
    specialty: $("spec").value, city: $("city").value,
    practices, queries, mock
  };

  fetch("/api/audit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
    .then((resp) => {
      if (!resp.ok) return resp.json().then((j) => { throw new Error(j.error || "HTTP " + resp.status); });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "", total = queries.length || 10;
      function pump() {
        reader.read().then(({ done, value }) => {
          if (done) return;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf("\n\n")) !== -1) {
            handleEvent(buf.slice(0, idx), () => total, (t) => (total = t));
            buf = buf.slice(idx + 2);
          }
          pump();
        }).catch((e) => failWith(e.message));
      }
      pump();
    })
    .catch((e) => failWith(e.message));
}

function cancelAudit() {
  if (evtSource) { evtSource.close(); evtSource = null; }
  $("runLog").innerHTML += '<div class="r-err">\u2192 Cancelled after ' + elapsed() + "</div>";
  setRunState(false);
  $("status").textContent = "Cancelled.";
}

function handleEvent(chunk, getTotal, setTotal) {
  const lines = chunk.split("\n");
  for (const line of lines) {
    if (line.indexOf("data:") !== 0) continue;
    const p = line.slice(5).trim();
    if (!p) continue;
    let ev;
    try { ev = JSON.parse(p); } catch (e) { continue; }

    if (ev.type === "start") {
      setTotal(ev.total); handleEvent.mock = !!ev.mock;
      $("runLabel").textContent = "0 / " + ev.total;
      if (ev.mock) $("runCost").textContent = "mock (no cost)";
    } else if (ev.type === "query") {
      runningCost = ev.run_cost || 0;
      const pct = getTotal() ? Math.round((ev.done / getTotal()) * 100) : 0;
      $("runFill").style.width = pct + "%";
      $("runLabel").textContent = ev.done + " / " + getTotal();
      $("runElapsed").textContent = elapsed();
      if (ev.mentions && ev.mentions.length) {
        $("runLog").innerHTML += '<div class="r-hit">\u2713 ' + esc(ev.query) + " \u2192 " + esc(ev.mentions.join(", ")) + "</div>";
      } else {
        $("runLog").innerHTML += '<div class="r-miss">\u2717 ' + esc(ev.query) + " (none)</div>";
      }
      if (!handleEvent.mock) $("runCost").textContent = fmtCost(runningCost);
      $("runLog").scrollTop = $("runLog").scrollHeight;
    } else if (ev.type === "error") {
      $("runLog").innerHTML += '<div class="r-err">ERROR: ' + esc(ev.query) + "</div>";
    } else if (ev.type === "done") {
      setRunState(false);
      $("status").textContent = "";
      $("running").style.display = "none";
      $("result").style.display = "block";
      renderFinal(ev.result);
      addToHistory(ev.result);
      $("result").scrollIntoView({ behavior: "smooth" });
    }
  }
}

function failWith(msg) {
  $("running").style.display = "none";
  setRunState(false);
  $("status").innerHTML = '<span style="color:var(--bad)">Error: ' + esc(msg) + "</span>";
}

// --- render ---
function renderFinal(d) {
  const cls = d.verdict.indexOf("REAL") !== -1 ? "good" : d.verdict.indexOf("AMBIGUOUS") !== -1 ? "warn" : "bad";
  const icon = cls === "good" ? "\u2713" : cls === "warn" ? "\u26a0" : "\u2717";
  $("verdict").className = "result-verdict " + cls;
  $("verdict").innerHTML = '<span class="vicon">' + icon + "</span><span>" + esc(d.verdict) + "</span>";

  const costTag = d.model === "mock" ? "mock run (no API cost)" : "Cost: " + fmtCost(d.total_cost);
  $("summary").textContent = d.detail + " \u00b7 " + d.queries_with_any + "/" + d.total_queries + " queries named a practice \u00b7 " + costTag + (d.total_queries ? " \u00b7 " + elapsed() + " elapsed" : "");

  const total = d.total_queries || 1;
  const maxCount = Math.max.apply(null, [1].concat(d.ranking.map((r) => r.count)));
  $("ranking").innerHTML = d.ranking
    .map((r, i) => {
      const pct = total ? (r.count / total) * 100 : 0;
      const rank = maxCount > 0 ? r.count / maxCount : 0;
      const cls2 = rank >= 0.6 ? "hi" : rank >= 0.3 ? "md" : "lo";
      return '<div class="rank-item"><span class="rank-pos">' + (i + 1) + "</span>" +
        '<span class="rank-name">' + esc(r.name) + "</span>" +
        '<span class="rank-bar-wrap"><div class="rank-bar-track"><div class="rank-bar-fill ' + cls2 + '" style="width:' + pct + '%"></div></div></span>' +
        '<span class="rank-count">' + r.count + ' <span class="of">/ ' + total + "</span></span></div>";
    })
    .join("");

  $("queryDetails").innerHTML = d.query_results
    .map((q, i) => {
      const hit = q.mentions.length > 0;
      return '<div class="query-item">' +
        '<div class="query-head"><span class="q-dot ' + (hit ? "hit" : "miss") + '">' + (hit ? "\u2713" : "\u00b7") + "</span>" +
        '<span class="q-text">' + esc(q.query) + "</span>" +
        '<span class="q-cost">' + (q.cost !== undefined ? fmtCost(q.cost) : "") + "</span></div>" +
        '<div class="query-mentions ' + (hit ? "hit" : "miss") + '">' + (hit ? "\u2192 " + esc(q.mentions.join(", ")) : "\u2192 no tracked practices named") + "</div>" +
        '<details class="query-answer"><summary></summary><div class="ans-body">' + esc(q.answer) + "</div></details>" +
        "</div>";
    })
    .join("");
}

$("runBtn").addEventListener("click", startAudit);
$("cancelBtn").addEventListener("click", cancelAudit);
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); if (!$("runBtn").disabled) startAudit(); }
  if (e.key === "Escape" && $("cancelBtn").style.display !== "none") { e.preventDefault(); cancelAudit(); }
});

// init
updateStats();
$("historyCount").style.display = loadHistory().length ? "" : "none";
"""


# Build the practice list {name, aliases} from the page's textarea input.
def parse_practices(lines):
    out = []
    for name in lines:
        name = name.strip()
        if not name:
            continue
        low = name.lower().strip()
        al = [low]
        clean = low.replace(" & ", " ").replace("&", "and")
        if clean != low:
            al.append(clean)
        # first two words as a shorter alias (handles "Forest Family Dentistry" -> "forest family")
        words = clean.split()
        if len(words) >= 3:
            al.append(" ".join(words[:2]))
        al = list(dict.fromkeys(al))  # dedupe preserving order
        out.append({"name": name, "aliases": al})
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silence default stderr logging

    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML, ctype="text/html; charset=utf-8")
        elif self.path == "/app.js":
            self._send(200, APP_JS, ctype="application/javascript; charset=utf-8")
        else:
            self._send(404, '{"error":"not found"}')

    def _send_json(self, code, obj):
        self._send(code, json.dumps(obj), ctype="application/json")

    def _start_sse(self):
        """Begin a chunked Server-Sent Events response. Returns nothing; caller
        writes with self.wfile and flushes. Connection closes at handler end."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _sse(self, obj):
        """Write one SSE event and flush."""
        self.wfile.write(("data: " + json.dumps(obj) + "\n\n").encode("utf-8"))
        self.wfile.flush()

    def do_POST(self):
        if self.path != "/api/audit":
            self._send_json(404, {"error": "not found"}); return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception as e:
            self._send_json(400, {"error": "bad JSON: %s" % e}); return

        specialties = [s.strip() for s in (payload.get("specialty") or "").split(",") if s.strip()]
        city = (payload.get("city") or "").strip()
        market = f"{' / '.join(specialties)} in {city}" if specialties and city else ""

        mock = bool(payload.get("mock"))
        practices = parse_practices(payload.get("practices") or [])
        if not practices:
            practices = probe.PRACTICES

        provider, model, key = "openrouter", probe.DEFAULTS["openrouter"], ""
        if not mock:
            key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            if not key:
                self._send_json(400, {"error": "OPENROUTER_API_KEY not set on the server. Run the server with it, or tick Mock mode."})
                return

        # Use the queries the user typed; fall back to the default set if none.
        queries = [q.strip() for q in (payload.get("queries") or []) if q.strip()]
        if not queries:
            queries = probe.QUERIES
        self._start_sse()
        self._sse({"type": "start", "total": len(queries), "mock": mock})

        # Stream a query event for each query as it completes, then the final result.
        def on_query(i, total, q, hits, query_cost=0.0, run_cost=0.0):
            if hits is None:
                self._sse({"type": "error", "done": i, "total": total,
                           "query": q, "error": "API call failed"})
            else:
                self._sse({"type": "query", "done": i, "total": total,
                           "query": q, "mentions": hits or [],
                           "query_cost": round(query_cost, 6),
                           "run_cost": round(run_cost, 6)})

        try:
            result = probe.run_audit(provider, model, key, queries, practices,
                                     mock=mock, on_query=on_query, market=market)
            self._sse({"type": "done", "result": result})
        except Exception as e:
            self._sse({"type": "fatal", "error": str(e).replace('"', "'")})


def main():
    ap = argparse.ArgumentParser(description="Healthcare GEO Audit — local web UI")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    key_set = "yes" if os.environ.get("OPENROUTER_API_KEY", "").strip() else "NO (Mock mode only)"
    print(f"Healthcare GEO Audit — web UI running at {url}")
    print(f"OPENROUTER_API_KEY set: {key_set}")
    print("Press Ctrl+C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping."); srv.shutdown()


if __name__ == "__main__":
    main()
