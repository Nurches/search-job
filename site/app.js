(() => {
  "use strict";

  const DATA_URL = "data/jobs.json";
  const PAGE = 40;
  const REFRESH_MS = 5 * 60 * 1000;

  const TAGS = {
    mobile: "Мобильные", frontend: "Фронтенд", backend: "Бэкенд", web: "Сайты/веб",
    bots: "Боты", ai: "AI/парсинг", devops: "DevOps", crm: "1С/CRM", games: "Игры",
    design: "UI/UX", qa: "QA", study: "Учёба",
  };
  const TEMP = { hot: "🔥 горячий", warm: "🟡 тёплый", cold: "❄️ холодный" };
  const DIR_ORDER = ["Казахстан", "СНГ", "Мир", "Учёба", "Telegram"];

  // ── хранилище (только этот браузер) ──
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem("sj." + key); return v ? JSON.parse(v) : fallback; }
      catch { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem("sj." + key, JSON.stringify(value)); } catch { /* приватный режим */ }
    },
  };

  const marks = store.get("marks", { fav: {}, applied: {}, hidden: {} });
  let prevVisit = null;
  try { prevVisit = sessionStorage.getItem("sj.prevVisit"); } catch { /* ignore */ }
  if (prevVisit === null) {
    prevVisit = store.get("lastVisit", "") || "";
    try { sessionStorage.setItem("sj.prevVisit", prevVisit); } catch { /* ignore */ }
  }

  const defaults = {
    temp: null, q: "", kind: "all", sort: "score", minBudget: "", tags: [], excludedSources: [],
    hideSeen: true, favOnly: false, budgetOnly: false,
  };
  const filters = Object.assign({}, defaults, store.get("filters", {}));

  let data = null;
  let shown = PAGE;

  const $ = (sel) => document.querySelector(sel);
  const el = (tag, props = {}, ...children) => {
    const node = document.createElement(tag);
    Object.assign(node, props);
    for (const c of children) node.append(c);
    return node;
  };

  // ── форматирование ──
  function timeAgo(iso) {
    if (!iso) return "";
    const diff = (Date.now() - Date.parse(iso)) / 1000;
    if (diff < 60) return "только что";
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
    const d = Math.floor(diff / 86400);
    return d === 1 ? "вчера" : `${d} дн назад`;
  }
  const fmtKzt = (n) => n == null ? "" : `≈ ${Math.round(n).toLocaleString("ru-RU")} ₸`;
  const isNew = (j) => prevVisit && j.first_seen && j.first_seen > prevVisit;
  const jobDate = (j) => j.published || j.first_seen || "";

  // ── фильтрация ──
  function matches(j, { ignoreTemp = false, ignoreTags = false, ignoreSources = false } = {}) {
    if (!ignoreTemp && filters.temp) {
      if (filters.temp === "new") { if (!isNew(j)) return false; }
      else if (j.temperature !== filters.temp) return false;
    }
    if (filters.kind !== "all" && j.kind !== filters.kind) return false;
    if (filters.hideSeen && (marks.hidden[j.id] || marks.applied[j.id])) return false;
    if (filters.favOnly && !marks.fav[j.id]) return false;
    if (filters.budgetOnly && j.budget_kzt == null) return false;
    const min = Number(filters.minBudget);
    if (min > 0 && (j.budget_kzt == null || j.budget_kzt < min)) return false;
    if (!ignoreSources && filters.excludedSources.includes(j.source)) return false;
    if (!ignoreTags && filters.tags.length && !filters.tags.some((t) => j.tags.includes(t))) return false;
    if (filters.q) {
      const hay = (j.title + " " + j.description + " " + j.source_name).toLowerCase().replaceAll("ё", "е");
      const words = filters.q.toLowerCase().replaceAll("ё", "е").split(/\s+/).filter(Boolean);
      if (!words.every((w) => hay.includes(w))) return false;
    }
    return true;
  }

  function sorted(list) {
    const by = {
      score: (a, b) => b.score - a.score || jobDate(b).localeCompare(jobDate(a)),
      date: (a, b) => jobDate(b).localeCompare(jobDate(a)),
      budget: (a, b) => (b.budget_kzt ?? -1) - (a.budget_kzt ?? -1) || b.score - a.score,
    }[filters.sort] || (() => 0);
    return list.slice().sort(by);
  }

  // ── рендер ленты ──
  function renderCard(j) {
    const node = $("#card-tpl").content.firstElementChild.cloneNode(true);
    node.classList.add(j.temperature);
    if (marks.hidden[j.id] || marks.applied[j.id]) node.classList.add("dim");
    const temp = node.querySelector(".temp");
    temp.textContent = TEMP[j.temperature];
    temp.classList.add(j.temperature);
    node.querySelector(".score").textContent = j.score;
    node.querySelector(".new-badge").hidden = !isNew(j);
    node.querySelector(".kind").textContent = j.kind === "vacancy" ? "вакансия" : "заказ";

    const a = node.querySelector(".title a");
    a.href = j.url;
    a.textContent = j.title;

    const meta = node.querySelector(".meta");
    meta.append(el("span", { textContent: j.source_name }));
    if (j.also_in && j.also_in.length) meta.append(el("span", { textContent: `+ ${j.also_in.join(", ")}` }));
    meta.append(el("span", { textContent: timeAgo(jobDate(j)), title: jobDate(j) }));
    if (j.budget_text) {
      const b = el("span", { className: "budget", textContent: j.budget_text });
      if (j.currency && j.currency !== "KZT" && j.budget_kzt) b.title = fmtKzt(j.budget_kzt);
      meta.append(b);
    }
    if (j.responses != null) meta.append(el("span", { textContent: `откликов: ${j.responses}` }));

    const desc = node.querySelector(".desc");
    // В Telegram заголовок — первая строка поста; не повторяем её в описании.
    const lines = (j.description || "").split("\n");
    const text = (lines[0].trim() === j.title.trim() ? lines.slice(1).join("\n") : j.description || "").trim();
    desc.textContent = text || "";
    if (!text) desc.remove();
    else if (text.length > 280) {
      const btn = node.querySelector(".expand");
      btn.hidden = false;
      btn.onclick = () => {
        const full = desc.classList.toggle("full");
        btn.textContent = full ? "Свернуть" : "Показать полностью";
      };
    }

    const tags = node.querySelector(".tags");
    for (const t of j.tags) tags.append(el("span", { className: "tag", textContent: TAGS[t] || t }));
    node.querySelector(".reasons").textContent = j.reasons.join(" · ");

    for (const kind of ["fav", "applied", "hide"]) {
      const key = kind === "hide" ? "hidden" : kind;
      const btn = node.querySelector(".act." + kind);
      if (marks[key][j.id]) btn.classList.add("on");
      if (kind === "fav") btn.textContent = marks.fav[j.id] ? "★" : "☆";
      btn.onclick = () => {
        if (marks[key][j.id]) delete marks[key][j.id]; else marks[key][j.id] = 1;
        store.set("marks", marks);
        render();
      };
    }
    return node;
  }

  function renderFeed() {
    const jobs = data.jobs;
    const base = jobs.filter((j) => matches(j, { ignoreTemp: true }));
    $("#n-hot").textContent = base.filter((j) => j.temperature === "hot").length;
    $("#n-warm").textContent = base.filter((j) => j.temperature === "warm").length;
    $("#n-cold").textContent = base.filter((j) => j.temperature === "cold").length;
    $("#n-new").textContent = base.filter(isNew).length;
    document.querySelectorAll(".stat").forEach((b) => b.classList.toggle("active", b.dataset.temp === filters.temp));

    // Чипы категорий со счётчиками
    const forTags = jobs.filter((j) => matches(j, { ignoreTags: true }));
    const chips = $("#tagChips");
    chips.replaceChildren();
    for (const [key, label] of Object.entries(TAGS)) {
      const n = forTags.filter((j) => j.tags.includes(key)).length;
      const chip = el("button", { className: "chip" + (filters.tags.includes(key) ? " active" : ""), type: "button" },
        label, el("span", { className: "cnt", textContent: n }));
      chip.onclick = () => {
        filters.tags = filters.tags.includes(key) ? filters.tags.filter((t) => t !== key) : [...filters.tags, key];
        changed();
      };
      chips.append(chip);
    }

    // Список источников со счётчиками
    const forSrc = jobs.filter((j) => matches(j, { ignoreSources: true }));
    const counts = {};
    const names = {};
    for (const j of jobs) names[j.source] = j.source_name;
    for (const j of forSrc) counts[j.source] = (counts[j.source] || 0) + 1;
    const srcList = $("#srcList");
    srcList.replaceChildren();
    Object.keys(names).sort((a, b) => (counts[b] || 0) - (counts[a] || 0)).forEach((id) => {
      const cb = el("input", { type: "checkbox", checked: !filters.excludedSources.includes(id) });
      cb.onchange = () => {
        filters.excludedSources = cb.checked
          ? filters.excludedSources.filter((s) => s !== id)
          : [...filters.excludedSources, id];
        changed();
      };
      srcList.append(el("label", { className: "src-item" }, cb, names[id], el("span", { className: "cnt", textContent: counts[id] || 0 })));
    });
    const total = Object.keys(names).length;
    const on = total - filters.excludedSources.filter((s) => names[s]).length;
    $("#srcCount").textContent = on === total ? "" : `(${on}/${total})`;

    const list = sorted(jobs.filter((j) => matches(j)));
    $("#resultCount").textContent = `Найдено: ${list.length}`;
    const box = $("#list");
    box.replaceChildren();
    if (!list.length) {
      box.append(el("div", { className: "empty", textContent: "Ничего не найдено. Попробуйте ослабить фильтры." }));
    }
    for (const j of list.slice(0, shown)) box.append(renderCard(j));
    $("#more").hidden = list.length <= shown;
  }

  function renderDirectory() {
    const box = $("#directory");
    box.replaceChildren();
    const groups = {};
    for (const d of data.directory || []) (groups[d.region] ||= []).push(d);
    const order = [...DIR_ORDER, ...Object.keys(groups).filter((r) => !DIR_ORDER.includes(r))];
    for (const region of order) {
      if (!groups[region]) continue;
      const grid = el("div", { className: "dir-grid" });
      for (const d of groups[region]) {
        const badge = el("span", { className: "badge " + (d.auto ? "auto" : "manual"), textContent: d.auto ? "авто" : "вручную" });
        grid.append(el("a", { className: "dir-card", href: d.url, target: "_blank", rel: "noopener" },
          el("b", {}, d.name, badge), el("p", { textContent: d.note || "" })));
      }
      box.append(el("div", { className: "dir-group" }, el("h2", { textContent: region }), grid));
    }
  }

  function renderSources() {
    const body = $("#sourcesBody");
    body.replaceChildren();
    for (const s of data.sources || []) {
      const name = s.link ? el("a", { href: s.link, target: "_blank", rel: "noopener", textContent: s.name }) : s.name;
      const nameCell = el("td", {}, name);
      if (s.error) nameCell.append(el("span", { className: "err", textContent: s.error }));
      body.append(el("tr", {},
        nameCell,
        el("td", { className: s.ok ? "status-ok" : "status-err", textContent: s.ok ? "✓ работает" : "✕ ошибка" }),
        el("td", { className: "num", textContent: s.fetched }),
        el("td", { className: "num", textContent: s.accepted }),
        el("td", { textContent: s.last_ok ? timeAgo(s.last_ok) : "—" }),
      ));
    }
  }

  function renderHeader() {
    const st = data.stats || {};
    $("#updated").textContent = `обновлено ${timeAgo(data.generated_at)} · источников работает ${st.sources_ok ?? "?"} из ${st.sources_total ?? "?"} · всего ${st.total ?? data.jobs.length}`;
    $("#demo-banner").hidden = !data.demo;
    if (data.thresholds) {
      $("#thHot").textContent = data.thresholds.hot;
      $("#thWarm").textContent = data.thresholds.warm;
    }
  }

  function render() {
    if (!data) return;
    renderHeader();
    renderFeed();
  }

  function changed() {
    shown = PAGE;
    store.set("filters", filters);
    render();
  }

  // ── связывание контролов ──
  function bindControls() {
    const q = $("#q");
    q.value = filters.q;
    let t;
    q.oninput = () => { clearTimeout(t); t = setTimeout(() => { filters.q = q.value.trim(); changed(); }, 200); };

    for (const id of ["kind", "sort"]) {
      $("#" + id).value = filters[id];
      $("#" + id).onchange = (e) => { filters[id] = e.target.value; changed(); };
    }
    $("#minBudget").value = filters.minBudget;
    $("#minBudget").oninput = (e) => { filters.minBudget = e.target.value; changed(); };
    for (const id of ["hideSeen", "favOnly", "budgetOnly"]) {
      $("#" + id).checked = filters[id];
      $("#" + id).onchange = (e) => { filters[id] = e.target.checked; changed(); };
    }
    document.querySelectorAll(".stat").forEach((b) => {
      b.onclick = () => { filters.temp = filters.temp === b.dataset.temp ? null : b.dataset.temp; changed(); };
    });
    document.querySelectorAll("[data-src-all]").forEach((b) => {
      b.onclick = () => {
        filters.excludedSources = b.dataset.srcAll === "1" ? [] : [...new Set(data.jobs.map((j) => j.source))];
        changed();
      };
    });
    $("#resetFilters").onclick = () => {
      Object.assign(filters, defaults, { tags: [], excludedSources: [] });
      bindControls();
      changed();
    };
    $("#more").onclick = () => { shown += PAGE; renderFeed(); };

    document.querySelectorAll(".tabs button").forEach((b) => {
      b.onclick = () => showTab(b.dataset.tab);
    });
  }

  function showTab(name) {
    if (!document.getElementById("tab-" + name)) name = "feed";
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tab-panel").forEach((p) => { p.hidden = p.id !== "tab-" + name; });
    if (location.hash !== "#" + name) history.replaceState(null, "", name === "feed" ? location.pathname : "#" + name);
  }

  async function load() {
    try {
      const resp = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
      if (!resp.ok) throw new Error(resp.status);
      data = await resp.json();
      data.jobs = data.jobs || [];
    } catch (err) {
      $("#updated").textContent = "данные ещё не собраны";
      $("#list").replaceChildren(el("div", { className: "empty", textContent:
        "Файл data/jobs.json не найден. Запустите `python -m aggregator run` или дождитесь первого прогона GitHub Actions." }));
      return;
    }
    renderDirectory();
    renderSources();
    render();
  }

  bindControls();
  showTab((location.hash || "#feed").slice(1) || "feed");
  load();
  setInterval(load, REFRESH_MS);
  // Запоминаем визит: «новые» в следующий раз — всё, что появится после этого момента.
  setTimeout(() => store.set("lastVisit", new Date().toISOString().replace(/\.\d+Z$/, "Z")), 3000);
})();
