'use strict';
const { app, BrowserWindow, ipcMain, nativeTheme, shell, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn, execFile } = require('child_process');

const isMac = process.platform === 'darwin';
const isWin = process.platform === 'win32';
let win = null;

app.commandLine.appendSwitch('disable-gpu-shader-disk-cache');
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
}

// ---------- paths ----------
const pyDir = () => (app.isPackaged ? path.join(process.resourcesPath, 'python') : path.join(__dirname, 'python'));
const reqFile = () => (app.isPackaged ? path.join(process.resourcesPath, 'python', 'requirements.txt') : path.join(__dirname, 'python', 'requirements.txt'));
const venvDir = () => path.join(app.getPath('userData'), 'venv');
const venvPy = () => {
  if (process.env.OPAI_PYTHON && fs.existsSync(process.env.OPAI_PYTHON)) return process.env.OPAI_PYTHON;
  if (process.env.CONDA_PREFIX) {
    const condaPy = path.join(process.env.CONDA_PREFIX, isWin ? 'python.exe' : 'bin/python');
    if (fs.existsSync(condaPy)) return condaPy;
  }
  const defaultConda = isWin
    ? path.join(os.homedir(), 'miniconda3', 'envs', 'thermo_agent', 'python.exe')
    : path.join(os.homedir(), 'miniconda3', 'envs', 'thermo_agent', 'bin', 'python');
  if (fs.existsSync(defaultConda)) return defaultConda;
  return path.join(venvDir(), isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');
};
const dataDir = () => path.join(app.getPath('userData'), 'data');

// ---------- settings ----------
const settingsFile = () => path.join(app.getPath('userData'), 'settings.json');
function getSettings() { try { return { theme: 'system', ...JSON.parse(fs.readFileSync(settingsFile(), 'utf8')) }; } catch { return { theme: 'system' }; } }
function saveSettings(s) { fs.mkdirSync(app.getPath('userData'), { recursive: true }); fs.writeFileSync(settingsFile(), JSON.stringify(s, null, 2)); }

// ---------- python environment ----------
function run(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    execFile(cmd, args, { timeout: opts.timeout || 20000, windowsHide: true, ...opts }, (err, stdout, stderr) => resolve({ err, stdout: String(stdout || ''), stderr: String(stderr || '') }));
  });
}
async function findSystemPython() {
  const cands = isWin ? [['py', ['-3']], ['python', []], ['python3', []]] : [['python3', []], ['python', []]];
  for (const [cmd, pre] of cands) {
    const r = await run(cmd, [...pre, '-c', 'import sys;print(sys.version_info[0]*100+sys.version_info[1])']);
    if (!r.err && parseInt(r.stdout.trim(), 10) >= 309) return { cmd, pre };
  }
  return null;
}
async function envStatus() {
  if (!fs.existsSync(venvPy())) {
    const sys = await findSystemPython();
    return { ok: false, reason: sys ? 'not_installed' : 'no_python', message: sys ? 'Python found. Dependencies not installed yet.' : 'Python 3.9+ not found. Install it from python.org, then reopen this app.' };
  }
  const r = await run(venvPy(), ['-c', 'import mujoco, numpy, psutil; print(mujoco.__version__)']);
  if (r.err) return { ok: false, reason: 'broken', message: 'Environment is incomplete. Run install again.' };
  return { ok: true, mujoco: r.stdout.trim(), python: venvPy() };
}
function installEnv(emit) {
  return new Promise(async (resolve) => {
    const sys = await findSystemPython();
    if (!sys) return resolve({ ok: false, error: 'Python 3.9+ not found' });
    const step = (cmd, args) => new Promise((res) => {
      emit(`$ ${cmd} ${args.join(' ')}`);
      const p = spawn(cmd, args, { windowsHide: true });
      p.stdout.on('data', (d) => emit(String(d).trimEnd()));
      p.stderr.on('data', (d) => emit(String(d).trimEnd()));
      p.on('error', (e) => { emit('error: ' + e.message); res(1); });
      p.on('close', (c) => res(c));
    });
    fs.mkdirSync(app.getPath('userData'), { recursive: true });
    if (!fs.existsSync(venvPy())) {
      if (await step(sys.cmd, [...sys.pre, '-m', 'venv', venvDir()])) return resolve({ ok: false, error: 'venv creation failed' });
    }
    await step(venvPy(), ['-m', 'pip', 'install', '--upgrade', 'pip']);
    let code = await step(venvPy(), ['-m', 'pip', 'install', '-r', reqFile()]);
    if (code) {   // nvidia-ml-py is optional (not on every platform)
      emit('Retrying without optional GPU monitoring package ...');
      code = await step(venvPy(), ['-m', 'pip', 'install', 'mujoco>=3.1', 'numpy>=1.24', 'psutil>=5.9']);
    }
    resolve(code ? { ok: false, error: 'pip install failed' } : { ok: true });
  });
}

