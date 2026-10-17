'use strict';
const { contextBridge, ipcRenderer } = require('electron');
const call = (ch) => (...a) => ipcRenderer.invoke(ch, ...a);
contextBridge.exposeInMainWorld('opai', {
  platform: process.platform,
  info: call('app:info'),
  getSettings: call('settings:get'),
  setSettings: call('settings:set'),
  envStatus: call('env:status'),
  envInstall: call('env:install'),
  rpc: call('rpc'),
  exportCard: call('card:export'),
  saveCsv: call('csv:save'),
  openData: call('data:open'),
  openLink: call('link:open'),
  onEvent: (cb) => { const h = (_e, d) => cb(d); ipcRenderer.on('sidecar:event', h); return () => ipcRenderer.removeListener('sidecar:event', h); },
});
