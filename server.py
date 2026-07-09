#!/usr/bin/env python3
"""
GeoAudit — Healthcare AI Visibility Intelligence (Phase 1)

Local web dashboard. Source citation analysis, competitive ranking,
actionable recommendations. Reuses probe.run_audit().

Usage:
    OPENROUTER_API_KEY=... python3 server.py
    python3 server.py --port 8765
"""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import probe

HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GeoAudit — AI Visibility Intelligence</title>
<style>
*{box-sizing:border-box}::selection{background:rgba(99,102,241,.25);color:#fff}
:root{
--bg:#fafbfc;--card:#fff;--card2:#f7f8fa;--border:#e8eaed;--border2:#d3d6da;
--text:#1a1c20;--text2:#555a62;--text3:#808791;--muted:#a5aab3;
--accent:#6366f1;--accent2:#4f46e5;--accent-soft:#eef2ff;--accent-glow:rgba(99,102,241,.15);
--good:#059669;--good-bg:#ecfdf5;--warn:#d97706;--warn-bg:#fffbeb;--bad:#dc2626;--bad-bg:#fef2f2;
--rank1:linear-gradient(135deg,#6366f1,#818cf8);--rank2:linear-gradient(135deg,#7c3aed,#a78bfa);
--rank3:linear-gradient(135deg,#0891b2,#22d3ee);
--sh:0 1px 2px rgba(0,0,0,.04);--sh-md:0 4px 12px rgba(0,0,0,.06);--sh-lg:0 12px 32px rgba(0,0,0,.08);
--r:14px;--r2:10px;--r3:7px;
--sans:-apple-system,BlinkMacSystemFont,'Inter','SF Pro',system-ui,sans-serif;
--mono:'SF Mono','JetBrains Mono','Fira Code',monospace;
}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
@media(prefers-reduced-motion:reduce){*,::before,::after{animation-duration:.01ms!important}}

/* layout */
.app{display:flex;min-height:100vh}
.sidebar{width:230px;background:var(--card);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;position:sticky;top:0;height:100vh;z-index:10}
.side-h{padding:22px 20px 16px;border-bottom:1px solid var(--border)}
.side-h .logo{font-size:1rem;font-weight:800;display:flex;align-items:center;gap:8px;letter-spacing:-.02em}
.side-h .logo svg{width:28px;height:28px}
.side-h .beta{font-size:.6rem;font-weight:700;color:var(--accent);background:var(--accent-soft);padding:2px 7px;border-radius:99px;text-transform:uppercase;letter-spacing:.05em}
.side-nav{padding:10px 12px;flex:1}
.side-nav a{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:var(--r3);font-size:.82rem;font-weight:500;color:var(--text2);text-decoration:none;cursor:pointer;transition:all .12s;margin-bottom:2px}
.side-nav a:hover{background:var(--card2);color:var(--text)}
.side-nav a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.side-nav .nav-icon{width:19px;text-align:center;font-size:.85rem;opacity:.7}
.side-nav a.active .nav-icon{opacity:1}
.side-f{font-size:.7rem;color:var(--muted);padding:12px 20px;border-top:1px solid var(--border)}
.side-f b{color:var(--accent)}

.main{flex:1;min-width:0}
.topbar{background:var(--card);border-bottom:1px solid var(--border);padding:14px 32px;display:flex;align-items:center;justify-content:space-between}
.topbar h2{margin:0;font-size:1.05rem;font-weight:700;letter-spacing:-.01em}
.topbar .kpi{display:flex;gap:24px}
.kpi .kv{font-size:1.1rem;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .kl{font-size:.64rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.content{padding:24px 32px 80px}
.tab{display:none}.tab.active{display:block;animation:in .2s ease}
@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

/* cards */
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:22px 24px;margin-bottom:18px;box-shadow:var(--sh)}
.card:hover{box-shadow:var(--sh-md)}
.card-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.card-t{font-size:.68rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:750px){.g2{grid-template-columns:1fr}.topbar .kpi{gap:16px}.sidebar{display:none}.content{padding:16px}}

/* form */
.field{margin-bottom:14px}
.field label{display:block;font-size:.76rem;font-weight:600;color:var(--text2);margin-bottom:5px}
.field label span{color:var(--muted);font-weight:400}
.field input,.field textarea{width:100%;background:var(--card);color:var(--text);font-family:var(--sans);border:1.5px solid var(--border);border-radius:var(--r3);padding:9px 13px;font-size:.84rem;line-height:1.55;transition:border .15s,box-shadow .15s}
.field input:focus,.field textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}
.field input:disabled,.field textarea:disabled{background:var(--card2);color:var(--muted);border-color:var(--border);cursor:not-allowed}
.field textarea{min-height:90px;resize:vertical}
.field input{height:38px}
.acts{display:flex;align-items:center;gap:10px;margin-top:16px;flex-wrap:wrap}
.btn{padding:9px 18px;font-size:.82rem;font-weight:600;border-radius:var(--r3);cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-family:inherit;border:0;transition:all .12s}
.btn-p{background:var(--accent);color:#fff;box-shadow:0 1px 3px rgba(99,102,241,.25)}
.btn-p:hover:not(:disabled){background:var(--accent2);box-shadow:0 4px 12px rgba(99,102,241,.3)}
.btn-p:disabled{opacity:.5;cursor:not-allowed}
.btn-gh{background:transparent;color:var(--text2);border:1.5px solid var(--border)}
.btn-gh:hover:not(:disabled){background:var(--card2);border-color:var(--border2)}
.btn-d{background:var(--bad-bg);color:var(--bad);border:1.5px solid #fecaca}
.btn-d:hover:not(:disabled){background:var(--bad);color:#fff}
.tog{display:flex;align-items:center;gap:7px;font-size:.8rem;color:var(--text2);cursor:pointer;user-select:none}
.tog input{width:30px;height:17px;appearance:none;background:var(--border2);border-radius:99px;cursor:pointer;position:relative;transition:background .15s}
.tog input::after{content:'';width:13px;height:13px;background:#fff;border-radius:50%;position:absolute;top:2px;left:2px;transition:transform .15s;box-shadow:0 1px 2px rgba(0,0,0,.1)}
.tog input:checked{background:var(--accent)}
.tog input:checked::after{transform:translateX(13px)}
.st{color:var(--bad);font-size:.8rem;min-height:1em}

/* progress */
.run-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:18px 22px;margin-bottom:18px;box-shadow:var(--sh)}
.run-top{display:flex;align-items:center;gap:14px;margin-bottom:12px}
.run-track{flex:1;height:5px;background:var(--border2);border-radius:3px;overflow:hidden}
.run-fill{height:100%;width:0;background:linear-gradient(90deg,var(--accent),#8b5cf6);border-radius:3px;transition:width .25s ease}
.run-pct{font-size:.78rem;font-weight:600;color:var(--text2);min-width:50px;text-align:right;font-variant-numeric:tabular-nums}
.run-log{background:var(--card2);border-radius:var(--r3);padding:10px 14px;max-height:260px;overflow-y:auto;font-size:.76rem;line-height:1.7;font-family:var(--mono)}
.run-log .hit{color:var(--good)}
.run-log .miss{color:var(--muted)}
.run-log .err{color:var(--bad)}
.run-foot{display:flex;justify-content:space-between;margin-top:10px;font-size:.74rem;color:var(--text3)}
.run-foot .cost{color:var(--good);font-weight:600}

/* verdict */
.vb{padding:22px 28px;border-radius:var(--r);margin-bottom:18px;display:flex;align-items:center;gap:16px;font-weight:700;font-size:.92rem;box-shadow:var(--sh-md)}
.vb.good{background:var(--good-bg);color:var(--good);border:1.5px solid #a7f3d0}
.vb.warn{background:var(--warn-bg);color:var(--warn);border:1.5px solid #fde68a}
.vb.bad{background:var(--bad-bg);color:var(--bad);border:1.5px solid #fecaca}
.vb .vb-icon{font-size:1.4rem;flex-shrink:0}
.summary{font-size:.8rem;color:var(--text3);margin-bottom:20px}
.summary .sc{color:var(--good);font-weight:600}

/* KPI row */
.kpi-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}
@media(max-width:750px){.kpi-row{grid-template-columns:1fr}}
.kpi-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:18px 22px;box-shadow:var(--sh);text-align:center}
.kpi-card .kv{font-size:1.6rem;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;margin-bottom:2px}
.kpi-card .kl{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.kpi-card .kv.g{color:var(--good)}.kpi-card .kv.a{color:var(--warn)}.kpi-card .kv.r{color:var(--bad)}

/* ranking */
.rk-item{display:grid;grid-template-columns:28px 1fr 69px 52px;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border);font-size:.83rem}
.rk-item:last-child{border-bottom:0}
.rk-pos{width:22px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:700;color:#fff}
.rk-pos.t1{background:var(--rank1)}.rk-pos.t2{background:var(--rank2)}.rk-pos.t3{background:var(--rank3)}
.rk-pos.def{background:var(--card2);color:var(--muted)}
.rk-name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rk-bar-wrap{min-width:0}
.rk-bar-track{height:7px;background:var(--border2);border-radius:4px;overflow:hidden}
.rk-bar-fill{height:100%;border-radius:4px;transition:width .5s ease}.rk-bar-fill.hi{background:var(--accent)}.rk-bar-fill.md{background:var(--accent);opacity:.45}.rk-bar-fill.lo{background:var(--muted);opacity:.25}
.rk-cnt{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}.rk-cnt span{font-weight:400;color:var(--muted)}

/* recommendations */
.rec-card{display:grid;grid-template-columns:22px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--border);font-size:.82rem;align-items:flex-start}
.rec-card:last-child{border:0}
.rec-prio{width:22px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.6rem;font-weight:700;color:#fff;flex-shrink:0}
.rec-prio.p5{background:var(--good)}.rec-prio.p4{background:var(--accent)}.rec-prio.p3{background:#0891b2}.rec-prio.p2{background:var(--muted)}
.rec-body .rec-act{font-weight:600;margin-bottom:2px}
.rec-body .rec-det{font-size:.76rem;color:var(--text3);line-height:1.5}
.rec-body .rec-src{font-size:.68rem;color:var(--accent);margin-top:3px}

/* source domains */
.dom-tag{display:inline-block;padding:3px 10px;background:var(--card2);border:1px solid var(--border);border-radius:99px;font-size:.7rem;color:var(--text2);margin:3px 5px 3px 0;font-family:var(--mono)}

/* query detail */
.q-item{padding:10px 0;border-bottom:1px solid var(--border)}
.q-item:last-child{border-bottom:0}
.q-head{display:flex;align-items:center;gap:9px}
.q-dot{width:19px;height:19px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.62rem;flex-shrink:0}
.q-dot.hit{background:var(--good-bg);color:var(--good)}.q-dot.miss{background:var(--card2);color:var(--muted)}
.q-txt{font-size:.82rem;font-weight:500;flex:1;min-width:0;word-break:break-word}
.q-cost{font-size:.7rem;color:var(--muted);font-family:var(--mono);flex-shrink:0}
.q-ment{margin:4px 0 0 28px;font-size:.76rem}.q-ment.hit{color:var(--good)}.q-ment.miss{color:var(--muted)}
.q-ans{margin:6px 0 0 28px;font-size:.74rem}.q-ans summary{cursor:pointer;color:var(--accent);font-weight:500;list-style:none;font-size:.73rem}
.q-ans summary::-webkit-details-marker{display:none}
.q-ans summary::before{content:'Show sources →'}
.q-ans[open] summary::before{content:'Hide sources ↑'}
.q-ans .ans-body{margin-top:8px;padding:12px;background:var(--card2);border-radius:var(--r3);border-left:3px solid var(--accent);white-space:pre-wrap;font-size:.76rem;color:var(--text2);max-height:240px;overflow:auto;line-height:1.6}

/* history */
.his-empty{text-align:center;padding:50px 20px;color:var(--muted);font-size:.85rem}
.his-item{display:flex;align-items:center;gap:14px;padding:12px 0;border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}
.his-item:hover{background:var(--card2);margin:0 -24px;padding:12px 24px}
.his-item .hv{font-size:.64rem;font-weight:700;padding:3px 8px;border-radius:99px}
.his-item .hv.g{background:#d1fae5;color:#065f46}
.his-item .hv.a{background:#fef3c7;color:#92400e}
.his-item .hv.c{background:#fee2e2;color:#991b1b}
.his-item .hi{flex:1;min-width:0}.hi .hm{font-weight:600;font-size:.82rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hi .hd{font-size:.7rem;color:var(--muted)}.hi .hd .hit{color:var(--good)}
.his-item .hc{font-size:.78rem;color:var(--text2);font-family:var(--mono)}
.clr-btn{font-size:.74rem;color:var(--bad);cursor:pointer;border:0;background:0;margin-top:10px}.clr-btn:hover{text-decoration:underline}
</style>
</head><body>
<div class="app">
<aside class="sidebar">
<div class="side-h"><div class="logo"><svg viewBox="0 0 28 28" fill="none"><rect width="28" height="28" rx="6" fill="url(#g)"/><defs><linearGradient id="g" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs><text x="14" y="19" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">G</text></svg>GeoAudit <span class="beta">Beta</span></div></div>
<nav class="side-nav">
<a data-tab="audit" class="active"><span class="nav-icon">⟐</span>New Audit</a>
<a data-tab="history"><span class="nav-icon">☰</span>History<span id="hc" style="margin-left:auto;font-size:.65rem;color:var(--muted)"></span></a>
</nav>
<div class="side-f"><b>Perplexity Sonar</b><br>via OpenRouter</div>
</aside>

<main class="main">
<div class="topbar"><h2 id="ttl">New Audit</h2>
<div class="kpi"><div class="kpi"><div class="kv" id="st1">0</div><div class="kl">Audits</div></div>
<div class="kpi"><div class="kv" id="st2">—</div><div class="kl">Last Result</div></div></div></div>

<div class="content">
<!-- TAB: new audit -->
<div id="tab-audit" class="tab active">
<div class="card"><div class="card-h"><span class="card-t">Setup</span></div>
<div class="g2">
<div class="field"><label>Specialty</label><input id="spec" placeholder="dentist, dermatologist..." value="dentist"></div>
<div class="field"><label>City / Region</label><input id="city" placeholder="Austin, TX" value="Austin, TX"></div>
</div>
<div class="field"><label>Practices <span>— one per line</span></label><textarea id="practices">Forest Family Dentistry
Austin Dental Spa
Enamel Dentistry
Walden Dental
Westlake Hills Dentistry
Celebrate Dental & Braces
ATX Family Dental
Tech Ridge Dental
Belterra Dental</textarea></div>
<div class="field"><label>Queries <span>— one per line</span></label><textarea id="queries">best dentist in austin tx
top rated dentist in austin
dentist near me that takes delta dental austin
affordable dentist south austin
family dentist austin tx
cosmetic dentist austin
invisalign provider austin tx
emergency dentist austin open saturday
pediatric dentist austin tx
dentist for crowns and implants austin</textarea></div>
<div class="acts">
<button id="rb" class="btn btn-p">▶ Run Audit</button>
<button id="cb" class="btn btn-d" style="display:none">■ Cancel</button>
<label class="tog"><input type="checkbox" id="mt"><span>Mock mode</span></label>
<button id="lex" class="btn btn-gh">Load example</button>
<span class="st" id="status" role="alert"></span>
</div></div>

<div id="running" style="display:none"><div class="run-card">
<div class="run-top"><div class="run-track"><div id="rf" class="run-fill"></div></div><div id="rl" class="run-pct">0/0</div></div>
<div id="rlog" class="run-log"></div>
<div class="run-foot"><span id="re">0s</span><span id="rc" class="cost"></span></div>
</div></div>

<div id="result" style="display:none">
<div id="verdict" class="vb"></div>
<div id="summ" class="summary"></div>

<div class="kpi-row" id="kpis" style="display:none"></div>

<div class="card" id="recs-card" style="display:none">
<div class="card-t">Recommended Actions</div><div id="recs"></div></div>

<div class="card" id="dom-card" style="display:none">
<div class="card-t">Top Cited Sources</div><div id="domains"></div></div>

<div class="card"><div class="card-t">Visibility Ranking</div><div id="ranking"></div></div>
<div class="card"><div class="card-t">Query Details</div><div id="qlist"></div></div>
</div></div>

<!-- TAB: history -->
<div id="tab-history" class="tab"><div class="card"><div class="card-h"><span class="card-t">Past Audits</span><button class="clr-btn" onclick="ch()">Clear all</button></div>
<div id="hlist"><div class="his-empty">No audits yet — run one to start.</div></div></div></div>
</div>
</main></div>
<script src="/app.js"></script></body></html>"""

APP_JS = r"""
const $=id=>document.getElementById(id);let es=null,rcost=0,ts=0;
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,c=>c==='&'?'&amp;':c==='<'?'&lt;':c==='>'?'&gt;')}
function fc(c){return'$'+(Number(c||0)).toFixed(4)}
function el(){return((Date.now()-ts)/1000).toFixed(1)+'s'}

// tabs
document.querySelectorAll('.side-nav a').forEach(a=>a.addEventListener('click',()=>st(a.dataset.tab)));
function st(n){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.side-nav a').forEach(a=>a.classList.remove('active'));
$('tab-'+n).classList.add('active');document.querySelector('[data-tab="'+n+'"]').classList.add('active');
$('ttl').textContent=n==='history'?'Audit History':'New Audit';if(n==='history')rh()}

// history
function lh(){try{return JSON.parse(localStorage.getItem('ga_hist')||'[]')}catch(e){return[]}}
function sh(a){localStorage.setItem('ga_hist',JSON.stringify(a))}
function ah(d){var h=lh();h.unshift({ts:new Date().toISOString(),market:d.market||(($('spec').value)+(($('city').value)?' in '+$('city').value:'')),verdict:d.verdict,tq:d.total_queries,qa:d.queries_with_any,tc:d.total_cost,ranking:d.ranking,recs:d.recommendations||[],domains:d.top_cited_domains||[],src:d.source_analysis||{},qr:d.query_results});if(h.length>50)h.length=50;sh(h);us()}
function ch(){if(confirm('Delete all?')&&(sh([]),rh(),us()));}
function us(){var h=lh();$('st1').textContent=h.length;var hc=$('hc');hc.textContent=h.length||'';hc.style.display=h.length?'':'none';if(h.length){var v=h[0].verdict;$('st2').textContent=v.indexOf('REAL')!==-1?'Gap':v.indexOf('AMBIGUOUS')!==-1?'?':'None';$('st2').style.color=v.indexOf('REAL')!==-1?'var(--good)':v.indexOf('AMBIGUOUS')!==-1?'var(--warn)':'var(--bad)'}else{$('st2').textContent='\u2014';$('st2').style.color=''}}
function rh(){var h=lh(),el=$('hlist');if(!h.length){el.innerHTML='<div class="his-empty">No audits yet — run one to start.</div>';return}
el.innerHTML=h.map((r,i)=>{var vc=r.verdict.indexOf('REAL')!==-1?'g':r.verdict.indexOf('AMBIGUOUS')!==-1?'a':'c';
var vt=r.verdict.indexOf('REAL')!==-1?'GAP':r.verdict.indexOf('AMBIGUOUS')!==-1?'AMBIG':'COLLAPSED';
var d=new Date(r.ts);var ds=d.toLocaleDateString()+' '+d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
return'<div class="his-item" onclick="vh('+i+')"><span class="hv '+vc+'">'+vt+'</span><div class="hi"><div class="hm">'+esc(r.market)+'</div><div class="hd"><span class="hit">'+r.qa+'/'+r.tq+'</span> queries &middot; '+ds+'</div></div><span class="hc">'+(r.ranking[0]?esc(r.ranking[0].name):'')+'</span></div>'}).join('')}
function vh(i){var r=lh()[i];if(!r)return;st('audit');$('spec').value=(r.market||'').split(' in ')[0]||'';$('city').value=(r.market||'').split(' in ')[1]||'';$('practices').value=(r.ranking||[]).map(p=>p.name).join('\n');$('queries').value=(r.qr||[]).map(q=>q.query).join('\n');$('result').style.display='block';$('running').style.display='none';rf(r);$('result').scrollIntoView({behavior:'smooth'})}

// load example
$('lex').addEventListener('click',()=>{$('spec').value='dentist';$('city').value='Austin, TX';$('practices').value='Forest Family Dentistry\nAustin Dental Spa\nEnamel Dentistry\nWalden Dental\nWestlake Hills Dentistry\nCelebrate Dental & Braces\nATX Family Dental\nTech Ridge Dental\nBelterra Dental';$('queries').value='best dentist in austin tx\ntop rated dentist in austin\ndentist near me that takes delta dental austin\naffordable dentist south austin\nfamily dentist austin tx\ncosmetic dentist austin\ninvisalign provider austin tx\nemergency dentist austin open saturday\npediatric dentist austin tx\ndentist for crowns and implants austin'});

// audit
function srs(r){['spec','city','practices','queries','mt'].forEach(id=>$(id).disabled=r);$('rb').style.display=r?'none':'';$('cb').style.display=r?'':'none';$('lex').style.display=r?'none':''}
function ra(){if(es){es.close();es=null}srs(true);$('status').textContent='';$('result').style.display='none';$('running').style.display='block';rcost=0;ts=Date.now();$('rf').style.width='0';$('rl').textContent='0/0';$('rlog').innerHTML='';$('re').textContent='0s';$('rc').textContent='';
var ps=$('practices').value.split('\n').map(s=>s.trim()).filter(Boolean);var qs=$('queries').value.split('\n').map(s=>s.trim()).filter(Boolean);
var b={specialty:$('spec').value,city:$('city').value,practices:ps,queries:qs,mock:$('mt').checked};
fetch('/api/audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>{if(!r.ok)return r.json().then(j=>{throw new Error(j.error||'HTTP '+r.status)});var rd=r.body.getReader(),dc=new TextDecoder(),buf='',tt=qs.length||10;
function p(){rd.read().then(({done,v})=>{if(done)return;buf+=dc.decode(v,{stream:true});var i;while((i=buf.indexOf('\n\n'))!==-1){he(buf.slice(0,i),()=>tt,t=>tt=t);buf=buf.slice(i+2)}p()}).catch(e=>fw(e.message))}p()}).catch(e=>fw(e.message))}
function ca(){if(es){es.close();es=null}$('rlog').innerHTML+='<div class="err">Cancelled after '+el()+'</div>';srs(false);$('status').textContent='Cancelled'}
function he(c,gt,st){var ls=c.split('\n');for(var i=0;i<ls.length;i++){var l=ls[i];if(l.indexOf('data:')!==0)continue;var p=l.slice(5).trim();if(!p)continue;var ev;try{ev=JSON.parse(p)}catch(e){continue}
if(ev.type==='start'){st(ev.total);he.mock=!!ev.mock;$('rl').textContent='0/'+ev.total;if(ev.mock)$('rc').textContent='mock'}else if(ev.type==='query'){rcost=ev.run_cost||0;var pct=gt()?Math.round((ev.done/gt())*100):0;$('rf').style.width=pct+'%';$('rl').textContent=ev.done+'/'+gt();$('re').textContent=el();if(ev.mentions&&ev.mentions.length)$('rlog').innerHTML+='<div class="hit">✓ '+esc(ev.query)+' → '+esc(ev.mentions.join(', '))+'</div>';else $('rlog').innerHTML+='<div class="miss">✗ '+esc(ev.query)+' (none)</div>';if(!he.mock)$('rc').textContent=fc(rcost);$('rlog').scrollTop=$('rlog').scrollHeight}else if(ev.type==='error'){$('rlog').innerHTML+='<div class="err">ERROR: '+esc(ev.query)+'</div>'}else if(ev.type==='done'){srs(false);$('status').textContent='';$('running').style.display='none';$('result').style.display='block';rf(ev.result);ah(ev.result);$('result').scrollIntoView({behavior:'smooth'})}}}
function fw(m){$('running').style.display='none';srs(false);$('status').textContent='Error: '+m}

// render
function rf(d){
var cl=d.verdict.indexOf('REAL')!==-1?'good':d.verdict.indexOf('AMBIGUOUS')!==-1?'warn':'bad';
var ic=cl==='good'?'✓':cl==='warn'?'⚠':'✗';
$('verdict').className='vb '+cl;$('verdict').innerHTML='<span class="vb-icon">'+ic+'</span><span>'+esc(d.verdict)+'</span>';
var ct=d.model==='mock'?'mock run (no cost)':fc(d.total_cost);
$('summ').innerHTML=esc(d.detail)+' &middot; '+d.queries_with_any+'/'+d.total_queries+' queries &middot; <span class="sc">'+ct+'</span>'+(d.total_queries?' &middot; '+el()+' elapsed':'');

// KPI row
var prs=d.ranking.filter(r=>r.count>0),zrs=d.ranking.filter(r=>r.count===0);
$('kpis').style.display='block';
$('kpis').innerHTML='<div class="kpi-card"><div class="kv g">'+d.queries_with_any+'</div><div class="kl">Queries with mentions</div></div>'+
'<div class="kpi-card"><div class="kv">'+(d.top_cited_domains?d.top_cited_domains.length:0)+'</div><div class="kl">Unique domains cited</div></div>'+
'<div class="kpi-card"><div class="kv a">'+zrs.length+'</div><div class="kl">Practices invisible</div></div>';

// recommendations
if(d.recommendations&&d.recommendations.length){$('recs-card').style.display='block';
$('recs').innerHTML=d.recommendations.map(r=>'<div class="rec-card"><div class="rec-prio p'+r.priority+'">'+r.priority+'</div><div class="rec-body"><div class="rec-act">'+esc(r.action)+'</div><div class="rec-det">'+esc(r.detail)+'</div>'+(r.domain?'<div class="rec-src">Source: '+esc(r.domain)+' ('+r.citation_count+'×)</div>':'')+'</div></div>').join('')}else{$('recs-card').style.display='none'}

// domains
if(d.top_cited_domains&&d.top_cited_domains.length){$('dom-card').style.display='block';
$('domains').innerHTML=d.top_cited_domains.map(e=>'<span class="dom-tag">'+esc(e[0])+' <b>'+e[1]+'×</b></span>').join('')}else{$('dom-card').style.display='none'}

// ranking
var tot=d.total_queries||1,mc=Math.max(1,Math.max.apply(null,d.ranking.map(r=>r.count)));
$('ranking').innerHTML=d.ranking.map((r,i)=>{
var pct=tot?(r.count/tot)*100:0,rn=r.count/mc,cls2=i<3?'t'+(i+1):'def',bc=rn>=.6?'hi':rn>=.3?'md':'lo';
return'<div class="rk-item"><div class="rk-pos '+cls2+'">'+(i+1)+'</div><div class="rk-name">'+esc(r.name)+'</div><div class="rk-bar-wrap"><div class="rk-bar-track"><div class="rk-bar-fill '+bc+'" style="width:'+pct+'%"></div></div></div><div class="rk-cnt">'+r.count+' <span>/'+tot+'</span></div></div>'}).join('');

// query details
$('qlist').innerHTML=d.query_results.map((q,i)=>{
var h=q.mentions.length>0,sr=q.sources||[],dms=(q.source_analysis||{}).domains_cited||(sr.map(s=>{try{return new URL(s.link||s.url||'').hostname.replace('www.','')}catch(e){return''}}).filter(Boolean));
return'<div class="q-item"><div class="q-head"><span class="q-dot '+(h?'hit':'miss')+'">'+(h?'✓':'·')+'</span><span class="q-txt">'+esc(q.query)+'</span><span class="q-cost">'+(q.cost!==undefined?fc(q.cost):'')+'</span></div><div class="q-ment '+(h?'hit':'miss')+'">'+(h?'→ '+esc(q.mentions.join(', ')):'→ no tracked practices named')+'</div>'+
(dms.length?'<div style="margin:3px 0 0 28px;font-size:.7rem;color:var(--text3)">Cited: '+dms.map(d=>'<span class="dom-tag">'+esc(d)+'</span>').join('')+'</div>':'')+
'<details class="q-ans"><summary></summary><div class="ans-body">Sources:\n'+sr.map(s=>'- '+esc(s.title||'')+' ['+esc(s.link||'')+']').join('\n')+'\n\nAnswer:\n'+esc(q.answer)+'</div></details></div>'}).join('')}

$('rb').addEventListener('click',ra);$('cb').addEventListener('click',ca);
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();if(!$('rb').disabled)ra()}if(e.key==='Escape'&&$('cb').style.display!=='none'){e.preventDefault();ca()}});
us();$('hc').style.display=lh().length?'':'none'
"""


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
        words = clean.split()
        if len(words) >= 3:
            al.append(" ".join(words[:2]))
        al = list(dict.fromkeys(al))
        out.append({"name": name, "aliases": al})
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

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
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _sse(self, obj):
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
                self._send_json(400, {"error": "OPENROUTER_API_KEY not set. Run the server with it, or tick Mock mode."})
                return

        queries = [q.strip() for q in (payload.get("queries") or []) if q.strip()]
        if not queries:
            queries = probe.QUERIES
        self._start_sse()
        self._sse({"type": "start", "total": len(queries), "mock": mock})

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
    ap = argparse.ArgumentParser(description="GeoAudit — AI Visibility Intelligence")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    key_set = "yes" if os.environ.get("OPENROUTER_API_KEY", "").strip() else "NO (Mock only)"
    print(f"GeoAudit running at {url} | API key set: {key_set}")
    print("Ctrl+C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping."); srv.shutdown()


if __name__ == "__main__":
    main()
