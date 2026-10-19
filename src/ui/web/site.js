// Perspectome — sign-in page and panel chrome. Only the theme choice is stored (localStorage); no cookies or tracking.
(() => {
  const root = document.documentElement;

  // Theme: light by default in the app, the choice is remembered.
  document.querySelectorAll('.theme-toggle').forEach((b) => b.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('pt-app-theme', next); } catch (e) {}
  }));

  // Side video on the sign-in page: never with reduced motion.
  const video = document.querySelector('.auth-side video');
  if (video && !matchMedia('(prefers-reduced-motion: reduce)').matches) video.play().catch(() => {});
})();
