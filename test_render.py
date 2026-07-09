#!/usr/bin/env python3
"""Quick test: load render test data and verify all cards display."""
import json, http.server, socketserver, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Read the saved test data
with open(os.path.join(os.path.dirname(__file__), 'data', 'audits', 'test-ui-render.json')) as f:
    data = f.read()

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><title>UI Render Test</title>
<style>
body{{font-family:sans-serif;padding:20px;background:#fafbfc}}
.pass{{color:green}} .fail{{color:red;font-weight:bold}}
#result{{background:#fff;border:1px solid #e8eaed;border-radius:12px;padding:24px;margin:16px 0}}
</style></head><body>
<h1>UI Render Test</h1>
<div id="checks"></div>
<script>
window.TEST_DATA = {data};

setTimeout(function() {{
  var script = document.createElement('script');
  script.src = '/test-app.js';
  script.onload = function() {{
    var el = document.getElementById('checks');
    try {{
      rf(window.TEST_DATA);
      var kpis = document.getElementById('kpis').querySelectorAll('.kpi-card').length;
      var ranks = document.getElementById('ranking').querySelectorAll('.rk-item').length;
      var recs = document.getElementById('recs').querySelectorAll('.rec-card').length;
      var tags = document.getElementById('domains').querySelectorAll('.dom-tag').length;
      var qitems = document.getElementById('qlist').querySelectorAll('.q-item').length;
      var verdict = document.getElementById('verdict').innerText.length > 0;

      var ok = kpis > 0 && ranks > 0 && qitems > 0 && verdict;
      el.innerHTML = '<div class="' + (ok ? 'pass' : 'fail') + '">' +
        (ok ? 'PASS' : 'FAIL') + ': KPI=' + kpis + ' ranks=' + ranks +
        ' recs=' + recs + ' tags=' + tags + ' queries=' + qitems +
        ' verdict=' + verdict + '</div>';
    }} catch(e) {{
      el.innerHTML = '<div class="fail">ERROR: ' + e.message + '</div>';
    }}
  }};
  document.body.appendChild(script);
}}, 100);
</script>
</body></html>"""

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._send(HTML, 'text/html')
        elif self.path == '/test-app.js':
            import server
            self._send(server.APP_JS, 'application/javascript')
        else:
            super().do_GET()

    def _send(self, body, ctype):
        b = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a): pass

port = 8766
srv = socketserver.TCPServer(('127.0.0.1', port), H)
print(f'Test server at http://127.0.0.1:{port}')
srv.serve_forever()
