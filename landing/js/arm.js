// Hero scene: a 5-DOF-style arm doing pick and place with a grasp slip and recovery.
// Illustrative animation of the simulator (not a live MuJoCo stream). Three.js, no build step.
import * as THREE from 'three';
import { RoomEnvironment } from '../vendor/RoomEnvironment.js';
import { RoundedBoxGeometry } from '../vendor/RoundedBoxGeometry.js';

export function startArm(canvas, opts = {}) {
  const onLog = opts.onLog || (() => {});
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;
  scene.environmentIntensity = 0.55;
  scene.fog = new THREE.Fog(0x05060a, 2.2, 4.6);

  const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 20);
  const look = new THREE.Vector3(0.02, 0.1, 0.08);

  // ---------- lights ----------
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(1.1, 1.8, 0.9);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -0.9; key.shadow.camera.right = 0.9;
  key.shadow.camera.top = 0.9; key.shadow.camera.bottom = -0.9;
  key.shadow.camera.near = 0.5; key.shadow.camera.far = 5;
  key.shadow.bias = -0.0004; key.shadow.normalBias = 0.01;
  scene.add(key);
  const rim = new THREE.PointLight(0x0a84ff, 14, 3.5, 2); rim.position.set(-0.9, 0.5, -0.7); scene.add(rim);
  const rim2 = new THREE.PointLight(0x5e5ce6, 8, 3.5, 2); rim2.position.set(0.9, 0.35, 0.9); scene.add(rim2);

  // ---------- table ----------
  const gridTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 512;
    const g = c.getContext('2d');
    g.fillStyle = '#0c1018'; g.fillRect(0, 0, 512, 512);
    g.strokeStyle = 'rgba(90,200,250,0.10)'; g.lineWidth = 2;
    for (let i = 0; i <= 512; i += 64) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, 512); g.stroke(); g.beginPath(); g.moveTo(0, i); g.lineTo(512, i); g.stroke(); }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(3, 2); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
  })();
  const table = new THREE.Mesh(new RoundedBoxGeometry(1.7, 0.05, 1.1, 4, 0.02), new THREE.MeshStandardMaterial({ map: gridTex, roughness: 0.55, metalness: 0.25 }));
  table.position.y = -0.025; table.receiveShadow = true; scene.add(table);
  const edge = new THREE.Mesh(new THREE.BoxGeometry(1.704, 0.004, 1.104), new THREE.MeshBasicMaterial({ color: 0x0a84ff }));
  edge.position.y = -0.052; scene.add(edge);

  // ---------- materials ----------
  const white = new THREE.MeshPhysicalMaterial({ color: 0xf2f4f8, roughness: 0.32, metalness: 0.05, clearcoat: 1, clearcoatRoughness: 0.12 });
  const graphite = new THREE.MeshStandardMaterial({ color: 0x1b1e26, roughness: 0.4, metalness: 0.7 });
  const steel = new THREE.MeshStandardMaterial({ color: 0xaab2c0, roughness: 0.25, metalness: 1 });
  const glow = new THREE.MeshStandardMaterial({ color: 0x0a84ff, emissive: 0x0a84ff, emissiveIntensity: 2.2, roughness: 0.4 });
  const rubber = new THREE.MeshStandardMaterial({ color: 0x0f1014, roughness: 0.9 });
  const mesh = (geo, mat, parent, cast = true) => { const m = new THREE.Mesh(geo, mat); m.castShadow = cast; m.receiveShadow = true; parent.add(m); return m; };

  // ---------- arm ----------
  const B = new THREE.Vector3(-0.33, 0, 0.02);
  const H0 = 0.24, L1 = 0.34, L2 = 0.30, LT = 0.115;
  const root = new THREE.Group(); root.position.copy(B); scene.add(root);
  mesh(new THREE.CylinderGeometry(0.105, 0.12, 0.03, 64), graphite, root).position.y = 0.015;
  mesh(new THREE.CylinderGeometry(0.075, 0.09, 0.07, 64), white, root).position.y = 0.065;
  const ring = mesh(new THREE.TorusGeometry(0.083, 0.004, 12, 96), glow, root, false); ring.rotation.x = Math.PI / 2; ring.position.y = 0.045;
  const yaw = new THREE.Group(); yaw.position.y = 0.1; root.add(yaw);
  mesh(new THREE.CylinderGeometry(0.066, 0.072, 0.07, 48), white, yaw).position.y = 0.035;
  const sh = new THREE.Group(); sh.position.set(0, H0 - 0.1, 0); yaw.add(sh);
  const shMount = mesh(new RoundedBoxGeometry(0.1, 0.1, 0.12, 4, 0.02), graphite, yaw); shMount.position.set(0, H0 - 0.1 - 0.0, 0); shMount.position.y = 0.1;
  const joint = (parent, r, len) => { const m = mesh(new THREE.CylinderGeometry(r, r, len, 48), steel, parent); m.rotation.x = Math.PI / 2; return m; };
  joint(sh, 0.05, 0.13);
  const capA = mesh(new THREE.CylinderGeometry(0.026, 0.026, 0.002, 32), glow, sh, false); capA.rotation.x = Math.PI / 2; capA.position.z = 0.066;
  const link1 = mesh(new RoundedBoxGeometry(L1 + 0.07, 0.07, 0.075, 5, 0.03), white, sh); link1.position.x = L1 / 2; link1.position.z = 0.0;
  const el = new THREE.Group(); el.position.x = L1; sh.add(el);
  joint(el, 0.042, 0.115);
  const capB = mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.002, 32), glow, el, false); capB.rotation.x = Math.PI / 2; capB.position.z = 0.058;
  const link2 = mesh(new RoundedBoxGeometry(L2 + 0.06, 0.058, 0.062, 5, 0.026), white, el); link2.position.x = L2 / 2;
  const wr = new THREE.Group(); wr.position.x = L2; el.add(wr);
  joint(wr, 0.032, 0.09);
  const tool = new THREE.Group(); wr.add(tool);
  mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.03, 40), graphite, tool).rotation.z = Math.PI / 2;
  tool.children[0].position.x = 0.02;
  mesh(new RoundedBoxGeometry(0.03, 0.06, 0.11, 3, 0.008), graphite, tool).position.x = 0.045;
  const fingerGeo = new RoundedBoxGeometry(0.07, 0.03, 0.012, 3, 0.004);
  const fL = mesh(fingerGeo, steel, tool), fR = mesh(fingerGeo, steel, tool);
  const padGeo = new THREE.BoxGeometry(0.03, 0.026, 0.003);
  const pL = mesh(padGeo, rubber, fL, false), pR = mesh(padGeo, rubber, fR, false);
  fL.position.x = fR.position.x = 0.08; pL.position.set(0.02, 0, 0.0075); pR.position.set(0.02, 0, -0.0075);

  // ---------- objects ----------
  const CUBE = 0.05;
  const cubeColors = [0xff453a, 0x30d158, 0xffd60a];
  const cubeSpots = [new THREE.Vector3(0.05, CUBE / 2, 0.22), new THREE.Vector3(0.2, CUBE / 2, 0.12), new THREE.Vector3(0.12, CUBE / 2, 0.30)];
  const cubes = cubeColors.map((c, i) => {
    const m = new THREE.Mesh(new RoundedBoxGeometry(CUBE, CUBE, CUBE, 4, 0.006), new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.35, clearcoat: 0.8, clearcoatRoughness: 0.2 }));
    m.castShadow = m.receiveShadow = true; m.position.copy(cubeSpots[i]); m.rotation.y = 0.3 * i; scene.add(m); return m;
  });
  // container (open top tray)
  const CONT = new THREE.Vector3(0.22, 0, -0.26);
  const tray = new THREE.Group(); tray.position.copy(CONT); scene.add(tray);
  const trayMat = new THREE.MeshStandardMaterial({ color: 0x2748d4, roughness: 0.5, metalness: 0.2 });
  mesh(new THREE.BoxGeometry(0.24, 0.006, 0.24), trayMat, tray).position.y = 0.003;
  [[0, 0.117, 0.24, 0.006], [0, -0.117, 0.24, 0.006]].forEach(([x, z, w, d]) => { const w1 = mesh(new THREE.BoxGeometry(w, 0.05, d), trayMat, tray); w1.position.set(x, 0.025, z); });
  [[0.117, 0], [-0.117, 0]].forEach(([x, z]) => { const w1 = mesh(new THREE.BoxGeometry(0.006, 0.05, 0.24), trayMat, tray); w1.position.set(x, 0.025, z); });
  const slots = [new THREE.Vector3(-0.06, 0, -0.05), new THREE.Vector3(0.06, 0, -0.05), new THREE.Vector3(0, 0, 0.06)].map(v => v.add(CONT));

  // conveyor strip (decor + motion)
  const beltTex = (() => {
    const c = document.createElement('canvas'); c.width = 256; c.height = 64; const g = c.getContext('2d');
    g.fillStyle = '#14171f'; g.fillRect(0, 0, 256, 64); g.fillStyle = '#232a38';
    for (let i = 0; i < 256; i += 32) g.fillRect(i, 0, 16, 64);
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(8, 1); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const belt = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.012, 0.16), new THREE.MeshStandardMaterial({ map: beltTex, roughness: 0.8 }));
  belt.position.set(-0.05, 0.006, 0.46); belt.receiveShadow = true; scene.add(belt);
  const bcube = new THREE.Mesh(new RoundedBoxGeometry(0.04, 0.04, 0.04, 3, 0.005), new THREE.MeshPhysicalMaterial({ color: 0x5ac8fa, roughness: 0.3, clearcoat: 0.8 }));
  bcube.castShadow = true; scene.add(bcube);

  // ---------- IK ----------
  const cur = new THREE.Vector3(0.1, 0.26, 0.1);   // tool tip target (world)
  let grip = 0.04;                                  // finger half opening
  function applyPose() {
    const dx = cur.x - B.x, dz = cur.z - B.z;
    const r = Math.max(0.12, Math.hypot(dx, dz));
    yaw.rotation.y = Math.atan2(-dz, dx);
    const wx = r, wy = cur.y + LT - (yaw.position.y + sh.position.y);
    let d = Math.hypot(wx, wy); d = Math.min(Math.max(d, Math.abs(L1 - L2) + 0.01), L1 + L2 - 0.003);
    const base = Math.atan2(wy, wx);
    const a1 = base + Math.acos(THREE.MathUtils.clamp((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1));
    const ex = L1 * Math.cos(a1), ey = L1 * Math.sin(a1);
    const a2 = Math.atan2(wy - ey, wx - ex);
    sh.rotation.z = a1; el.rotation.z = a2 - a1; wr.rotation.z = -Math.PI / 2 - a2;
    fL.position.z = grip + 0.006; fR.position.z = -(grip + 0.006);
  }
  const tipOf = () => cur.clone();

  // ---------- tweens ----------
  const tweens = [];
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const tween = (d, fn) => new Promise(res => { tweens.push({ t: 0, d, fn, res }); });
  const wait = d => tween(d, () => {});
  const moveTo = (x, y, z, d) => { const s = cur.clone(); const e = new THREE.Vector3(x, y, z); return tween(d, k => cur.lerpVectors(s, e, k)); };
  const setGrip = (g, d = 0.25) => { const s = grip; return tween(d, k => { grip = s + (g - s) * k; }); };
  let held = null;
  const HOVER = 0.2, GRASP_Y = 0.02;
  const names = ['red', 'green', 'yellow'];

  async function pick(i, slip) {
    const c = cubes[i], p = c.position;
    onLog('planner → pick(' + names[i] + ')', 'plan');
    await setGrip(0.04, 0.2);
    await moveTo(p.x, HOVER, p.z, 0.95);
    await moveTo(p.x, GRASP_Y, p.z, 0.55);
    await setGrip(CUBE / 2 - 0.0005, 0.25);
    held = c;
    await moveTo(p.x, HOVER * 0.7, p.z, 0.5);
    if (slip) {
      await moveTo(p.x, HOVER * 0.85, p.z, 0.25);
      onLog('verify V2 → FAIL: grasp slip detected', 'fail');
      held = null; await setGrip(0.04, 0.12);
      const dxs = 0.03;
      const sx = c.position.x;
      await tween(0.38, k => { c.position.y = Math.max(CUBE / 2, (HOVER * 0.85 - 0.02) * (1 - k * k) + CUBE / 2 * k * k); c.position.x = sx + dxs * k; c.rotation.y += 0.05; });
      onLog('diagnose → grasp_slip · re-observe', 'diag');
      await moveTo(c.position.x, HOVER, c.position.z, 0.5);
      await wait(0.35);
      onLog('recover → replan pick(' + names[i] + ')', 'plan');
      await moveTo(c.position.x, HOVER, c.position.z, 0.2);
      await moveTo(c.position.x, GRASP_Y, c.position.z, 0.6);
      await setGrip(CUBE / 2 - 0.0005, 0.25);
      held = c;
      await moveTo(c.position.x, HOVER * 0.7, c.position.z, 0.5);
      onLog('verify V2 → ok · recovered', 'ok');
    } else {
      onLog('verify V2 → ok · grasp holds', 'ok');
    }
  }
  async function place(i) {
    const s = slots[i];
    await moveTo(s.x, HOVER, s.z, 1.05);
    await moveTo(s.x, 0.075, s.z, 0.5);
    held = null; await setGrip(0.04, 0.2);
    cubes[i].position.set(s.x, CUBE / 2 + 0.003, s.z);
    onLog('verify V2 → placed inside container', 'ok');
    await moveTo(s.x, HOVER, s.z, 0.5);
  }
  async function program() {
    let cycle = 0;
    for (;;) {
      cubes.forEach((c, i) => { c.visible = true; c.scale.setScalar(1); c.position.copy(cubeSpots[i]); });
      for (let i = 0; i < 3; i++) { await pick(i, cycle % 2 === 0 && i === 1); await place(i); }
      onLog('episode complete · 3/3', 'ok');
      await moveTo(0.1, 0.27, 0.12, 0.9);
      await wait(0.6);
      await tween(0.5, k => cubes.forEach(c => c.scale.setScalar(1 - k)));
      cycle++;
      await tween(0.01, () => {});
      for (let i = 0; i < 3; i++) { cubes[i].position.copy(cubeSpots[i]); }
      await tween(0.5, k => cubes.forEach(c => c.scale.setScalar(k)));
    }
  }

  // ---------- frame loop ----------
  let R = 2.35, t0 = performance.now(), running = false, raf = 0, w = 0, h = 0, px = 0, py = 0, ptx = 0, pty = 0, tAll = 0;
  function resize() {
    const r = canvas.getBoundingClientRect(); w = Math.max(320, r.width); h = Math.max(320, r.height);
    renderer.setSize(w, h, false); camera.aspect = w / h;
    const wide = w > 900;
    camera.fov = wide ? 30 : 40; R = wide ? 2.35 : 3.0;
    camera.setViewOffset(w, h, wide ? -w * 0.16 : 0, wide ? 0 : -h * 0.18, w, h);
    camera.updateProjectionMatrix();
  }
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - t0) / 1000); t0 = now; tAll += dt;
    for (let i = tweens.length - 1; i >= 0; i--) { const tw = tweens[i]; tw.t = Math.min(1, tw.t + dt / tw.d); tw.fn(ease(tw.t)); if (tw.t >= 1) { tweens.splice(i, 1); tw.res(); } }
    px += (ptx - px) * 0.05; py += (pty - py) * 0.05;
    const ang = 0.62 + px * 0.18, el2 = 0.5 + py * 0.06;
    camera.position.set(look.x + Math.sin(ang) * R * Math.cos(el2), look.y + Math.sin(el2) * R + 0.08, look.z + Math.cos(ang) * R * Math.cos(el2));
    camera.lookAt(look);
    applyPose();
    if (held) { held.position.set(cur.x, cur.y + 0.003, cur.z); }
    beltTex.offset.x = -tAll * 0.08; bcube.position.set(-0.05 + ((tAll * 0.04) % 1.0) * 1.0 - 0.5, 0.032, 0.46);
    rim.intensity = 14 + Math.sin(tAll * 1.2) * 3;
    renderer.render(scene, camera);
  }
  function start() { if (running) return; running = true; t0 = performance.now(); raf = requestAnimationFrame(frame); }
  function stop() { running = false; cancelAnimationFrame(raf); }
  resize(); window.addEventListener('resize', resize);
  window.addEventListener('pointermove', e => { ptx = (e.clientX / innerWidth - 0.5) * 2; pty = (e.clientY / innerHeight - 0.5) * 2; }, { passive: true });
  new IntersectionObserver(es => { es[0].isIntersecting ? start() : stop(); }, { threshold: 0.02 }).observe(canvas);
  document.addEventListener('visibilitychange', () => { document.hidden ? stop() : start(); });
  program();
  if (reduced) { // render a still frame, no loop
    applyPose(); renderer.render(scene, camera); stop();
    tweens.length = 0;
  } else start();
  return { stop, start, renderer };
}
