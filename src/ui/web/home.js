// Perspectome — intro page interactions. Only the theme choice is stored (localStorage); no cookies or tracking.
(() => {
  document.documentElement.classList.add('js');
  const root = document.documentElement;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');

  // Theme: dark by default, the choice is remembered.
  document.querySelector('.theme-toggle')?.addEventListener('click', () => {
    const next = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.dataset.theme = next;
    try { localStorage.setItem('pt-theme', next); } catch (e) {}
  });

  // Intro video: plays only while the hero is on screen and never with reduced motion.
  const video = document.querySelector('.hero video');
  if (video) {
    const play = (on) => { if (on && !reduce.matches) video.play().catch(() => {}); else video.pause(); };
    new IntersectionObserver(([e]) => play(e.isIntersecting)).observe(video);
    reduce.addEventListener?.('change', () => play(!reduce.matches));
  }

  // People walking past, side by side: each row is one SVG strip drawn twice and slid by half its width,
  // so it loops seamlessly. Only a CSS transform moves (off the main thread); it pauses off screen.
  // Phones get two rows and fewer people.
  const PEOPLE = window.PTPeople;
  const seeded = (seed) => () => { seed = (seed + 0x6D2B79F5) >>> 0; let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
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
  const small = matchMedia('(max-width: 640px)').matches;
  const rows = small ? [[22, 'is-mid'], [18, 'is-near']] : [[34, 'is-far'], [28, 'is-mid'], [24, 'is-near']];
  const live = new IntersectionObserver((entries) => {
    for (const e of entries) e.target.classList.toggle('is-live', e.isIntersecting && !reduce.matches);
  });
  if (PEOPLE) document.querySelectorAll('[data-crowd]').forEach((el, i) => {
    const rand = seeded(4242 + i);
    for (const [n, cls] of rows) {
      const { out, w } = crowdRow(n, rand);
      const strip = `<svg viewBox="0 -12 ${w} 112" preserveAspectRatio="xMinYMax meet" style="aspect-ratio:${w}/112">${out}</svg>`;
      const row = document.createElement('div');
      row.className = 'crowd__row ' + cls;
      row.innerHTML = `<div class="crowd__strip">${strip}${strip}</div>`;
      el.append(row);
    }
    live.observe(el);
  });

  // Sections fade in once as they enter the viewport.
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -8% 0px', threshold: .06 });
  document.querySelectorAll('[data-reveal]').forEach((el) => io.observe(el));
})();
