'use strict';
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const view = $('#view');
  const S = { page: 'home', env: null, hw: null, hello: null, ollama: null, runs: [], cfg: null, running: false, progress: null, frame: null, log: [],
              selected: null, detail: null, batch: null, installLog: [], installing: false, err: '' };
  const call = async (cmd, payload) => { const r = await window.opai.rpc(cmd, payload); if (!r.ok) throw new Error(r.error); return r.result; };

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === 'class') el.className = v; else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (v === true) el.setAttribute(k, ''); else if (v !== false && v != null) el.setAttribute(k, v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return el;
  }
  const pc = (x) => (x == null ? 'n/a' : (x * 100).toFixed(1) + '%');
  const fmt = (x, d = 0) => (x == null ? 'n/a' : Number(x).toFixed(d));
  const ms = (x) => (x == null ? 'n/a' : x < 10 ? Number(x).toFixed(2) : Number(x).toFixed(0));
  const ICON = {
    home: 'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10', run: 'M6 4l14 8-14 8z', results: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
    compare: 'M7 4v16M17 4v16M3 8h8M13 16h8', models: 'M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5',
    settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1-2-4-2 1a7 7 0 0 0-2-1l-.5-2h-4L10 7a7 7 0 0 0-2 1L6 7 4 11l2 1a7 7 0 0 0 0 2l-2 1 2 4 2-1a7 7 0 0 0 2 1l.5 2h4l.5-2a7 7 0 0 0 2-1l2 1 2-4-2-1a7 7 0 0 0 0-2z',
  };
  const icon = (k) => { const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); s.setAttribute('viewBox', '0 0 24 24'); const p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.setAttribute('d', ICON[k]); s.append(p); return s; };
  const PAGES = [['home', 'Home'], ['run', 'New Run'], ['results', 'Results'], ['compare', 'Experiments'], ['models', 'Models'], ['settings', 'Settings']];
  function renderNav() { const n = $('#nav'); n.textContent = ''; for (const [id, l] of PAGES) n.append(h('button', { class: S.page === id ? 'active' : '', onclick: () => go(id) }, icon(id), l)); }
  function go(p) { S.page = p; S.err = ''; renderNav(); render(); if (p === 'models') loadOllama(); }

  // ---------- controls ----------
  const lbl = (label, hint) => h('div', null, h('div', { class: 'lbl' }, label), hint ? h('div', { class: 'hint' }, hint) : null);
  function selectRow(label, key, opts, hint) {
    return h('div', { class: 'row' }, lbl(label, hint), h('select', { onchange: (e) => { S.cfg[key] = e.target.value; render(); } }, opts.map((o) => h('option', { value: o.v, selected: S.cfg[key] === o.v }, o.l))));
  }
  function segRow(label, key, opts, hint) {
    const seg = h('div', { class: 'seg' }); for (const o of opts) seg.append(h('button', { class: S.cfg[key] === o.v ? 'on' : '', onclick: () => { S.cfg[key] = o.v; render(); } }, o.l));
    return h('div', { class: 'row' }, lbl(label, hint), seg);
  }
  function numRow(label, key, min, max, hint) {
    return h('div', { class: 'row' }, lbl(label, hint), h('input', { type: 'number', min, max, value: S.cfg[key], onchange: (e) => { S.cfg[key] = Math.max(min, Math.min(max, parseFloat(e.target.value) || 0)); } }));
  }
  const card = (k, v, s) => h('div', { class: 'card' }, h('div', { class: 'k' }, k), h('div', { class: 'v' }, v), s ? h('div', { class: 's' }, s) : null);
  const pill = (ok, a, b) => h('span', { class: 'pill ' + (ok ? 'pass' : 'fail') }, ok ? a : b);

  // ---------- data ----------
  async function refreshRuns() { try { S.runs = await call('list_runs'); } catch (e) { S.err = e.message; } }
  async function loadOllama() { try { S.ollama = await call('ollama', {}); } catch (e) { S.ollama = { ok: false, error: e.message, models: [] }; } if (S.page === 'models' || S.page === 'run') render(); }
  async function bootSidecar() {
    try {
      S.hello = await call('hello'); S.hw = await call('hardware'); await refreshRuns(); loadOllama();
    } catch (e) { S.err = 'Could not start the simulation engine: ' + e.message; }
    render();
  }

  // ---------- pages ----------
  function pageHome() {
    const env = S.env;
    const kids = [h('h1', { class: 'large' }, 'OpenPhysicalAI Lab'),
      h('p', { class: 'sub' }, 'Real MuJoCo physics, real perception, real planners. Measures task success, recovery, latency and resource use under an explicit budget.')];
    if (!env || !env.ok) {
      kids.push(h('div', { class: 'banner' }, h('b', null, 'Setup needed. '), env ? env.message : 'Checking Python environment...'));
      if (env && env.reason !== 'no_python') {
        kids.push(h('div', { class: 'actions' }, h('button', { class: 'btn', disabled: S.installing, onclick: installEnv }, S.installing ? 'Installing...' : 'Install dependencies')));
        kids.push(h('p', { class: 'sub', style: 'margin-top:10px' }, 'Creates a private Python environment in the app data folder and installs mujoco, numpy and psutil (about 300 MB).'));
      }
      if (S.installLog.length) kids.push(h('div', { class: 'log', id: 'ilog', style: 'height:220px;margin-top:12px' }, S.installLog.join('\n')));
      return h('div', { class: 'wrap' }, kids);
    }
    const hw = S.hw, g = hw && hw.gpu, last = S.runs[0];
    kids.push(S.err ? h('div', { class: 'err' }, S.err) : null,
      h('div', { class: 'cards' },
        card('Hardware class', hw ? hw.hardware_class : '...', g ? `${g.name}, ${g.total_gb.toFixed(1)} GB` : 'no NVIDIA GPU detected (CPU only)'),
        card('RAM', hw ? hw.ram_total_gb + ' GB' : '...', hw ? hw.ram_free_gb + ' GB free' : ''),
        card('Ollama', S.ollama ? (S.ollama.ok ? S.ollama.models.length + ' models' : 'not running') : '...', 'local LLM planners'),
        card('Runs saved', String(S.runs.length), last ? `last: ${last.task}, TSR ${pc(last.tsr)}` : 'none yet')),
      h('h3', { class: 'section' }, 'Start here'),
      h('div', { class: 'group' },
        h('div', { class: 'row' }, lbl('Smoke test', 'Pick & Place, rule-based planner, 20 episodes, no model needed'),
          h('button', { class: 'btn', onclick: () => { Object.assign(S.cfg, { task: 'pick_place', policy: 'rule', agent: 'recovery', perception: 'oracle', perturb: 'moderate', episodes: 20 }); go('run'); } }, 'Configure')),
        h('div', { class: 'row' }, lbl('Compare closed-loop vs open-loop', 'Runs three agents on the same seeds'), h('button', { class: 'btn gray', onclick: () => go('compare') }, 'Open')),
        h('div', { class: 'row' }, lbl('Use a local LLM as planner', 'Needs Ollama running with a model pulled'), h('button', { class: 'btn gray', onclick: () => go('models') }, 'Check'))));
    return h('div', { class: 'wrap' }, kids);
  }

  async function installEnv() {
    S.installing = true; S.installLog = []; render();
    const r = await window.opai.envInstall();
    S.installing = false; S.env = await window.opai.envStatus();
    if (!r.ok) S.installLog.push('FAILED: ' + r.error); else await bootSidecar();
    render();
  }

  function policyOptions() {
    const o = [{ v: 'rule', l: 'Rule-based planner (no model)' }];
    if (S.ollama && S.ollama.ok) for (const m of S.ollama.models) o.push({ v: 'ollama:' + m.name, l: `Ollama: ${m.name} (${m.size_gb} GB)` });
    if (!o.find((x) => x.v === S.cfg.policy)) o.push({ v: S.cfg.policy, l: S.cfg.policy });
    return o;
  }
  function taskOptions() { return Object.entries((S.hello && S.hello.tasks) || { pick_place: 'Pick & Place' }).map(([v, l]) => ({ v, l })); }
  const budgetOptions = () => Object.keys((S.hello && S.hello.budgets) || { standard: {} }).map((k) => ({ v: k, l: `${k} (plan p95 <= ${S.hello ? S.hello.budgets[k].planning_ms_p95 : '?'} ms)` }));

  function configGroups() {
    return [
      h('h3', { class: 'section' }, 'Task and policy'),
      h('div', { class: 'group' }, selectRow('Task', 'task', taskOptions()), selectRow('Planner', 'policy', policyOptions(), 'Planner track: never ranked against learned policies'), selectRow('Budget profile', 'budget', budgetOptions(), 'Provisional until Phase 0 measurement on your machine')),
      h('h3', { class: 'section' }, 'Agent, perception, verifier'),
      h('div', { class: 'group' },
        segRow('Agent', 'agent', [{ v: 'open_loop', l: 'Open-loop' }, { v: 'closed_loop', l: 'Closed-loop' }, { v: 'recovery', l: 'Recovery' }], 'Recovery: detect, diagnose, re-observe, replan'),
        segRow('Perception', 'perception', [{ v: 'oracle', l: 'Oracle' }, { v: 'vision', l: 'Vision' }], 'Vision = colour segmentation on a top-down camera frame'),
        segRow('Verifier', 'verifier', [{ v: 'V0', l: 'V0 oracle' }, { v: 'V1', l: 'V1 proprio' }, { v: 'V2', l: 'V2 + camera' }], 'V0 uses simulator truth: upper bound only')),
      h('h3', { class: 'section' }, 'Timing and failures'),
      h('div', { class: 'group' },
        segRow('Mode', 'mode', [{ v: 'sync', l: 'Sync' }, { v: 'realtime', l: 'Real-time' }], 'Real-time: world advances by the planner latency before it acts'),
        segRow('Perturbation', 'perturb', [{ v: 'clean', l: 'Clean' }, { v: 'mild', l: 'Mild' }, { v: 'moderate', l: 'Moderate' }, { v: 'severe', l: 'Severe' }], 'Slip, displaced object, wrong placement, perception noise'),
        numRow('Extra latency (ms)', 'extra_latency_ms', 0, 60000, 'Explicit synthetic delay added to every plan, for latency sweeps')),
      h('h3', { class: 'section' }, 'Protocol'),
      h('div', { class: 'group' }, numRow('Episodes', 'episodes', 1, 2000, 'Never report a single run'), numRow('First seed', 'seed', 0, 999999, 'Seeds are shared across compared configs'))];
  }

  function pageRun() {
    const p = S.progress, pct = p ? (p.done / p.total) * 100 : 0;
    const side = h('div', { class: 'live' }, S.frame ? h('img', { id: 'live', src: 'data:image/png;base64,' + S.frame.png }) : h('div', { class: 'empty' }, 'Live view appears here during a run'),
      h('small', { id: 'liveinfo' }, S.frame ? `sim time ${S.frame.sim_time} s` : ''));
    return h('div', { class: 'wrap', style: 'max-width:1160px' },
      h('h1', { class: 'large' }, 'New Run'),
      h('p', { class: 'sub' }, 'Runs real MuJoCo episodes with real-time 3D GPU physics rendering (RTX 3050 accelerated).'),
      S.err ? h('div', { class: 'err' }, S.err) : null,
      h('div', { class: 'runrow' }, h('div', null, ...configGroups(),
        h('div', { class: 'actions' }, h('button', { class: 'btn', disabled: S.running, onclick: () => startRuns([{ ...S.cfg }]) }, S.running ? 'Running...' : 'Start run'),
          S.running ? h('button', { class: 'btn danger', onclick: () => { S.batch = null; call('cancel'); } }, 'Cancel') : null)),
        h('div', { style: 'position:sticky;top:0' }, side,
          S.running || p ? h('div', { class: 'card', style: 'margin-top:12px' }, h('div', { class: 'k', id: 'ptxt' }, p ? `Episode ${p.done} of ${p.total}, ${p.successes} successes` : 'Starting...'),
            h('div', { class: 'bar', style: 'margin:10px 0' }, h('i', { id: 'pbar', style: `width:${pct}%` })), h('div', { class: 'log', id: 'log', style: 'height:100px' }, S.log.join('\n'))) : null)));
  }

  // ---- batch runner: sequential runs through the single sidecar ----
  async function startRuns(cfgs, title) {
    if (S.running) return;
    S.batch = { cfgs, i: 0, results: [], title: title || '' }; S.err = ''; S.log = []; S.frame = null;
    nextBatch();
  }
  async function nextBatch() {
    const b = S.batch; if (!b) return;
    if (b.i >= b.cfgs.length) { S.running = false; S.progress = null; await refreshRuns(); if (b.cfgs.length === 1) { S.selected = b.results[0]; await openDetail(S.selected); go('results'); } else { S.batchDone = b; S.batch = null; go('compare'); } return; }
    S.running = true; S.progress = null; S.log.push(`run ${b.i + 1} of ${b.cfgs.length}: ${b.cfgs[b.i].task}, ${b.cfgs[b.i].agent}, ${b.cfgs[b.i].perception}, ${b.cfgs[b.i].mode}`);
    render();
    try { await call('run', { config: { ...b.cfgs[b.i], frames: S.page === 'run' } }); } catch (e) { S.err = e.message; S.running = false; S.batch = null; render(); }
  }

  window.opai.onEvent(async (ev) => {
    if (ev.event === 'env_log') { S.installLog.push(ev.line); const l = $('#ilog'); if (l) { l.textContent = S.installLog.join('\n'); l.scrollTop = l.scrollHeight; } else if (S.page === 'home') render(); return; }
    if (ev.event === 'frame') { S.frame = ev; const im = $('#live'); if (im) { im.src = 'data:image/png;base64,' + ev.png; const t = $('#liveinfo'); if (t) t.textContent = `sim time ${ev.sim_time} s`; } else if (S.page === 'run') render(); return; }
    if (ev.event === 'progress') { S.progress = ev; const t = $('#ptxt'); if (t) { t.textContent = `Episode ${ev.done} of ${ev.total}, ${ev.successes} successes`; $('#pbar').style.width = (ev.done / ev.total) * 100 + '%'; } return; }
    if (ev.event === 'log') { S.log.push(ev.line); const l = $('#log'); if (l) { l.textContent = S.log.join('\n'); l.scrollTop = l.scrollHeight; } return; }
    if (ev.event === 'done') { if (S.batch) { S.batch.results.push(ev.run_id); S.batch.i++; nextBatch(); } return; }
    if (ev.event === 'cancelled') { S.running = false; S.batch = null; S.progress = null; render(); return; }
    if (ev.event === 'error') { S.err = ev.message; S.running = false; S.batch = null; render(); return; }
    if (ev.event === 'sidecar_closed') { S.running = false; S.hello = null; return; }
  });

  async function openDetail(id) { try { S.detail = await call('get_run', { run_id: id }); S.selected = id; } catch (e) { S.err = e.message; } }

  function pageResults() {
    if (S.selected && S.detail && S.detail.id === S.selected) return pageDetail(S.detail);
    return h('div', { class: 'wrap' }, h('h1', { class: 'large' }, 'Results'), h('p', { class: 'sub' }, 'Saved runs. Tracks (planner, learned, scripted) are not ranked against each other.'),
      S.runs.length === 0 ? h('div', { class: 'empty' }, 'No runs yet.') :
        h('div', { class: 'group' }, h('table', null, h('thead', null, h('tr', null, ['Task', 'Policy', 'Agent', 'Perc.', 'Ver.', 'Pert.', 'Mode', 'Eps', 'TSR', 'Budget'].map((x) => h('th', null, x)))),
          h('tbody', null, S.runs.map((r) => h('tr', { class: 'click', onclick: async () => { await openDetail(r.id); render(); } },
            h('td', null, r.task), h('td', null, r.policy), h('td', null, r.agent), h('td', null, r.perception), h('td', null, r.verifier), h('td', null, r.perturb), h('td', null, r.mode), h('td', null, r.episodes),
            h('td', null, pc(r.tsr)), h('td', null, pill(r.budget_pass, 'PASS', 'FAIL'))))))),
      S.runs.length ? h('div', { class: 'actions' }, h('button', { class: 'btn danger', onclick: async () => { if (confirm('Delete all saved runs?')) { await call('clear_runs'); S.runs = []; S.detail = null; S.selected = null; render(); } } }, 'Clear all')) : null);
  }

  function pageDetail(r) {
    const m = r.metrics, c = r.config, p = r.profile;
    return h('div', { class: 'wrap' }, h('h1', { class: 'large' }, 'Budget Card'),
      h('p', { class: 'sub' }, `${c.task} with ${r.policy_name}. ${c.agent}, ${c.perception} perception, verifier ${c.verifier}, ${c.perturb}, ${c.mode}. Run ${r.id}.`),
      c.verifier === 'V0' ? h('div', { class: 'banner' }, h('b', null, 'V0 is oracle-assisted. '), 'Use as an upper bound, not as a headline recovery result.') : null,
      h('div', { class: 'cards' }, card('Budget', r.budget.pass ? 'PASS' : 'FAIL', 'profile: ' + r.budget.profile), card('Task success', pc(m.tsr), `95% CI ${pc(m.tsr_ci[0])} to ${pc(m.tsr_ci[1])}`),
        card('Plan latency p95', ms(m.latency_ms.p95) + ' ms', `p50 ${ms(m.latency_ms.p50)}, p99 ${ms(m.latency_ms.p99)}`), card('Staleness', fmt(m.staleness_s_mean, 2) + ' s', `deadline misses ${pc(m.deadline_miss_rate)}`)),
      h('h3', { class: 'section' }, 'Budget checks'),
      h('div', { class: 'group' }, r.budget.checks.map((k) => h('div', { class: 'row' }, lbl(k.name, k.note), h('div', null, h('span', { class: 'val' }, `${k.value == null ? '-' : fmt(k.value, 2)} / ${k.cap}  `), pill(k.ok, 'OK', 'OVER'))))),
      h('p', { class: 'sub', style: 'margin-top:8px' }, `VRAM process source: ${p.vram_process_source}. Measurement confidence: ${p.confidence}. GPU: ${p.gpu_name || 'none detected'}.${p.throttled_any ? ' GPU thermal throttling was detected.' : ''}`),
      h('h3', { class: 'section' }, 'Reliability and recovery'),
      h('div', { class: 'group' },
        ...[['Failures injected', m.failures_injected], ['Detection rate', pc(m.detection_rate)], ['Recovery rate', pc(m.recovery_rate)], ['Diagnosis accuracy', pc(m.diagnosis_accuracy)],
          ['Verifier false-alarm rate', pc(m.false_alarm_rate)], ['Missed-failure rate', pc(m.missed_failure_rate)], ['Plans per episode', fmt(m.plans_per_episode, 2)], ['Actions per episode', fmt(m.actions_per_episode, 1)],
          ['Sim time per episode', fmt(m.sim_time_s_mean, 1) + ' s'], ['LLM tokens/s', m.tokens_per_s_mean ? fmt(m.tokens_per_s_mean, 1) : 'n/a'], ['Energy per episode', m.energy_j_per_episode != null ? fmt(m.energy_j_per_episode) + ' J' : 'n/a'],
          ['Failure breakdown', Object.keys(m.failure_breakdown).length ? Object.entries(m.failure_breakdown).map(([k, v]) => `${k}: ${v}`).join(', ') : 'none']]
          .map(([k, v]) => h('div', { class: 'row' }, h('div', { class: 'lbl' }, k), h('span', { class: 'val' }, v)))),
      h('div', { class: 'actions' }, h('button', { class: 'btn gray', onclick: () => { S.selected = null; S.detail = null; render(); } }, 'Back'),
        h('button', { class: 'btn', onclick: async () => { const x = await window.opai.exportCard(r.id); if (x.ok) alert('Saved to ' + x.path); else if (x.error) alert(x.error); } }, 'Export Budget Card')));
  }

  // ---------- experiments ----------
  async function summaries(ids) { const all = await call('list_runs'); return ids.map((i) => all.find((r) => r.id === i)).filter(Boolean); }
  async function runPreset(kind) {
    const base = { ...S.cfg };
    if (kind === 'loop') {
      if (base.perturb === 'clean') base.perturb = 'moderate';
      S.batchTitle = 'Loop structure (open vs closed vs recovery), perturbation ' + base.perturb;
      return startRuns(['open_loop', 'closed_loop', 'recovery'].map((a) => ({ ...base, agent: a, label: 'E1' })), S.batchTitle);
    }
    if (kind === 'verifier') {
      base.agent = 'recovery'; if (base.perturb === 'clean') base.perturb = 'moderate';
      S.batchTitle = 'Verifier honesty (V0 oracle vs V1 proprio vs V2 camera), perturbation ' + base.perturb;
      return startRuns(['V0', 'V1', 'V2'].map((v) => ({ ...base, verifier: v, label: 'E7' })), S.batchTitle);
    }
    if (kind === 'latency') {
      base.agent = 'closed_loop'; base.task = 'dynamic'; base.perception = 'vision'; base.perturb = 'clean';
      S.batchTitle = 'Latency tax: dynamic task, vision perception, sync vs real-time at increasing planner latency';
      const cfgs = [{ ...base, mode: 'sync', extra_latency_ms: 0, label: 'E4' }];
      for (const l of [0, 1000, 2000, 4000]) cfgs.push({ ...base, mode: 'realtime', extra_latency_ms: l, label: 'E4' });
      return startRuns(cfgs, S.batchTitle);
    }
  }
  function pageCompare() {
    const b = S.batchDone;
    const kids = [h('h1', { class: 'large' }, 'Experiments'),
      h('p', { class: 'sub' }, 'Each preset runs several configurations back to back on the same seeds (paired). Uses the settings from New Run (task, planner, perception, episodes).'),
      S.err ? h('div', { class: 'err' }, S.err) : null,
      h('div', { class: 'group' },
        h('div', { class: 'row' }, lbl('Loop structure', 'Open-loop vs closed-loop vs recovery'), h('button', { class: 'btn', disabled: S.running, onclick: () => runPreset('loop') }, 'Run')),
        h('div', { class: 'row' }, lbl('Verifier honesty', 'Recovery with V0 oracle vs V1 proprio vs V2 camera'), h('button', { class: 'btn', disabled: S.running, onclick: () => runPreset('verifier') }, 'Run')),
        h('div', { class: 'row' }, lbl('Latency tax', 'Moving cube, vision agent, sync vs real-time with 0, 1, 2, 4 s plan latency'), h('button', { class: 'btn', disabled: S.running, onclick: () => runPreset('latency') }, 'Run'))),
      S.running && S.batch ? h('div', { class: 'card', style: 'margin-top:14px' }, h('div', { class: 'k', id: 'ptxt' }, `Run ${S.batch.i + 1} of ${S.batch.cfgs.length}. ` + (S.progress ? `Episode ${S.progress.done} of ${S.progress.total}` : 'Starting...')),
        h('div', { class: 'bar', style: 'margin:10px 0' }, h('i', { id: 'pbar', style: `width:${S.progress ? (S.progress.done / S.progress.total) * 100 : 0}%` })),
        h('div', { class: 'actions', style: 'margin-top:4px' }, h('button', { class: 'btn danger', onclick: () => { S.batch = null; call('cancel'); } }, 'Cancel'))) : null];
    if (b && !S.running) {
      kids.push(h('h3', { class: 'section' }, S.batchTitle || 'Results'));
      kids.push(h('div', { class: 'group', id: 'btable' }, h('div', { class: 'row' }, 'Loading...')));
      summaries(b.results).then(async (rows) => {
        const full = await Promise.all(rows.map((r) => call('get_run', { run_id: r.id })));
        const t = $('#btable'); if (!t) return; t.textContent = '';
        t.append(h('table', null, h('thead', null, h('tr', null, ['Agent', 'Verif.', 'Mode', 'Latency', 'TSR (95% CI)', 'Detect', 'Recover', 'False alarm', 'Missed', 'p95 ms'].map((x) => h('th', null, x)))),
          h('tbody', null, full.map((r) => h('tr', null, h('td', null, r.config.agent), h('td', null, r.config.verifier), h('td', null, r.config.mode), h('td', null, r.config.extra_latency_ms + ' ms'),
            h('td', null, `${pc(r.metrics.tsr)} (${pc(r.metrics.tsr_ci[0])} to ${pc(r.metrics.tsr_ci[1])})`), h('td', null, pc(r.metrics.detection_rate)), h('td', null, pc(r.metrics.recovery_rate)),
            h('td', null, pc(r.metrics.false_alarm_rate)), h('td', null, pc(r.metrics.missed_failure_rate)), h('td', null, fmt(r.metrics.latency_ms.p95)))))));
        const csv = ['agent,verifier,mode,extra_latency_ms,perception,perturb,task,episodes,tsr,ci_lo,ci_hi,detection,recovery,false_alarm,missed,p95_ms'].concat(full.map((r) => [r.config.agent, r.config.verifier, r.config.mode, r.config.extra_latency_ms, r.config.perception, r.config.perturb, r.config.task, r.metrics.episodes, r.metrics.tsr, r.metrics.tsr_ci[0], r.metrics.tsr_ci[1], r.metrics.detection_rate ?? '', r.metrics.recovery_rate ?? '', r.metrics.false_alarm_rate ?? '', r.metrics.missed_failure_rate ?? '', r.metrics.latency_ms.p95].join(','))).join('\n');
        t.parentNode.append(h('div', { class: 'actions' }, h('button', { class: 'btn gray', onclick: () => window.opai.saveCsv('opai_experiment.csv', csv) }, 'Export CSV')));
      }).catch((e) => { S.err = e.message; });
    }
    return h('div', { class: 'wrap' }, kids);
  }

  // ---------- models ----------
  function pageModels() {
    const o = S.ollama;
    return h('div', { class: 'wrap' }, h('h1', { class: 'large' }, 'Models'),
      h('p', { class: 'sub' }, 'Planners run through Ollama on this machine (http://127.0.0.1:11434). The rule-based planner needs nothing.'),
      h('div', { class: 'group' }, h('div', { class: 'row' }, lbl('Ollama status', o && !o.ok ? o.error : ''), h('span', { class: 'val' }, o ? (o.ok ? 'running' : 'not reachable') : 'checking...'))),
      o && o.ok ? h('div', { class: 'group', style: 'margin-top:14px' }, o.models.length ? o.models.map((m) => h('div', { class: 'row' }, h('div', { class: 'lbl' }, m.name), h('span', { class: 'val' }, m.size_gb + ' GB'))) : h('div', { class: 'row' }, 'No models pulled yet.')) : null,
      h('h3', { class: 'section' }, 'Suggested for a 4 GB GPU (e.g. RTX 3050)'),
      h('div', { class: 'card' }, h('div', { class: 'kv' }, h('div', null, 'Install Ollama'), h('div', null, 'ollama.com/download'), h('div', null, 'Small planners'), h('div', null, 'ollama pull qwen3:0.6b    ollama pull qwen3:1.7b'), h('div', null, 'Verified 4 GB'), h('div', null, 'ollama run qwen3:4b-instruct-2507-q4_K_M  (Q4, ~2.5 GB)'))),
      h('div', { class: 'actions' }, h('button', { class: 'btn gray', onclick: loadOllama }, 'Refresh'), h('button', { class: 'btn gray', onclick: () => window.opai.openLink('https://ollama.com/download') }, 'Open ollama.com')));
  }

  function pageSettings() {
    const hw = S.hw, set = S.settings || { theme: 'system' };
    const seg = h('div', { class: 'seg' }, ['system', 'light', 'dark'].map((t) => h('button', { class: set.theme === t ? 'on' : '', onclick: async () => { S.settings = await window.opai.setSettings({ theme: t }); render(); } }, t[0].toUpperCase() + t.slice(1))));
    const g = hw && hw.gpu;
    return h('div', { class: 'wrap' }, h('h1', { class: 'large' }, 'Settings'), h('div', { class: 'group', style: 'margin-top:14px' }, h('div', { class: 'row' }, h('div', { class: 'lbl' }, 'Appearance'), seg)),
      h('h3', { class: 'section' }, 'Hardware profile'),
      h('div', { class: 'card' }, hw ? h('div', { class: 'kv' }, h('div', null, 'Class'), h('div', null, hw.hardware_class), h('div', null, 'OS'), h('div', null, hw.os), h('div', null, 'CPU'), h('div', null, `${hw.cpu || 'unknown'}, ${hw.cores} threads`),
        h('div', null, 'RAM'), h('div', null, `${hw.ram_total_gb} GB total, ${hw.ram_free_gb} GB free`), h('div', null, 'GPU'), h('div', null, g ? `${g.name}, ${g.total_gb.toFixed(2)} GB total, ${g.used_gb.toFixed(2)} GB in use now (${g.source})` : 'none detected'),
        h('div', null, 'GPU temp / power'), h('div', null, g ? `${fmt(g.temp_c)} C, ${fmt(g.power_w)} W` : 'n/a'), h('div', null, 'Python'), h('div', null, hw.python)) : 'Engine not started'),
      h('div', { class: 'actions' }, h('button', { class: 'btn gray', onclick: async () => { try { S.hw = await call('hardware'); } catch (e) { S.err = e.message; } render(); } }, 'Re-measure'), h('button', { class: 'btn gray', onclick: () => window.opai.openData() }, 'Open data folder')),
      h('h3', { class: 'section' }, 'Measurement notes'),
      h('p', { class: 'sub' }, 'Device VRAM is read from the driver (NVML or nvidia-smi). Per-process VRAM is used only where the driver exposes it (usually Linux); otherwise it is estimated as device peak minus the baseline before the run and flagged as estimated. Close other GPU apps for clean numbers.'),
      h('h3', { class: 'section' }, 'About'),
      h('div', { class: 'card' }, h('div', { class: 'kv' }, h('div', null, 'App'), h('div', null, S.info ? S.info.version : ''), h('div', null, 'Engine'), h('div', null, S.hello ? S.hello.version : 'not started'), h('div', null, 'Data folder'), h('div', null, S.info ? S.info.userData : ''), h('div', null, 'License'), h('div', null, 'Apache-2.0'))));
  }

  function render() {
    const pages = { home: pageHome, run: pageRun, results: pageResults, compare: pageCompare, models: pageModels, settings: pageSettings };
    const top = view.scrollTop; view.textContent = ''; view.append(pages[S.page]()); view.scrollTop = top;
  }

  async function init() {
    document.body.classList.add(window.opai.platform === 'darwin' ? 'mac' : window.opai.platform === 'win32' ? 'win' : 'linux');
    [S.info, S.settings] = await Promise.all([window.opai.info(), window.opai.getSettings()]);
    S.cfg = { task: 'pick_place', policy: 'rule', agent: 'recovery', perception: 'oracle', verifier: 'V1', perturb: 'moderate', mode: 'sync', episodes: 50, seed: 0, budget: 'standard', extra_latency_ms: 0 };
    $('#sideFoot').textContent = `v${S.info.version}  Apache-2.0`;
    renderNav(); render();
    S.env = await window.opai.envStatus(); render();
    if (S.env.ok) bootSidecar();
  }
  init();
})();
