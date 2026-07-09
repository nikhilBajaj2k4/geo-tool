#!/usr/bin/env python3
"""GeoAudit — AI Visibility Intelligence. Multi-engine, source analysis, gap reports, PDF export."""
import argparse, json, os, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import probe

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GeoAudit — AI Visibility Intelligence</title>
<style>
:root{--bg:#f8f9fc;--card:#fff;--card2:#f4f5f9;--border:#e5e7ec;--border2:#d0d3db;--text:#17191e;--text2:#5a5e6b;--text3:#848896;--muted:#abaeb9;--accent:#5b5fe7;--a2:#474bc9;--as:#eeeefd;--ag:rgba(91,95,231,.14);--good:#0d9e5a;--gb:#ebfaf2;--gb2:#b8e8d0;--warn:#d9880e;--wb:#fffef0;--bad:#e32c3a;--bb:#fdefef;--bb2:#fbc5ca;--r1:linear-gradient(135deg,#5b5fe7,#8b5cf6);--r2:linear-gradient(135deg,#6366f1,#818cf8);--r3:linear-gradient(135deg,#0891b2,#22d3ee);--sh:0 1px 2px #00000006;--sh2:0 4px 12px #0000000a;--sh3:0 10px 30px #0000000d;--rr:12px;--r8:8px;--r6:6px;--sans:system-ui,-apple-system,'Inter','SF Pro',sans-serif;--mono:'SF Mono','JetBrains Mono','Fira Code',monospace}
*{box-sizing:border-box}::selection{background:var(--ag);color:var(--accent)}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
@media(prefers-reduced-motion:reduce){*,:before,:after{animation-duration:.01ms!important;transition-duration:.01ms!important}}

.app{display:flex;min-height:100vh}.sidebar{width:230px;background:var(--card);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;position:sticky;top:0;height:100vh;z-index:20}
.sh{padding:24px 20px 18px;border-bottom:1px solid var(--border)}.sh .lg{font-size:1rem;font-weight:800;display:flex;align-items:center;gap:8px;letter-spacing:-.02em}
.sh svg{width:28px;height:28px}.sh .bt{font-size:.6rem;font-weight:700;color:var(--accent);background:var(--as);padding:2px 7px;border-radius:99px;text-transform:uppercase;letter-spacing:.05em}
.sn{padding:10px 12px;flex:1}.sn a{display:flex;align-items:center;gap:10px;padding:9px 13px;border-radius:var(--r6);font-size:.83rem;font-weight:500;color:var(--text2);text-decoration:none;cursor:pointer;transition:all .12s;margin-bottom:2px}
.sn a:hover{background:var(--card2);color:var(--text)}.sn a.ac{background:var(--as);color:var(--accent);font-weight:600}
.sn .ni{width:20px;text-align:center;font-size:.85rem;opacity:.6}.sn a.ac .ni{opacity:1}
.sf{padding:14px 20px;border-top:1px solid var(--border);font-size:.7rem;color:var(--text3)}.sf b{color:var(--accent)}.sf .eng-line{font-size:.65rem;margin-top:4px;display:flex;gap:4px;flex-wrap:wrap}
.sf .eng-dot{width:6px;height:6px;border-radius:50%;display:inline-block}.eng-dot.sonar{background:#5b5fe7}.eng-dot.gpt4o{background:#0d9e5a}.eng-dot.gemini{background:#0891b2}

.main{flex:1;min-width:0}.tb{background:var(--card);border-bottom:1px solid var(--border);padding:14px 32px;display:flex;align-items:center;justify-content:space-between}
.tb h2{margin:0;font-size:1.05rem;font-weight:700;letter-spacing:-.01em}.tkr{display:flex;gap:22px}.tkv{font-size:1.1rem;font-weight:700;font-variant-numeric:tabular-nums}.tkl{font-size:.64rem;color:var(--text3);text-transform:uppercase;letter-spacing:.06em}
.ct{padding:24px 32px 80px}.tab{display:none}.tab.ac{display:block;animation:fi .2s ease}@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

.card{background:var(--card);border:1px solid var(--border);border-radius:var(--rr);padding:22px 26px;margin-bottom:18px;box-shadow:var(--sh);transition:box-shadow .15s}.card:hover{box-shadow:var(--sh2)}
.ch{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.ctt{font-size:.68rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.07em}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:768px){.g2{grid-template-columns:1fr}.sidebar{display:none}.ct{padding:14px}.tb{padding:10px 16px}.tkr{gap:14px}}

.fd{margin-bottom:14px}.fd label{display:block;font-size:.76rem;font-weight:600;color:var(--text2);margin-bottom:5px}.fd label em{color:var(--text3);font-weight:400;font-style:normal}
.fd input,.fd textarea{width:100%;background:var(--card);color:var(--text);font:13px/1.55 var(--sans);border:1.5px solid var(--border);border-radius:var(--r6);padding:9px 13px;transition:border .15s,box-shadow .15s}
.fd input:focus,.fd textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--ag)}.fd input:disabled,.fd textarea:disabled{background:var(--card2);color:var(--text3);border-color:var(--border);cursor:not-allowed}
.fd textarea{min-height:88px;resize:vertical}.fd input{height:38px}
.acs{display:flex;align-items:center;gap:10px;margin-top:16px;flex-wrap:wrap}
.btn{padding:9px 18px;font-size:.82rem;font-weight:600;border-radius:var(--r6);cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-family:inherit;border:0;transition:all .12s}
.bp{background:var(--accent);color:#fff;box-shadow:0 1px 3px #5b5fe740;gap:6px}.bp:hover:not(:disabled){background:var(--a2);box-shadow:0 4px 14px #5b5fe750}
.bp:disabled{opacity:.5;cursor:not-allowed}.bgh{background:0;color:var(--text2);border:1.5px solid var(--border);font-size:.78rem;padding:7px 14px}
.bgh:hover:not(:disabled){background:var(--card2);border-color:var(--border2)}.bd{background:var(--bb);color:var(--bad);border:1.5px solid var(--bb2)}.bd:hover:not(:disabled){background:var(--bad);color:#fff}
.tg{display:flex;align-items:center;gap:8px;font-size:.8rem;color:var(--text2);cursor:pointer;user-select:none}.tg input{width:32px;height:18px;appearance:none;background:var(--border2);border-radius:99px;cursor:pointer;position:relative;transition:background .15s}
.tg input::after{content:'';width:14px;height:14px;background:#fff;border-radius:50%;position:absolute;top:2px;left:2px;transition:transform .15s;box-shadow:0 1px 2px #00000012}.tg input:checked{background:var(--accent)}.tg input:checked::after{transform:translateX(14px)}
.st{color:var(--bad);font-size:.8rem;min-height:1em}

/* engine pills */
.ep{display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap}.ep .e-pill{padding:6px 14px;border-radius:99px;font-size:.72rem;font-weight:600;cursor:pointer;border:1.5px solid var(--border);background:var(--card);color:var(--text2);transition:all .12s}
.ep .e-pill:hover{border-color:var(--accent);color:var(--accent)}.ep .e-pill.sel{background:var(--as);color:var(--accent);border-color:var(--accent)}.ep .e-pill.sonar.sel{background:#f0effe;color:#5b5fe7;border-color:#5b5fe7}.ep .e-pill.gpt4o.sel{background:#eaf8f1;color:#0d9e5a;border-color:#0d9e5a}.ep .e-pill.gemini.sel{background:#e8f7fa;color:#0891b2;border-color:#0891b2}
.ep .e-pill .em{font-size:.64rem;opacity:.7;margin-left:4px}

/* progress */
.rnc{background:var(--card);border:1px solid var(--border);border-radius:var(--rr);padding:18px 22px;margin-bottom:18px}
.rnt{display:flex;align-items:center;gap:14px;margin-bottom:12px}.rntrk{flex:1;height:5px;background:var(--border2);border-radius:3px;overflow:hidden}.rnf{height:100%;width:0;background:linear-gradient(90deg,var(--accent),#8b5cf6);border-radius:3px;transition:width .25s}
.rnp{font-size:.78rem;font-weight:600;color:var(--text2);min-width:52px;text-align:right;font-variant-numeric:tabular-nums}.rnlog{background:var(--card2);border-radius:var(--r6);padding:10px 14px;max-height:220px;overflow-y:auto;font:12px/1.7 var(--mono)}
.rnlog .hl{color:var(--good)}.rnlog .ml{color:var(--text3)}.rnlog .el{color:var(--bad)}
.rnf2{display:flex;justify-content:space-between;margin-top:10px;font-size:.74rem;color:var(--text3)}.rnf2 .cs{color:var(--good);font-weight:600}

/* verdict */
.vb{padding:24px 28px;border-radius:var(--rr);margin-bottom:18px;display:flex;align-items:center;gap:16px;font-weight:700;font-size:.94rem;box-shadow:var(--sh2)}
.vb.g{background:var(--gb);color:var(--good);border:1.5px solid var(--gb2)}.vb.w{background:var(--wb);color:var(--warn);border:1.5px solid #fde68a}
.vb.b{background:var(--bb);color:var(--bad);border:1.5px solid var(--bb2)}.vb .vi{font-size:1.4rem;flex-shrink:0}
.sum{font-size:.8rem;color:var(--text3);margin-bottom:20px}.sum .cs{color:var(--good);font-weight:600}

/* kpi row */
.kr{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}@media(max-width:768px){.kr{grid-template-columns:repeat(2,1fr)}}
.kc{background:var(--card);border:1px solid var(--border);border-radius:var(--rr);padding:16px 20px;box-shadow:var(--sh);text-align:center}
.kc .kv{font-size:1.5rem;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;margin-bottom:2px}.kc .kl{font-size:.62rem;color:var(--text3);text-transform:uppercase;letter-spacing:.06em}
.kc .kv.g2{color:var(--good)}.kc .kv.a2{color:var(--warn)}.kc .kv.r2{color:var(--bad)}

/* scatter */
.plt{position:relative;width:100%;height:220px;background:var(--card2);border-radius:var(--r6);margin:8px 0 16px;overflow:hidden}
.plt .ax{position:absolute;font-size:.6rem;color:var(--text3);text-transform:uppercase;letter-spacing:.05em}
.plt .ax.x{bottom:6px;left:50%;transform:translateX(-50%)}.plt .ax.y{left:6px;top:50%;transform:rotate(-90deg)translateX(-50%);transform-origin:left}
.plt .dot{position:absolute;width:10px;height:10px;border-radius:50%;transform:translate(-50%,-50%);transition:all .4s ease;cursor:pointer;z-index:2}
.plt .dot:hover{width:14px;height:14px;box-shadow:0 0 0 6px var(--ag)}.plt .dot .dt{position:absolute;bottom:-16px;left:50%;transform:translateX(-50%);font-size:.58rem;white-space:nowrap;color:var(--text3);font-weight:600}

/* ranking */
.rk-item{display:grid;grid-template-columns:32px 1fr 70px 54px;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border);font-size:.83rem}.rk-item:last-child{border-bottom:0}
.rk-pos{width:24px;height:24px;border-radius:var(--r6);display:flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:700;color:#fff}.rk-pos.t1{background:var(--r1)}.rk-pos.t2{background:var(--r2)}.rk-pos.t3{background:var(--r3)}.rk-pos.def{background:var(--card2);color:var(--text3)}
.rk-name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.rk-bw{min-width:0}.rk-bt{height:7px;background:var(--border2);border-radius:4px;overflow:hidden}
.rk-bf{height:100%;border-radius:4px;transition:width .5s ease}.rk-bf.hi{background:var(--accent)}.rk-bf.md{background:var(--accent);opacity:.45}.rk-bf.lo{background:var(--text3);opacity:.25}
.rk-cnt{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}.rk-cnt em{font-weight:400;color:var(--text3);font-style:normal}

/* recs */
.rc-item{display:grid;grid-template-columns:24px 1fr;gap:12px;padding:11px 0;border-bottom:1px solid var(--border);font-size:.82rem;align-items:flex-start}.rc-item:last-child{border:0}
.rc-p{width:24px;height:24px;border-radius:var(--r6);display:flex;align-items:center;justify-content:center;font-size:.6rem;font-weight:700;color:#fff;flex-shrink:0}.rc-p.p5{background:var(--good)}.rc-p.p4{background:var(--accent)}.rc-p.p3{background:#0891b2}.rc-p.p2{background:var(--text3)}
.rc-act{font-weight:600;margin-bottom:2px}.rc-det{font-size:.76rem;color:var(--text3);line-height:1.5}.rc-src{font-size:.68rem;color:var(--accent);margin-top:3px}

/* gap analysis */
.gap-item{padding:12px 16px;background:var(--bb);border-left:3px solid var(--bad);border-radius:var(--r6);margin-bottom:10px;animation:fi .3s ease}
.gap-item h4{font-size:.82rem;font-weight:700;margin:0 0 4px;color:var(--bad)}.gap-item .gm{font-size:.78rem;color:var(--text2);margin-bottom:6px}
.gap-item .gq{padding:8px 10px;background:var(--card);border-radius:var(--r6);margin-bottom:6px;font-size:.76rem}.gap-item .gq em{color:var(--bad);font-weight:600}
.gap-item .gq .gsrc{font-size:.7rem;color:var(--text3);margin-top:3px}

/* domain tags */
.dt{display:inline-block;padding:3px 10px;background:var(--card2);border:1px solid var(--border);border-radius:99px;font-size:.7rem;color:var(--text2);margin:3px 5px 3px 0;font-family:var(--mono)}

/* query */
.qi{padding:10px 0;border-bottom:1px solid var(--border)}.qi:last-child{border:0}
.qh{display:flex;align-items:center;gap:9px}.qdot{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.62rem;flex-shrink:0}
.qdot.h{background:var(--gb);color:var(--good)}.qdot.m{background:var(--card2);color:var(--text3)}
.qqt{font-size:.82rem;font-weight:500;flex:1;min-width:0;word-break:break-word}.qqc{font-size:.7rem;color:var(--text3);font-family:var(--mono)}
.qm{margin:4px 0 0 29px;font-size:.76rem}.qm.h{color:var(--good)}.qm.m{color:var(--text3)}
.qa{margin:6px 0 0 29px;font-size:.74rem}.qa summary{cursor:pointer;color:var(--accent);font-weight:500;list-style:none;font-size:.73rem}.qa summary::-webkit-details-marker{display:none}.qa summary::before{content:'Show sources →'}.qa[open] summary::before{content:'Hide sources ↑'}
.qa .ab{margin-top:8px;padding:12px;background:var(--card2);border-radius:var(--r6);border-left:3px solid var(--accent);white-space:pre-wrap;font-size:.76rem;color:var(--text2);max-height:220px;overflow:auto;line-height:1.6}

/* history */
.he{text-align:center;padding:50px 20px;color:var(--text3);font-size:.85rem}
.hi2{display:flex;align-items:center;gap:14px;padding:12px 0;border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}.hi2:hover{background:var(--card2);margin:0 -26px;padding:12px 26px}
.hi2 .hv{font-size:.64rem;font-weight:700;padding:3px 8px;border-radius:99px}.hv.g2{background:#d1fae5;color:#065f46}.hv.a2{background:#fef3c7;color:#92400e}.hv.r2{background:#fee2e2;color:#991b1b}
.hi2 .hi3{flex:1;min-width:0}.hi3 .hm2{font-weight:600;font-size:.82rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hi3 .hd2{font-size:.7rem;color:var(--text3)}.hi3 .hd2 .ht{color:var(--good)}.hi2 .hc2{font-size:.78rem;color:var(--text2);font-family:var(--mono)}
.clr{font-size:.74rem;color:var(--bad);cursor:pointer;border:0;background:0;margin-top:10px}.clr:hover{text-decoration:underline}
</style></head><body><div class="app"><aside class="sidebar"><div class="sh"><div class="lg"><svg viewBox="0 0 28 28" fill="none"><rect width="28" height="28" rx="6" fill="url(#gh)"/><defs><linearGradient id="gh" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#5b5fe7"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs><text x="14" y="19" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">G</text></svg>GeoAudit <span class="bt">Beta</span></div></div><nav class="sn">
<a data-tab="audit" class="ac"><span class="ni">◇</span>New Audit</a><a data-tab="history"><span class="ni">☰</span>History<span id="hc" style="margin-left:auto;font-size:.65rem;color:var(--text3)"></span></a></nav>
<div class="sf"><div><b>3 engines</b> via OpenRouter</div><div class="eng-line"><span class="eng-dot sonar"></span>Sonar <span class="eng-dot gpt4o"></span>GPT <span class="eng-dot gemini"></span>Gemini</div></div></aside>
<main class="main"><div class="tb"><h2 id="ttl">New Audit</h2>
<div class="tkr"><div class="tkr"><div class="tkv" id="st1">0</div><div class="tkl">Audits</div></div><div class="tkr"><div class="tkv" id="st2">—</div><div class="tkl">Last Result</div></div></div></div>
<div class="ct">
<div id="tab-audit" class="tab ac">
<div class="card"><div class="ch"><span class="ctt">Setup</span></div>
<div class="g2"><div class="fd"><label>Specialty</label><input id="spec" placeholder="dentist" value="dentist"></div><div class="fd"><label>City / Region</label><input id="city" placeholder="Austin, TX" value="Austin, TX"></div></div>
<div class="fd"><label>Practices <em>— one per line</em></label><textarea id="practices">Forest Family Dentistry
Austin Dental Spa
Enamel Dentistry
Walden Dental
Westlake Hills Dentistry
Celebrate Dental & Braces
ATX Family Dental
Tech Ridge Dental
Belterra Dental</textarea></div>
<div class="fd"><label>Queries <em>— one per line</em></label><textarea id="queries">best dentist in austin tx
top rated dentist in austin
dentist near me that takes delta dental austin
affordable dentist south austin
family dentist austin tx
cosmetic dentist austin
invisalign provider austin tx
emergency dentist austin open saturday
pediatric dentist austin tx
dentist for crowns and implants austin</textarea></div>
<div class="acs">
<button id="rb" class="btn bp">▶ Run Audit</button>
<button id="cb" class="btn bd" style="display:none">■ Cancel</button>
<label class="tg"><input type="checkbox" id="mt"><span>Mock mode</span></label>
<button id="lex" class="btn bgh">Load example</button>
<button id="dlex" class="btn bgh" style="font-size:.74rem;padding:5px 10px" onclick="downloadReport()" disabled>↓ Report</button>
<span class="st" id="status"></span>
</div></div>

<div id="running" style="display:none"><div class="rnc"><div class="rnt"><div class="rntrk"><div id="rnf" class="rnf"></div></div><div id="rnp" class="rnp">0/0</div></div>
<div id="rnl" class="rnlog"></div><div class="rnf2"><span id="rntm">0s</span><span id="rnc2" class="cs"></span></div></div></div>

<div id="result" style="display:none">
<div id="vb" class="vb"></div><div id="sm" class="sum"></div>
<div class="ep" id="engpills"></div>
<div class="kr" id="kpis" style="display:none"></div>

<div class="card" id="scatter-card" style="display:none"><div class="ctt">Visibility Landscape</div><div class="plt" id="scatter"></div></div>

<div class="card" id="gap-card" style="display:none"><div class="ctt">Competitor Gap Analysis</div><div id="gaps"></div></div>

<div class="card" id="recs-card" style="display:none"><div class="ctt">Recommended Actions</div><div id="recs"></div></div>
<div class="card" id="dom-card" style="display:none"><div class="ctt">Top Cited Sources</div><div id="domains"></div></div>

<div class="card"><div class="ch"><span class="ctt">Visibility Ranking</span></div><div id="ranking"></div></div>
<div class="card"><div class="ctt">Query Details</div><div id="qlist"></div></div>
</div></div>

<div id="tab-history" class="tab"><div class="card"><div class="ch"><span class="ctt">Past Audits</span><button class="clr" onclick="CH()">Clear all</button></div>
<div id="hlist"><div class="he">No audits yet — run one to start.</div></div></div></div>
</div></main></div>
<script src="/app.js"></script></body></html>"""

APP_JS = r"""
(function(){"use strict";var $=document.getElementById.bind(document);var ES=null,RC=0,TS=0,AEID="all",AD=null;
function E(s){return String(s==null?"":s).replace(/[&<>]/g,function(c){return c==="&"?"&amp;":c==="<"?"&lt;":"&gt;"})}
function F(c){return"$"+(Number(c||0)).toFixed(4)}function EL(){return((Date.now()-TS)/1000).toFixed(1)+"s"}

// tabs
document.querySelectorAll(".sn a").forEach(function(a){a.addEventListener("click",function(){ST(a.dataset.tab)})});
function ST(n){document.querySelectorAll(".tab").forEach(function(t){t.classList.remove("ac")});document.querySelectorAll(".sn a").forEach(function(a){a.classList.remove("ac")});
$("tab-"+n).classList.add("ac");document.querySelector('[data-tab="'+n+'"]').classList.add("ac");$("ttl").textContent=n==="history"?"Audit History":"New Audit";if(n==="history")RH()}

// history
function LH(){try{return JSON.parse(localStorage.getItem("ga_hist")||"[]")}catch(e){return[]}}function SH(a){localStorage.setItem("ga_hist",JSON.stringify(a))}
function AH(d){var h=LH();h.unshift({ts:new Date().toISOString(),market:d.market||($("spec").value+(($("city").value)?" in "+$("city").value:"")),verdict:d.verdict,tq:d.total_queries,qa:d.queries_with_any,tc:d.total_cost,ranking:d.ranking,recs:d.recommendations||[],domains:d.top_cited_domains||[],gaps:d.gap_analysis||[],engs:d.engines||{},qr:d.query_results});if(h.length>50)h.length=50;SH(h);US()}
function CH(){if(confirm("Delete all?")){SH([]);RH();US()}}
function US(){var h=LH();$("st1").textContent=h.length;var hc=$("hc");hc.textContent=h.length||"";hc.style.display=h.length?"":"none";if(h.length){var v=h[0].verdict;$("st2").textContent=v.indexOf("REAL")!==-1?"Gap":v.indexOf("AMBIGUOUS")!==-1?"?":"None";$("st2").style.color=v.indexOf("REAL")!==-1?"var(--good)":v.indexOf("AMBIGUOUS")!==-1?"var(--warn)":"var(--bad)"}else{$("st2").textContent="\u2014";$("st2").style.color=""}}
function RH(){var h=LH(),el=$("hlist");if(!h.length){el.innerHTML='<div class="he">No audits yet.</div>';return}
el.innerHTML=h.map(function(r,i){var vc=r.verdict.indexOf("REAL")!==-1?"g2":r.verdict.indexOf("AMBIGUOUS")!==-1?"a2":"r2";var vt=r.verdict.indexOf("REAL")!==-1?"GAP":r.verdict.indexOf("AMBIGUOUS")!==-1?"AMBIG":"COLLAPSED";var d=new Date(r.ts);var ds=d.toLocaleDateString()+" "+d.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
return'<div class="hi2" onclick="VH('+i+')"><span class="hv '+vc+'">'+vt+'</span><div class="hi3"><div class="hm2">'+E(r.market)+'</div><div class="hd2"><span class="ht">'+r.qa+"/"+r.tq+"</span> queries &middot; "+ds+"</div></div><span class=\"hc2\">"+(r.ranking[0]?E(r.ranking[0].name):"")+"</span></div>"}).join("")}
function VH(i){var r=LH()[i];if(!r)return;ST("audit");$("spec").value=(r.market||"").split(" in ")[0]||"";$("city").value=(r.market||"").split(" in ")[1]||"";$("practices").value=(r.ranking||[]).map(function(p){return p.name}).join("\n");$("queries").value=(r.qr||[]).map(function(q){return q.query}).join("\n");RESET();RF(r);$("result").scrollIntoView({behavior:"smooth"})}

// load example
$("lex").addEventListener("click",EX);
function EX(){$("spec").value="dentist";$("city").value="Austin, TX";$("practices").value="Forest Family Dentistry\nAustin Dental Spa\nEnamel Dentistry\nWalden Dental\nWestlake Hills Dentistry\nCelebrate Dental & Braces\nATX Family Dental\nTech Ridge Dental\nBelterra Dental";$("queries").value="best dentist in austin tx\ntop rated dentist in austin\ndentist near me that takes delta dental austin\naffordable dentist south austin\nfamily dentist austin tx\ncosmetic dentist austin\ninvisalign provider austin tx\nemergency dentist austin open saturday\npediatric dentist austin tx\ndentist for crowns and implants austin"}

// audit
function SRS(r){["spec","city","practices","queries","mt"].forEach(function(id){$(id).disabled=r});$("rb").style.display=r?"none":"";$("cb").style.display=r?"":"none";$("lex").style.display=r?"none":"";
$("dlex").style.display=r?"none":"";$("dlex").disabled=!r;if(!r&&AD)$("dlex").style.display=""}
function RESET(){$("result").style.display="none";$("running").style.display="none";$("dlex").style.display="none"}
function RA(){if(ES){ES.close();ES=null}SRS(true);$("status").textContent="";RESET();$("running").style.display="block";RC=0;TS=Date.now();$("rnf").style.width="0";$("rnp").textContent="0/0";$("rnl").innerHTML="";$("rntm").textContent="0s";$("rnc2").textContent="";
var ps=$("practices").value.split("\n").map(function(s){return s.trim()}).filter(Boolean);var qs=$("queries").value.split("\n").map(function(s){return s.trim()}).filter(Boolean);
var b={specialty:$("spec").value,city:$("city").value,practices:ps,queries:qs,mock:$("mt").checked};
fetch("/api/audit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}).then(function(r){if(!r.ok)return r.json().then(function(j){throw new Error(j.error||"HTTP "+r.status)});var rd=r.body.getReader(),dc=new TextDecoder(),buf="",tt=qs.length||10;
(function pump(){rd.read().then(function(x){var data=x.value||"";buf+=dc.decode(data,{stream:!x.done});var i;while((i=buf.indexOf("\n\n"))!==-1){HE(buf.slice(0,i),function(){return tt},function(t){tt=t});buf=buf.slice(i+2)}if(!x.done){pump()}else{if(buf.trim())HE(buf,function(){return tt},function(t){tt=t})}}).catch(function(e){FW(e.message)})})()}).catch(function(e){FW(e.message)})}
function CA(){if(ES){ES.close();ES=null}$("rnl").innerHTML+='<div class="el">Cancelled after '+EL()+"</div>";SRS(false);$("status").textContent="Cancelled"}
function HE(c,gt,st){var ls=c.split("\n");for(var i=0;i<ls.length;i++){var l=ls[i];if(l.indexOf("data:")!==0)continue;var p=l.slice(5).trim();if(!p)continue;var ev;try{ev=JSON.parse(p)}catch(e){continue}
if(ev.type==="start"){st(ev.total);HE.mock=!!ev.mock;HE.engs=ev.engs||1;$("rnp").textContent="0/"+ev.total;if(ev.mock)$("rnc2").textContent="mock"}else if(ev.type==="query"){RC=ev.run_cost||0;var pct=gt()?Math.round((ev.done/gt())*100):0;$("rnf").style.width=pct+"%";$("rnp").textContent=ev.done+"/"+gt();$("rntm").textContent=EL();if(ev.mentions&&ev.mentions.length)$("rnl").innerHTML+='<div class="hl">\u2713 '+E(ev.query)+" \u2192 "+E(ev.mentions.join(", "))+(ev.engine?" <span style=color:var(--text3)>["+ev.engine+"]</span>":"")+"</div>";else $("rnl").innerHTML+='<div class="ml">\u2717 '+E(ev.query)+" (none)"+(ev.engine?" <span style=color:var(--text3)>["+ev.engine+"]</span>":"")+"</div>";if(!HE.mock)$("rnc2").textContent=F(RC);$("rnl").scrollTop=$("rnl").scrollHeight}else if(ev.type==="error"){$("rnl").innerHTML+='<div class="el">ERROR: '+E(ev.query)+"</div>"}else if(ev.type==="done"){SRS(false);$("status").textContent="";$("running").style.display="none";AD=ev.result;RF(ev.result);AH(ev.result);$("result").style.display="block";$("result").scrollIntoView({behavior:"smooth"})}}}
function FW(m){$("running").style.display="none";SRS(false);$("status").textContent="Error: "+m}

// engine pills
function SP(eid){AEID=eid;var ps=document.querySelectorAll(".e-pill");ps.forEach(function(p){p.classList.toggle("sel",p.dataset.eng===eid)});if(AD)RF(AD)}
function BP(d){var engs=d.engines;if(!engs||Object.keys(engs).length<2){$("engpills").style.display="none";return}
$("engpills").style.display="flex";$("engpills").innerHTML='<span class="e-pill sel" data-eng="all" onclick="SP(\'all\')">All</span>';
Object.keys(engs).forEach(function(eid){var eng=engs[eid];var cls=eid==="sonar"?"sonar":eid==="gpt4o"?"gpt4o":eid==="gemini"?"gemini":"";
$("engpills").innerHTML+='<span class="e-pill '+cls+'" data-eng="'+eid+'" onclick="SP(\''+eid+'\')">'+E(eng.name)+' <span class="em">'+eng.queries_with_any+"/"+(d.total_queries||1)+'</span></span>'})}

// render
function RF(d){if(!d)return;AEID="all";try{AD=d;
var cl=d.verdict.indexOf("REAL")!==-1?"g":d.verdict.indexOf("AMBIGUOUS")!==-1?"w":"b";var ic=cl==="g"?"\u2713":cl==="w"?"\u26a0":"\u2717";
var vb=$("vb");if(vb){vb.className="vb "+cl;vb.innerHTML='<span class="vi">'+ic+'</span><span>'+E(d.verdict)+'</span>'}
var ct=d.total_cost?F(d.total_cost):"0.00";var sm=$("sm");if(sm)sm.innerHTML=E(d.detail)+" &middot; "+d.queries_with_any+"/"+(d.total_queries_all||d.total_queries)+" queries &middot; <span class=cs>"+ct+"</span>"+(d.total_queries?" &middot; "+EL()+" elapsed":"");

// engine pills
BP(d);

// KPI
var kp=$("kpis");if(kp){kp.style.display="grid";kp.innerHTML=
'<div class="kc"><div class="kv g2">'+d.queries_with_any+'</div><div class="kl">Queries with mentions</div></div>'+
'<div class="kc"><div class="kv">'+(d.top_cited_domains?d.top_cited_domains.length:"0")+'</div><div class="kl">Unique domains cited</div></div>'+
'<div class="kc"><div class="kv a2">'+(d.ranking?d.ranking.filter(function(r){return r.count===0}).length:"0")+'</div><div class="kl">Practices invisible</div></div>'+
'<div class="kc"><div class="kv">'+(d.engines?Object.keys(d.engines).length:"1")+'</div><div class="kl">Engines</div></div>'}

// scatter plot
var sc=$("scatter-card");if(sc&&d.ranking&&d.ranking.length>=2&&d.total_queries){
sc.style.display="block";var scd=$("scatter");var maxV=d.total_queries||1,h=scd.clientHeight||220,w=scd.clientWidth||600;var pad=40;
var items=d.ranking.slice(0,6).filter(function(r){return r.count>=0});
scd.innerHTML='<div class="ax x">Mentions</div><div class="ax y">Rank</div>';
items.forEach(function(r,i){var x=pad+((r.count/maxV)*(w-pad*2));var y=pad+((i/(items.length-1||1))*(h-pad*2));var name=r.name.length>14?r.name.slice(0,12)+"\u2026":r.name;
scd.innerHTML+='<div class="dot" style="left:'+x+'px;top:'+y+'px;background:'+(i===0?"var(--accent)":i===1?"#8b5cf6":"#0891b2")+'"><div class="dt">'+E(name)+'</div></div>'})}

// gap analysis
var gc=$("gap-card"),gd=$("gaps");if(gc&&gd&&d.gap_analysis&&d.gap_analysis.length){var gapData=d.gap_analysis.filter(function(g){return g&&g.gap_queries&&g.gap_queries.length>0});
if(gapData.length){gc.style.display="block";gd.innerHTML=gapData.map(function(g){return'<div class="gap-item"><h4>'+E(g.practice)+'</h4><div class="gm">Invisible in <b>'+g.missing_from+'</b> queries while competitors won.</div>'+g.gap_queries.slice(0,2).map(function(gq){return'<div class="gq">Query: <em>"'+E(gq.query)+'"</em><br>Competitors: '+E((gq.competitors_mentioned||[]).join(", "))+"<br>"+(gq.dominant_domain?'<span class="gsrc">Top source: '+E(gq.dominant_domain)+'</span>':"")+"</div>"}).join("")+"</div>"}).join("")}else{gc.style.display="none"}}else if(gc)gc.style.display="none";

// recs
var rc=$("recs-card"),rd=$("recs");if(rc&&rd&&d.recommendations&&d.recommendations.length){rc.style.display="block";
rd.innerHTML=d.recommendations.map(function(r){return'<div class="rc-item"><div class="rc-p p'+r.priority+'">'+r.priority+'</div><div class="rc-body"><div class="rc-act">'+E(r.action)+'</div><div class="rc-det">'+E(r.detail)+'</div>'+(r.domain?'<div class="rc-src">Source: '+E(r.domain)+' ('+r.citation_count+'\u00d7)</div>':"")+"</div></div>"}).join("")}else if(rc)rc.style.display="none";

// domains
var dc=$("dom-card"),dd=$("domains");if(dc&&dd&&d.top_cited_domains&&d.top_cited_domains.length){dc.style.display="block";
dd.innerHTML=d.top_cited_domains.map(function(e){return'<span class="dt">'+E(e[0])+' <b>'+e[1]+'\u00d7</b></span>'}).join("")}else if(dc)dc.style.display="none";

// ranking
var rk=$("ranking");if(rk){var tot=d.total_queries||1,mc=Math.max.apply(null,[1].concat(d.ranking.map(function(r){return r.count})));
rk.innerHTML=d.ranking.map(function(r,i){var pct=tot?(r.count/tot)*100:0,rn=r.count/mc,cls2=i<3?"t"+(i+1):"def",bc=rn>=.6?"hi":rn>=.3?"md":"lo";
return'<div class="rk-item"><div class="rk-pos '+cls2+'">'+(i+1)+'</div><div class="rk-name">'+E(r.name)+'</div><div class="rk-bw"><div class="rk-bt"><div class="rk-bf '+bc+'" style="width:'+pct+'%"></div></div></div><div class="rk-cnt">'+r.count+' <em>/'+tot+'</em></div></div>'}).join("")}

// queries
var ql=$("qlist");if(ql){ql.innerHTML=d.query_results.map(function(q,i){var h=q.mentions.length>0,sr=q.sources||[],dms=[];
sr.forEach(function(s){try{var u=s.link||s.url||"";if(u){var hst=(new URL(u)).hostname.replace(/^www\./,"");if(hst&&dms.indexOf(hst)<0)dms.push(hst)}}catch(e){}});
return'<div class="qi"><div class="qh"><span class="qdot '+(h?"h":"m")+'">'+(h?"\u2713":"\u00b7")+'</span><span class="qqt">'+E(q.query)+'</span><span class="qqc">'+(q.cost!==undefined?F(q.cost):"")+'</span></div><div class="qm '+(h?"h":"m")+'">'+(h?"\u2192 "+E(q.mentions.join(", ")):"\u2192 no tracked practices named")+'</div>'+(dms.length?'<div style="margin:3px 0 0 29px;font-size:.7rem;color:var(--text3)">'+dms.map(function(dm){return'<span class="dt">'+E(dm)+'</span>'}).join("")+'</div>':"")+'<details class="qa"><summary></summary><div class="ab">Sources:\n'+sr.map(function(s){return"- "+E(s.title||"")+" ["+E(s.link||"")+"]"}).join("\n")+"\n\nAnswer:\n"+E(q.answer)+"</div></details></div>"}).join("")}
}catch(e){var st=$("status");if(st)st.textContent="Render: "+e.message}}

// report download
function downloadReport(){if(!AD)return;var w=window.open("","_blank");w.document.write('<html><body style=background:#f8f9fc;padding:24px;font-family:sans-serif;color:#5a5e6b;text-align:center><h3>Generating report...</h3></body></html>');w.document.close();
fetch("/api/report",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({result:AD})}).then(function(r){return r.text()}).then(function(html){w.document.write(html);w.document.close();setTimeout(function(){w.print()},600)})}

$("rb").addEventListener("click",RA);$("cb").addEventListener("click",CA);
document.addEventListener("keydown",function(e){if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){e.preventDefault();if(!$("rb").disabled)RA()}if(e.key==="Escape"&&$("cb").style.display!=="none"){e.preventDefault();CA()}});
US();$("hc").style.display=LH().length?"":"none"
window.downloadReport=downloadReport;window.CH=CH;window.VH=VH;window.EX=EX;window.SP=SP;window.RF=RF
})()
"""

def parse_practices(lines):
    out = []
    for name in lines:
        name = name.strip()
        if not name: continue
        low = name.lower().strip()
        al = [low]
        clean = low.replace(" & ", " ").replace("&", "and")
        if clean != low: al.append(clean)
        words = clean.split()
        if len(words) >= 3: al.append(" ".join(words[:2]))
        al = list(dict.fromkeys(al))
        out.append({"name": name, "aliases": al})
    return out

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _send_json(self, code, obj): self._send(code, json.dumps(obj))
    def _start_sse(self):
        self.send_response(200); self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "keep-alive"); self.end_headers()
    def _sse(self, obj): self.wfile.write(("data: "+json.dumps(obj)+"\n\n").encode("utf-8")); self.wfile.flush()

    def do_GET(self):
        if self.path in ("/", "/index.html"): self._send(200, HTML, ctype="text/html; charset=utf-8")
        elif self.path == "/app.js": self._send(200, APP_JS, ctype="application/javascript; charset=utf-8")
        elif self.path.startswith("/api/report"): self._handle_report()
        else: self._send_json(404, {"error":"not found"})

    def _handle_report(self):
        params = urllib.parse.parse_qs(self.path.split("?")[-1])
        filename = params.get("file", [None])[0]
        if not filename: self._send_json(400, {"error":"missing file"}); return
        try:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "audits")
            with open(os.path.join(data_dir, os.path.basename(filename))) as f: data = json.load(f)
            from report import generate_report
            self._send(200, generate_report(data), ctype="text/html; charset=utf-8")
        except FileNotFoundError: self._send_json(404, {"error":"not found"})

    def do_POST(self):
        if self.path == "/api/report": self._handle_report_post(); return
        if self.path != "/api/audit": self._send_json(404, {"error":"not found"}); return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception as e: self._send_json(400, {"error":"bad JSON: %s"%e}); return

        specialties = [s.strip() for s in (payload.get("specialty") or "").split(",") if s.strip()]
        city = (payload.get("city") or "").strip()
        market = f"{' / '.join(specialties)} in {city}" if specialties and city else ""
        mock = bool(payload.get("mock"))
        practices = parse_practices(payload.get("practices") or [])
        if not practices: practices = probe.PRACTICES

        engines = probe.MULTI_ENGINES if not mock else [probe.MULTI_ENGINES[0]]
        if not mock:
            key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            if not key: self._send_json(400, {"error":"OPENROUTER_API_KEY not set"}); return

        queries = [q.strip() for q in (payload.get("queries") or []) if q.strip()]
        if not queries: queries = probe.QUERIES
        self._start_sse()
        self._sse({"type":"start","total":len(queries),"mock":mock,"engines":len(engines)})

        try:
            if not mock and len(engines) > 1:
                result = probe.run_multi_audit(key, queries, practices, engines=engines, mock=mock, market=market,
                    on_query=lambda i,t,q,h,qc,rc,eid: self._sse({"type":"query" if h is not None else "error","done":i,"total":t,"query":q,"mentions":h or[],"query_cost":round(qc,6),"run_cost":round(rc,6),"engine":eid}))
            else:
                prov, mod = engines[0]["provider"], engines[0]["model"]
                def on_q(i,t,q,h,qc,rc):
                    if h is None: self._sse({"type":"error","done":i,"total":t,"query":q,"error":"API call failed"})
                    else: self._sse({"type":"query","done":i,"total":t,"query":q,"mentions":h or[],"query_cost":round(qc,6),"run_cost":round(rc,6)})
                result = probe.run_audit(prov, mod, key, queries, practices, mock=mock, on_query=on_q, market=market)
            self._sse({"type":"done","result":result})
            import time; time.sleep(0.05)  # ensure client drains SSE buffer
        except Exception as e: self._sse({"type":"fatal","error":str(e).replace('"',"'")})

    def _handle_report_post(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            from report import generate_report
            self._send(200, generate_report(payload.get("result", payload)), ctype="text/html; charset=utf-8")
        except Exception as e: self._send_json(400, {"error":str(e)})

def main():
    ap = argparse.ArgumentParser(description="GeoAudit")
    ap.add_argument("--port", type=int, default=8765); ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    ks = "yes" if os.environ.get("OPENROUTER_API_KEY","").strip() else "NO (mock only)"
    print(f"GeoAudit → http://{args.host}:{args.port} | API key: {ks}\nCtrl+C to stop.\n")
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\nStopped."); srv.shutdown()

if __name__ == "__main__": main()
