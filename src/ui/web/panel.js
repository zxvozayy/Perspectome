// Perspectome — analysis panel. The server renders every answer; this file only
// sends questions, swaps chats and toggles chart tabs.
(() => {
  const thread = document.getElementById("thread");
  const history = document.getElementById("history");
  const form = document.getElementById("ask");
  const input = document.getElementById("q");
  const side = document.getElementById("side");
  const toggle = document.querySelector(".side-toggle");
  let current = null;
  let suggestions = [];
  let busy = false;

  const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function api(path, body) {
    const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    if (res.status === 401) { location.href = "/giris"; throw new Error("auth"); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Bir sorun oluştu.");
    return data;
  }

  function chips(list) {
    return `<div class="chips">${list.map((q) => `<button type="button" class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>`;
  }

  function welcome() {
    current = null;
    thread.innerHTML = `<div class="welcome"><p class="kicker">Analiz</p><h1>Hangi senaryoyu inceleyelim?</h1>
      <p>Soru yazın ya da aşağıdakilerden birini seçin. Yanıtlar simülasyon ve doğrulama ekiplerinin hazır sonuçlarından gelir.</p>
      ${chips(suggestions)}</div>`;
    markHistory();
    input.focus();
  }

  function title(text) {
    return `<div class="chat-title"><h1>${esc(text)}</h1></div>`;
  }

  function markHistory() {
    history.querySelectorAll("button").forEach((b) => b.setAttribute("aria-current", String(b.dataset.id === current)));
  }

  function renderHistory(chats) {
    history.innerHTML = chats.length
      ? chats.map((c) => `<li><button type="button" data-id="${esc(c.id)}" title="${esc(c.title)}">${esc(c.title)}</button></li>`).join("")
      : '<li class="empty">Henüz sohbet yok.</li>';
    markHistory();
  }

  async function refresh() {
    const state = await api("/api/state");
    suggestions = state.suggestions;
    renderHistory(state.chats);
    return state;
  }

  async function open(id) {
    const chat = await api("/api/chat?id=" + encodeURIComponent(id));
    current = chat.id;
    thread.innerHTML = title(chat.title) + chat.html;
    markHistory();
    closeSide();
    scrollTo({ top: 0 });
  }

  async function ask(q) {
    q = q.trim();
    if (!q || busy) return;
    busy = true;
    form.querySelector("button").disabled = true;
    input.value = "";
    if (!current) thread.innerHTML = title(q);
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

  function closeSide() { side.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); }

  form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
  document.getElementById("new").addEventListener("click", () => { welcome(); closeSide(); });
  history.addEventListener("click", (e) => { const b = e.target.closest("button[data-id]"); if (b) open(b.dataset.id); });
  toggle.addEventListener("click", () => { const o = side.classList.toggle("open"); toggle.setAttribute("aria-expanded", String(o)); });

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
