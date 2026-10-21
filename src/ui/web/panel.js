// Perspectome — analysis panel. The server renders every answer; this file only
// sends questions, swaps chats and toggles chart tabs.
(() => {
  const thread = document.getElementById("thread");
  const head = document.getElementById("head");
  const crumb = document.getElementById("crumb");
  const homeBtn = document.getElementById("home");
  const form = document.getElementById("ask");
  const input = document.getElementById("q");
  const side = document.getElementById("side");
  const scrim = document.querySelector(".scrim");
  const opener = document.querySelector(".side-open");
  let current = null;
  let state = { counts: {} };
  let busy = false;

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (path) => `<span class="w-ico"><svg class="nav-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg></span>`;
  const ICONS = {
    scenario: "M5 19V9M10 19V5M15 19v-7M20 19v-4",
    probe: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17zM8.5 12.2l2.4 2.4 4.6-4.9",
    models: "M4 5h16v14H4zM4 10h16M10 10v9",
  };

  async function api(path, body) {
    const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    if (res.status === 401) { location.href = "/giris"; throw new Error("auth"); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Bir sorun oluştu.");
    return data;
  }

  function setHead(kicker, title, sub, action = "", trail = "") {
    head.innerHTML = `<div>${kicker ? `<p class="kicker">${esc(kicker)}</p>` : ""}<h1>${esc(title)}</h1>${sub ? `<p>${esc(sub)}</p>` : ""}</div>${action}`;
    crumb.hidden = !trail;
    crumb.textContent = trail;
  }

  function welcome() {
    current = null;
    setHead("Panel", "Perspectome'a hoş geldin", "Hazır senaryo ve doğrulama çalıştırmalarının genel durumu.");
    const c = state.counts || {};
    const stat = (label, n, kind) => `<div class="w-stat"><div><p>${label}</p><b>${n ?? 0}</b></div>${icon(ICONS[kind])}</div>`;
    thread.innerHTML = `<div class="welcome">
      <div class="w-stats">${stat("Senaryo çalıştırması", c.scenarios, "scenario")}${stat("Doğrulama sorusu", c.probes, "probe")}${stat("Karşılaştırılan model", c.models, "models")}</div>
      <div class="w-grid">
        <section class="w-card"><h2>Nasıl okunur</h2><ul class="w-read">
          <li><b>Etki</b><span>Senaryo kolu eksi placebo kolu. Nüfustaki oran değil, senaryonun yarattığı fark.</span></li>
          <li><b>Gürültü tabanı</b><span>Aynı ayarın tekrarındaki oynaklık. Bundan küçük etkiler sayı olarak gösterilmez.</span></li>
          <li><b>Alt gruplar</b><span>Yalnızca yön okları; n &lt; 30 olan hücreler test edilmez.</span></li>
          <li><b>Doğrulama</b><span>Gerçek anket sorularında motorun isabeti, temel modellerle yan yana (TVD).</span></li>
        </ul></section>
      </div></div>`;
    markNav();
    closeSide();
  }

  function chatHead(title) {
    setHead("Sohbet", title, "", '<button class="btn" type="button" data-new><svg class="nav-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Yeni sohbet</button>', title);
  }

  function markNav() {
    homeBtn.setAttribute("aria-current", String(current === null));
  }

  async function refresh() {
    state = await api("/api/state");
  }

  async function ask(q) {
    q = q.trim();
    if (!q || busy) return;
    busy = true;
    form.querySelector("button").disabled = true;
    input.value = "";
    closeSide();
    homeBtn.setAttribute("aria-current", "false");
    if (!current) { chatHead(q); thread.innerHTML = ""; }
    thread.querySelectorAll(".answer .chips").forEach((c) => c.remove()); // follow-ups belong to the newest answer only
    const pending = document.createElement("div");
    pending.innerHTML = `<div class="pt pt-user"><div>${esc(q)}</div></div><div class="pt pt-typing" aria-label="Yanıt hazırlanıyor"><i></i><i></i><i></i></div>`;
    thread.append(pending);
    pending.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const [res] = await Promise.all([api("/api/ask", { chat_id: current, q }), new Promise((r) => setTimeout(r, 450))]);
      const isNew = current !== res.id;
      current = res.id;
      pending.outerHTML = res.html;
      if (isNew) await refresh();
    } catch (err) {
      if (err.message !== "auth") pending.querySelector(".pt-typing").outerHTML = `<p class="form-error" role="alert">${esc(err.message)}</p>`;
    } finally {
      busy = false;
      form.querySelector("button").disabled = false;
      input.focus();
    }
  }

  function closeSide() { side.classList.remove("open"); scrim.hidden = true; opener.setAttribute("aria-expanded", "false"); }
  function openSide() { side.classList.add("open"); scrim.hidden = false; opener.setAttribute("aria-expanded", "true"); }

  form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
  homeBtn.addEventListener("click", welcome);
  document.getElementById("new").addEventListener("click", () => { welcome(); input.focus(); });
  head.addEventListener("click", (e) => { if (e.target.closest("[data-new]")) { welcome(); input.focus(); } });
  opener.addEventListener("click", openSide);
  scrim.addEventListener("click", closeSide);
  document.querySelector(".side-close").addEventListener("click", closeSide);

  thread.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) return ask(chip.dataset.q);
    const tab = e.target.closest(".tab-list button");
    if (tab) {
      const box = tab.closest(".tabs");
      box.querySelectorAll(".tab-list button").forEach((b) => b.setAttribute("aria-selected", String(b === tab)));
      box.querySelectorAll(".tab-panel").forEach((p) => { p.hidden = p.dataset.panel !== tab.dataset.tab; });
    }
  });

  refresh().then(welcome).catch(() => {});
})();
