// Perspectome — the intro: a close-up of a few people that pulls back into a relief map of Turkey.
//
// The figures breathe in the colours of different communities; the camera eases back over a dark
// map, and a soft pool of light shows the crowd only where it falls. Purely decorative: the figures
// are not personas and carry no data — where the coloured communities sit is random on every load.
//
// Built to stay smooth on a weak machine: the pull-back plays once, then the whole lit crowd is
// painted into an offscreen canvas and nothing animates on its own any more. The light moves only
// when the visitor scrolls, and each of those frames is just two image copies and one small mask.
(() => {
  const T = window.TR;
  const cv = document.getElementById('hero-canvas');
  if (!T || !cv) return;
  const hero = document.querySelector('.hero');
  const skip = document.getElementById('hero-skip');
  const ctx = cv.getContext('2d');

  const HUES = ['#F4C95D', '#FF7D7D', '#B88CFF'];  // the communities
  const SLATES = ['#47586E', '#3B4A5E', '#313F52', '#404F64', '#29374B'];
  // The two themes. At night the light adds to the dark ground; by day it tints a pale one.
  const THEMES = {
    dark: { SLATES: ['#47586E', '#3B4A5E', '#313F52', '#404F64', '#29374B'], FLOOR: [7, 18, 32], GLINT: [205, 232, 255], blend: 'lighter', land: ['#0A1622', '#060E17', '#03080E'], shadow: 'rgba(0,0,0,.6)',
      coast: ['rgba(0,0,0,.55)', 'rgba(214,236,255,.3)', 'rgba(150,192,228,.55)'] },
    // by day: a blue map, near-white grey people, and a light that brightens rather than glows
    light: { FLOOR: [78, 112, 186], GLINT: [190, 212, 250], blend: 'screen', land: ['#AFC8F3', '#9FBBEC', '#90AEE4'], shadow: 'rgba(20,50,120,.3)',
      coast: ['rgba(20,50,110,.3)', 'rgba(255,255,255,.8)', 'rgba(20,80,200,.75)'],
      SLATES: ['#F4F6FA', '#E9EDF3', '#DEE3EB', '#ECEFF5', '#E2E7EF'] },
  };
  const theme = () => THEMES[document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'];
  let P = theme();
  const FIG_H = 30, FIG_W = 19, ZOOM = 9, HOLD = 900, PULL = 4600;
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // A weak device skips the pull-back and starts on the finished map.
  const weak = (navigator.hardwareConcurrency || 8) <= 2 || (navigator.deviceMemory || 8) <= 2 ||
    (navigator.connection && navigator.connection.saveData);
  let lite = weak;

  const outline = new Path2D();
  T.rings.forEach(r => {
    r.forEach((q, i) => i ? outline.lineTo(q[0], q[1]) : outline.moveTo(q[0], q[1]));
    outline.closePath();
  });

  // ---- figure sprites: one shaded person per colour, drawn once ----
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  const mix = (a, b, k) => a.map((v, i) => Math.round(v + (b[i] - v) * k));
  const css = (c, alpha = 1) => `rgba(${c[0]},${c[1]},${c[2]},${alpha})`;

  function sprite(hex, fade, SH) {
    const SW = SH * FIG_W / FIG_H, PAD = Math.ceil(SH * .02);
    const base = rgb(hex), hi = mix(base, [255, 255, 255], .3), lo = mix(base, P.FLOOR, fade);
    const c = document.createElement('canvas');
    c.width = Math.ceil(SW + PAD * 2); c.height = SH + PAD * 2;
    const g = c.getContext('2d');
    const x = c.width / 2, top = PAD, bottom = PAD + SH, w = SW, h = SH;
    const hr = h * .15, neck = hr * .5, sh = top + hr * 2 + h * .03;  // shoulder line
    const soften = SH > 400 ? 'blur(.8px)' : 'none';
    g.filter = soften;

    // torso: light on the shoulders, melting into the floor further down
    g.beginPath();
    g.moveTo(x - neck, top + hr * 1.6);
    g.quadraticCurveTo(x - neck, sh - h * .01, x - neck * 2.1, sh + h * .005);
    g.bezierCurveTo(x - w * .36, sh + h * .02, x - w / 2, sh + h * .06, x - w / 2, sh + h * .2);
    g.lineTo(x - w * .47, bottom);
    g.lineTo(x + w * .47, bottom);
    g.lineTo(x + w / 2, sh + h * .2);
    g.bezierCurveTo(x + w / 2, sh + h * .06, x + w * .36, sh + h * .02, x + neck * 2.1, sh + h * .005);
    g.quadraticCurveTo(x + neck, sh - h * .01, x + neck, top + hr * 1.6);
    g.closePath();
    const body = g.createLinearGradient(0, sh, 0, bottom);
    body.addColorStop(0, css(hi)); body.addColorStop(.22, css(base)); body.addColorStop(.75, css(lo)); body.addColorStop(1, css(lo));
    g.fillStyle = body;
    g.fill();

    g.filter = 'none';
    g.globalCompositeOperation = 'source-atop';  // shading stays inside the torso
    const side = g.createLinearGradient(x - w / 2, 0, x + w / 2, 0);
    side.addColorStop(0, 'rgba(0,0,0,.3)'); side.addColorStop(.3, 'rgba(0,0,0,0)');
    side.addColorStop(.7, 'rgba(0,0,0,0)'); side.addColorStop(1, 'rgba(0,0,0,.3)');
    g.fillStyle = side; g.fillRect(0, 0, c.width, c.height);
    const under = g.createRadialGradient(x, sh - h * .01, 0, x, sh - h * .01, hr * 1.5);
    under.addColorStop(0, 'rgba(0,0,0,.42)'); under.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = under; g.fillRect(0, 0, c.width, c.height);
    g.globalCompositeOperation = 'source-over';

    // head: lit from the upper left
    g.filter = soften;
    const head = g.createRadialGradient(x - hr * .3, top + hr * .6, hr * .1, x, top + hr, hr * 1.25);
    head.addColorStop(0, css(mix(hi, [255, 255, 255], .12))); head.addColorStop(.55, css(base)); head.addColorStop(1, css(mix(base, [0, 0, 0], .4)));
    g.fillStyle = head;
    g.beginPath();
    g.ellipse(x, top + hr, hr * .82, hr, 0, 0, 6.2832);
    g.fill();
    return { c, SW, SH, PAD };
  }
  // Sharp for the figures in focus, soft for the ones out of focus, small once the camera has pulled back.
  // The close-up sizes are only drawn when the pull-back actually plays.
  let greySprites, hueSprites;
  function sprites(sizes) {  // redrawn when the theme changes, since the figures fade into its ground
    const set = (hex, fade) => Object.fromEntries(Object.entries(sizes).map(([k, v]) => [k, sprite(hex, fade, v)]));
    greySprites = P.SLATES.map(hex => set(hex, .92));
    hueSprites = Object.fromEntries(HUES.map(hex => [hex, set(hex, .8)]));
  }
  sprites(lite || still ? { small: 176 } : { big: 800, mid: 260, small: 176 });

  function draw(g, f, sprites, size) {
    const sp = sprites[size], kx = f.w / sp.SW, ky = f.h / sp.SH;
    g.drawImage(sp.c, f.x - f.w / 2 - sp.PAD * kx, f.y - f.h - sp.PAD * ky, sp.c.width * kx, sp.c.height * ky);
  }

  // ---- the crowd ----
  const figs = [], CELL = 40, cells = new Map();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const inside = (x, y) => ctx.isPointInPath(outline, x, y);
  const within = (x, y, h, w) =>
    inside(x, y) && inside(x, y - h) && inside(x - w / 2, y - h * .6) && inside(x + w / 2, y - h * .6);
  function free(x, y, h, w) {
    const gx = Math.floor(x / CELL), gy = Math.floor(y / CELL);
    for (let i = gx - 1; i <= gx + 1; i++) for (let j = gy - 1; j <= gy + 1; j++) {
      for (const f of cells.get(i + ':' + j) || []) {
        const dx = (x - f.x) / ((w + f.w) * .5), dy = (y - f.y) / ((h + f.h) * .26);
        if (dx * dx + dy * dy < 1) return false;
      }
    }
    return true;
  }
  function add(x, y, k) {
    const f = { x, y, h: FIG_H * k, w: FIG_W * k * (.95 + Math.random() * .1),
      grey: Math.floor(Math.random() * SLATES.length), hue: null, phase: Math.random() * 6.28 };
    figs.push(f);
    const key = Math.floor(x / CELL) + ':' + Math.floor(y / CELL);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(f);
  }
  for (let row = 0, y = 6; y < T.height + FIG_H; y += 14, row++) {
    for (let x = (row % 2) * 9; x < T.width; x += 18) {
      const fx = x + (Math.random() - .5) * 4, fy = y + (Math.random() - .5) * 3;
      const k = .95 + Math.random() * .1;
      if (within(fx, fy, FIG_H * k, FIG_W * k)) add(fx, fy, k);
    }
  }
  for (const scale of [.72, .52, .38]) {
    const sx = 18 * scale, sy = 14 * scale;
    for (let row = 0, y = sy; y < T.height; y += sy, row++) {
      for (let x = (row % 2) * sx / 2; x < T.width; x += sx) {
        const k = scale * (.95 + Math.random() * .1);
        if (free(x, y, FIG_H * k, FIG_W * k) && within(x, y, FIG_H * k, FIG_W * k)) add(x, y, k);
      }
    }
  }
  figs.sort((a, b) => a.y - b.y);  // back rows first
  const anyFig = () => figs[Math.floor(Math.random() * figs.length)];

  const cx = T.width * .52, cy = T.height * .52;
  const focal = figs.filter(f => f.h > FIG_H * .9)
    .reduce((a, b) => Math.hypot(b.x - cx, b.y - cy) < Math.hypot(a.x - cx, a.y - cy) ? b : a);

  // ---- who is coloured ----
  const smooth = u => { u = Math.min(Math.max(u, 0), 1); return u * u * (3 - 2 * u); };
  focal.hue = HUES[0];
  const near = figs.filter(f => f !== focal && Math.abs(f.h - focal.h) < 5)
    .sort((a, b) => Math.hypot(a.x - focal.x, a.y - focal.y) - Math.hypot(b.x - focal.x, b.y - focal.y));
  const left = near.find(f => f.x < focal.x - 12), right = near.find(f => f.x > focal.x + 12 && f !== left);
  if (left) left.hue = HUES[1];
  if (right) right.hue = HUES[2];
  const opening = [focal, left, right].filter(Boolean);

  const hubs = [];
  for (let tries = 0; hubs.length < 18 && tries < 500; tries++) {
    const c = anyFig();
    if (Math.hypot(c.x - focal.x, c.y - focal.y) < 140) continue;
    if (hubs.some(h => Math.hypot(c.x - h.x, c.y - h.y) < 95)) continue;
    hubs.push({ x: c.x, y: c.y, r: 48 + Math.random() * 40, hue: HUES[hubs.length % HUES.length], phase: Math.random() * 6.28 });
  }
  for (const f of figs) {
    if (f.hue) continue;
    for (const h of hubs) {
      const d = Math.hypot(f.x - h.x, f.y - h.y) / h.r;
      if (d < 1 && Math.random() < .9 - .55 * d * d) { f.hue = h.hue; break; }
    }
  }

  // ---- the light ----
  const lamp = { x: focal.x, y: focal.y - focal.h / 2, R: 175 };
  const stops = [[.24, .47], [.4, .64], [.56, .44], [.73, .6], [.87, .44], [.66, .3], [.42, .33]]
    .map(([u, v]) => ({ x: u * T.width, y: v * T.height }))
    .filter(q => inside(q.x - 60, q.y) && inside(q.x + 60, q.y) && inside(q.x, q.y - 35) && inside(q.x, q.y + 35));
  // The route the light takes as the page scrolls: from the opening group through every region.
  const route = [{ x: lamp.x, y: lamp.y }, ...stops];
  function along(p) {  // a smooth (Catmull-Rom) point on the route, p in 0..1
    const n = route.length - 1;
    if (n < 1) return route[0];
    const t = Math.min(Math.max(p, 0), 1) * n, i = Math.min(Math.floor(t), n - 1), u = t - i;
    const p0 = route[Math.max(i - 1, 0)], p1 = route[i], p2 = route[i + 1], p3 = route[Math.min(i + 2, n)];
    const cr = (a, b, c, d) => .5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u);
    return { x: cr(p0.x, p1.x, p2.x, p3.x), y: cr(p0.y, p1.y, p2.y, p3.y) };
  }
  const reach = (x, y) => Math.hypot((x - lamp.x) / lamp.R, (y - lamp.y) / (lamp.R * .62));
  const lit = (x, y) => 1 - smooth((reach(x, y) - .45) / .55);

  function blob(g, x, y, r, colour, alpha, squash) {
    g.save();
    g.translate(x, y); g.scale(1, squash);
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, r);
    gr.addColorStop(0, css(colour, alpha)); gr.addColorStop(1, css(colour, 0));
    g.fillStyle = gr;
    g.beginPath(); g.arc(0, 0, r, 0, 6.2832); g.fill();
    g.restore();
  }
  function glints(g, phase, strength) {  // three pools that slide over each other, like light off water
    g.save();
    g.globalCompositeOperation = P.blend;
    for (let i = 0; i < 3; i++) {
      const a = phase + i * 2.1, r = lamp.R * (.82 + .12 * Math.sin(a * .7));
      blob(g, lamp.x + Math.cos(a) * lamp.R * .16, lamp.y + Math.sin(a * 1.3) * lamp.R * .08, r, P.GLINT, .075 * strength, .62);
    }
    g.restore();
  }
  function shaft(g, strength) {  // a faint shaft from above, just enough to give the air some volume
    const ax = T.width / 2 + (lamp.x - T.width / 2) * .4, ay = -170;
    g.save();
    g.globalCompositeOperation = P.blend;
    for (let i = 0; i < 4; i++) {
      const k = 1 - i * .2, gr = g.createLinearGradient(0, ay, 0, lamp.y);
      gr.addColorStop(0, css(P.GLINT, .045 * strength)); gr.addColorStop(1, css(P.GLINT, .012 * strength));
      g.fillStyle = gr;
      g.beginPath();
      g.moveTo(ax - 8 * k, ay); g.lineTo(ax + 8 * k, ay);
      g.lineTo(lamp.x + lamp.R * k, lamp.y);
      g.ellipse(lamp.x, lamp.y, lamp.R * k, lamp.R * .62 * k, 0, 0, Math.PI);
      g.closePath(); g.fill();
    }
    g.restore();
  }
  function land(g) {  // the map: a low relief resting on its own shadow
    g.save();
    g.shadowColor = P.shadow; g.shadowBlur = 24 * dpr; g.shadowOffsetY = 9 * dpr;
    const gr = g.createLinearGradient(0, 0, T.width * .3, T.height);
    gr.addColorStop(0, P.land[0]); gr.addColorStop(.55, P.land[1]); gr.addColorStop(1, P.land[2]);
    g.fillStyle = gr;
    g.fill(outline);
    g.restore();
  }
  function coast(g, hair, alpha) {  // embossed: shadow below-right, highlight above-left, a quiet line between
    g.lineJoin = 'round';
    g.lineWidth = hair * 1.1;
    for (const [dx, dy, colour] of [[1.2, 1.6, P.coast[0]], [-.8, -.9, P.coast[1]], [0, 0, P.coast[2]]]) {
      g.save();
      g.translate(dx * hair, dy * hair);
      g.globalAlpha = alpha;
      g.strokeStyle = colour;
      g.stroke(outline);
      g.restore();
    }
  }

  // ---- layout ----
  let W, H, dpr, s, ox, oy;
  function layout() {
    dpr = Math.min(devicePixelRatio || 1, lite ? 1 : 1.5);
    W = cv.clientWidth; H = cv.clientHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    const narrow = W < 720;
    const availW = W * (narrow ? .96 : .86), availH = H * (narrow ? .46 : .6);
    s = Math.min(availW / T.width, availH / T.height);
    ox = (W - T.width * s) / 2;
    oy = (narrow ? H * .14 : H * .1) + (availH - T.height * s) / 2;
  }

  // ---- the pull-back (plays once) ----
  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  let t0 = performance.now(), last = t0, probeN = 0, probeSum = 0, settled = false;

  function intro(now) {
    if (settled) return;
    const t = now - t0, raw = now - last; last = now;
    // Too slow to hold the frame rate: skip straight to the finished map.
    if (++probeN > 12 && probeN <= 42) {
      probeSum += raw;
      if (probeN === 42 && probeSum / 30 > 34) { lite = true; return settle(); }
    }
    if (t > HOLD + PULL) return settle();
    const e = ease(Math.min(Math.max((t - HOLD) / PULL, 0), 1));
    const z = Math.pow(ZOOM, 1 - e);
    const fxRest = ox + focal.x * s, fyRest = oy + (focal.y - focal.h / 2) * s;
    const px = W / 2 + (fxRest - W / 2) * e, py = H * .5 + (fyRest - H * .5) * e;
    const k = s * z * dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.setTransform(k, 0, 0, k, (px - focal.x * s * z) * dpr, (py - (focal.y - focal.h / 2) * s * z) * dpr);

    const m = 30 / z;
    const x0 = focal.x - px / (s * z) - m, x1 = focal.x + (W - px) / (s * z) + m;
    const y0 = focal.y - py / (s * z) - m, y1 = focal.y + (H - py) / (s * z) + m + FIG_H * 1.2;
    const on = smooth(t / 700), far = smooth((t - HOLD) / PULL);
    if (far > 0) { ctx.globalAlpha = far; land(ctx); ctx.globalAlpha = 1; }

    ctx.save();
    ctx.clip(outline);
    blob(ctx, lamp.x, lamp.y, lamp.R, P.FLOOR, on * (1 - far * .6), .62);
    glints(ctx, now / 1900, on * (.35 + .65 * far));
    ctx.globalCompositeOperation = P.blend;
    for (const h of hubs) {
      const v = on * lit(h.x, h.y) * (.8 + .2 * Math.sin(now / 1500 + h.phase));
      if (v > .01) blob(ctx, h.x, h.y, h.r * 1.15, rgb(h.hue), .11 * v, .7);
    }
    for (const f of opening) {
      const v = (1 - far) * on * (.75 + .25 * Math.sin(now / 650 + f.phase));
      if (v > .01) blob(ctx, f.x, f.y - f.h * .55, f.h * 1.3, rgb(f.hue), .2 * v, 1);
    }
    ctx.globalCompositeOperation = 'source-over';
    for (const f of figs) {
      if (f.x < x0 || f.x > x1 || f.y < y0 || f.y > y1) continue;
      const light = on * lit(f.x, f.y - f.h / 2);
      if (light < .01) continue;
      const colour = f.hue ? light * (.8 + .2 * Math.sin(now / 650 + f.phase)) : 0;
      const size = z > 3 && Math.abs(f.y - focal.y) < 16 ? 'big' : z > 1.6 ? 'mid' : 'small';
      ctx.globalAlpha = light; draw(ctx, f, greySprites[f.grey], size);
      if (colour >= .01) { ctx.globalAlpha = colour; draw(ctx, f, hueSprites[f.hue], size); }
    }
    ctx.globalAlpha = 1;
    ctx.restore();
    shaft(ctx, on * far);
    if (far > 0) coast(ctx, 1 / (s * z), far);
    if (t > HOLD + PULL * .72) hero.classList.add('is-ready');
    requestAnimationFrame(intro);
  }

  // ---- the finished map: painted once, then only the light moves ----
  let base, crowd, top, pool;
  const canvas = () => { const c = document.createElement('canvas'); c.width = cv.width; c.height = cv.height; return c; };
  function paint() {
    const k = s * dpr, at = g => g.setTransform(k, 0, 0, k, ox * dpr, oy * dpr);
    base = canvas(); crowd = canvas(); top = canvas(); pool = document.createElement('canvas');
    let g = base.getContext('2d'); at(g); land(g);
    g = crowd.getContext('2d'); at(g);  // the whole crowd as if it stood in full light
    g.save(); g.clip(outline);
    g.globalCompositeOperation = P.blend;
    for (const h of hubs) blob(g, h.x, h.y, h.r * 1.15, rgb(h.hue), .11 * .9, .7);
    g.globalCompositeOperation = 'source-over';
    for (const f of figs) {
      draw(g, f, greySprites[f.grey], 'small');
      if (f.hue) { g.globalAlpha = .9; draw(g, f, hueSprites[f.hue], 'small'); g.globalAlpha = 1; }
    }
    g.restore();
    g = top.getContext('2d'); at(g); coast(g, 1 / s, 1);
  }
  function frame() {
    const k = s * dpr, R = lamp.R * k, cxp = (ox + lamp.x * s) * dpr, cyp = (oy + lamp.y * s) * dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.drawImage(base, 0, 0);
    // floor and glints under the crowd
    ctx.setTransform(k, 0, 0, k, ox * dpr, oy * dpr);
    ctx.save(); ctx.clip(outline);
    blob(ctx, lamp.x, lamp.y, lamp.R, P.FLOOR, .4, .62);
    glints(ctx, (lamp.x + lamp.y) / 90, 1);
    ctx.restore();
    // the crowd, cut out by the pool of light (same fall-off as the pull-back)
    const pw = Math.ceil(R * 2) + 2, ph = Math.ceil(R * 1.24) + 2;
    if (pool.width !== pw || pool.height !== ph) { pool.width = pw; pool.height = ph; }
    const sx = Math.round(cxp - pw / 2), sy = Math.round(cyp - ph / 2);
    const g = pool.getContext('2d');
    g.globalCompositeOperation = 'copy';
    g.drawImage(crowd, -sx, -sy);
    g.globalCompositeOperation = 'destination-in';
    g.save(); g.translate(pw / 2, ph / 2); g.scale(1, .62);
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, R);
    gr.addColorStop(0, '#000'); gr.addColorStop(.45, '#000'); gr.addColorStop(.5875, 'rgba(0,0,0,.844)');
    gr.addColorStop(.725, 'rgba(0,0,0,.5)'); gr.addColorStop(.8625, 'rgba(0,0,0,.156)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(-R, -R, R * 2, R * 2);
    g.restore();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(pool, sx, sy);
    if (!lite) { ctx.setTransform(k, 0, 0, k, ox * dpr, oy * dpr); shaft(ctx, 1); ctx.setTransform(1, 0, 0, 1, 0, 0); }
    ctx.drawImage(top, 0, 0);
  }

  // ---- scrolling moves the light ----
  let target = { x: lamp.x, y: lamp.y }, moving = false;
  function progress() {
    const r = hero.getBoundingClientRect(), span = hero.offsetHeight - innerHeight;
    return span > 0 ? Math.min(Math.max(-r.top / span, 0), 1) : 0;
  }
  function chapters(p) {  // the hero copy changes as the light moves on
    const steps = hero.querySelectorAll('[data-step]'), n = steps.length;
    const i = Math.min(Math.floor(p * n * .999), n - 1);
    steps.forEach((el, j) => el.classList.toggle('is-on', j === i));
  }
  function step() {
    const dx = target.x - lamp.x, dy = target.y - lamp.y;
    lamp.x += dx * .14; lamp.y += dy * .14;
    const done = Math.abs(dx) < .4 && Math.abs(dy) < .4;
    if (done) { lamp.x = target.x; lamp.y = target.y; }
    frame();
    moving = !done;
    if (moving) requestAnimationFrame(step);
  }
  function onScroll() {
    if (!settled) return;
    const p = progress();
    chapters(p);
    target = along(p);
    if (!moving) { moving = true; requestAnimationFrame(step); }
  }

  function settle() {
    if (settled) return;
    settled = true;
    hero.classList.add('is-ready', 'is-settled');
    layout(); paint();
    const p = progress();
    target = along(p); lamp.x = target.x; lamp.y = target.y;
    chapters(p);
    frame();
  }

  let resizeTimer;
  addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { layout(); if (settled) { paint(); frame(); } }, 150);
  });
  addEventListener('scroll', onScroll, { passive: true });
  if (skip) skip.addEventListener('click', settle);
  new MutationObserver(() => {
    if (theme() === P) return;
    P = theme();
    settle();  // a theme switch ends the pull-back; the finished map is redrawn in the new colours
    sprites({ small: 176 });
    paint(); frame();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  layout();
  if (still || lite || progress() > 0) settle();
  else requestAnimationFrame(t => { t0 = last = t; intro(t); });
})();
