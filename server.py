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
<title>Healthcare GEO Audit</title>
<style>
  :root {
    --bg:#0a0e14; --surface:#12171f; --surface-2:#1a1f29; --surface-3:#222833;
    --border:#1e2733; --border-acc:#2d3b4d;
    --text:#e6edf3; --text-2:#8b949e; --muted:#595f6b;
    --accent:#39ff14; --accent-dim:#1a3a1a; --accent-border:#1f541f;
    --good:#3fb950; --good-dim:#0f2d14; --good-border:#1a4420;
    --warn:#d29922; --warn-dim:#2e2208; --warn-border:#4a3808;
    --bad:#f85149; --bad-dim:#2d0c0f; --bad-border:#4a1610;
    --bar:#39ff14; --bar-2:#58a6ff; --bar-dim:#0f1f0f; --bar-track:#1c2634;
    --radius:6px; --radius-sm:4px;
  }
  * { box-sizing:border-box; }
  @media (prefers-reduced-motion:reduce) {
    *, ::before, ::after { animation-duration:0s !important; transition-duration:0s !important; }
  }
  body {
    margin:0; background:var(--bg); color:var(--text);
    font-family:'JetBrains Mono','SF Mono','Fira Code','Cascadia Code',monospace;
    font-size:13px; line-height:1.65; -webkit-font-smoothing:antialiased;
  }
  ::selection { background:rgba(57,255,20,.25); color:var(--text); }

  .wrap { max-width:960px; margin:0 auto; padding:32px 20px 96px; }

  /* --- header --- */
  .header { margin-bottom:28px; }
  .header h1 { font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif;
    font-size:1.4rem; font-weight:700; margin:0; display:flex; align-items:center; gap:10px;
    letter-spacing:-.01em; }
  .header .bracket { color:var(--accent); font-size:.8rem; font-family:inherit;
    background:var(--accent-dim); border:1px solid var(--accent-border);
    padding:2px 10px; border-radius:var(--radius-sm); letter-spacing:.04em; font-weight:400; }
  .header .sub { color:var(--text-2); font-size:.8rem; margin-top:8px;
    font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif; max-width:620px; }

  /* --- cards --- */
  .card { background:var(--surface); border:1px solid var(--border);
    border-radius:var(--radius); padding:20px; margin-bottom:16px; }
  .card-title { font-size:.68rem; font-weight:600; color:var(--muted); text-transform:uppercase;
    letter-spacing:.08em; margin:0 0 14px; display:flex; align-items:center; gap:8px; }
  .card-title::before { content:''; width:8px; height:2px; background:var(--accent);
    opacity:.5; display:inline-block; }

  /* --- form --- */
  .row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  @media (max-width:640px) { .row { grid-template-columns:1fr; } }
  label { display:block; font-size:.72rem; color:var(--muted); margin:0 0 5px;
    text-transform:uppercase; letter-spacing:.06em; }
  .fm-label::before { content:'> '; color:var(--accent); opacity:.4; }
  input, textarea {
    width:100%; background:var(--bg); color:var(--text); font-family:inherit;
    border:1px solid var(--border); border-radius:var(--radius-sm);
    padding:9px 12px; font-size:.82rem; line-height:1.6;
    transition:border-color .15s, box-shadow .15s;
  }
  input::placeholder, textarea::placeholder { color:var(--muted); }
  input:focus, textarea:focus { outline:none; border-color:var(--accent);
    box-shadow:0 0 0 2px rgba(57,255,20,.1); }
  input:disabled, textarea:disabled { background:var(--surface-2); color:var(--muted);
    border-color:var(--border); cursor:not-allowed; opacity:.6; }
  textarea { min-height:96px; field-sizing:content; }
  input { height:36px; }

  .controls { display:flex; align-items:center; gap:14px; margin-top:18px; flex-wrap:wrap; }
  .controls .kb { font-size:.65rem; color:var(--muted); margin-left:6px; }
  .check { display:flex; align-items:center; gap:7px; color:var(--text-2); font-size:.78rem;
    cursor:pointer; user-select:none; }
  .check input { width:auto; height:auto; accent-color:var(--accent); cursor:pointer; }
  .check .flag { color:var(--accent); font-weight:600; opacity:.7; }

  button {
    background:var(--accent-dim); color:var(--accent); font-family:inherit;
    border:1px solid var(--accent-border); border-radius:var(--radius-sm);
    padding:8px 16px; font-size:.78rem; font-weight:600; cursor:pointer;
    display:inline-flex; align-items:center; gap:7px;
    transition:background .15s, box-shadow .15s, color .15s;
    text-transform:uppercase; letter-spacing:.04em;
  }
  button:hover:not(:disabled) { background:var(--accent); color:var(--bg); }
  button:active:not(:disabled) { transform:translateY(1px); }
  button:disabled { opacity:.4; cursor:not-allowed; }
  button.cancel { background:var(--bad-dim); color:var(--bad); border-color:var(--bad-border); }
  button.cancel:hover:not(:disabled) { background:var(--bad); color:#fff; }
  button.cancel .kb { color:inherit; opacity:.7; }

  /* --- terminal output (progress) --- */
  .term { background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);
    padding:14px 18px; margin-bottom:16px; font-size:.78rem; line-height:1.8;
    min-height:60px; max-height:440px; overflow-y:auto; }
  .term .line { padding:1px 0; white-space:pre-wrap; word-break:break-word; }
  .term .prompt { color:var(--muted); margin-right:6px; }
  .term .cmd { color:var(--text); }
  .term .hit { color:var(--good); }
  .term .miss { color:var(--muted); }
  .term .err { color:var(--bad); }
  .term .cursor { display:inline-block; width:8px; height:14px; background:var(--accent);
    margin-left:2px; vertical-align:text-bottom; animation:blink .8s step-end infinite; }
  @keyframes blink { 50% { opacity:0; } }
  .term .header-line { color:var(--muted); margin-bottom:4px; }
  .term .footer-line { display:flex; justify-content:space-between; color:var(--muted);
    font-size:.72rem; margin-top:8px; padding-top:6px; border-top:1px solid var(--border); }
  .term .footer-line .cost { color:var(--good); }
  .term .footer-line .cost.mock { color:var(--muted); }

  /* --- verdict banner --- */
  .verdict-banner { font-family:inherit; font-size:.82rem; line-height:1.4;
    white-space:pre; padding:12px 0; margin:0 0 16px; overflow-x:auto; }
  .verdict-banner.good { color:var(--good); }
  .verdict-banner.warn { color:var(--warn); }
  .verdict-banner.bad  { color:var(--bad); }

  .summary { color:var(--text-2); font-size:.76rem; padding:6px 0; margin-bottom:8px;
    border-bottom:1px solid var(--border); }
  .summary .cost { color:var(--good); }

  /* --- ranking bars --- */
  #ranking { margin-top:6px; }
  .bar-row { display:grid; grid-template-columns:220px 1fr 64px; gap:12px; align-items:center;
    padding:7px 0; border-bottom:1px solid var(--border); font-size:.78rem; }
  @media (max-width:640px) { .bar-row { grid-template-columns:1fr 1fr; }
    .bar-row .name { grid-column:1/-1; margin-bottom:2px; }
    .bar-row .count { text-align:right; } }
  .bar-row:last-child { border-bottom:0; }
  .bar-row .name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    color:var(--text); }
  .bar-row .rank { color:var(--muted); display:inline-block; width:18px; text-align:right;
    margin-right:6px; font-size:.68rem; }
  .bar-track { background:var(--bar-track); border-radius:3px; height:14px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:3px; transition:width .6s cubic-bezier(.4,0,.2,1); }
  .bar-fill.top { background:var(--bar); }
  .bar-fill.mid { background:var(--bar-2); opacity:.7; }
  .bar-fill.low { background:var(--bar-2); opacity:.4; }
  .bar-row .count { text-align:right; color:var(--text-2); font-size:.74rem;
    font-variant-numeric:tabular-nums; }

  /* --- query detail --- */
  .q { padding:11px 0; border-bottom:1px solid var(--border);
    font-family:inherit; }
  .q:last-child { border-bottom:0; }
  .q .qq { display:flex; align-items:center; gap:8px; font-size:.8rem; }
  .q .qq .qnum { color:var(--muted); font-size:.68rem; min-width:28px; }
  .q .qq .qtext { color:var(--text); flex:1; }
  .q .qq .tick { font-size:.75rem; flex-shrink:0; }
  .q .qq .tick.hit { color:var(--good); }
  .q .qq .tick.miss { color:var(--muted); }
  .q .mm { color:var(--good); font-size:.74rem; margin:3px 0 0 36px; }
  .q .none { color:var(--muted); font-size:.74rem; margin:3px 0 0 36px; }
  details { margin:4px 0 0 36px; }
  details summary { cursor:pointer; color:var(--accent); font-size:.72rem;
    list-style:none; opacity:.7; transition:opacity .15s; }
  details summary:hover { opacity:1; }
  details summary::-webkit-details-marker { display:none; }
  details summary::before { content:'[+] '; }
  details[open] summary::before { content:'[-] '; }
  .q-ans { white-space:pre-wrap; color:var(--text-2); font-size:.73rem;
    margin:8px 0 0 0; padding:10px 12px; background:var(--surface-2);
    border-radius:var(--radius-sm); border-left:2px solid var(--accent);
    max-height:240px; overflow:auto; line-height:1.6; }
  .q-ans::before { content:''; }

  #status { color:var(--bad); font-size:.74rem; min-height:1.2em; margin-left:auto; }
  .note { font-size:.72rem; color:var(--muted); margin-top:12px;
    font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif; }
