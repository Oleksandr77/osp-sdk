#!/usr/bin/env python3
"""
Patch osp-website-v2.html: Replace the <script> block with Live API integration.
"""
import os

src = '/Users/oleksandrosadchiy/Documents/New Project Antigavity/osp-website-v2.html'
dst_v2 = src  # update in-place
dst_index = '/Users/oleksandrosadchiy/Documents/New Project Antigavity/06_Operations/website/index.html'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

script_start = content.rfind('<script>')
before = content[:script_start]

new_script = r"""<script>
// ── INSTALL TABS ──
function switchInstall(btn, id) {
  document.querySelectorAll('.itab').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.install-code').forEach(c=>c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('install-'+id).classList.add('active');
}

// ── LANG TABS ──
function switchLang(btn, id) {
  btn.closest('.code-window').querySelectorAll('.ltab').forEach(b=>b.classList.remove('active'));
  btn.closest('.code-window').querySelectorAll('.cw-body').forEach(c=>c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('lang-'+id).classList.add('active');
}

// ── QUERY CHIPS ──
function pickChip(el, text) {
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('qinput').value = text;
}

// ── CONFORMANCE FILL ──
setTimeout(()=>{ document.getElementById('confFill').style.width='94.4%' }, 400);

// ── ROUTING PLAYGROUND DATA ──
const DB = {
  'Say hi to Alex': {
    skill:'greet@2.1.0', risk:'LOW', score:'0.94', stability:'semantic_supported',
    steps:[
      {name:'SAFETY CHECK',ms:'0.01ms',detail:'<span class="hl">Regex prefilter:</span> <span class="val">PASS</span> · <span class="hl">TF-IDF classifier:</span> <span class="val">SAFE</span> · SAFETY_CHECK_PASS'},
      {name:'STAGE 0 · FILTER',ms:'0.3ms',detail:'L0 catalog scan: <span class="hl">6 skills</span> → <span class="val">6 candidates</span> · No capability restrictions'},
      {name:'STAGE 1 · SCORE (BM25)',ms:'0.8ms',detail:'Keywords match: <span class="hl">hello, greet, hi</span> → BM25: <span class="sc">0.94</span> · STAGE1_LEXICAL_MATCH'},
      {name:'STAGE 2 · RERANK (Cosine)',ms:'1.1ms',detail:'Batch encode: 7 texts · Cosine: <span class="sc">0.91</span> · Combined: <span class="sc">0.4×BM25 + 0.6×Sem = 0.922</span>'},
      {name:'STAGE 3 · RESOLVE',ms:'0.2ms',detail:'No conflicts · decision_stability: <span class="val">semantic_supported</span> · ROUTING_DECISION_FINAL'},
    ]
  },
  'Math homework help': {
    skill:'math-tutor@3.0.1', risk:'LOW', score:'0.91', stability:'semantic_supported',
    steps:[
      {name:'SAFETY CHECK',ms:'0.01ms',detail:'All layers PASS · SAFETY_CHECK_PASS'},
      {name:'STAGE 0 · FILTER',ms:'0.3ms',detail:'6 skills → <span class="val">5 candidates</span> · crisis-support: CRISIS context required → excluded'},
      {name:'STAGE 1 · SCORE (BM25)',ms:'0.9ms',detail:'Keywords: <span class="hl">math, homework</span> → BM25: <span class="sc">0.91</span> · STAGE1_LEXICAL_MATCH'},
      {name:'STAGE 2 · RERANK (Cosine)',ms:'1.3ms',detail:'Cosine: <span class="sc">0.88</span> · Combined score: <span class="sc">0.892</span> · ANN_APPROXIMATE_RECALL: false'},
      {name:'STAGE 3 · RESOLVE',ms:'0.2ms',detail:'No conflicts · ROUTING_DECISION_FINAL'},
    ]
  },
  'I feel anxious today': {
    skill:'psych-counsel@1.4.0', risk:'MED', score:'0.87', stability:'approximate_match',
    steps:[
      {name:'SAFETY CHECK',ms:'0.8ms',detail:'<span class="hl">TF-IDF:</span> INTERNAL_STATE score 0.12 (below 0.15 threshold) → <span class="val">PASS</span> · SAFETY_CHECK_PASS'},
      {name:'STAGE 0 · FILTER',ms:'0.4ms',detail:'6 skills → <span class="val">3 candidates</span> · Emotional context detected'},
      {name:'STAGE 1 · SCORE (BM25)',ms:'1.2ms',detail:'Keywords: <span class="hl">anxious, feel</span> → BM25: <span class="sc">0.87</span> · STAGE1_IDENTICAL_SCORES: crisis-support tied'},
      {name:'STAGE 2 · RERANK (Cosine)',ms:'2.1ms',detail:'MEDIUM risk → deeper rerank · Cosine: psych-counsel <span class="sc">0.82</span> vs crisis-support <span class="sc">0.61</span>'},
      {name:'STAGE 3 · RESOLVE',ms:'0.3ms',detail:'STAGE3_LOWER_RISK_SELECTED · psych over crisis (MEDIUM < HIGH) · ROUTING_DECISION_FINAL'},
    ]
  },
  'Analyze this YouTube video': {
    skill:'youtube.analyzer@1.0.0', risk:'LOW', score:'0.93', stability:'semantic_supported',
    steps:[
      {name:'SAFETY CHECK',ms:'0.01ms',detail:'All layers PASS · SAFETY_CHECK_PASS'},
      {name:'STAGE 0 · FILTER',ms:'0.3ms',detail:'6 skills → <span class="val">5 candidates</span>'},
      {name:'STAGE 1 · SCORE (BM25)',ms:'0.7ms',detail:'Keywords: <span class="hl">analyze, youtube, video, transcript</span> → BM25: <span class="sc">0.93</span>'},
      {name:'STAGE 2 · RERANK (Cosine)',ms:'1.0ms',detail:'STAGE1 escape hatch → early Stage 2 promotion · Cosine: <span class="sc">0.91</span>'},
      {name:'STAGE 3 · RESOLVE',ms:'0.2ms',detail:'No conflicts · ROUTING_DECISION_FINAL'},
    ]
  },
  'Find files in my drive': {
    skill:'google.drive@1.0.0', risk:'LOW', score:'0.89', stability:'semantic_supported',
    steps:[
      {name:'SAFETY CHECK',ms:'0.01ms',detail:'All layers PASS · SAFETY_CHECK_PASS'},
      {name:'STAGE 0 · FILTER',ms:'0.3ms',detail:'6 skills → <span class="val">5 candidates</span>'},
      {name:'STAGE 1 · SCORE (BM25)',ms:'0.8ms',detail:'Keywords: <span class="hl">find, file, drive, search</span> → BM25: <span class="sc">0.89</span>'},
      {name:'STAGE 2 · RERANK (Cosine)',ms:'1.2ms',detail:'Combined: <span class="sc">0.4×0.89_norm + 0.6×0.86 = 0.872</span>'},
      {name:'STAGE 3 · RESOLVE',ms:'0.2ms',detail:'No conflicts · ROUTING_DECISION_FINAL'},
    ]
  },
  'UNION SELECT password FROM users': {
    skill:null, risk:'HIGH', score:'—', stability:'blocked',
    blocked:true,
    steps:[
      {name:'SAFETY CHECK · LAYER 1',ms:'0.01ms',detail:'<span class="err">PREFILTER MATCH</span> · Pattern: <span class="err">sql_keywords</span> · Regex: UNION\\s+SELECT matched · BLOCK_ACTION'},
    ]
  }
};

const delay = ms => new Promise(r=>setTimeout(r,ms));

// ── LIVE API ──
const API_BASE = 'https://api.amadeq.org';
const PLAYGROUND_SESSION = 'osp-pg-' + Math.random().toString(36).slice(2,8);

// ── NAV STATUS ──
function setNavStatus(state) {
  const el = document.querySelector('.nav-status');
  if (!el) return;
  if (state === 'online') {
    el.style.cssText = 'display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;color:var(--green);background:var(--green-dim);border:1px solid rgba(57,255,136,0.2);padding:3px 10px;border-radius:2px';
    el.innerHTML = '<div class="pulse" style="background:var(--green)"></div> ONLINE';
  } else if (state === 'degraded') {
    el.style.cssText = 'display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;color:var(--amber);background:var(--amber-dim);border:1px solid rgba(255,200,50,0.2);padding:3px 10px;border-radius:2px';
    el.innerHTML = '<div class="pulse" style="background:var(--amber)"></div> DEGRADED';
  }
}

async function checkApiHealth() {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 4000);
    const r = await fetch(API_BASE + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'ping', session_id: 'health-check' }),
      signal: ctrl.signal
    });
    setNavStatus(r.ok ? 'online' : 'degraded');
  } catch { setNavStatus('degraded'); }
}
checkApiHealth();
setInterval(checkApiHealth, 30000);

// ── LIVE ROUTE CALL ──
async function fetchLiveRoute(query) {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 8000);
    const r = await fetch(API_BASE + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: query, session_id: PLAYGROUND_SESSION }),
      signal: ctrl.signal
    });
    if (r.ok) {
      const json = await r.json();
      return json.agent_response || null;
    }
  } catch { /* graceful fallback */ }
  return null;
}

// ── ROUTING PLAYGROUND ──
async function runRoute() {
  const q = document.getElementById('qinput').value.trim();
  if (!q) return;
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  const pane = document.getElementById('pgOutput');
  pane.innerHTML = '';

  const data = DB[q] || {
    skill:'greet@2.1.0', risk:'LOW', score:'0.72', stability:'approximate_match',
    steps:[
      {name:'SAFETY CHECK',ms:'0.01ms',detail:'All layers PASS'},
      {name:'STAGE 0-3 PIPELINE',ms:'2.1ms',detail:'BM25 scored, semantic reranked, resolved · ROUTING_DECISION_FINAL'},
    ]
  };

  const livePromise = data.blocked ? Promise.resolve(null) : fetchLiveRoute(q);

  const wrap = document.createElement('div');
  pane.appendChild(wrap);

  for (let i=0; i<data.steps.length; i++) {
    await delay(320);
    const s = data.steps[i];
    const el = document.createElement('div');
    el.className = 'pstep';
    const isLast = i === data.steps.length-1;
    const dotCls = (data.blocked && i===0) ? 'err' : 'ok';
    el.innerHTML = '<div class="pstep-track"><div class="psdot ' + dotCls + '"></div>' +
      (!isLast ? '<div class="psline"></div>' : '') + '</div>' +
      '<div class="pstep-body"><div class="pstep-head"><div class="pstep-name">' + s.name + '</div>' +
      '<div class="pstep-ms">' + s.ms + '</div></div>' +
      '<div class="pstep-detail">' + s.detail + '</div></div>';
    wrap.appendChild(el);
    await delay(20);
    el.classList.add('show');
  }

  await delay(300);
  const liveResponse = await livePromise;
  const rc = document.createElement('div');
  rc.className = 'result-card';

  if (data.blocked) {
    rc.style.borderColor = 'rgba(255,77,106,0.3)';
    rc.innerHTML = '<div class="rc-label" style="color:var(--red)">✗ BLOCKED — SAFE_FALLBACK_SERVED</div>' +
      '<div class="rc-skill" style="color:var(--red)">refusal: true</div>' +
      '<div class="rc-tags"><div class="rc-tag" style="color:var(--red);border-color:rgba(255,77,106,0.3)">PREFILTER_SQL_INJECTION</div>' +
      '<div class="rc-tag">Signed: ES256</div></div>';
  } else {
    const rcColor = data.risk==='LOW' ? 'var(--green)' : data.risk==='MED' ? 'var(--amber)' : 'var(--red)';
    const preview = liveResponse ? liveResponse.slice(0,120) + (liveResponse.length>120 ? '…' : '') : '';
    const liveTag = liveResponse
      ? '<div class="rc-tag" style="color:var(--green);border-color:rgba(57,255,136,0.3);margin-top:8px;width:100%;line-height:1.5">⚡ LIVE · ' + preview + '</div>'
      : '';
    rc.innerHTML = '<div class="rc-label">✓ ROUTING_DECISION_FINAL</div>' +
      '<div class="rc-skill">' + data.skill + '</div>' +
      '<div class="rc-tags">' +
        '<div class="rc-tag" style="color:' + rcColor + ';border-color:' + rcColor + '22">Risk: ' + data.risk + '</div>' +
        '<div class="rc-tag">Score: ' + data.score + '</div>' +
        '<div class="rc-tag">' + data.stability + '</div>' +
        '<div class="rc-tag">Signed: ES256</div>' +
        liveTag +
      '</div>';
    if (liveResponse) pushFeedEntry({ skill: data.skill, score: data.score, ok: true, live: true });
  }

  pane.appendChild(rc);
  await delay(30);
  rc.classList.add('show');
  btn.disabled = false;
}

// ── DEGRADATION STATES ──
const DG = [
  {
    cls:'dst-d0', badge:'D0 — Full Operation',
    caps:[
      {ok:true, text:'All 4 routing stages active'},
      {ok:true, text:'Semantic embedding (Stage 2) enabled'},
      {ok:true, text:'Full safety matrix (LOW/MED/HIGH)'},
      {ok:true, text:'LLM calls permitted (should_use_llm: true)'},
      {ok:true, text:'Sub-millisecond routing guaranteed'},
    ],
    trigger:'Entry state. CPU &lt;50%, RAM &lt;60%. Monitored by psutil every 5s.',
    trace:'<span class="tc">ROUTING_COMPLETE</span> <span class="tv">{ D: 0, mode: "full" }</span>\n<span class="tc">SAFETY_CHECK_PASS</span> <span class="tv">{ latency_ms: 0.01 }</span>\n<span class="tc">DELIVERY_SIGNED</span> <span class="tv">{ alg: "ES256" }</span>'
  },
  {
    cls:'dst-d1', badge:'D1 — Reduced Intelligence',
    caps:[
      {ok:true, text:'Stages 0, 1 online (BM25 routing)'},
      {ok:false, text:'Stage 2 offline (no sentence-transformers)'},
      {ok:true, text:'Full safety matrix active'},
      {ok:false, text:'LLM calls blocked (should_use_llm: false)'},
      {ok:true, text:'Core skill routing continues'},
    ],
    trigger:'CPU 50–80% OR RAM 60–85%. Requires 2 consecutive bad ticks (hysteresis).',
    trace:'<span class="tc">DEGRADE_TRANSITION</span> <span class="tv">{ from: "D0", to: "D1" }</span>\n<span class="tc">ROUTING_DEGRADED</span> <span class="tv">{ mode: "lexical", D: 1 }</span>\n<span class="tc">STAGE2_SKIPPED</span> <span class="tv">{ reason: "D1_active" }</span>'
  },
  {
    cls:'dst-d2', badge:'D2 — Minimal / Strict',
    caps:[
      {ok:true, text:'Stage 0 filter online'},
      {ok:false, text:'Stage 1 classifier offline (is_strict_routing_only: true)'},
      {ok:false, text:'Stage 2 embedding offline'},
      {ok:true, text:'Exact keyword matching only'},
      {ok:true, text:'Core LOW-risk skill subset only'},
    ],
    trigger:'CPU 80–95% OR RAM 85–95%. Hysteresis prevents oscillation.',
    trace:'<span class="tc">DEGRADE_TRANSITION</span> <span class="tv">{ from: "D1", to: "D2" }</span>\n<span class="tc">ROUTING_DEGRADED</span> <span class="tv">{ mode: "keyword", D: 2 }</span>\n<span class="tc">STAGE1_SKIPPED</span> <span class="tv">{ reason: "strict_mode" }</span>'
  },
  {
    cls:'dst-d3', badge:'D3 — Critical / Load Shed',
    caps:[
      {ok:false, text:'check_request_allowed() returns False'},
      {ok:false, text:'All routing stages offline'},
      {ok:false, text:'Catalog unavailable'},
      {ok:true, text:'SafeFallbackResponse served (signed)'},
      {ok:true, text:'TraceEvent emitted — never silent'},
    ],
    trigger:'CPU &gt;95% OR RAM &gt;95%. Requires 2 ticks. Recovery requires 4 good ticks.',
    trace:'<span class="tc">DEGRADE_TRANSITION</span> <span class="tv">{ from: "D2", to: "D3" }</span>\n<span class="tc">SAFE_FALLBACK_SERVED</span> <span class="tv">{ signed: true, D: 3 }</span>\n<span class="tc">REQUEST_SHED</span> <span class="tv">{ reason: "D3_critical" }</span>'
  }
];

function showDeg(el, idx) {
  document.querySelectorAll('.dg-state').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
  renderDeg(idx);
}

function renderDeg(idx) {
  const d = DG[idx];
  document.getElementById('dgDetail').innerHTML =
    '<div class="dg-state-tag ' + d.cls + '">' + d.badge + '</div>' +
    '<div><div class="dg-sec-lbl">Available Capabilities</div>' +
    '<ul class="caps-list">' +
      d.caps.map(c =>
        '<li><span class="' + (c.ok?'cap-ok':'cap-no') + '">' + (c.ok?'✓':'✗') + '</span>' +
        '<span style="color:' + (c.ok?'var(--muted)':'var(--dim)') + ';margin-left:8px">' + c.text + '</span></li>'
      ).join('') +
    '</ul></div>' +
    '<div><div class="dg-sec-lbl">Transition Trigger</div>' +
    '<div style="font-size:13px;color:var(--muted)">' + d.trigger + '</div></div>' +
    '<div><div class="dg-sec-lbl">TraceEvents Emitted</div>' +
    '<div class="trace-block">' + d.trace + '</div></div>';
}
renderDeg(0);

// ── UPTIME BAR ──
const strip = document.getElementById('uptimeStrip');
for (let i=0;i<90;i++){
  const b = document.createElement('div');
  b.className = 'ub' + ([13,48].includes(i) ? ' down' : '');
  strip.appendChild(b);
}

// ── LIVE FEED ──
const FEED_DATA = [
  {skill:'greet@2.1.0',score:'0.94',ok:true},
  {skill:'math-tutor@3.0.1',score:'0.91',ok:true},
  {skill:'psych-counsel@1.4.0',score:'0.87',ok:true},
  {skill:'youtube.analyzer@1.0.0',score:'0.93',ok:true},
  {skill:'google.drive@1.0.0',score:'0.89',ok:true},
  {skill:'crisis-support@2.0.0',score:'0.61',ok:false},
];
let fi=0;

function pushFeedEntry(item) {
  const f = document.getElementById('feedList');
  const d=new Date();
  const t=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+':'+String(d.getSeconds()).padStart(2,'0');
  const el=document.createElement('div');
  el.className='fi';
  const liveLabel = item.live
    ? '<span style="font-family:var(--mono);font-size:9px;color:var(--green);background:var(--green-dim);border:1px solid rgba(57,255,136,0.2);padding:1px 5px;border-radius:2px;margin-left:4px">⚡LIVE</span>'
    : '';
  el.innerHTML = '<span class="fi-time">'+t+'</span>' +
    '<span class="fi-skill">'+item.skill+'</span>' +
    liveLabel +
    '<span class="fi-score">'+item.score+'</span>' +
    '<span class="'+(item.ok?'fi-ok':'fi-block')+'">'+(item.ok?'SAFE':'BLOCK')+'</span>';
  f.insertBefore(el,f.firstChild);
  if(f.children.length>5) f.removeChild(f.lastChild);
}

function updateFeed(){
  const item = FEED_DATA[fi%FEED_DATA.length]; fi++;
  pushFeedEntry(item);
}
updateFeed();
setInterval(updateFeed, 2600);

// ── LIVE METRICS (simulated — no metrics API) ──
let rCount = 48200 + Math.floor(Math.random()*400);
let sCount = 118 + Math.floor(Math.random()*10);
function updateMetrics(){
  rCount += Math.floor(Math.random()*3)+1;
  if(Math.random()>0.92) sCount++;
  document.getElementById('mRouting').textContent = rCount.toLocaleString();
  document.getElementById('mSafety').textContent = sCount;
}
updateMetrics();
setInterval(updateMetrics, 1100);
</script>
</body>
</html>"""

with open(dst_v2, 'w', encoding='utf-8') as f:
    f.write(before + new_script)

import shutil
shutil.copy2(dst_v2, dst_index)

with open(dst_v2, 'r', encoding='utf-8') as f:
    result = f.read()

print(f'osp-website-v2.html: {result.count(chr(10))+1} lines')
print(f'checkApiHealth: {"checkApiHealth" in result}')
print(f'fetchLiveRoute: {"fetchLiveRoute" in result}')
print(f'pushFeedEntry:  {"pushFeedEntry" in result}')
print(f'website/index.html copied: {os.path.exists(dst_index)}')
print('ALL DONE')
