#!/usr/bin/env python3
"""Verify: load audit JSON via static page, check rf() renders all cards."""
import json, http.server, socketserver, os, sys
sys.path.insert(0, '/Users/nikhilbajaj/geo-tool')

with open('/Users/nikhilbajaj/geo-tool/data/audits/probe-openrouter-20260709-220757.json') as f:
    data = json.load(f)

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><title>GeoAudit Render Test</title>
<style>
body{{font-family:sans-serif;padding:20px;background:#fafbfc}}h2{{margin-top:0}}
.pass{{color:#059669;font-weight:bold}}.fail{{color:#dc2626;font-weight:bold}}
#result{{background:#fff;border:1px solid #e8eaed;border-radius:12px;padding:24px;margin:16px 0}}
</style></head><body>
<h2>GeoAudit Phase 1 Render Test</h2>
<p id="status">Loading JS...</p>
<div id="result"><div class="vb" id="verdict"></div><div class="summary" id="summ"></div>
<div class="kpi-row" id="kpis" style="display:none"></div>
<div class="card" id="recs-card" style="display:none"><h3>Recommended Actions</h3><div id="recs"></div></div>
<div class="card" id="dom-card" style="display:none"><h3>Top Cited Sources</h3><div id="domains"></div></div>
<div class="card"><h3>Visibility Ranking</h3><div id="ranking"></div></div>
<div class="card"><h3>Query Details</h3><div id="qlist"></div></div></div>
<script src="/app.js"></script>
<script>window.onload=function(){{try{{rf({json.dumps(data)});document.getElementById("status").innerHTML=
'<span class=pass>PASS</span> — verdict: '+document.getElementById("verdict").innerText+
' | KPIs: '+document.getElementById("kpis").querySelectorAll(".kpi-card").length+
' | ranks: '+document.getElementById("ranking").querySelectorAll(".rk-item").length+
' | recs: '+document.getElementById("recs").querySelectorAll(".rec-card").length+
' | tags: '+document.getElementById("domains").querySelectorAll(".dom-tag").length+
' | queries: '+document.getElementById("qlist").querySelectorAll(".q-item").length}}catch(e){{document.getElementById("status").innerHTML=
'<span class=fail>FAIL</span>: '+e.message}}}}</script>
<script src="/server-app.js"></script>
</body></html>"""

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._send(HTML, 'text/html')
        elif self.path == '/app.js':
            import server
            self._send(server.APP_JS, 'application/javascript')
        else:
            super().do_GET()
    def _send(self, body, ctype):
        b = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', ctype+'; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def log_message(self, *a): pass

port = 8767
srv = socketserver.TCPServer(('127.0.0.1', port), H)
print(f'Render test at http://127.0.0.1:{port}')
srv.serve_forever()
