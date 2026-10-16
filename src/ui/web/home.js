// Perspectome — intro page interactions. No cookies, storage or tracking.
(() => {
  const T = window.TR;
  const NS = 'http://www.w3.org/2000/svg';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- Turkey maps with people that light up at different places ----
  // Each [data-people] element gets the outline and N small figures at random points inside it.
  // The blinking is plain CSS opacity, so it costs the main thread nothing; it pauses off screen.
  function seeded(seed) {
    let a = seed >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const d = T ? T.rings.map(r => 'M' + r.map(q => q.join(',')).join('L') + 'Z').join('') : '';
  const probe = document.createElement('canvas').getContext('2d');
  const shape = T ? new Path2D(d) : null;
  const inside = (x, y) => probe.isPointInPath(shape, x, y);

  // Blinking coloured points scattered over the country: mostly blues, with the communities'
  // colours from the opening animation in between. Each point has a core, a soft halo and a ring
  // that widens as it fades — all CSS (opacity and transform), paused while off screen.
  const BLUES = ['#2F7BFF', '#6EA8FF', '#1E4FD0', '#9CC3FF'];
  const ACCENTS = ['#F4C95D', '#FF7D7D', '#B88CFF'];
  function dotsMap(el, i) {
    const n = Math.round((+el.dataset.people || 24) * 1.6), rand = seeded(+el.dataset.seed || (i + 1) * 977);
    const size = +el.dataset.size || 1;
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `-20 -20 ${T.width + 40} ${T.height + 40}`);
    svg.setAttribute('aria-hidden', 'true');
    let html = `<path class="tm-land" d="${d}"/>`;
    const placed = [];
    for (let tries = 0; placed.length < n && tries < n * 60; tries++) {
      const x = 20 + rand() * (T.width - 40), y = 15 + rand() * (T.height - 30);
      if (!inside(x, y) || !inside(x - 8, y) || !inside(x + 8, y)) continue;
      if (placed.some(p => Math.hypot(p[0] - x, p[1] - y) < 46)) continue;
      placed.push([x, y]);
    }
    // data-wave: a shock spreads from Ankara; each point lights up as the wave reaches it
    const wave = 'wave' in el.dataset, ex = 470, ey = 190;
    if (wave) {
      html += `<clipPath id="tmc${i}"><path d="${d}"/></clipPath><g clip-path="url(#tmc${i})">` +
        [0, 1, 2].map(k => `<circle class="tm-wave" cx="${ex}" cy="${ey}" r="60" style="--d:${k * 1.6}s"/>`).join('') + '</g>';
    }
    for (const [x, y] of placed) {
      const colour = rand() < .62 ? BLUES[Math.floor(rand() * BLUES.length)] : ACCENTS[Math.floor(rand() * ACCENTS.length)];
      const r = size * (7.5 + rand() * 5);
      const dl = wave ? -(4.8 - Math.hypot(x - ex, y - ey) / 110).toFixed(2) : (rand() * 6).toFixed(2), dur = wave ? '4.8' : (2.8 + rand() * 2.8).toFixed(2);
      html += `<g class="tm-d" style="--d:-${dl}s;--t:${dur}s;color:${colour}" transform="translate(${x.toFixed(1)} ${y.toFixed(1)})">` +
        `<circle class="tm-ring" r="${(r * 1.6).toFixed(1)}"/><circle class="tm-halo" r="${(r * 2.2).toFixed(1)}"/><circle class="tm-core" r="${r.toFixed(1)}"/></g>`;
    }
    svg.innerHTML = html;
    el.prepend(svg);
  }
  if (T) document.querySelectorAll('[data-people]').forEach(dotsMap);

  // ---- one picture per step, each drawn for what the step is about ----
  // All in a 400 × 260 box; motion is CSS only and stops while the picture is off screen.
  const PEOPLE = window.PTPeople;
  const person = (name, x, y, k, cls = '', style = '') =>
    `<g class="${cls}" style="${style}" transform="translate(${x} ${y}) scale(${k})">${PEOPLE.TYPES[name].svg}</g>`;
  const mini = (x, y, k, cls = '', style = '') =>  // a plain figure for small crowds
    `<g class="${cls}" style="${style}" transform="translate(${x} ${y}) scale(${k})"><circle cx="0" cy="-26" r="7"/><path d="M-11-6q0-11 11-11t11 11v6h-22z"/></g>`;
  const label = (x, y, text, cls = 'v-label', anchor = 'middle') => `<text class="${cls}" x="${x}" y="${y}" text-anchor="${anchor}">${text}</text>`;

  const VISUALS = {
    // a row of different people; one after another steps forward with a persona card above
    personas() {
      const names = ['business', 'elderwoman', 'student', 'girl', 'worker', 'longhair', 'elder'];
      return names.map((n, i) => {
        const x = 34 + i * 55.5, k = n === 'girl' ? 1.55 : 1.42, top = n === 'girl' ? 232 - 60 * k : 232 - 102 * k;
        return `<g class="v-pick" style="--d:${i * 1.1}s">` + person(n, x, 232, k, 'v-fig') +
          `<g class="v-tag"><rect x="${x - 24}" y="${top - 36}" width="48" height="26" rx="6"/>` +
          `<rect class="v-tag__l" x="${x - 17}" y="${top - 29}" width="34" height="4" rx="2"/><rect class="v-tag__l" x="${x - 17}" y="${top - 21}" width="22" height="4" rx="2"/></g></g>`;
      }).join('') + '<rect class="v-ground" x="10" y="232" width="380" height="2" rx="1"/>';
    },
    // a scenario text is written, then sent out; the people on the right react one by one
    scenario() {
      let s = '<rect class="v-card" x="34" y="44" width="128" height="164" rx="10"/><rect class="v-acc" x="34" y="44" width="128" height="26" rx="10"/><rect class="v-acc" x="34" y="58" width="128" height="12"/>';
      [92, 76, 88, 60, 84, 70].forEach((w, i) => { s += `<rect class="v-type" style="--d:${i * .35}s" x="50" y="${86 + i * 18}" width="${w}" height="7" rx="3.5"/>`; });
      [24, 46, 68].forEach((r, i) => { s += `<path class="v-wave" style="--d:${2.2 + i * .25}s" d="M180 ${126 - r} a${r} ${r} 0 0 1 0 ${r * 2}"/>`; });
      const spots = [[280, 120], [322, 112], [364, 124], [262, 196], [304, 188], [346, 198], [384, 186]];
      spots.forEach(([x, y], i) => { s += mini(x, y, 1.15, 'v-react', `--d:${3 + i * .18}s`); });
      return s;
    },
    // the three arms side by side: the same people, a different text, a different answer
    arms() {
      const cols = [['Treatment', 120, 'is-t'], ['Placebo', 74, 'is-p'], ['Vanilla', 52, 'is-v']];
      return cols.map(([name, h, cls], i) => {
        const x = 78 + i * 122;
        return label(x, 254, name) + mini(x - 22, 78, .9, 'v-fig') + mini(x, 72, .9, 'v-fig') + mini(x + 22, 78, .9, 'v-fig') +
          `<rect class="v-bar ${cls}" style="--d:${i * .3}s" x="${x - 30}" y="${232 - h}" width="60" height="${h}" rx="5"/>`;
      }).join('') +
        '<rect class="v-ground" x="16" y="232" width="368" height="2" rx="1"/>' +
        '<g class="v-delta"><path d="M116 108v-6h126v6"/>' + label(179, 96, 'fark', 'v-label is-strong') + '</g>';
    },
    // a jittery line that never leaves its band, and one real effect that rises above it
    noise() {
      const rand = seeded(91);
      let pts = '';
      for (let x = 0; x <= 720; x += 12) pts += `${x},${(160 + (rand() - .5) * 34).toFixed(1)} `;
      return '<rect class="v-band" x="20" y="136" width="360" height="48" rx="6"/>' +
        label(26, 128, 'gürültü tabanı', 'v-label', 'start') +
        '<clipPath id="v-noise-clip"><rect x="20" y="100" width="360" height="120"/></clipPath>' +
        `<g clip-path="url(#v-noise-clip)"><polyline class="v-noise" points="${pts}"/></g>` +
        '<g class="v-spike"><rect x="292" y="70" width="10" height="114" rx="5"/><circle cx="297" cy="66" r="9"/></g>' +
        label(316, 72, 'etki', 'v-label is-strong v-spike-l', 'start') +
        '<rect class="v-ground" x="20" y="214" width="360" height="2" rx="1"/>';
    },
    // the model's answers slide over the survey's until the two shapes agree
    curves() {
      return '<path class="v-real" d="M30 220C110 220 140 70 200 70S290 220 370 220"/>' +
        '<path class="v-model" d="M30 220C100 220 135 88 195 88S300 220 370 220Z"/>' +
        '<rect class="v-ground" x="20" y="220" width="360" height="2" rx="1"/>' +
        '<g class="v-legend"><rect class="v-real-k" x="250" y="26" width="18" height="4" rx="2"/>' + label(274, 32, 'Anket', 'v-label', 'start') +
        '<rect class="v-model-k" x="250" y="42" width="18" height="8" rx="2"/>' + label(274, 50, 'Model', 'v-label', 'start') + '</g>' +
        label(200, 250, 'mesafe (TVD) küçüldükçe uyum artar', 'v-label is-small');
    },
    // the same experiment through several models; the results meet in one comparison
    models() {
      const ys = [50, 112, 174];
      let s = '';
      ys.forEach((y, i) => {
        const path = `M126 ${y + 20}C180 ${y + 20} 180 130 236 130`;
        s += `<rect class="v-card" x="28" y="${y}" width="98" height="40" rx="10"/>` + label(77, y + 25, 'Model ' + 'ABC'[i], 'v-label is-strong') +
          `<path class="v-link" d="${path}"/><path class="v-pulse" style="--d:${i * .5}s" d="${path}"/>`;
      });
      s += '<circle class="v-node-ring" cx="262" cy="130" r="26"/><circle class="v-node" cx="262" cy="130" r="26"/>' +
        '<path class="v-check" d="M251 130l8 8 15-16"/>';
      [[310, 46], [330, 70], [350, 58]].forEach(([x, h], i) => { s += `<rect class="v-bar is-t" style="--d:${i * .3}s" x="${x}" y="${190 - h}" width="14" height="${h}" rx="3"/>`; });
      return s + '<rect class="v-ground" x="300" y="190" width="72" height="2" rx="1"/>';
    },
    // paired bars: the survey (outline) and the model (filled) settle onto each other
    validate() {
      const real = [70, 128, 96, 150, 84], start = [.55, 1.3, .7, 1.2, .62];
      let s = '';
      real.forEach((h, i) => {
        const x = 52 + i * 66;
        s += `<rect class="v-real-bar" x="${x}" y="${222 - h}" width="24" height="${h}" rx="4"/>` +
          `<rect class="v-fit" style="--a:${start[i]};--d:${i * .15}s" x="${x + 26}" y="${222 - h}" width="24" height="${h}" rx="4"/>`;
      });
      return s + '<rect class="v-ground" x="30" y="222" width="340" height="2" rx="1"/>' +
        '<g class="v-legend"><rect class="v-real-k2" x="40" y="22" width="12" height="12" rx="3"/>' + label(58, 32, 'Anket', 'v-label', 'start') +
        '<rect class="v-model-k" x="112" y="22" width="12" height="12" rx="3"/>' + label(130, 32, 'Model', 'v-label', 'start') + '</g>' +
        '<g class="v-ok"><circle cx="354" cy="30" r="15"/><path d="M347 30l5 5 9-10"/></g>';
    },
  };
  document.querySelectorAll('[data-visual]').forEach(el => {
    const make = VISUALS[el.dataset.visual];
    if (!make) return;
    el.insertAdjacentHTML('afterbegin', `<svg viewBox="0 0 400 260" aria-hidden="true">${make()}</svg>`);
  });

  // Animations only run while their element is on screen.
  const live = new IntersectionObserver((entries) => {
    for (const e of entries) {
      e.target.classList.toggle('is-live', e.isIntersecting);
      if (e.target.tagName === 'VIDEO' && !reduce) e.isIntersecting ? e.target.play().catch(() => {}) : e.target.pause();
    }
  }, { rootMargin: '80px' });
  document.querySelectorAll('[data-people], [data-visual], video[data-auto]').forEach(el => live.observe(el));

  // ---- people streaming past: rows of different people side by side ----
  // Business people, older people, children, students, workers… nobody repeats until everyone has
  // had a turn. Each row is one strip drawn twice and slid by half its width, so it loops seamlessly;
  // only a CSS transform moves, which the browser does off the main thread.
  function crowdRow(n, rand) {
    let x = 0, out = '';
    for (const name of PEOPLE.cast(n, rand)) {
      const t = PEOPLE.TYPES[name], k = .9 + rand() * .16, flip = rand() < .5 ? -1 : 1;
      x += t.w * k / 2;
      out += `<g class="c${Math.floor(rand() * 5)}" transform="translate(${x.toFixed(1)} 100) scale(${(k * flip).toFixed(3)} ${k.toFixed(3)})">${t.svg}</g>`;
      x += t.w * k / 2 + 3 + rand() * 9;
    }
    return { out, w: Math.ceil(x) };
  }
  document.querySelectorAll('[data-crowd]').forEach((el, i) => {
    const rand = seeded(4242 + i);
    for (const [n, cls] of [[40, 'is-far'], [34, 'is-mid'], [28, 'is-near']]) {
      const { out, w } = crowdRow(n, rand);
      const row = document.createElement('div');
      row.className = 'crowd__row ' + cls;
      const strip = `<svg viewBox="0 -12 ${w} 112" preserveAspectRatio="xMinYMax meet" style="aspect-ratio:${w}/112">${out}</svg>`;
      row.innerHTML = `<div class="crowd__strip">${strip}${strip}</div>`;
      el.append(row);
    }
    live.observe(el);
  });

  // ---- theme: dark by default, light on request; the choice is remembered on this device ----
  const root = document.documentElement, themeBtn = document.querySelector('.theme-toggle');
  const isLight = () => root.dataset.theme === 'light';
  const ariaLabel = () => themeBtn && themeBtn.setAttribute('aria-label', isLight() ? 'Koyu temaya geç' : 'Açık temaya geç');
  if (themeBtn) {
    ariaLabel();
    themeBtn.addEventListener('click', () => {
      root.dataset.theme = isLight() ? 'dark' : 'light';
      try { localStorage.setItem('pt-theme', root.dataset.theme); } catch (e) {}
      ariaLabel();
    });
  }

  // ---- sections fade in once ----
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -8% 0px', threshold: .05 });
  document.querySelectorAll('[data-reveal]').forEach(el => io.observe(el));

  // ---- header: transparent over the hero, solid below it ----
  const bar = document.querySelector('.topbar');
  const hero = document.querySelector('.hero');
  if (bar && hero) {
    const solid = () => bar.classList.toggle('is-solid', hero.getBoundingClientRect().bottom < 80);
    addEventListener('scroll', solid, { passive: true }); solid();
  }

  // ---- mobile menu ----
  const toggle = document.querySelector('.burger'), nav = document.getElementById('drawer');
  if (toggle && nav) {
    const set = open => { nav.classList.toggle('is-open', open); toggle.setAttribute('aria-expanded', String(open)); document.body.style.overflow = open ? 'hidden' : ''; };
    toggle.addEventListener('click', () => set(!nav.classList.contains('is-open')));
    nav.addEventListener('click', e => { if (e.target.closest('a, .drawer__close')) set(false); });
  }


  // ---- rail arrows ----
  document.querySelectorAll('[data-rail]').forEach(wrap => {
    const track = wrap.querySelector('.rail__track');
    wrap.querySelectorAll('[data-dir]').forEach(b => b.addEventListener('click', () => {
      track.scrollBy({ left: +b.dataset.dir * track.clientWidth * .8, behavior: reduce ? 'auto' : 'smooth' });
    }));
  });
})();
