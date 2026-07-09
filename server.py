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
    --bg:#f6f8fa; --surface:#ffffff; --surface-2:#f1f5f9; --surface-3:#e9eef3;
    --border:#e2e8f0; --border-strong:#cbd5e1;
    --text:#0f172a; --text-2:#475569; --muted:#64748b; --muted-2:#94a3b8;
    --accent:#2563eb; --accent-soft:#eff6ff; --accent-border:#bfdbfe;
    --good:#059669; --good-soft:#ecfdf5; --good-border:#a7f3d0;
    --warn:#d97706; --warn-soft:#fffbeb; --warn-border:#fde68a;
    --bad:#dc2626; --bad-soft:#fef2f2; --bad-border:#fecaca;
    --bar:#2563eb; --bar-soft:#dbeafe;
    --shadow-sm:0 1px 2px rgba(15,23,42,.04);
    --shadow:0 1px 3px rgba(15,23,42,.06),0 1px 2px rgba(15,23,42,.04);
    --shadow-md:0 4px 12px rgba(15,23,42,.06),0 2px 4px rgba(15,23,42,.04);
    --radius:12px; --radius-sm:8px;
  }
  * { box-sizing:border-box; }
  body {
    margin:0;
    font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif;
    background:var(--bg); color:var(--text); line-height:1.55;
    -webkit-font-smoothing:antialiased; font-size:15px;
  }
  .wrap { max-width:940px; margin:0 auto; padding:40px 24px 96px; }
  h1 { font-size:1.75rem; font-weight:700; margin:0 0 6px; letter-spacing:-.02em;
       color:var(--text); }
  .sub { color:var(--text-2); font-size:.95rem; margin-bottom:28px; max-width:620px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
          padding:24px; margin-bottom:18px; box-shadow:var(--shadow-sm); }
  .card-title { font-size:.78rem; font-weight:600; color:var(--muted);
                text-transform:uppercase; letter-spacing:.06em; margin:0 0 14px; }
  label { display:block; font-size:.82rem; font-weight:500; color:var(--text-2);
          margin:0 0 7px; }
  input, select, textarea {
    width:100%; background:var(--surface); color:var(--text);
    border:1px solid var(--border-strong); border-radius:var(--radius-sm);
    padding:10px 12px; font-size:.95rem; font-family:inherit;
    transition:border-color .15s, box-shadow .15s;
  }
  input:focus, textarea:focus { outline:none; border-color:var(--accent);
    box-shadow:0 0 0 3px rgba(37,99,235,.12); }
  input:disabled, textarea:disabled { background:var(--surface-2); color:var(--muted-2); cursor:not-allowed; }
  textarea { resize:vertical; min-height:120px; line-height:1.7; }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .controls { display:flex; align-items:center; gap:16px; margin-top:20px; flex-wrap:wrap; }
  button {
    background:var(--accent); color:#fff; border:0; border-radius:var(--radius-sm);
    padding:11px 22px; font-size:.95rem; font-weight:600; cursor:pointer;
    display:inline-flex; align-items:center; gap:9px;
    box-shadow:0 1px 2px rgba(37,99,235,.2), inset 0 1px 0 rgba(255,255,255,.15);
    transition:transform .1s, box-shadow .15s;
  }
  button:hover:not(:disabled) { box-shadow:0 4px 12px rgba(37,99,235,.25); }
  button:active:not(:disabled) { transform:translateY(1px); }
  button:disabled { opacity:.6; cursor:not-allowed; }
  .check { display:flex; align-items:center; gap:8px; color:var(--text-2); font-size:.9rem; cursor:pointer; }
  .check input { width:auto; }
  #status { color:var(--text-2); font-size:.9rem; min-height:1.2em; margin-left:auto; }

  /* --- spinner --- */
  .spinner { width:15px; height:15px; border:2.5px solid rgba(255,255,255,.3);
          border-top-color:#fff; border-radius:50%; animation:spin .65s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }

  /* --- progress --- */
  .progress-wrap { display:flex; align-items:center; gap:14px; margin:4px 0 14px; }
  .progress-track { flex:1; height:8px; background:var(--surface-3); border-radius:5px; overflow:hidden; }
  .progress-fill { height:100%; width:0%; background:linear-gradient(90deg,var(--accent),#3b82f6);
          border-radius:5px; transition:width .4s ease; }
  .progress-label { font-size:.85rem; font-weight:600; color:var(--text-2);
          min-width:54px; text-align:right; font-variant-numeric:tabular-nums; }
  .live-line { font-size:.9rem; color:var(--text-2); min-height:1.4em; padding:8px 12px;
          background:var(--surface-2); border-radius:var(--radius-sm); }
  .live-line.err { color:var(--bad); background:var(--bad-soft); }
  .cost-line { font-size:.82rem; color:var(--muted); margin-top:10px; min-height:1.2em;
          display:flex; align-items:center; gap:6px; }
  .cost-line .dot { width:6px; height:6px; border-radius:50%; background:var(--good); display:inline-block; }
  .cost-line.mock .dot { background:var(--muted-2); }

  /* --- verdict --- */
  .verdict { font-size:1.1rem; font-weight:700; padding:16px 18px; border-radius:var(--radius-sm);
          margin:0 0 16px; display:flex; align-items:center; gap:10px; }
  .verdict .vicon { font-size:1.25rem; line-height:1; }
  .verdict.good { background:var(--good-soft); color:var(--good); border:1px solid var(--good-border); }
  .verdict.warn { background:var(--warn-soft); color:var(--warn); border:1px solid var(--warn-border); }
  .verdict.bad  { background:var(--bad-soft);  color:var(--bad);  border:1px solid var(--bad-border); }

  /* --- ranking bars --- */
  #ranking { margin-top:6px; }
  .bar-row { display:grid; grid-template-columns:240px 1fr 60px; gap:14px; align-items:center;
          padding:9px 0; border-bottom:1px solid var(--border); font-size:.92rem; }
  .bar-row:last-child { border-bottom:0; }
  .bar-row .name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:500; color:var(--text); }
  .bar-row .rank { color:var(--muted-2); font-weight:400; margin-right:8px; }
  .bar-track { background:var(--bar-soft); border-radius:6px; height:20px; overflow:hidden; }
  .bar-fill { background:var(--bar); height:100%; border-radius:6px; transition:width .6s cubic-bezier(.4,0,.2,1); }
  .bar-row .count { text-align:right; color:var(--text-2); font-weight:600; font-variant-numeric:tabular-nums; }

  /* --- query detail --- */
  .q { padding:13px 0; border-bottom:1px solid var(--border); }
  .q:last-child { border-bottom:0; }
  .q .qq { font-weight:600; font-size:.92rem; display:flex; align-items:center; gap:9px; color:var(--text); }
  .q .tick { display:inline-flex; align-items:center; justify-content:center;
          width:18px; height:18px; border-radius:50%; font-size:.7rem; flex-shrink:0; }
  .q .tick.hit { background:var(--good-soft); color:var(--good); }
  .q .tick.miss { background:var(--surface-3); color:var(--muted-2); }
  .q .mm { color:var(--accent); font-size:.85rem; margin:5px 0 0 27px; }
  .q .none { color:var(--muted); font-size:.85rem; margin:5px 0 0 27px; }
  details summary { cursor:pointer; color:var(--accent); font-size:.82rem; margin:6px 0 0 27px;
          list-style:none; }
  details summary::-webkit-details-marker { display:none; }
  details summary::before { content:'\203a  '; }
  details[open] summary::before { content:'\2038  '; }
  .q-ans { white-space:pre-wrap; color:var(--text-2); font-size:.85rem;
          margin:10px 0 0 27px; padding:12px; background:var(--surface-2); border-radius:var(--radius-sm);
          max-height:260px; overflow:auto; border:1px solid var(--border); }
  .meta { color:var(--muted); font-size:.85rem; }
  .note { font-size:.82rem; color:var(--muted); margin-top:14px; line-height:1.6; }
  .pill { display:inline-block; background:var(--accent-soft); color:var(--accent);
          border:1px solid var(--accent-border); font-size:.72rem; font-weight:600;
          padding:2px 9px; border-radius:99px; margin-left:8px; vertical-align:middle; }
</style></head><body><div class="wrap">
  <h1>Healthcare GEO Audit <span class="pill">probe</span></h1>
  <div class="sub">Measures how often competing medical practices appear in AI-search answers (ChatGPT, Perplexity) when patients search for their specialty &mdash; and whether visibility gaps exist to close.</div>

  <div class="card">
    <div class="card-title">Audit configuration</div>
    <div class="row">
      <div>
        <label for="specialty">Specialty</label>
        <input id="specialty" value="dentist">
      </div>
      <div>
        <label for="city">City</label>
        <input id="city" value="Austin, TX">
      </div>
    </div>
    <div style="margin-top:16px">
      <label for="practices">Practices to track (one per line)</label>
      <textarea id="practices">Forest Family Dentistry
Austin Dental Spa
Enamel Dentistry
Walden Dental
Westlake Hills Dentistry
Celebrate Dental &amp; Braces
ATX Family Dental
Tech Ridge Dental
Belterra Dental</textarea>
    </div>
    <div style="margin-top:16px">
      <label for="queries">Patient queries to ask the AI (one per line)</label>
      <textarea id="queries">best dentist in austin tx
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
      <button id="runBtn">Run audit</button>
      <label class="check"><input type="checkbox" id="mockChk"> Mock mode (no API cost)</label>
      <span id="status"></span>
    </div>
    <div class="note">The audit sends 10 realistic patient questions to a web-grounded AI-search model, then counts how often each practice is named &mdash; in the answer and its cited sources. Live runs take ~20&ndash;30s.</div>
  </div>

  <!-- live progress (shown while running) -->
  <div id="running" class="card" style="display:none">
    <div class="progress-wrap">
      <div class="progress-track"><div id="progressFill" class="progress-fill"></div></div>
      <div id="progressLabel" class="progress-label">0 / 0</div>
    </div>
    <div id="liveLine" class="live-line">Starting\u2026</div>
    <div id="costLine" class="cost-line"><span class="dot"></span><span></span></div>
  </div>

  <!-- final results (shown when done) -->
  <div id="result" style="display:none">
    <div class="card">
      <div id="verdict" class="verdict"></div>
      <div id="summary" class="meta" style="margin-bottom:18px"></div>
      <div class="card-title">Visibility ranking</div>
      <div id="ranking"></div>
    </div>
    <div class="card">
      <div class="card-title">Per-query detail</div>
      <div id="queries"></div>
    </div>
  </div>
</div>
<script src="/app.js"></script>
</body></html>"""


APP_JS = r"""// Healthcare GEO Audit — client logic (served as real JS, separate from HTML)
// Uses Server-Sent Events to stream per-query progress as the audit runs.
const $ = (id) => document.getElementById(id);
let evtSource = null;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>]/g, (c) =>
    c === "&" ? "&amp;" : c === "<" ? "&lt;" : "&gt;"
  );
}

