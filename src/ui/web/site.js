// Perspectome — small interaction layer for the intro page. No cookies, storage or tracking.
(() => {
  // Sections fade in once as they enter the viewport.
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
  }, { rootMargin: "0px 0px -10% 0px", threshold: .06 });
  document.querySelectorAll("[data-reveal]").forEach((el) => io.observe(el));

  // The hero light only moves while the hero is on screen.
  const hero = document.querySelector(".hero, .auth-side");
  if (hero) new IntersectionObserver(([e]) => hero.classList.toggle("is-off", !e.isIntersecting)).observe(hero);

  // Menu: underline the section in view.
  const links = [...document.querySelectorAll('.menu ul a[href^="#"]')];
  const spy = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) {
      links.forEach((a) => a.setAttribute("aria-current", String(a.getAttribute("href") === "#" + e.target.id)));
    }
  }, { rootMargin: "-45% 0px -50% 0px" });
  links.forEach((a) => { const s = document.querySelector(a.getAttribute("href")); if (s) spy.observe(s); });
})();