</style></head><body><div class="wrap">
  <div class="header">
    <h1>Healthcare GEO Audit <span class="bracket">[PROBE]</span></h1>
    <div class="sub">Measures how often competing medical practices appear in AI-search answers when patients search for their specialty &mdash; and whether visibility gaps exist to close.</div>
  </div>

  <div class="card">
    <div class="card-title">Configuration</div>
    <div class="row">
      <div>
        <label for="specialty" class="fm-label">specialty</label>
        <input id="specialty" value="dentist" aria-label="Medical specialty">
      </div>
      <div>
        <label for="city" class="fm-label">city</label>
        <input id="city" value="Austin, TX" aria-label="City">
      </div>
    </div>
    <div style="margin-top:14px">
      <label for="practices" class="fm-label">practices</label>
      <textarea id="practices" aria-label="Practices to track">Forest Family Dentistry
Austin Dental Spa
Enamel Dentistry
Walden Dental
Westlake Hills Dentistry
Celebrate Dental &amp; Braces
ATX Family Dental
Tech Ridge Dental
Belterra Dental</textarea>
    </div>
    <div style="margin-top:14px">
      <label for="queries" class="fm-label">queries</label>
      <textarea id="queries" aria-label="Patient queries">best dentist in austin tx
top rated dentist in austin
dentist near me that takes delta dental austin
affordable dentist south austin
family dentist austin tx
cosmetic dentist austin
invisalign provider austin tx
emergency dentist austin open saturday
pediatric dentist austin tx
dentist for crowns and implants austin</textarea>
    </div>
    <div class="controls">
      <button id="runBtn" aria-label="Run audit">&#9654; Run Audit <span class="kb">Ctrl+Enter</span></button>
      <button id="cancelBtn" class="cancel" style="display:none" aria-label="Cancel audit">&#9632; Cancel <span class="kb">Esc</span></button>
      <label class="check"><input type="checkbox" id="mockChk" aria-label="Mock mode">
        <span class="flag">--mock</span> no API cost</label>
      <span id="status" role="alert"></span>
    </div>
    <div class="note">Sends patient queries to a web-grounded AI model, counts how often each practice is named in answers and cited sources.</div>
  </div>

  <!-- terminal output log (shown while running) -->
  <div id="running" style="display:none">
    <div id="termOut" class="term" role="log" aria-live="polite" aria-label="Audit progress"></div>
  </div>

  <!-- final results (shown when done) -->
  <div id="result" style="display:none">
    <div class="card">
      <div id="verdict" class="verdict-banner"></div>
      <div id="summary" class="summary"></div>
      <div class="card-title">Visibility Ranking</div>
      <div id="ranking"></div>
    </div>
    <div class="card">
      <div class="card-title">Query Details</div>
      <div id="queryDetails"></div>
    </div>
  </div>
