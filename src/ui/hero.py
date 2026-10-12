"""Intro: a close-up of a few people that pulls back into a relief map of Turkey.

A handful of figures breathe in the colours of different communities; the
camera eases back over a dark relief map, and a soft light, like a reflection
off water, drifts across it. Only where the light falls does the crowd show —
grey silhouettes and the communities' colours; everything else stays dark.

Purely decorative. The figures are not personas and carry no data — where the
coloured communities sit is random on every load.
"""

from __future__ import annotations

from pathlib import Path

from src.ui import theme

_TURKEY = Path(__file__).parent / "assets" / "turkey.json"

_HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<link rel="stylesheet" href="__FONT__">
<style>
  /* No frame: a deep-sea glow in the middle that eases all the way to black before it reaches any edge. */
  html, body { margin: 0; height: 100%; overflow: hidden; font-family: 'Instrument Sans', system-ui, sans-serif;
    background: #000 radial-gradient(ellipse closest-side at 50% 44%,
      #0B2640 0%, #0A2138 16%, #081A2E 32%, #061423 48%, #040D18 63%, #02070E 78%, #010306 90%, #000 100%); }
  /* The scene itself also dissolves towards the edges, so nothing is ever cut off by the frame. */
  canvas, .grain-box { position: absolute; inset: 0; width: 100%; height: 100%;
    -webkit-mask-image: linear-gradient(90deg, transparent, #000 9%, #000 91%, transparent),
      linear-gradient(transparent, #000 9%, #000 86%, transparent);
    -webkit-mask-composite: source-in;
    mask-image: linear-gradient(90deg, transparent, #000 9%, #000 91%, transparent),
      linear-gradient(transparent, #000 9%, #000 86%, transparent);
    mask-composite: intersect; }
  .grain-box { overflow: hidden; pointer-events: none; }
  /* very fine film grain */
  .grain { position: absolute; inset: -60%; pointer-events: none; opacity: .05;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .7 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
    animation: grain .8s steps(5) infinite; }
  @keyframes grain { to { transform: translate(-90px, 70px); } }
  .lite .grain { display: none; }
  /* The title keeps its own band at the bottom of the frame; the map never reaches into it. */
  .copy { position: absolute; left: 10%; right: 10%; bottom: 18px; text-align: center; color: __INK__;
    opacity: 0; transform: translateY(12px); transition: opacity 1.6s ease, transform 1.6s ease;
    pointer-events: none; }
  .copy.on { opacity: 1; transform: none; }
  h1 { font-weight: 500; font-size: 44px; line-height: 1.1; letter-spacing: -.03em; margin: 0 0 8px; }
  p { margin: 0; color: __MUTED__; font-size: 15px; line-height: 1.4; }
  .note { position: absolute; right: 10%; top: 12px; font-size: 11px; color: __MUTED__; opacity: .55; }
  #skip { position: absolute; right: 10%; top: 38px; padding: 6px 14px; border-radius: 999px; cursor: pointer;
    font: 500 12px 'Instrument Sans', system-ui, sans-serif; color: __MUTED__; background: rgba(14, 30, 50, .6);
    border: 1px solid rgba(140, 180, 220, .2); transition: opacity .6s ease, color .2s ease; }
  #skip:hover, #skip:focus-visible { color: __INK__; }
  #skip.off { opacity: 0; pointer-events: none; }
  @media (max-width: 640px) { h1 { font-size: 32px; } p { font-size: 13.5px; } }
  @media (prefers-reduced-motion: reduce) { .grain { animation: none; } }
</style></head>
<body>
<canvas id="c" aria-label="Türkiye haritası üzerinde farklı renklerde insan toplulukları"></canvas>
<div class="grain-box"><div class="grain"></div></div>
<div class="copy" id="copy">
  <h1>Perspectome</h1>
  <p>Türkiye için yapay toplum laboratuvarı — bireyleri değil, eğilimleri gösterir.</p>
</div>
<div class="note">Figürler temsilidir, veri göstermez</div>
<button id="skip" type="button">Geç</button>
<script>
const T = __TURKEY__;
const HUES = ['__AMBER__', '__CORAL__', '__PURPLE__'];  // the communities
const SLATES = ['#47586E', '#3B4A5E', '#313F52', '#404F64', '#29374B'];
const FLOOR = [7, 18, 32];  // what the crowd fades into
const GLINT = [205, 232, 255];  // the drifting light
const FIG_H = 30, FIG_W = 19, ZOOM = 9, HOLD = 900, PULL = 4600;
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
let lite = false;  // set when the device can't hold the frame rate

const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const copy = document.getElementById('copy');
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
  const base = rgb(hex), hi = mix(base, [255, 255, 255], .3), lo = mix(base, FLOOR, fade);
  const c = document.createElement('canvas');
  c.width = Math.ceil(SW + PAD * 2); c.height = SH + PAD * 2;
  const g = c.getContext('2d');
  const x = c.width / 2, top = PAD, bottom = PAD + SH, w = SW, h = SH;
  const hr = h * .15, neck = hr * .5, sh = top + hr * 2 + h * .03;  // shoulder line
  const soften = SH > 400 ? 'blur(.8px)' : 'none';  // just enough to take the edge off, no outline
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
  const side = g.createLinearGradient(x - w / 2, 0, x + w / 2, 0);  // rounder: darker towards the arms
  side.addColorStop(0, 'rgba(0,0,0,.3)'); side.addColorStop(.3, 'rgba(0,0,0,0)');
  side.addColorStop(.7, 'rgba(0,0,0,0)'); side.addColorStop(1, 'rgba(0,0,0,.3)');
  g.fillStyle = side; g.fillRect(0, 0, c.width, c.height);
  const under = g.createRadialGradient(x, sh - h * .01, 0, x, sh - h * .01, hr * 1.5);  // shadow under the head
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
// Three sizes: sharp for the figures in focus, soft for the ones out of focus
// in the close-up, and small once the camera has pulled back.
const pair = (hex, fade) => ({ big: sprite(hex, fade, 800), mid: sprite(hex, fade, 260), small: sprite(hex, fade, 176) });
const greySprites = SLATES.map(hex => pair(hex, .92));
const hueSprites = Object.fromEntries(HUES.map(hex => [hex, pair(hex, .8)]));

function draw(f, sprites, size) {
  const sp = sprites[size], kx = f.w / sp.SW, ky = f.h / sp.SH;
  ctx.drawImage(sp.c, f.x - f.w / 2 - sp.PAD * kx, f.y - f.h - sp.PAD * ky, sp.c.width * kx, sp.c.height * ky);
}

// ---- the crowd ----
// Even-sized figures in tight, overlapping rows fill the country; smaller
// ones then go only where a full-size figure didn't fit, along the border.
const figs = [], CELL = 40, cells = new Map();
ctx.setTransform(1, 0, 0, 1, 0, 0);
const inside = (x, y) => ctx.isPointInPath(outline, x, y);
const within = (x, y, h, w) =>
  inside(x, y) && inside(x, y - h) && inside(x - w / 2, y - h * .6) && inside(x + w / 2, y - h * .6);
function free(x, y, h, w) {  // looks only at figures in the neighbouring grid cells
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
    grey: greySprites[Math.floor(Math.random() * SLATES.length)], hue: null, phase: Math.random() * 6.28 };
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
// The opening group: the focal figure and one neighbour on each side, each from another community.
focal.hue = HUES[0];
const near = figs.filter(f => f !== focal && Math.abs(f.h - focal.h) < 5)
  .sort((a, b) => Math.hypot(a.x - focal.x, a.y - focal.y) - Math.hypot(b.x - focal.x, b.y - focal.y));
const left = near.find(f => f.x < focal.x - 12), right = near.find(f => f.x > focal.x + 12 && f !== left);
if (left) left.hue = HUES[1];
if (right) right.hue = HUES[2];
const opening = [focal, left, right].filter(Boolean);

// Communities: patches of the crowd that share a colour, spread evenly and in equal number.
const hubs = [];
for (let tries = 0; hubs.length < 18 && tries < 500; tries++) {
  const c = anyFig();
  if (Math.hypot(c.x - focal.x, c.y - focal.y) < 140) continue;  // the opening group stands apart
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

// ---- the light: one soft pool that drifts from region to region ----
const lamp = { x: focal.x, y: focal.y - focal.h / 2, vx: 0, vy: 0, R: 175, next: 0 };
const SPEED = 52;  // map units per second
const stops = [[.24, .47], [.4, .64], [.56, .44], [.73, .6], [.87, .44], [.66, .3], [.42, .33]]
  .map(([u, v]) => ({ x: u * T.width, y: v * T.height }))
  .filter(q => inside(q.x - 60, q.y) && inside(q.x + 60, q.y) && inside(q.x, q.y - 35) && inside(q.x, q.y + 35));
function moveLamp(dt) {
  if (!stops.length) return;
  let q = stops[lamp.next % stops.length];
  if (Math.hypot(q.x - lamp.x, q.y - lamp.y) < 28) q = stops[++lamp.next % stops.length];
  const dx = q.x - lamp.x, dy = q.y - lamp.y, d = Math.hypot(dx, dy) || 1, turn = Math.min(1, dt * 1.1);
  lamp.vx += (dx / d * SPEED - lamp.vx) * turn;
  lamp.vy += (dy / d * SPEED - lamp.vy) * turn;
  lamp.x += lamp.vx * dt; lamp.y += lamp.vy * dt;
}
// 0 at the centre of the pool of light, 1 at its edge (the pool is an ellipse on the ground).
const reach = (x, y) => Math.hypot((x - lamp.x) / lamp.R, (y - lamp.y) / (lamp.R * .62));
const lit = (x, y) => 1 - smooth((reach(x, y) - .45) / .55);

function blob(x, y, r, colour, alpha, squash) {
  ctx.save();
  ctx.translate(x, y); ctx.scale(1, squash);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
  g.addColorStop(0, css(colour, alpha)); g.addColorStop(1, css(colour, 0));
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(0, 0, r, 0, 6.2832); ctx.fill();
  ctx.restore();
}
// Light on the ground: three overlapping pools that slide over each other, like a reflection off water.
function glints(now, strength) {
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 3; i++) {
    const a = now / 1900 + i * 2.1, r = lamp.R * (.82 + .12 * Math.sin(a * .7));
    blob(lamp.x + Math.cos(a) * lamp.R * .16, lamp.y + Math.sin(a * 1.3) * lamp.R * .08, r, GLINT, .075 * strength, .62);
  }
  ctx.restore();
}
// A faint shaft from above, just enough to give the air some volume.
function shaft(strength) {
  const ax = T.width / 2 + (lamp.x - T.width / 2) * .4, ay = -170;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 4; i++) {
    const k = 1 - i * .2, g = ctx.createLinearGradient(0, ay, 0, lamp.y);
    g.addColorStop(0, css(GLINT, .045 * strength)); g.addColorStop(1, css(GLINT, .012 * strength));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(ax - 8 * k, ay); ctx.lineTo(ax + 8 * k, ay);
    ctx.lineTo(lamp.x + lamp.R * k, lamp.y);
    ctx.ellipse(lamp.x, lamp.y, lamp.R * k, lamp.R * .62 * k, 0, 0, Math.PI);
    ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}

let W, H, dpr, s, ox, oy;
function layout() {
  dpr = lite ? 1 : Math.min(devicePixelRatio || 1, 2);
  W = cv.clientWidth; H = cv.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr;
  // The map gets whatever the title doesn't need: the title's real height is measured, so a
  // subtitle that wraps onto two lines on a narrow window still can't run into the map.
  const band = copy.offsetHeight + 18 + 22;
  const availW = W * .8, availH = Math.max(H * .86 - band - H * .09, 80);
  s = Math.min(availW / T.width, availH / T.height);
  ox = (W - T.width * s) / 2;
  oy = H * .125 + (availH - T.height * s) / 2;
}
addEventListener('resize', layout);
layout();
if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);  // the web font changes the title's height

const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
let t0 = performance.now(), last = t0, probeN = 0, probeSum = 0;
const skip = document.getElementById('skip');
skip.addEventListener('click', () => { t0 = performance.now() - HOLD - PULL - 1; });

function frame(now) {
  const t = still ? HOLD + PULL + 3000 : now - t0;
  const raw = now - last, dt = Math.min(raw / 1000, .05); last = now;
  // Slow device: drop to a lighter version of the scene. The first frames are
  // skipped — they include one-off work — and the next sixty are timed.
  if (!lite && !still && probeN < 80 && ++probeN > 20) {
    probeSum += raw;
    if (probeN === 80 && probeSum / 60 > 34) { lite = true; document.body.classList.add('lite'); layout(); }
  }
  const e = ease(Math.min(Math.max((t - HOLD) / PULL, 0), 1));
  const z = Math.pow(ZOOM, 1 - e);
  // Camera: start centred on the focal figure, end with the whole map at rest.
  const fxRest = ox + focal.x * s, fyRest = oy + (focal.y - focal.h / 2) * s;
  const px = W / 2 + (fxRest - W / 2) * e, py = H * .5 + (fyRest - H * .5) * e;
  const k = s * z * dpr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.setTransform(k, 0, 0, k, (px - focal.x * s * z) * dpr, (py - (focal.y - focal.h / 2) * s * z) * dpr);

  const m = 30 / z;  // cull what the camera can't see
  const x0 = focal.x - px / (s * z) - m, x1 = focal.x + (W - px) / (s * z) + m;
  const y0 = focal.y - py / (s * z) - m, y1 = focal.y + (H - py) / (s * z) + m + FIG_H * 1.2;
  const settled = t > HOLD + PULL;
  if (settled && !still) moveLamp(dt);
  const on = smooth(t / 700);  // the scene comes up out of the dark
  const far = smooth((t - HOLD) / PULL);  // how much of the wide view has arrived
  const hair = 1 / (s * z);  // one screen pixel, whatever the zoom

  // The map: a low relief lit from the upper left, resting on its own shadow.
  if (far > 0) {
    ctx.save();
    ctx.globalAlpha = far;
    ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 24 * dpr; ctx.shadowOffsetY = 9 * dpr;
    const land = ctx.createLinearGradient(0, 0, T.width * .3, T.height);
    land.addColorStop(0, '#0A1622'); land.addColorStop(.55, '#060E17'); land.addColorStop(1, '#03080E');
    ctx.fillStyle = land;
    ctx.fill(outline);
    ctx.restore();
  }

  ctx.save();
  ctx.clip(outline);  // nothing is ever drawn outside the country
  blob(lamp.x, lamp.y, lamp.R, FLOOR, on * (1 - far * .6), .62);  // a floor for the lit crowd to stand on
  glints(now, on * (.35 + .65 * far));
  if (!lite) {
    ctx.globalCompositeOperation = 'lighter';
    for (const h of hubs) {  // each community's colour pools softly on the ground around it
      const v = on * lit(h.x, h.y) * (.8 + .2 * Math.sin(now / 1500 + h.phase));
      if (v > .01) blob(h.x, h.y, h.r * 1.15, rgb(h.hue), .11 * v, .7);
    }
    for (const f of opening) {  // and the opening figures give off a little of theirs
      const v = (1 - far) * on * (.75 + .25 * Math.sin(now / 650 + f.phase));
      if (v > .01) blob(f.x, f.y - f.h * .55, f.h * 1.3, rgb(f.hue), .2 * v, 1);
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  for (const f of figs) {
    if (f.x < x0 || f.x > x1 || f.y < y0 || f.y > y1) continue;
    const light = on * lit(f.x, f.y - f.h / 2);
    if (light < .01) continue;  // outside the light there is nothing to see: the rest of the country stays dark
    const grey = light;
    const colour = f.hue ? light * (.8 + .2 * Math.sin(now / 650 + f.phase)) : 0;
    // Depth of field in the close-up: only the focal row is sharp.
    const size = z > 3 && Math.abs(f.y - focal.y) < 16 ? 'big' : z > 1.6 ? 'mid' : 'small';
    if (grey >= .01) { ctx.globalAlpha = grey; draw(f, f.grey, size); }
    if (colour >= .01) { ctx.globalAlpha = colour; draw(f, hueSprites[f.hue], size); }  // slow breath, never a blink
  }
  ctx.globalAlpha = 1;
  ctx.restore();
  if (!lite) shaft(on * far);

  // The coastline, embossed: a shadow below-right, a highlight above-left, a quiet line between.
  if (far > 0) {
    ctx.lineJoin = 'round';
    ctx.lineWidth = hair * 1.1;
    for (const [dx, dy, colour] of [[1.2, 1.6, 'rgba(0,0,0,.55)'], [-.8, -.9, 'rgba(214,236,255,.3)'], [0, 0, 'rgba(150,192,228,.55)']]) {
      ctx.save();
      ctx.translate(dx * hair, dy * hair);
      ctx.globalAlpha = far;
      ctx.strokeStyle = colour;
      ctx.stroke(outline);
      ctx.restore();
    }
  }

  if (t > HOLD + PULL * .72) copy.classList.add('on');
  if (settled) skip.classList.add('off');
  if (!still) requestAnimationFrame(frame);
}
if (still) {  // no motion: the finished map, with the light resting on its first stop
  if (stops.length) { lamp.x = stops[0].x; lamp.y = stops[0].y; }
  frame(performance.now());
} else {
  requestAnimationFrame(frame);
}
</script>
</body></html>
"""


def html() -> str:
    out = _HTML
    for key, value in {
        "__TURKEY__": _TURKEY.read_text(encoding="utf-8"),
        "__FONT__": theme.FONT_URL,
        "__NIGHT__": theme.NIGHT,
        "__DEEP__": theme.DEEP,
        "__INK__": theme.INK,
        "__MUTED__": theme.MUTED,
        "__AMBER__": theme.COMMUNITIES[0],
        "__CORAL__": theme.COMMUNITIES[1],
        "__PURPLE__": theme.COMMUNITIES[2],
    }.items():
        out = out.replace(key, value)
    return out
