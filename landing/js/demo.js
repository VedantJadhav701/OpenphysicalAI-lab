// Interactive latency-tax illustration (top-down, simplified). Not a measurement.
export function startDemo(canvas, { slider, valueEl, verdictEl, toggles }) {
  const g = canvas.getContext('2d'), W = canvas.width, H = canvas.height;
  const PXMM = 4;                 // 1 mm = 4 px
  const V = 0.02 * 1000 * PXMM;   // 20 mm/s -> px/s
  const TRAVEL = 0.4;             // arm travel time (s)
  const ZONE = 12 * PXMM;         // capture half-width (illustrative)
  const BELT_Y = 300, X0 = 130;
  let lead = 0, lat = +slider.value / 1000, t = 0, last = performance.now(), phase = 0;
  const cyan = '#5ac8fa', blue = '#0a84ff', red = '#ff453a', green = '#30d158';
  slider.addEventListener('input', () => { lat = +slider.value / 1000; valueEl.textContent = slider.value + ' ms'; t = 0; });
  toggles.forEach(b => b.addEventListener('click', () => { lead = +b.dataset.lead; toggles.forEach(x => x.classList.toggle('on', x === b)); t = 0; }));
  valueEl.textContent = slider.value + ' ms';

  const rr = (x, y, w, h, r) => { g.beginPath(); g.roundRect(x, y, w, h, r); };
  function draw(now) {
    requestAnimationFrame(draw);
    const dt = Math.min(0.05, (now - last) / 1000); last = now; t += dt;
    const tGrasp = lat + TRAVEL, hold = 1.8, cycle = tGrasp + hold + 0.3;
    if (t > cycle) t = 0;
    const cubeX = X0 + V * t;                          // true cube position
    const seenX = X0;                                  // what the planner observed at t=0
    const target = lead ? X0 + V * tGrasp : seenX;     // where the gripper aims
    const move = Math.max(0, Math.min(1, (t - lat) / TRAVEL)), e = move * move * (3 - 2 * move);
    const gx = 90 + (target - 90) * e;                 // gripper x
    const miss = Math.abs((X0 + V * tGrasp) - target) / PXMM;   // mm at grasp time
    const hit = miss <= ZONE / PXMM;

    g.clearRect(0, 0, W, H); g.textAlign = 'left';
    // background grid
    g.fillStyle = '#07090e'; g.fillRect(0, 0, W, H);
    g.strokeStyle = 'rgba(90,200,250,.06)'; g.lineWidth = 1;
    for (let x = 0; x < W; x += 40) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
    for (let y = 0; y < H; y += 40) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    // belt
    g.fillStyle = '#12151d'; rr(30, BELT_Y - 70, W - 60, 140, 18); g.fill();
    g.strokeStyle = 'rgba(255,255,255,.08)'; g.lineWidth = 2; g.stroke();
    g.save(); g.beginPath(); g.roundRect(30, BELT_Y - 70, W - 60, 140, 18); g.clip();
    g.fillStyle = 'rgba(255,255,255,.04)'; const off = (t * V) % 60; for (let x = 20 + off; x < W; x += 60) g.fillRect(x, BELT_Y - 70, 22, 140); g.restore();
    // labels
    g.font = '600 20px Inter,system-ui,sans-serif'; g.fillStyle = 'rgba(235,235,245,.5)';
    g.textAlign = 'right'; g.fillText('conveyor → 20 mm/s', W - 46, BELT_Y + 100); g.textAlign = 'left';

    // ghost: what the planner saw
    g.setLineDash([6, 6]); g.strokeStyle = 'rgba(255,255,255,.55)'; g.lineWidth = 2; rr(seenX - 26, BELT_Y - 26, 52, 52, 8); g.stroke(); g.setLineDash([]);
    g.fillStyle = 'rgba(255,255,255,.6)'; g.font = '600 19px Inter,system-ui,sans-serif'; g.textAlign = 'center'; g.fillText('observed at t = 0', seenX, BELT_Y + 62);
    // capture zone around target
    g.fillStyle = 'rgba(10,132,255,.14)'; g.fillRect(target - ZONE, BELT_Y - 70, ZONE * 2, 140);
    g.strokeStyle = 'rgba(10,132,255,.6)'; g.lineWidth = 1.5; g.strokeRect(target - ZONE, BELT_Y - 70, ZONE * 2, 140);
    g.fillStyle = blue; g.textAlign = 'center'; g.fillText(lead ? 'aim (velocity lead)' : 'aim (stale)', target, BELT_Y - 164); g.textAlign = 'left';
    // real cube
    const holdPhase = t > tGrasp;
    g.save(); g.shadowColor = 'rgba(255,214,10,.5)'; g.shadowBlur = 22; g.fillStyle = '#ffd60a'; rr(cubeX - 25, BELT_Y - 25, 50, 50, 8); g.fill(); g.restore();
    // gripper (top-down: two prongs)
    const gap = holdPhase ? 30 : 56;
    g.fillStyle = '#c7c7cc'; rr(gx - 14, BELT_Y - 150, 28, 80 + (move > 0 ? 40 * e : 0), 8); g.fill();
    g.fillStyle = '#e5e5ea'; rr(gx - gap / 2 - 8, BELT_Y - 40 + 0, 8, 80, 3); g.fill(); rr(gx + gap / 2, BELT_Y - 40, 8, 80, 3); g.fill();
    // planner bar
    const pb = Math.min(1, t / Math.max(lat, 0.001));
    g.fillStyle = 'rgba(255,255,255,.08)'; rr(46, 40, 300, 14, 7); g.fill();
    g.fillStyle = cyan; rr(46, 40, Math.max(0, 300 * (lat === 0 ? 1 : pb)), 14, 7); g.fill();
    g.textAlign = 'left'; g.fillStyle = 'rgba(235,235,245,.7)'; g.font = '600 20px Inter,system-ui,sans-serif';
    g.fillText(t < lat ? 'planner thinking… the cube keeps moving' : (t < tGrasp ? 'arm moving' : 'grasp'), 46, 80);
    // offset readout
    if (holdPhase) {
      g.textAlign = 'right'; g.font = '700 34px Inter,system-ui,sans-serif'; g.fillStyle = hit ? green : red;
      g.fillText((hit ? 'HIT · ' : 'MISS · ') + miss.toFixed(0) + ' mm off', W - 46, 66);
    }
    // stale distance bracket
    const gapPx = cubeX - seenX;
    if (gapPx > 8 && !holdPhase) { g.strokeStyle = amber(); g.lineWidth = 2; g.beginPath(); g.moveTo(seenX, BELT_Y + 100); g.lineTo(cubeX, BELT_Y + 100); g.stroke(); g.fillStyle = amber(); g.textAlign = 'center'; g.fillText((gapPx / PXMM).toFixed(0) + ' mm drift', (seenX + cubeX) / 2, BELT_Y + 126); }
    verdictEl.className = 'verdict ' + (holdPhase ? (hit ? 'hit' : 'miss') : '');
    verdictEl.textContent = holdPhase ? (hit ? 'Grasp succeeds' : 'Grasp misses: stale observation') : (t < lat ? 'Planning…' : 'Executing');
  }
  function amber() { return '#ff9f0a'; }
  if (!CanvasRenderingContext2D.prototype.roundRect) CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, r) { this.moveTo(x + r, y); this.arcTo(x + w, y, x + w, y + h, r); this.arcTo(x + w, y + h, x, y + h, r); this.arcTo(x, y + h, x, y, r); this.arcTo(x, y, x + w, y, r); this.closePath(); };
  requestAnimationFrame(draw);
}