</div>
<script src="/app.js"></script>
</body></html>"""


APP_JS = r"""// Healthcare GEO Audit — terminal-style client logic
const $ = (id) => document.getElementById(id);
let evtSource = null;
let runningTotal = 0;
let auditStart = 0;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>]/g, (c) =>
    c === "&" ? "&amp;" : c === "<" ? "&lt;" : "&gt;"
  );
}

function fmtCost(c) {
  return "$" + Number(c || 0).toFixed(4);
}

function elapsed() {
  const s = auditStart ? ((Date.now() - auditStart) / 1000).toFixed(1) : "0";
  return s + "s";
}

// --- UI state ---

function setRunState(running) {
  $("specialty").disabled = running;
  $("city").disabled = running;
  $("practices").disabled = running;
  $("queries").disabled = running;
  $("mockChk").disabled = running;
  $("runBtn").style.display = running ? "none" : "";
  $("cancelBtn").style.display = running ? "" : "none";
}

function showRunning(total, mock) {
  $("result").style.display = "none";
  $("running").style.display = "block";
  runningTotal = 0;
  auditStart = Date.now();
  const t = $("termOut");
  const m = mock ? " --mock" : "";
  t.innerHTML = '<div class="header-line">$ probe' + m + ' ' + total + ' queries' +
    ' <span class="cursor"></span></div>';
}