function setRunState(running) {
  const btn = $("runBtn");
  btn.disabled = running;
  btn.innerHTML = running
    ? '<span class="spinner"></span> Running'
    : "Run audit";
  // inputs lock while running
  $("specialty").disabled = running;
  $("city").disabled = running;
  $("practices").disabled = running;
  $("queries").disabled = running;
  $("mockChk").disabled = running;
}

function setCostLine(mock, text) {
  var cl = $("costLine");
  cl.className = "cost-line" + (mock ? " mock" : "");
  cl.innerHTML = '<span class="dot"></span><span class="ctxt"></span>';
  cl.querySelector(".ctxt").textContent = text;
}

function showRunning(total, mock) {
  $("result").style.display = "none";
  $("running").style.display = "block";
  $("progressFill").style.width = "0%";
  $("progressLabel").textContent = "0 / " + total;
  var live = $("liveLine");
  live.className = "live-line";
  live.textContent = "Starting\u2026";
  setCostLine(
    mock,
    mock ? "Mock mode \u2014 no real API cost." : "Running cost: $0.0000"
  );
}

function fmtCost(c) {
  return "$" + Number(c || 0).toFixed(4);
}

function updateProgress(done, total, queryText, mentions, isError, runCost, mock) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  $("progressFill").style.width = pct + "%";
  $("progressLabel").textContent = done + " / " + total;
  const live = $("liveLine");
  if (isError) {
    live.className = "live-line err";
    live.textContent = "Error on: " + queryText;
  } else {
    live.className = "live-line";
    if (mentions && mentions.length) {
      live.textContent =
        "\u2713 " + queryText + "  \u2014  " + mentions.join(", ");
    } else if (mentions) {
      live.textContent =
        "\u2717 " + queryText + "  \u2014  none of the tracked practices named";
    } else {
      live.textContent = "Answering: " + queryText;
    }
  }
  setCostLine(
    mock,
    mock ? "Mock mode \u2014 no real API cost." : "Running cost: " + fmtCost(runCost)
  );
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
  const vicon =
    cls === "good" ? "\u2713" : cls === "warn" ? "\u26a0" : "\u2717";
  const v = $("verdict");
  v.className = "verdict " + cls;
  v.innerHTML =
    '<span class="vicon">' + vicon + "</span><span>" + esc(d.verdict) + "</span>";
  const costTag =
    d.model === "mock"
      ? "(mock run \u2014 no API cost)"
      : "API cost for this run: " + fmtCost(d.total_cost);
  $("summary").textContent =
    d.detail +
    "  \u00b7  " +
    d.queries_with_any +
    "/" +
    d.total_queries +
    " queries named a tracked practice." +
    "  \u00b7  " +
    costTag;
  const max = Math.max.apply(
    null,
    [1].concat(d.ranking.map((r) => r.count))
  );
  $("ranking").innerHTML = d.ranking
    .map((r, i) => {
      const pct = (r.count / max) * 100;
      return (
        '<div class="bar-row"><div class="name"><span class="rank">' +
        (i + 1) +
        "</span>" +
        esc(r.name) +
        "</div>" +
        '<div class="bar-track"><div class="bar-fill" style="width:' +
        pct +
        '%"></div></div>' +
        '<div class="count">' +
        r.count +
        "/" +
        d.total_queries +
        "</div></div>"
      );
    })
    .join("");
  $("queries").innerHTML = d.query_results
    .map((q) => {
      const hit = q.mentions.length > 0;
      const m = hit
        ? '<div class="mm">\u2192 ' + esc(q.mentions.join(", ")) + "</div>"
        : '<div class="none">\u2192 none of the tracked practices named</div>';
      return (
        '<div class="q"><div class="qq"><span class="tick ' +
        (hit ? "hit" : "miss") +
        '">' +
        (hit ? "\u2713" : "\u00b7") +
        "</span> " +
        esc(q.query) +
        "</div>" +
        m +
        "<details><summary>show AI answer</summary><div class=\"q-ans\">" +
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
  $("status").innerHTML =
    '<span style="color:var(--bad)">Error: ' + esc(msg) + "</span>";
}

$("runBtn").addEventListener("click", () => {
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
  // POST to start, get a stream back via fetch ReadableStream (SSE-style).
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
      const ct = resp.headers.get("content-type") || "";
      // Stream of SSE events: data: {...}\n\n
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let total = 10;
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
});

function handleEvent(chunk, getTotal, setTotal) {
  // parse "data: {json}"
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
      updateProgress(
        ev.done,
        getTotal(),
        ev.query,
        ev.mentions,
        false,
        ev.run_cost,
        handleEvent.mock
      );
    } else if (ev.type === "error") {
      updateProgress(ev.done, getTotal(), ev.query, null, true, ev.run_cost || 0, handleEvent.mock);
    } else if (ev.type === "done") {
      setRunState(false);
      $("status").textContent = "";
      renderFinal(ev.result);
    }
  }
}
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
