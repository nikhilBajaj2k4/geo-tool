#!/usr/bin/env python3
"""Quick render test — injects real audit data into the GeoAudit UI."""
import json, sys, os
sys.path.insert(0, '/Users/nikhilbajaj/geo-tool')
os.chdir('/Users/nikhilbajaj/geo-tool')

import probe
result = probe.run_multi_audit('', probe.QUERIES, probe.PRACTICES, mock=True, market='dentist in Austin, TX')

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Render Test</title>
<style>body{{font-family:sans-serif;padding:20px;background:#f8f9fc}}h2{{margin:0 0 10px}}
.p{{color:green;font-weight:bold}}.f{{color:red;font-weight:bold}}</style></head><body>
<h2>GeoAudit Render Verification</h2>
<div id="out">Loading JS...</div><div id="status" style="color:#dc2626"></div>
<script>
window._TEST = {};
</script>
<script src="/app.js"></script>
<script>
setTimeout(function() {{ try {{ 
var td = {json.dumps(result)};
window.RF(td); 
var ks = document.getElementById('kpis').querySelectorAll('.kc').length; 
var rs = document.getElementById('ranking').querySelectorAll('.rk-item').length; 
var cs = document.getElementById('recs').querySelectorAll('.rc-item').length; 
var gs = document.getElementById('gaps').querySelectorAll('.gap-item').length; 
var ep = document.getElementById('engpills').querySelectorAll('.e-pill').length; 
document.getElementById('out').innerHTML = '<span class=p>PASS</span> — KPI=' + ks + ' RANK=' + rs + ' REC=' + cs + ' GAPS=' + gs + ' PILLS=' + ep; 
}} catch(e) {{ document.getElementById('out').innerHTML = '<span class=f>FAIL</span>: ' + e.message; }} }}, 500);
</script>
</body></html>"""

import http.server, socketserver

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._send(html, 'text/html')
        elif self.path == '/app.js':
            import server; self._send(server.APP_JS, 'application/javascript')
        else: super().do_GET()
    def _send(self, body, ctype):
        b = body.encode('utf-8'); self.send_response(200)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

port = 8768
srv = socketserver.TCPServer(('127.0.0.1', port), H)
print(f'Render test: http://127.0.0.1:{port}')
srv.serve_forever()