function appendTerm(css, html) {
  const t = $("termOut");
  // remove cursor from last line, append, re-add cursor
  t.innerHTML = t.innerHTML.replace(/<span class="cursor"><\/span>$/, "");
  t.innerHTML += '<div class="line ' + css + '">' + html + "</div>";
  t.innerHTML += '<span class="cursor"></span>';
  t.scrollTop = t.scrollHeight;
}

function updateFooter(mock, runCost) {
  const t = $("termOut");
  const existing = t.querySelector(".footer-line");
  if (existing) existing.remove();
  const costHtml = mock
    ? '<span class="cost mock">--mock (no cost)</span>'
    : '<span class="cost">$' + fmtCost(runCost) + "</span>";
  t.innerHTML += '<div class="footer-line"><span>' + elapsed() +
    "</span>" + costHtml + "</div>";
}

// --- render final ---

function makeBanner(text, cls) {
  const icon = cls === "good" ? "\u2713" : cls === "warn" ? "\u26a0" : "\u2717";
  const w = Math.max(48, text.length + 4);
  const top = "\u2554" + "\u2550".repeat(w + 2) + "\u2557";
  const mid = "\u2551  " + icon + "  " + text.padEnd(w - 3) + "\u2551";
  const bot = "\u255a" + "\u2550".repeat(w + 2) + "\u255d";
  return top + "\n" + mid + "\n" + bot;
}

function renderFinal(d) {
  $("running").style.display = "none";
  $("result").style.display = "block";
  const cls =
    d.verdict.indexOf("REAL") !== -1
      ? "good"
      : d.verdict.indexOf("AMBIGUOUS") !== -1
      ? "warn"
      : "bad";
  $("verdict").textContent = makeBanner(d.verdict, cls);
  $("verdict").className = "verdict-banner " + cls;

  const costTag =
    d.model === "mock"
      ? "mock run (no API cost)"
      : "cost: <span class='cost'>" + fmtCost(d.total_cost) + "</span>";
  $("summary").innerHTML =
    esc(d.detail) +
    " &middot; " +
    d.queries_with_any +
    "/" +
    d.total_queries +
    " queries named a practice &middot; " +
    costTag +
    (d.total_queries ? " &middot; " + elapsed() + " elapsed" : "");

  // ranking bars — proportional to total_queries, not leader
  const total = d.total_queries || 1;
  const maxCount = Math.max.apply(null, [1].concat(d.ranking.map((r) => r.count)));
  $("ranking").innerHTML = d.ranking
    .map((r, i) => {
      const pct = total ? (r.count / total) * 100 : 0;
      const rank = maxCount > 0 ? r.count / maxCount : 0;
      const cls = rank >= 0.6 ? "top" : rank >= 0.3 ? "mid" : "low";
      return (
        '<div class="bar-row"><div class="name"><span class="rank">' +
        (i + 1) +
        ".</span>" +
        esc(r.name) +
        "</div>" +
        '<div class="bar-track"><div class="bar-fill ' + cls + '" style="width:' +
        pct +
        '%"></div></div>' +
        '<div class="count">' +
        r.count +
        "/" +
        total +
        "</div></div>"
      );
    })
    .join("");

  $("queryDetails").innerHTML = d.query_results
    .map((q, i) => {
      const hit = q.mentions.length > 0;
      const m = hit
        ? '<div class="mm">&rarr; ' + esc(q.mentions.join(", ")) + "</div>"
        : '<div class="none">&rarr; none of the tracked practices named</div>';
      return (
        '<div class="q"><div class="qq"><span class="qnum">[' +
        String(i + 1).padStart(2, "0") +
        "]</span>" +
        '<span class="tick ' +
        (hit ? "hit" : "miss") +
        '">' +
        (hit ? "\u2713" : "\u00b7") +
        "</span>" +
        '<span class="qtext">' +
        esc(q.query) +
        "</span></div>" +
        m +
        "<details><summary>show answer</summary><div class=\"q-ans\">" +
        esc(q.answer) +
        "</div></details></div>"
      );
    })
    .join("");

  $("result").scrollIntoView({ behavior: "smooth" });
}

