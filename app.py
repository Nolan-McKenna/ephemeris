"""
Ephemeris Demo - Flask Backend v0.3
Connects to CelesTrak API, fetches TLE data,
propagates orbits, computes closest approach.

Changes from v0.2:
- Switched data source from Space-Track to CelesTrak
- Removed authentication requirements
- Disabled Historical mode (WIP - CelesTrak historical API pending)
"""

from flask import Flask, request, jsonify, render_template_string
import requests
from sgp4_propagate import parse_tle, propagate, propagate_at_wall_time, find_closest_approach, compute_miss_distance

app = Flask(__name__)

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"


# ─────────────────────────── HTML ───────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ephemeris — Collision Risk Intelligence</title>
<script src="https://cesium.com/downloads/cesiumjs/releases/1.111/Build/Cesium/Cesium.js"></script>
<link href="https://cesium.com/downloads/cesiumjs/releases/1.111/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
<style>
:root {
  --bg:#f5f5f3; --panel:#fff; --border:#e0e0db; --text:#1a1a18;
  --muted:#6b6b66; --accent:#1d4ed8; --accent-lt:#eff6ff;
  --warn:#dc2626; --warn-lt:#fef2f2; --ok:#16a34a; --ok-lt:#f0fdf4;
  --ylw:#d97706; --ylw-lt:#fffbeb; --r:6px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Georgia','Times New Roman',serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:var(--panel);border-bottom:1px solid var(--border);padding:0 20px;height:52px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.logo{font-size:15px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.logo span{color:var(--accent)}
.htag{font-family:monospace;font-size:11px;color:var(--muted);background:var(--bg);padding:3px 8px;border-radius:3px}
.app{display:flex;flex:1;overflow:hidden}

/* sidebar */
.sidebar{width:300px;flex-shrink:0;background:var(--panel);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto}
.sec{padding:14px 16px;border-bottom:1px solid var(--border)}
.stitle{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
label{font-size:12px;color:var(--muted);margin-bottom:2px;display:block}
input[type=text],input[type=password],input[type=email],input[type=datetime-local]{
  width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:var(--r);
  font-size:13px;font-family:monospace;background:var(--bg);color:var(--text);transition:border-color .15s}
input:focus{outline:none;border-color:var(--accent)}
.btn{padding:8px 14px;border:none;border-radius:var(--r);font-size:12px;font-weight:600;cursor:pointer;transition:opacity .15s}
.btn:hover{opacity:.85}
.btn-p{background:var(--accent);color:#fff}
.btn-sm{padding:5px 10px;font-size:11px}
.btn-o{background:transparent;border:1px solid var(--border);color:var(--text)}
.sdot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;background:#d1d5db}
.sdot.on{background:var(--ok)}.sdot.err{background:var(--warn)}
.stxt{font-size:12px;color:var(--muted)}
.srow{display:flex;gap:6px;margin-bottom:8px}
.srow input{flex:1}
.oslot{background:var(--bg);border:1px solid var(--border);border-radius:var(--r);padding:10px 12px;margin-bottom:8px}
.oslot .olbl{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.oname{font-size:13px;font-weight:600}
.ometa{font-size:11px;color:var(--muted);font-family:monospace;margin-top:2px}
.cbtn{float:right;font-size:11px;color:var(--muted);cursor:pointer;border:none;background:none;padding:0}
.cbtn:hover{color:var(--warn)}
.sres{background:var(--panel);border:1px solid var(--border);border-radius:var(--r);max-height:160px;overflow-y:auto;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:8px;display:none}
.sri{padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--border);font-size:12px;transition:background .1s}
.sri:last-child{border-bottom:none}
.sri:hover{background:var(--accent-lt)}
.srn{font-weight:600}
.srid{color:var(--muted);font-family:monospace;font-size:11px}

/* mode + duration */
.mtog{display:flex;border:1px solid var(--border);border-radius:var(--r);overflow:hidden;margin-bottom:12px}
.mbtn{flex:1;padding:7px 6px;border:none;background:transparent;font-size:12px;cursor:pointer;transition:background .15s;color:var(--muted)}
.mbtn.active{background:var(--accent);color:#fff;font-weight:600}
.mbtn:disabled{opacity:0.5; cursor:not-allowed; background:#f3f4f6;}
.dgrid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-top:6px}
.dbtn{padding:6px 4px;border:1px solid var(--border);border-radius:var(--r);font-size:11px;cursor:pointer;background:var(--bg);color:var(--muted);transition:all .1s;text-align:center}
.dbtn:hover{border-color:var(--accent);color:var(--accent)}
.dbtn.active{background:var(--accent-lt);border-color:var(--accent);color:var(--accent);font-weight:700}
.dnote{font-size:10px;color:var(--muted);margin-top:4px}

/* risk */
.rcard{border-radius:var(--r);padding:12px 14px;margin-bottom:8px}
.rok{background:var(--ok-lt);border:1px solid #bbf7d0}
.rwarn{background:var(--ylw-lt);border:1px solid #fde68a}
.rdng{background:var(--warn-lt);border:1px solid #fecaca}
.rtitle{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
.rok .rtitle{color:var(--ok)}.rwarn .rtitle{color:var(--ylw)}.rdng .rtitle{color:var(--warn)}
.rval{font-size:22px;font-weight:700;font-family:monospace}
.rlbl{font-size:11px;color:var(--muted)}
.mrow{display:flex;gap:8px}
.met{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:var(--r);padding:8px 10px;text-align:center}
.mv{font-size:16px;font-weight:700;font-family:monospace}
.ml{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}

/* analyze btn */
.abtn{width:100%;background:var(--accent);color:#fff;padding:10px;font-size:13px;border-radius:var(--r);border:none;cursor:pointer;font-weight:700;letter-spacing:.05em;text-transform:uppercase;transition:opacity .15s;margin-top:4px}
.abtn:disabled{opacity:.4;cursor:not-allowed}
.abtn:not(:disabled):hover{opacity:.88}

/* globe */
.gc{flex:1;position:relative;background:#0d1117}
#cc{width:100%;height:100%}
.gover{position:absolute;top:12px;right:12px;background:rgba(255,255,255,.93);border:1px solid var(--border);border-radius:var(--r);padding:12px 14px;font-size:12px;backdrop-filter:blur(4px);max-width:240px;display:none;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.gover.vis{display:block}
.gotitle{font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:8px}
.gr{display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;gap:8px}
.gr span:first-child{color:var(--muted);white-space:nowrap}
.gr span:last-child{font-family:monospace;font-weight:600;text-align:right}
.spin{display:inline-block;width:14px;height:14px;border:2px solid #e5e7eb;border-top-color:var(--accent);border-radius:50%;animation:sp .6s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes sp{to{transform:rotate(360deg)}}
.msg{font-size:12px;margin-top:6px;min-height:18px}
.msg.err{color:var(--warn)}
.leg{padding:12px 16px;font-size:11px}
.li{display:flex;align-items:center;gap:8px;margin-bottom:6px;color:var(--muted)}
.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.tc{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);background:rgba(255,255,255,.93);border:1px solid var(--border);border-radius:20px;padding:8px 16px;display:none;align-items:center;gap:10px;font-size:12px;backdrop-filter:blur(4px);white-space:nowrap}
.tc.vis{display:flex}
.tbtn{background:none;border:1px solid var(--border);border-radius:4px;padding:3px 8px;font-size:11px;cursor:pointer;transition:background .1s}
.tbtn:hover{background:var(--bg)}
.tbtn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
#tl{font-family:monospace;font-size:12px;color:var(--muted);min-width:90px;text-align:center}
.trail-ctrl{display:flex;align-items:center;gap:8px;padding:6px 16px;font-size:11px;color:var(--muted);border-bottom:1px solid var(--border);background:var(--panel)}
.trail-ctrl label{white-space:nowrap;font-size:11px}
.trail-ctrl input[type=range]{flex:1;accent-color:var(--accent)}
#trailVal{font-family:monospace;font-size:11px;min-width:48px;text-align:right;color:var(--text)}
</style>
</head>
<body>
<header>
  <div class="logo">EPHEMERIS</div>
  <div class="htag">Conjunction Risk Intelligence &middot; Demo v0.3 (CelesTrak)</div>
</header>
<div class="app">
  <div class="sidebar">

    <div class="sec">
      <div class="stitle">Data Source</div>
      <div><span class="sdot on"></span><span class="stxt">Connected to CelesTrak API</span></div>
    </div>

    <div class="sec">
      <div class="stitle">Object 1</div>
      <div id="slot1" class="oslot" style="display:none"></div>
      <div class="srow">
        <input type="text" id="s1" placeholder="Name or NORAD ID…" onkeydown="if(event.key==='Enter')doSearch(1)">
        <button class="btn btn-o btn-sm" onclick="doSearch(1)">Search</button>
      </div>
      <div class="sres" id="res1"></div>
      <div class="msg" id="m1"></div>
    </div>

    <div class="sec">
      <div class="stitle">Object 2</div>
      <div id="slot2" class="oslot" style="display:none"></div>
      <div class="srow">
        <input type="text" id="s2" placeholder="Name or NORAD ID…" onkeydown="if(event.key==='Enter')doSearch(2)">
        <button class="btn btn-o btn-sm" onclick="doSearch(2)">Search</button>
      </div>
      <div class="sres" id="res2"></div>
      <div class="msg" id="m2"></div>
    </div>

    <div class="sec">
      <div class="stitle">Analysis Options</div>

      <div class="mtog">
        <button class="mbtn active" id="mNow" onclick="setMode('now')">Now / Future</button>
        <button class="mbtn" id="mHist" onclick="setMode('historical')" disabled title="Historical data fetch is WIP for CelesTrak">Historical (WIP)</button>
      </div>

      <div id="histOpts" style="display:none;margin-bottom:10px">
        <div class="msg err" style="margin-bottom:8px">Historical mode is a work in progress (requires CelesTrak supplementary data integration).</div>
        <label style="margin-bottom:4px">Start (UTC)</label>
        <input type="datetime-local" id="histStart" style="margin-bottom:8px" disabled>
        <label style="margin-bottom:4px">End (UTC)</label>
        <input type="datetime-local" id="histEnd" disabled>
      </div>

      <div id="fwdOpts">
        <label>Look-ahead window</label>
        <div class="dgrid">
          <button class="dbtn active" data-mins="90"    onclick="setDur(this)">90 min</button>
          <button class="dbtn"        data-mins="360"   onclick="setDur(this)">6 hr</button>
          <button class="dbtn"        data-mins="1440"  onclick="setDur(this)">1 day</button>
          <button class="dbtn"        data-mins="4320"  onclick="setDur(this)">3 days</button>
          <button class="dbtn"        data-mins="10080" onclick="setDur(this)">7 days</button>
          <button class="dbtn"        data-mins="20160" onclick="setDur(this)">14 days</button>
        </div>
        <div class="dnote" id="durnote">Scanning 90 min ahead</div>
      </div>

      <button class="abtn" id="abtn" disabled onclick="runAnalysis()">Analyze Conjunction</button>
      <div class="msg" id="amsg"></div>
    </div>

    <div class="sec" id="riskSec" style="display:none">
      <div class="stitle">Conjunction Assessment</div>
      <div id="rcard"></div>
      <div class="mrow" style="margin-top:8px">
        <div class="met"><div class="mv" id="mdist">—</div><div class="ml">Miss Dist (km)</div></div>
        <div class="met"><div class="mv" id="mtca">—</div><div class="ml">TCA</div></div>
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px" id="modeLabel"></div>
    </div>

    <div class="leg">
      <div class="stitle" style="margin-bottom:8px">Legend</div>
      <div class="li"><div class="dot" style="background:#3b82f6"></div>Object 1 orbit</div>
      <div class="li"><div class="dot" style="background:#ef4444"></div>Object 2 orbit</div>
      <div class="li"><div class="dot" style="background:#f59e0b"></div>Closest approach</div>
    </div>

  </div><div class="gc">
    <div id="cc"></div>

    <div class="gover" id="gover">
      <div class="gotitle">Closest Approach Summary</div>
      <div class="gr"><span>Object 1</span><span id="gn1">—</span></div>
      <div class="gr"><span>Object 2</span><span id="gn2">—</span></div>
      <div class="gr"><span>Miss distance</span><span id="gdist">—</span></div>
      <div class="gr"><span>TCA offset</span><span id="gtca">—</span></div>
      <div class="gr"><span>Mode</span><span id="gmode">—</span></div>
      <div class="gr"><span>Risk level</span><span id="grisk" style="font-weight:700">—</span></div>
    </div>

    <div class="tc" id="tc">
      <span style="font-size:11px;color:#6b7280">Playback:</span>
  <button class="tbtn" id="bp" onclick="setSpeed(0)">&#9646;&#9646;</button>
  <button class="tbtn" id="b1" onclick="setSpeed(1)">1&times;</button>
  <button class="tbtn" id="b10" onclick="setSpeed(10)">10&times;</button>
    <button class="tbtn" id="b10" onclick="setSpeed(60)">60&times;</button>

  
  <input type="range" id="timeSlider" min="0" max="100" value="0" step="0.1" style="width:180px; accent-color:var(--accent);">
  
  <button class="tbtn" onclick="jumpToTCA()" style="color:var(--ylw); font-weight:700; border-color:var(--ylw)">Jump to TCA</button>
  
  <span id="tl">T+0</span>
      
      <span style="font-size:11px;color:#6b7280;margin-left:8px">Trail:</span>
      <input type="range" id="trailSlider" min="10" max="360" value="60" step="10"
        style="width:80px;accent-color:#1d4ed8" oninput="updateTrail(this.value)">
      <span id="trailVal" style="font-family:monospace;font-size:11px;min-width:44px">±60 min</span>
    </div>
</div>

<script>
// ── STATE ──
const objs = {1:null, 2:null};
let result = null, viewer = null, raf = null;
let tOff = 0, speed = 0, lastTs = null;
let oEnt = [], sEnt = [], tcaEnt = null;
let satState = [{idx:0},{idx:0}];
let mode = 'now', durMins = 90;
let trailWindowMins = 60;

let isDragging = false;

// We use a small delay to ensure the DOM is ready before attaching listeners
window.addEventListener('DOMContentLoaded', () => {
  const timeSlider = document.getElementById('timeSlider');
  if (timeSlider) {
    timeSlider.addEventListener('mousedown', () => { isDragging = true; });
    timeSlider.addEventListener('mouseup', () => { isDragging = false; });
    
    timeSlider.addEventListener('input', (e) => {
      if (result) {
        const frac = e.target.value / 100;
        tOff = frac * result.duration_minutes;
        updateFrames(); // Force a visual update immediately while scrubbing
      }
    });
  }
});

function updateTrail(val) {
  trailWindowMins = parseFloat(val);
  document.getElementById('trailVal').textContent = `±${val} min`;
}

function jumpToTCA() {
  if (!result) return;

  // Stop playback so the user can inspect the moment
  setSpeed(0);

  // result.tca_minutes is the offset from 'Now'
  const tcaRelative = result.tca_minutes;
  const totalDur = result.duration_minutes;

  // Update the global time offset
  tOff = tcaRelative;

  // Synchronize the slider UI
  const slider = document.getElementById('timeSlider');
  if (slider) {
    slider.value = (tcaRelative / totalDur) * 100;
  }

  // Force the satellites to move to the new position immediately
  updateFrames();
}

// ── CESIUM ──
Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYWE1OWUxNy1mMWZiLTQzYjYtYTQ0OS1kMWFjYmFkNjc4YjMiLCJpZCI6NTQ4NDQsImlhdCI6MTYyNTAzMjQ1NH0.X0Wy5FPLJzTt0B6xsMaTJPr5o2E_DkMmF0j4dNIEv5Q';

window.addEventListener('load', () => {
  try {
    viewer = new Cesium.Viewer('cc', {
      animation:false, baseLayerPicker:false, fullscreenButton:false,
      geocoder:false, homeButton:false, infoBox:false,
      sceneModePicker:false, selectionIndicator:false,
      timeline:false, navigationHelpButton:false,
    });
    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.addImageryProvider(
      new Cesium.OpenStreetMapImageryProvider({ url:'https://tile.openstreetmap.org/' })
    );
    viewer.scene.globe.enableLighting = false;
  } catch(e) { console.warn('Cesium init:', e); }
});

// ── MODE ──
function setMode(m) {
  mode = m;
  document.getElementById('mNow').classList.toggle('active', m==='now');
  document.getElementById('mHist').classList.toggle('active', m==='historical');
  document.getElementById('histOpts').style.display = m==='historical' ? 'block' : 'none';
  document.getElementById('fwdOpts').style.display  = m==='now'        ? 'block' : 'none';
}

// ── DURATION ──
function setDur(btn) {
  document.querySelectorAll('.dbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  durMins = parseInt(btn.dataset.mins);
  const h = btn.textContent;
  document.getElementById('durnote').textContent = `Scanning ${h} ahead`;
}

// ── SEARCH ──
async function doSearch(slot) {
  const q = document.getElementById(`s${slot}`).value.trim();
  if (!q) return;
  setMsg(slot,'<span class="spin"></span>Searching…',false);
  document.getElementById(`res${slot}`).style.display='none';
  try {
    const d = await post('/api/search', {query:q});
    if (d.error) { setMsg(slot,d.error,true); return; }
    if (!d.results?.length) { setMsg(slot,'No results',true); return; }
    setMsg(slot,'',false);
    const el = document.getElementById(`res${slot}`);
    el.innerHTML = d.results.map(o=>
      `<div class="sri" onclick='pick(${slot},${JSON.stringify(o)})'>
        <div class="srn">${o.name}</div>
        <div class="srid">NORAD ${o.norad_id} · ${o.obj_type||'PAYLOAD'}</div>
      </div>`
    ).join('');
    el.style.display='block';
  } catch(e) { setMsg(slot,'Search failed',true); }
}

function setMsg(slot,html,err) {
  const el=document.getElementById(`m${slot}`);
  el.innerHTML=html; el.className='msg'+(err?' err':'');
}

async function pick(slot, obj) {
  document.getElementById(`res${slot}`).style.display='none';
  setMsg(slot,'<span class="spin"></span>Fetching TLE…',false);
  try {
    const d = await post('/api/tle', {norad_id:obj.norad_id});
    if (d.error) { setMsg(slot,d.error,true); return; }
    objs[slot] = {...obj, tle1:d.tle1, tle2:d.tle2, epoch:d.epoch, epoch_age_days:d.epoch_age_days};
    if (d.stale_warning) {
      setMsg(slot, '⚠️ ' + d.stale_warning, true);
    } else {
      setMsg(slot,'',false);
    }
    renderSlot(slot);
    chkReady();
  } catch(e) { setMsg(slot,'TLE fetch failed',true); }
}

function renderSlot(slot) {
  const o=objs[slot], el=document.getElementById(`slot${slot}`);
  el.style.display='block';
  const age = o.epoch_age_days;
  const ageColor = age > 30 ? 'var(--warn)' : age > 7 ? 'var(--ylw)' : 'var(--ok)';
  const ageText = age != null ? `· TLE age: <span style="color:${ageColor};font-weight:600">${age}d</span>` : '';
  el.innerHTML=`<div class="olbl">Object ${slot}
    <button class="cbtn" onclick="clearSlot(${slot})">&#10005;</button></div>
    <div class="oname">${o.name}</div>
    <div class="ometa">NORAD ${o.norad_id} ${ageText}</div>`;
}

function clearSlot(slot) {
  objs[slot]=null;
  document.getElementById(`slot${slot}`).style.display='none';
  document.getElementById(`s${slot}`).value='';
  chkReady(); resetGlobe();
}

function chkReady() {
  document.getElementById('abtn').disabled=!(objs[1]&&objs[2]);
}

// ── ANALYSIS ──
async function runAnalysis() {
  const btn=document.getElementById('abtn'), msg=document.getElementById('amsg');
  btn.disabled=true;
  msg.innerHTML='<span class="spin"></span>Computing conjunction…';
  msg.className='msg';

  const payload={obj1:objs[1], obj2:objs[2], mode, duration_minutes:durMins};

  try {
    const d = await post('/api/analyze', payload);
    if (d.error) { msg.textContent=d.error; msg.className='msg err'; btn.disabled=false; return; }
    result=d; msg.textContent=''; btn.disabled=false;
    showRisk(d); renderGlobe(d);
  } catch(e) { msg.textContent='Analysis failed: '+e.message; msg.className='msg err'; btn.disabled=false; }
}

function fmtTCA(m) {
  if (m<60)   return m.toFixed(1)+' min';
  if (m<1440) return (m/60).toFixed(2)+' hrs';
  return (m/1440).toFixed(2)+' days';
}

function showRisk(d) {
  const dist=d.miss_distance_km, tca=d.tca_minutes, totalDur = d.duration_minutes;
  let lvl,cls;
  if (dist<1)  {lvl='CRITICAL RISK';cls='rdng';}
  else if (dist<5)  {lvl='HIGH RISK';cls='rdng';}
  else if (dist<20) {lvl='ELEVATED RISK';cls='rwarn';}
  else              {lvl='NOMINAL';cls='rok';}

  document.getElementById('riskSec').style.display='block';
  document.getElementById('rcard').innerHTML=
    `<div class="rcard ${cls}"><div class="rtitle">${lvl}</div>
     <div class="rval">${dist.toFixed(2)} km</div>
     <div class="rlbl">Predicted minimum miss distance</div></div>`;
  document.getElementById('mdist').textContent=dist.toFixed(2);
  document.getElementById('mtca').textContent=fmtTCA(tca);
  document.getElementById('modeLabel').textContent=
    d.mode==='historical'
      ? `Historical · epoch ${d.epoch_used||'closest available'}`
      : `Forward · ${fmtTCA(d.duration_minutes)} window`;


  // overlay
  document.getElementById('gn1').textContent=objs[1].name;
  document.getElementById('gn2').textContent=objs[2].name;
  document.getElementById('gdist').textContent=dist.toFixed(2)+' km';
  document.getElementById('gtca').textContent='T+'+fmtTCA(tca);
  document.getElementById('gmode').textContent=d.mode==='historical'?'Historical':'Forward';
  const re=document.getElementById('grisk');
  re.textContent=lvl;
  re.style.color=dist<5?'#dc2626':dist<20?'#d97706':'#16a34a';
  document.getElementById('gover').classList.add('vis');
}

// ── GLOBE ──
function resetGlobe() {
  if (!viewer) return;
  const dot = document.getElementById('tcaDot');
  if (dot) dot.style.display = 'none'; 
  
  oEnt.forEach(e=>viewer.entities.remove(e));
  sEnt.forEach(e=>viewer.entities.remove(e));
  if (tcaEnt) viewer.entities.remove(tcaEnt);
  oEnt=[]; sEnt=[]; tcaEnt=null;
  satState=[{idx:0},{idx:0}];
  if (raf) cancelAnimationFrame(raf);
  document.getElementById('gover').classList.remove('vis');
  document.getElementById('tc').classList.remove('vis');
  result=null;
}

function renderGlobe(d) {
  if (!viewer) return;
  resetGlobe();
  result = d;

  const cols = [
    Cesium.Color.fromCssColorString('#3b82f6'),
    Cesium.Color.fromCssColorString('#ef4444')
  ];

  const FADE_BANDS = 10;

  [d.orbit1, d.orbit2].forEach((orb, oi) => {
    const col = cols[oi];
    const nPts = orb.length;
    const dur = d.duration_minutes;

    // Pre-calculate Cartesian points for the base orbit
    const cartArr = orb.map(p => Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.alt * 1000));

    // Helper to get an interpolated position at any fractional index
    const getInterpolatedPos = (rawIdx) => {
      const i0 = Math.floor(rawIdx);
      const i1 = Math.min(i0 + 1, nPts - 1);
      const f = rawIdx - i0;
      const p0 = orb[i0];
      const p1 = orb[i1];
      const lat = p0.lat + (p1.lat - p0.lat) * f;
      const lon = p0.lon + (p1.lon - p0.lon) * f;
      const alt = p0.alt + (p1.alt - p0.alt) * f;
      return Cesium.Cartesian3.fromDegrees(lon, lat, alt * 1000);
    };

    const getTrailPts = (fLo, fHi) => {
      const iLo = Math.floor(fLo * (nPts - 1));
      const iHi = Math.floor(fHi * (nPts - 1));
      
      // Get the segment of pre-calculated points
      let pts = cartArr.slice(iLo + 1, iHi);

      // ADD INTERPOLATED HEAD AND TAIL for smooth rendering
      const headPos = getInterpolatedPos(fHi * (nPts - 1));
      const tailPos = getInterpolatedPos(fLo * (nPts - 1));
      
      pts.unshift(tailPos);
      pts.push(headPos);

      // Anti-meridian (Date Line) jump protection
      for (let k = 1; k < pts.length; k++) {
        // We check the original 'orb' data for longitude jumps
        const idx = iLo + k;
        if (orb[idx] && orb[idx-1] && Math.abs(orb[idx].lon - orb[idx-1].lon) > 180) {
            return [headPos, headPos]; // Collapse trail segment if it crosses the date line
        }
      }
      return pts;
    };

    for (let b = 0; b < FADE_BANDS; b++) {
      const bf0 = b / FADE_BANDS;
      const bf1 = (b + 1) / FADE_BANDS;
      const alpha = 0.1 + 0.8 * (b / (FADE_BANDS - 1));

      oEnt.push(viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => {
            if (!result) return [cartArr[0], cartArr[0]];
            
            const wf = Math.min(trailWindowMins / dur, 1);
            const cf = tOff / dur;

            // Define the window for this specific fade band
            const fLo = Math.max(0, cf - wf + (bf0 * wf));
            const fHi = Math.max(0, cf - wf + (bf1 * wf));

            return getTrailPts(fLo, fHi);
          }, false),
          width: 3.0, // Slightly thicker for smoother appearance
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.15,
            color: col.withAlpha(alpha)
          })
        }
      }));
    }
  });

  // TCA Marker
  const p1 = d.tca_positions.obj1, p2 = d.tca_positions.obj2;
  const ml = (p1.lat + p2.lat) / 2, mn = (p1.lon + p2.lon) / 2, ma = (p1.alt + p2.alt) / 2;
  tcaEnt = viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(mn, ml, ma * 1000),
    point: { pixelSize: 12, color: Cesium.Color.YELLOW, outlineColor: Cesium.Color.BLACK, outlineWidth: 1.5 },
    label: {
      text: `TCA: ${d.miss_distance_km.toFixed(1)} km`,
      font: '12px monospace', fillColor: Cesium.Color.YELLOW,
      outlineColor: Cesium.Color.BLACK, outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      pixelOffset: new Cesium.Cartesian2(0, -22)
    }
  });

  satState[0].idx = 0;
  satState[1].idx = 0;

  const makeSat = (orbIdx, col, name) => viewer.entities.add({
    position: new Cesium.CallbackProperty(() => {
      const orb = orbIdx === 0 ? result?.orbit1 : result?.orbit2;
      if (!orb) return Cesium.Cartesian3.fromDegrees(0, 0, 0);
      
      const rawIdx = satState[orbIdx].idx;
      const i0 = Math.floor(rawIdx);
      const i1 = Math.min(i0 + 1, orb.length - 1);
      const f = rawIdx - i0;

      const p0 = orb[i0];
      const p1 = orb[i1];

      const lat = p0.lat + (p1.lat - p0.lat) * f;
      const lon = p0.lon + (p1.lon - p0.lon) * f;
      const alt = p0.alt + (p1.alt - p0.alt) * f;

      return Cesium.Cartesian3.fromDegrees(lon, lat, alt * 1000);
    }, false),
    point: { pixelSize: 9, color: col, outlineColor: Cesium.Color.WHITE, outlineWidth: 1.5 },
    label: {
      text: name, font: '11px sans-serif', fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK, outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      pixelOffset: new Cesium.Cartesian2(0, -18)
    }
  });
  
  sEnt = [makeSat(0, cols[0], objs[1].name), makeSat(1, cols[1], objs[2].name)];

  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(mn, ml, 10000000), duration: 2
  });

  // Initialize and start animation
  tOff = 0;
  lastTs = null;
  
  // SAFE CHECK: Show the controls container
  const tcEl = document.getElementById('tc');
  if (tcEl) tcEl.classList.add('vis');

  setSpeed(1);
  animate();
}

function animate() {
  raf = requestAnimationFrame(ts => {
    if (lastTs !== null && speed !== 0 && !isDragging) {
      const deltaMins = ((ts - lastTs) / 60000) * speed;
      tOff += deltaMins;
      
      const dur = result?.duration_minutes || 90;
      if (tOff > dur) tOff = 0; 
      
      // SAFE CHECK: Update slider only if it exists
      const slider = document.getElementById('timeSlider');
      if (slider) {
        slider.value = (tOff / dur) * 100;
      }
    }
    
    lastTs = ts;
    updateFrames(); 
    animate();
  });
}

function updateFrames() {
  if (!result) return;
  
  const dur = result.duration_minutes || 90;
  const frac = Math.max(0, Math.min(tOff / dur, 1));
  const rawIdx = frac * (result.orbit1.length - 1);
  
  satState[0].idx = rawIdx;
  satState[1].idx = rawIdx;

  // SAFE CHECK: Update text label only if it exists
  const label = document.getElementById('tl');
  if (label) {
    label.textContent = 'T+' + fmtTCA(tOff);
  }
}

function setSpeed(s) {
  speed = s;
  // List all possible speed button IDs
  const buttonIds = ['p', '1', '10', '60'];
  
  buttonIds.forEach(id => {
    const btn = document.getElementById('b' + id);
    if (btn) { // <--- Add this check
      btn.classList.remove('active');
    }
  });

  const idMap = {0: 'p', 1: '1', 10: '10', 60: '60'};
  const activeBtn = document.getElementById('b' + idMap[s]);
  if (activeBtn) { // <--- Add this check
    activeBtn.classList.add('active');
  }
}

// ── UTILS ──
async function post(url,body) {
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
}
document.addEventListener('click',e=>{
  [1,2].forEach(s=>{
    if (!e.target.closest(`#res${s}`)&&!e.target.closest('.srow'))
      document.getElementById(`res${s}`).style.display='none';
  });
});
</script>
</body>
</html>"""


# ─────────────────────────── ROUTES ───────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/search', methods=['POST'])
def api_search():
    q = request.json.get('query', '').strip()
    try:
        if q.isdigit():
            url = f"{CELESTRAK_GP_URL}?CATNR={q}&FORMAT=json"
        else:
            url = f"{CELESTRAK_GP_URL}?NAME={q}&FORMAT=json"
            
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return jsonify({'error': f'CelesTrak API returned {r.status_code}'})
            
        data = r.json()
        
        # CelesTrak sometimes returns a string if nothing is found (e.g. "No GP data found")
        if not isinstance(data, list):
            return jsonify({'results': []})
            
        # Parse output and limit to 15
        return jsonify({'results': [
            {'name': i.get('OBJECT_NAME', '?'), 'norad_id': i.get('NORAD_CAT_ID', ''),
             'obj_type': i.get('OBJECT_TYPE', '')}
            for i in data[:15]
        ]})
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/tle', methods=['POST'])
def api_tle():
    norad_id = request.json.get('norad_id', '')
    try:
        # Fetch plain text TLE format instead of JSON
        url = f"{CELESTRAK_GP_URL}?CATNR={norad_id}&FORMAT=tle"
        r = requests.get(url, timeout=15)
        
        if r.status_code != 200:
            return jsonify({'error': f'CelesTrak API returned {r.status_code}'})
            
        text_data = r.text.strip()
        if not text_data or "No GP data found" in text_data:
            return jsonify({'error': f'No TLE found for NORAD {norad_id}'})
            
        # Parse the 3-line text block (Name, Line 1, Line 2)
        lines = [line.strip() for line in text_data.splitlines() if line.strip()]
        if len(lines) < 3:
            return jsonify({'error': 'Incomplete TLE data returned from CelesTrak.'})
            
        name = lines[0]
        tle1 = lines[1]
        tle2 = lines[2]

        # Extract Epoch directly from TLE Line 1 (chars 18-32)
        epoch_year_str = tle1[18:20]
        epoch_day_str = tle1[20:32]
        
        # Convert 2-digit year to 4-digit (57-99 = 1900s, 00-56 = 2000s)
        y = int(epoch_year_str)
        year = 2000 + y if y < 57 else 1900 + y
        day_of_year = float(epoch_day_str)
        
        from datetime import datetime, timedelta, timezone
        epoch_dt = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
        epoch_str = epoch_dt.isoformat()
        
        now = datetime.now(timezone.utc)
        epoch_age_days = (now - epoch_dt).days
        
        stale_warning = None
        if epoch_age_days > 30:
            stale_warning = (
                f"TLE is {epoch_age_days} days old (epoch: {epoch_dt.strftime('%Y-%m-%d')}). "
                f"This object may be decayed or no longer tracked. "
                f"Positions will be unreliable."
            )

        return jsonify({
            'tle1': tle1, 'tle2': tle2,
            'epoch': epoch_str, 'name': name,
            'epoch_age_days': epoch_age_days,
            'stale_warning': stale_warning,
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()})


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    data = request.json
    obj1 = data.get('obj1')
    obj2 = data.get('obj2')
    dur = float(data.get('duration_minutes', 90))
    
    if not obj1 or not obj2:
        return jsonify({'error': 'Missing object data'})

    try:
        # Parse the TLEs into satrec objects
        tle1 = parse_tle(obj1['tle1'], obj1['tle2'])
        tle2 = parse_tle(obj2['tle1'], obj2['tle2'])

        # 1. SYNCHRONIZE TO "NOW"
        from datetime import datetime, timezone
        from sgp4.api import jday
        
        now = datetime.now(timezone.utc)
        # Get Julian Date for the current moment
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
        now_jd = jd + fr
        
        # Calculate how many minutes have passed from Obj1's Epoch to "Now"
        now_offset = (now_jd - tle1['jd_epoch']) * 1440.0

        # 2. ANALYSIS: Scan from [Now] to [Now + duration]
        # We pass now_offset as the starting point for the scan
        tca_t, tca_dist = find_closest_approach(
            tle1, tle2, 
            start_minutes=now_offset, 
            duration_minutes=dur
        )

        # 3. GENERATE TRACKS: Start exactly at "Now"
        orbit1, orbit2 = [], []
        n_pts = 300
        for k in range(n_pts + 1):
            t_rel = (k / n_pts) * dur
            t_absolute = now_offset + t_rel # Time relative to Obj1 Epoch
            
            la1, lo1, al1, *_ = propagate(tle1, t_absolute)
            la2, lo2, al2, *_ = propagate_at_wall_time(tle2, tle1, t_absolute)
            
            orbit1.append({'lat': la1, 'lon': lo1, 'alt': al1})
            orbit2.append({'lat': la2, 'lon': lo2, 'alt': al2})

        # 4. TCA POSITIONS: Fixed to the exact moment of closest approach
        la1t, lo1t, al1t, *_ = propagate(tle1, tca_t)
        la2t, lo2t, al2t, *_ = propagate_at_wall_time(tle2, tle1, tca_t)

        # 5. METADATA: Define the variables you wanted to keep
        period1 = 1440.0 / tle1['mean_motion']
        period2 = 1440.0 / tle2['mean_motion']
        tle1_epoch_iso = obj1.get('epoch', 'N/A')

        return jsonify({
            'status': 'success',
            'miss_distance_km': round(tca_dist, 3),
            'tca_minutes': round(tca_t - now_offset, 2),
            'duration_minutes': dur,
            'period1_minutes': round(period1, 2),
            'period2_minutes': round(period2, 2),
            'tle1_epoch': tle1_epoch_iso,
            'orbit1': orbit1,
            'orbit2': orbit2,
            'tca_positions': {
                'obj1': {'lat': la1t, 'lon': lo1t, 'alt': al1t},
                'obj2': {'lat': la2t, 'lon': lo2t, 'alt': al2t}
            }
        })

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()})


if __name__ == '__main__':
    print("\n🛰  Ephemeris Demo Server v0.3 (CelesTrak)")
    print("=" * 40)
    print("Open: http://localhost:5050")
    print("=" * 40)
    app.run(debug=False, port=5050, host='0.0.0.0')