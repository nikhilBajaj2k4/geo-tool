#!/usr/bin/env python3
"""Standalone render test — feeds mock data to the full GeoAudit HTML+JS."""
import json, sys, os, http.server, socketserver
sys.path.insert(0, '/Users/nikhilbajaj/geo-tool')
os.chdir('/Users/nikhilbajaj/geo-tool')
import probe, server

result = probe.run_multi_audit('', probe.QUERIES[:3], probe.PRACTICES[:5], mock=True, market='dentist in Austin, TX')

# Build a page with the full server HTML + a test harness
html = server.HTML + f"""<script>
setTimeout(function(){{try{{window.RF({json.dumps(result)});document.title='PASS: '+document.getElementById('ranking').querySelectorAll('.rk-item').length+' ranks, '+document.getElementById('kpis').querySelectorAll('.kc').length+' KPIs'}}catch(e){{document.title='FAIL: '+e.message}}}},300)</script>"""

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/': self._send(html, 'text/html')
        elif self.path == '/app.js': self._send(server.APP_JS, 'application/javascript')
        else: super().do_GET()
    def _send(self, body, ctype):
        b = body.encode('utf-8'); self.send_response(200)
        self.send_header('Content-Type', ctype+'; charset=utf-8')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

port = 8777
srv = socketserver.TCPServer(('127.0.0.1', port), H)
print(f'http://127.0.0.1:{port}')
srv.serve_forever()