function failWith(msg) {
  $("running").style.display = "none";
  setRunState(false);
  $("status").innerHTML = "Error: " + esc(msg);
}

// --- cancel ---

function cancelAudit() {
  if (evtSource) {
    evtSource.close();
    evtSource = null;
  }
  appendTerm("err", "  ^C cancelled after " + elapsed());
  setRunState(false);
  $("status").textContent = "Cancelled.";
}

// --- click handler ---

$("runBtn").addEventListener("click", () => startAudit());
$("cancelBtn").addEventListener("click", () => cancelAudit());

function startAudit() {
  if (evtSource) {
    evtSource.close();
    evtSource = null;
  }
  setRunState(true);
  $("status").textContent = "";
  const practices = $("practices").value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const queries = $("queries").value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const body = {
    specialty: $("specialty").value,
    city: $("city").value,
    practices: practices,
    queries: queries,
    mock: $("mockChk").checked,
  };
  fetch("/api/audit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
    .then((resp) => {
      if (!resp.ok) {
        return resp.json().then((j) => {
          throw new Error(j.error || "HTTP " + resp.status);
        });
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let total = queries.length || 10;
      function pump() {
        reader
          .read()
          .then(({ done, value }) => {
            if (done) return;
            buf += decoder.decode(value, { stream: true });
            let idx;
            while ((idx = buf.indexOf("\n\n")) !== -1) {
              const chunk = buf.slice(0, idx);
              buf = buf.slice(idx + 2);
              handleEvent(chunk, () => total, (t) => (total = t));
            }
            pump();
          })
          .catch((e) => failWith(e.message));
      }
      pump();
    })
    .catch((e) => failWith(e.message));
}

function handleEvent(chunk, getTotal, setTotal) {
  const lines = chunk.split("\n");
  for (const line of lines) {
    if (line.indexOf("data:") !== 0) continue;
    const payload = line.slice(5).trim();
    if (!payload) continue;
    let ev;
    try {
      ev = JSON.parse(payload);
    } catch (e) {
      continue;
    }
    if (ev.type === "start") {
      setTotal(ev.total);
      handleEvent.mock = !!ev.mock;
      showRunning(ev.total, !!ev.mock);
    } else if (ev.type === "query") {
      runningTotal = ev.run_cost || 0;
      if (ev.mentions && ev.mentions.length) {
        appendTerm("hit", "  \u2713 " + esc(ev.query) + "  \u2192  " +
          esc(ev.mentions.join(", ")));
      } else {
        appendTerm("miss", "  \u2717 " + esc(ev.query) + "  (none)");
      }
      updateFooter(handleEvent.mock, runningTotal);
    } else if (ev.type === "error") {
      appendTerm("err", "  ERROR: " + esc(ev.query));
      updateFooter(handleEvent.mock, runningTotal);
    } else if (ev.type === "done") {
      setRunState(false);
      $("status").textContent = "";
      // remove cursor before rendering final
      $("termOut").innerHTML = $("termOut").innerHTML.replace(
        /<span class="cursor"><\/span>$/,
        ""
      );
      renderFinal(ev.result);
    }
  }
}

// --- keyboard shortcuts ---

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    if (!$("runBtn").disabled) startAudit();
  }
  if (e.key === "Escape" && !$("cancelBtn").style.display.match(/none/)) {
    e.preventDefault();
    cancelAudit();
  }
});
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
