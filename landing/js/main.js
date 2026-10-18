import { startArm } from './arm.js';
import { startDemo } from './demo.js';

const REPO = 'VedantJadhav701/OpenphysicalAI-lab';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const safe = (fn) => { try { return fn(); } catch (e) { return null; } };

/* ---------- hero 3D arm (falls back silently if WebGL is unavailable) ---------- */
const logEl = $('#log');
function onLog(msg, kind) {
  if (!logEl) return;
  const li = document.createElement('li'); li.className = kind || ''; li.textContent = msg;
  logEl.appendChild(li); while (logEl.children.length > 5) logEl.removeChild(logEl.firstChild);
}
try { startArm($('#arm'), { onLog }); } catch (e) { console.warn('3D hero disabled:', e); $('#arm').style.display = 'none'; }

/* ---------- latency demo ---------- */
safe(() => startDemo($('#demo'), { slider: $('#lat'), valueEl: $('#latVal'), verdictEl: $('#verdict'), toggles: $$('.toggle button') }));

/* ---------- reveal on scroll ---------- */
document.documentElement.classList.add('js');
const io = new IntersectionObserver((es) => es.forEach(e => {
  if (!e.isIntersecting) return;
  e.target.classList.add('in');
  io.unobserve(e.target);
  $$('.bar', e.target).forEach(b => { $('u', b).style.width = b.dataset.v + '%'; });
}), { threshold: 0.01, rootMargin: '0px 0px 80px 0px' });

$$('.rv').forEach(el => {
  const r = el.getBoundingClientRect();
  if (r.top < window.innerHeight + 150) {
    el.classList.add('in');
    $$('.bar', el).forEach(b => { $('u', b).style.width = b.dataset.v + '%'; });
  } else {
    io.observe(el);
  }
});

/* ---------- count-up stats ---------- */
const co = new IntersectionObserver((es) => es.forEach(e => {
  if (!e.isIntersecting) return; co.unobserve(e.target);
  const el = e.target, end = +el.dataset.count, suf = el.dataset.suffix || '', t0 = performance.now();
  (function tick(now) { const k = Math.min(1, (now - t0) / 1400), v = Math.round(end * (1 - Math.pow(1 - k, 3))); el.textContent = v + suf; if (k < 1) requestAnimationFrame(tick); })(t0);
}), { threshold: 0.6 });
$$('[data-count]').forEach(el => co.observe(el));

/* ---------- cursor glow ---------- */
addEventListener('pointermove', e => { document.documentElement.style.setProperty('--mx', e.clientX + 'px'); document.documentElement.style.setProperty('--my', e.clientY + 'px'); }, { passive: true });

/* ---------- video ---------- */
const vid = $('#launch'), box = $('#videoBox');
$('#playBtn').addEventListener('click', () => { vid.play(); });
vid.addEventListener('play', () => box.classList.add('playing'));
vid.addEventListener('ended', () => box.classList.remove('playing'));

/* ---------- copy buttons + install tabs ---------- */
async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); } catch (e) { const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); }
  const old = btn.textContent; btn.textContent = 'Copied'; setTimeout(() => (btn.textContent = old), 1400);
}
$$('[data-copy]').forEach(b => b.addEventListener('click', () => copy(b.dataset.copy, $('.cp', b) || b)));
$$('.tabs button').forEach(b => b.addEventListener('click', () => {
  $$('.tabs button').forEach(x => x.classList.toggle('on', x === b));
  $$('.term pre').forEach(p => p.classList.toggle('on', p.dataset.pane === b.dataset.tab));
}));
$('#copyPane').addEventListener('click', e => copy($('.term pre.on').innerText, e.currentTarget));

/* ---------- share links ---------- */
const url = encodeURIComponent(location.href.split('#')[0]), txt = encodeURIComponent('OpenPhysicalAI Lab: open-source Physical AI evaluation under real VRAM, RAM and latency budgets. Runs on a 4 GB laptop.');
const sh = { x: `https://twitter.com/intent/tweet?text=${txt}&url=${url}`, li: `https://www.linkedin.com/sharing/share-offsite/?url=${url}`, rd: `https://www.reddit.com/submit?url=${url}&title=${txt}`, hn: `https://news.ycombinator.com/submitlink?u=${url}&t=${encodeURIComponent('OpenPhysicalAI Lab: Physical AI evaluation under real hardware budgets')}` };
$$('#share a').forEach(a => { a.href = sh[a.dataset.s]; });

/* ---------- GitHub: live stars + latest release (cached 10 min, silent fallback) ---------- */
async function gh(path) {
  const key = 'opai:' + path, now = Date.now();
  try { const c = JSON.parse(sessionStorage.getItem(key) || 'null'); if (c && now - c.t < 600000) return c.d; } catch (e) {}
  const r = await fetch('https://api.github.com/repos/' + REPO + path, { headers: { Accept: 'application/vnd.github+json' } });
  if (!r.ok) throw new Error(r.status);
  const d = await r.json(); try { sessionStorage.setItem(key, JSON.stringify({ t: now, d })); } catch (e) {}
  return d;
}
const fmt = n => n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, '') + 'k' : String(n);
gh('').then(d => { ['#starCountNav', '#starCountHero', '#starCountBig'].forEach(id => { const el = $(id); if (el) el.textContent = d.stargazers_count >= 10 ? fmt(d.stargazers_count) : ''; }); }).catch(() => {});

const mb = n => (n / 1048576).toFixed(0) + ' MB';
gh('/releases/latest').then(rel => {
  const a = rel.assets || [], pick = f => a.find(x => f(x.name.toLowerCase()));
  const setup = pick(n => n.endsWith('.exe') && n.includes('setup')), portable = pick(n => n.endsWith('.exe') && !n.includes('setup')), mac = pick(n => n.endsWith('.dmg')) || pick(n => n.includes('mac') && n.endsWith('.zip'));
  const set = (kind, asset, label) => { const el = $(`.dl[data-kind="${kind}"]`); if (!el || !asset) return; el.href = asset.browser_download_url; $('small', el).textContent = `${rel.tag_name} · ${mb(asset.size)} · ${asset.name}`; if (label) $('b', el).textContent = label; };
  set('win', setup); set('portable', portable); set('mac', mac, 'macOS');
  const isMac = /Mac/i.test(navigator.platform || navigator.userAgent) && !/iPhone|iPad/i.test(navigator.userAgent);
  const main = isMac ? (mac || null) : (setup || portable);
  if (main) { $('#dlBtn').href = main.browser_download_url; $('#dlLabel').textContent = isMac ? 'Download for macOS' : 'Download for Windows'; }
  else if (isMac) { $('#dlLabel').textContent = 'Get the latest release'; }
}).catch(() => { /* keep static fallback links to /releases/latest */ });
if (/Mac/i.test(navigator.platform || '') && !/iPhone|iPad/i.test(navigator.userAgent)) $('#dlLabel').textContent = 'Get the latest release';