// ---------- sidecar ----------
let side = null, sideBuf = '', nextId = 1;
const pending = new Map();
function sendEvent(ev) { if (win && !win.isDestroyed()) win.webContents.send('sidecar:event', ev); }
function startSidecar() {
  if (side) return Promise.resolve();
  return new Promise((resolve, reject) => {
    fs.mkdirSync(dataDir(), { recursive: true });
    side = spawn(venvPy(), ['-u', '-m', 'openphysicalai.server', '--data', dataDir()], { cwd: pyDir(), env: { ...process.env, PYTHONPATH: pyDir(), PYTHONUNBUFFERED: '1' }, windowsHide: true });
    let ready = false;
    side.stdout.on('data', (d) => {
      sideBuf += d.toString();
      let i;
      while ((i = sideBuf.indexOf('\n')) >= 0) {
        const line = sideBuf.slice(0, i).trim(); sideBuf = sideBuf.slice(i + 1);
        if (!line) continue;
        let m; try { m = JSON.parse(line); } catch { continue; }
        if (m.event === 'ready' && !ready) { ready = true; resolve(); }
        if (m.id != null && m.ok !== undefined && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.ok ? p.resolve(m.result) : p.reject(new Error(m.error)); }
        else if (m.event) sendEvent(m);
      }
    });
    side.stderr.on('data', (d) => sendEvent({ event: 'stderr', line: d.toString() }));
    side.on('error', (e) => { side = null; reject(e); });
    side.on('close', () => { side = null; for (const p of pending.values()) p.reject(new Error('sidecar exited')); pending.clear(); sendEvent({ event: 'sidecar_closed' }); });
    setTimeout(() => { if (!ready) reject(new Error('sidecar start timeout')); }, 30000);
  });
}
async function rpc(cmd, payload = {}) {
  await startSidecar();
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    side.stdin.write(JSON.stringify({ id, cmd, ...payload }) + '\n');
  });
}

// ---------- window ----------
function createWindow() {
  const dark = nativeTheme.shouldUseDarkColors;
  win = new BrowserWindow({
    title: 'OpenPhysicalAI Lab',
    icon: path.join(__dirname, 'src', 'logo-icon-1024.png'),
    width: 1240, height: 820, minWidth: 980, minHeight: 640, show: true,
    backgroundColor: isMac ? '#00000000' : dark ? '#000000' : '#f2f2f7',
    ...(isMac ? { titleBarStyle: 'hiddenInset', vibrancy: 'sidebar', trafficLightPosition: { x: 18, y: 18 } } : {}),
    ...(isWin ? { titleBarStyle: 'hidden', titleBarOverlay: { color: dark ? '#000000' : '#f2f2f7', symbolColor: dark ? '#ffffff' : '#1c1c1e', height: 40 } } : {}),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  win.once('ready-to-show', () => win.show());
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https:\/\//.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith('file://')) e.preventDefault(); });
  win.loadFile(path.join(__dirname, 'src', 'index.html'));
  win.show();
  win.focus();
}

// ---------- IPC ----------
ipcMain.handle('app:info', () => ({ platform: process.platform, version: app.getVersion(), electron: process.versions.electron, userData: app.getPath('userData') }));
ipcMain.handle('settings:get', () => getSettings());
ipcMain.handle('settings:set', (_e, patch) => { const s = { ...getSettings(), ...patch }; if (!['system', 'light', 'dark'].includes(s.theme)) s.theme = 'system'; saveSettings(s); nativeTheme.themeSource = s.theme; return s; });
ipcMain.handle('env:status', () => envStatus());
ipcMain.handle('env:install', async () => { const r = await installEnv((line) => sendEvent({ event: 'env_log', line })); return r; });
ipcMain.handle('rpc', async (_e, cmd, payload) => {
  try { return { ok: true, result: await rpc(cmd, payload || {}) }; } catch (e) { return { ok: false, error: String(e && e.message || e) }; }
});
ipcMain.handle('card:export', async (_e, runId) => {
  try {
    const md = await rpc('card', { run_id: runId });
    if (!md) return { ok: false, error: 'run not found' };
    const r = await dialog.showSaveDialog(win, { defaultPath: `budget_card_${runId}.md`, filters: [{ name: 'Markdown', extensions: ['md'] }] });
    if (r.canceled || !r.filePath) return { ok: false };
    fs.writeFileSync(r.filePath, md);
    return { ok: true, path: r.filePath };
  } catch (e) { return { ok: false, error: String(e.message || e) }; }
});
ipcMain.handle('csv:save', async (_e, name, text) => {
  const r = await dialog.showSaveDialog(win, { defaultPath: name, filters: [{ name: 'CSV', extensions: ['csv'] }] });
  if (r.canceled || !r.filePath) return { ok: false };
  fs.writeFileSync(r.filePath, text); return { ok: true, path: r.filePath };
});
ipcMain.handle('data:open', () => shell.openPath(app.getPath('userData')));
ipcMain.handle('link:open', (_e, url) => { if (/^https:\/\//.test(url)) return shell.openExternal(url); });

app.whenReady().then(() => { nativeTheme.themeSource = getSettings().theme; createWindow(); app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); }); });
app.on('before-quit', () => { if (side) side.kill(); });
app.on('window-all-closed', () => { if (!isMac) app.quit(); });
