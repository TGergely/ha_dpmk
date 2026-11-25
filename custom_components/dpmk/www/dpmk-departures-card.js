/* Košice Public Transport – DPMK: Lovelace cards (both live in this one file):
 *   type: custom:dpmk-departures-card   entity: sensor.dpmk_<stop>_next_departure
 *   type: custom:dpmk-map-card          entity: sensor.dpmk_<stop>_next_departure
 */
(() => {
  // The file can end up loaded twice (integration auto-load + manual dashboard resource).
  if (window.__dpmkCardsLoaded) return;
  window.__dpmkCardsLoaded = true;

  // Slovak is the default, also when Home Assistant itself runs in English.
  // Card option `language`: sk (default) | en | auto (follow the Home Assistant language).
  const I18N = {
    sk: {
      now: "teraz",
      in: "o",
      ontime: "načas",
      live: "naživo",
      show_filter: "Zobraziť filter liniek",
      filter_type: "Typ vozidla",
      filter_line: "Linka",
      filter_all: "Všetky",
      filter_bus: "Autobus",
      filter_tram: "Električka",
      all_lines: "Všetky linky",
      none_filter: "Žiadne odchody pre tento filter",
      route_title: "Plánovač trasy",
      route_from: "Z",
      route_to: "Do",
      route_pick_from: "Vyberte začiatok",
      route_pick_to: "Vyberte cieľ",
      route_swap: "Vymeniť začiatok a cieľ",
      route_now: "Teraz",
      route_depart: "Odchod",
      route_arrive: "Príchod",
      route_time: "Čas",
      route_pick: "Vyberte zastávku, odkiaľ a kam idete.",
      route_loading: "Hľadám spojenie…",
      route_none: "Žiadne spojenie v najbližších 6 hodinách",
      route_hint: "Skúste neskorší čas alebo iné zastávky.",
      route_best: "najskôr v cieli",
      route_change: "Prestup",
      route_wait: "čakanie",
      route_walk: "chôdza",
      route_direct: "priamo",
      route_tomorrow: "zajtra",
      route_note: "Podľa cestovného poriadku DPMK, meškanie len pri prvom vozidle",
      route_same: "Začiatok a cieľ sú rovnaká zastávka.",
      route_unknown: "Neznáma zastávka.",
      route_no_service: "Do alebo z tejto zastávky nejde žiadna linka.",
      route_unavailable: "Plánovač teraz nie je dostupný. Skúste to neskôr.",
      route_no_integration: "Integrácia DPMK nie je načítaná.",
      from_stop: "Začiatok (zastávka)",
      to_stop: "Cieľ (zastávka)",
      route_name: "DPMK plánovač trasy",
      route_desc: "Spojenie medzi dvoma zastávkami DPMK Košice, aj s prestupom",
      walk: "Chôdza k blízkej zastávke (m, 0 = vypnuté)",
      walk_switch: "Chôdza",
      show_walk: "Zobraziť prepínač chôdze",
      show_favourites: "Zobraziť obľúbené trasy",
      fav_group: "Obľúbené trasy",
      fav_add: "+ Uložiť",
      fav_edit: "Upraviť obľúbené",
      fav_name: "Názov",
      fav_back: "Uložiť aj cestu späť",
      fav_save: "Uložiť",
      fav_cancel: "Zrušiť",
      fav_done: "Hotovo",
      fav_delete: "Zmazať",
      fav_deleted: "Zmazané",
      fav_undo: "Späť",
      fav_up: "Posunúť vyššie",
      fav_down: "Posunúť nižšie",
      fav_pinned: "pripnuté v nastaveniach karty",
      route_walk_start: "Chôdza {min} min na zastávku {stop}",
      route_walk_end: "Chôdza {min} min zo zastávky {stop}",
      none: "Žiadne ďalšie odchody",
      unavailable: "Údaje DPMK nie sú dostupné",
      missing: "Entita nebola nájdená:",
      choose: "Nenašiel sa žiadny senzor DPMK. Pridajte zastávku v integrácii Košice Public Transport – DPMK.",
      entity: "Zastávka (senzor)",
      title: "Nadpis",
      max_rows: "Počet riadkov",
      show_delay: "Zobraziť meškanie",
      language: "Jazyk",
      show_legend: "Zobraziť legendu",
      background: "Pozadie",
      map_style: "Štýl mapy",
      show_rings: "Zobraziť kruhy vzdialenosti",
      map_title: "Vozidlá pri zastávke",
      no_vehicles: "Žiadne vozidlá v okruhu",
      arriving: "prichádza",
      leaving: "odchádza",
      north: "S",
      departures_name: "DPMK odchody",
      departures_desc: "Najbližšie odchody DPMK Košice zo zastávky s aktuálnym meškaním",
      map_name: "DPMK mapa",
      map_desc: "Vozidlá DPMK v okolí zastávky, jednoduchý prehľad",
    },
    en: {
      now: "now",
      in: "in",
      ontime: "on time",
      live: "live",
      show_filter: "Show line filter",
      filter_type: "Vehicle type",
      filter_line: "Line",
      filter_all: "All",
      filter_bus: "Bus",
      filter_tram: "Tram",
      all_lines: "All lines",
      none_filter: "No departures for this filter",
      route_title: "Route planner",
      route_from: "From",
      route_to: "To",
      route_pick_from: "Choose start",
      route_pick_to: "Choose destination",
      route_swap: "Swap start and destination",
      route_now: "Now",
      route_depart: "Depart",
      route_arrive: "Arrive",
      route_time: "Time",
      route_pick: "Choose the stop you start from and the one you go to.",
      route_loading: "Looking for a connection…",
      route_none: "No connection in the next 6 hours",
      route_hint: "Try a later time or other stops.",
      route_best: "earliest arrival",
      route_change: "Change",
      route_wait: "wait",
      route_walk: "walk",
      route_direct: "direct",
      route_tomorrow: "tomorrow",
      route_note: "Based on the DPMK timetable, delay only for the first vehicle",
      route_same: "Start and destination are the same stop.",
      route_unknown: "Unknown stop.",
      route_no_service: "No line serves this stop.",
      route_unavailable: "The planner is not available right now. Try again later.",
      route_no_integration: "The DPMK integration is not loaded.",
      from_stop: "Start (stop)",
      to_stop: "Destination (stop)",
      route_name: "DPMK route planner",
      route_desc: "Connections between two DPMK Košice stops, also with a change",
      walk: "Walk to a nearby stop (m, 0 = off)",
      walk_switch: "Walk",
      show_walk: "Show the walk switch",
      show_favourites: "Show favourite routes",
      fav_group: "Favourite routes",
      fav_add: "+ Save",
      fav_edit: "Edit favourites",
      fav_name: "Name",
      fav_back: "Also save the way back",
      fav_save: "Save",
      fav_cancel: "Cancel",
      fav_done: "Done",
      fav_delete: "Delete",
      fav_deleted: "Deleted",
      fav_undo: "Undo",
      fav_up: "Move up",
      fav_down: "Move down",
      fav_pinned: "pinned in the card settings",
      route_walk_start: "Walk {min} min to {stop}",
      route_walk_end: "Walk {min} min from {stop}",
      none: "No upcoming departures",
      unavailable: "DPMK data is unavailable",
      missing: "Entity not found:",
      choose: "No DPMK sensor found. Add a stop in the Košice Public Transport – DPMK integration.",
      entity: "Stop (sensor)",
      title: "Title",
      max_rows: "Rows",
      show_delay: "Show delay",
      language: "Language",
      show_legend: "Show legend",
      background: "Background",
      map_style: "Map style",
      show_rings: "Show distance rings",
      map_title: "Vehicles near the stop",
      no_vehicles: "No vehicles within range",
      arriving: "arriving",
      leaving: "leaving",
      north: "N",
      departures_name: "DPMK departures",
      departures_desc: "Upcoming DPMK Košice departures at a stop, with live delays",
      map_name: "DPMK map",
      map_desc: "DPMK vehicles around the stop, simple overview",
    },
  };

  // Which sensor a card shows: its own `entity`; else the stop or place marked "Use as the default
  // for cards" in the integration options; else the first DPMK sensor there is.
  function resolveEntity(config, hass) {
    if (config?.entity) return config.entity;
    const all = Object.keys(hass?.states || {}).filter((e) =>
      Array.isArray(hass.states[e].attributes.departures)
    );
    return all.find((e) => hass.states[e].attributes.is_default === true) || all[0] || "";
  }

  // The language comes from, in this order: the card's own `language` option, the "Language of
  // the cards" setting of the integration (a sensor attribute), and finally automatic.
  function pickLanguage(config, hass) {
    let l = config?.language;
    if (!l || l === "default") l = hass?.states?.[resolveEntity(config, hass)]?.attributes?.language || "auto";
    if (l === "auto") return (hass?.language || "sk").startsWith("sk") ? "sk" : "en";
    return I18N[l] ? l : "sk";
  }

  const UNSET = Symbol("not drawn yet");

  const clock = (iso, lang) =>
    new Date(iso).toLocaleTimeString(lang === "en" ? "en-GB" : "sk-SK", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

  const sizeClass = (line) => (String(line).length <= 2 ? "" : String(line).length === 3 ? "s3" : "s4");

  // Everything that comes from the sensor or the card config is escaped before it goes into HTML.
  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
    );

  /* ------------------------------------------------------------------ */
  /* Line filter shared by both cards: a bus/tram switch plus one chip   */
  /* per line (a dropdown when there are many). The choice is remembered */
  /* in this browser only and never touches the sensor.                  */
  /* ------------------------------------------------------------------ */
  const MAX_CHIPS = 8;
  const NO_FILTER = { type: "all", line: null };

  const loadFilter = (key) => {
    try {
      const v = JSON.parse(localStorage.getItem(key));
      if (v && typeof v === "object") {
        return { type: v.type === "A" || v.type === "E" ? v.type : "all", line: v.line ? String(v.line) : null };
      }
    } catch (e) {
      /* storage blocked or unreadable: start unfiltered */
    }
    return { ...NO_FILTER };
  };
  const saveFilter = (key, f) => {
    try {
      localStorage.setItem(key, JSON.stringify(f));
    } catch (e) {
      /* not remembered, still works */
    }
  };

  // Drop a stored choice that no longer fits the stop (a line that was removed, the other type).
  const fixFilter = (f, lineTypes) => {
    let { type, line } = f;
    if (type !== "all" && !Object.values(lineTypes).includes(type)) type = "all";
    if (line && (!(line in lineTypes) || (type !== "all" && lineTypes[line] !== type))) line = null;
    return { type, line };
  };
  const passes = (f, line, type) =>
    (f.type === "all" || type === f.type) && (!f.line || String(line) === f.line);

  const byLine = (a, b) => parseInt(a, 10) - parseInt(b, 10) || a.localeCompare(b);

  // The markup of the bar, or "" when there is nothing to choose between.
  function filterBar(t, lineTypes, f) {
    const lines = Object.keys(lineTypes).sort(byLine);
    if (lines.length < 2) return "";
    const typeName = (ty) => (ty === "E" ? t("filter_tram") : t("filter_bus"));
    const types = new Set(Object.values(lineTypes));
    let html = "";
    if (types.has("A") && types.has("E")) {
      const seg = [["all", t("filter_all")], ["A", t("filter_bus")], ["E", t("filter_tram")]];
      html += `<span class="seg" role="group" aria-label="${esc(t("filter_type"))}">${seg
        .map(([k, name]) => `<button type="button" data-t="${k}" aria-pressed="${f.type === k}">${esc(name)}</button>`)
        .join("")}</span>`;
    }
    const shown = lines.filter((l) => f.type === "all" || lineTypes[l] === f.type);
    if (shown.length > MAX_CHIPS) {
      html += `<select data-sel aria-label="${esc(t("filter_line"))}"><option value="">${esc(t("all_lines"))}</option>${shown
        .map((l) => `<option value="${esc(l)}"${f.line === l ? " selected" : ""}>${esc(l)} (${esc(typeName(lineTypes[l]))})</option>`)
        .join("")}</select>`;
    } else {
      html += shown
        .map((l) => `<button type="button" class="chip" data-l="${esc(l)}" aria-pressed="${f.line === l}" aria-label="${esc(t("filter_line"))} ${esc(l)}">${esc(l)}</button>`)
        .join("");
    }
    return html;
  }

  // Put the bar in its place, but only when it changed: a periodic redraw must not close an open dropdown.
  function updateBar(root, el, html) {
    if (el._html !== html) {
      el._html = html;
      el.innerHTML = html;
    }
    if (root._focus) {
      root.querySelector(root._focus)?.focus();
      root._focus = null;
    }
  }

  // One listener per card; `apply(fn)` receives a function that turns the old choice into the new one.
  function bindFilter(root, apply) {
    root.addEventListener("click", (ev) => {
      const b = ev.target.closest?.("button[data-t], button[data-l]");
      if (!b) return;
      if (b.dataset.t) {
        root._focus = `[data-t="${b.dataset.t}"]`;
        apply(() => ({ type: b.dataset.t, line: null }));
      } else {
        root._focus = `[data-l="${CSS.escape(b.dataset.l)}"]`;
        apply((f) => ({ ...f, line: f.line === b.dataset.l ? null : b.dataset.l }));
      }
    });
    root.addEventListener("change", (ev) => {
      if (!ev.target.matches?.("select[data-sel]")) return;
      const value = ev.target.value || null;
      root._focus = "select[data-sel]";
      apply((f) => ({ ...f, line: value }));
    });
  }

  const FILTER_CSS = `
    .filter { display:flex; flex-wrap:wrap; gap:6px; align-items:center; padding:0 16px 8px; }
    .filter:empty { display:none; }
    .filter button { font:inherit; color:var(--primary-text-color); background:transparent; border:0;
                     cursor:pointer; padding:5px 12px; }
    .seg { display:inline-flex; border:1px solid var(--divider-color); border-radius:999px; overflow:hidden; margin-right:4px; }
    .seg button[aria-pressed="true"], .chip[aria-pressed="true"] {
      background:var(--primary-color); color:var(--text-primary-color, #fff); }
    .chip { border:1px solid var(--divider-color) !important; border-radius:999px; padding:4px 11px !important; font-weight:600; }
    .chip[aria-pressed="true"] { border-color:var(--primary-color) !important; }
    .chip[aria-pressed="true"]::before { content:"\\2713\\00a0"; }
    .filter select { font:inherit; color:var(--primary-text-color); background:var(--card-background-color);
                     border:1px solid var(--divider-color); border-radius:8px; padding:6px 10px; max-width:100%; }
    .filter button:focus-visible, .filter select:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
  `;

  /* Badge look shared by both cards: bus = rounded square, tram = circle. */
  const BADGE_CSS = `
    .line { flex:none; box-sizing:border-box; display:inline-flex; align-items:center;
            justify-content:center; font-weight:700; line-height:1; color:#fff;
            background:#9b9c9f; border-radius:8px; }
    .line.tE { border-radius:50%; }
  `;

  /* ------------------------------------------------------------------ */
  /* Departures list                                                     */
  /* ------------------------------------------------------------------ */
  class DpmkDeparturesCard extends HTMLElement {
    _t(key) {
      return I18N[pickLanguage(this._config, this._hass)][key];
    }

    static getConfigElement() {
      return document.createElement("dpmk-departures-card-editor");
    }
    static getStubConfig(hass) {
      return {}; // no entity: the default stop or place is used
    }

    setConfig(config) {
      this._config = config;
      this._lastState = UNSET;
      if (!this._root) {
        this._root = this.attachShadow({ mode: "open" });
        this._timer = setInterval(() => this._render(), 15000);
        bindFilter(this._root, (change) => {
          this._filter = fixFilter(change(this._filter || NO_FILTER), this._lineTypes || {});
          saveFilter(this._filterKey, this._filter);
          this._render();
        });
      }
      this._render();
    }

    // Home Assistant hands over a new `hass` on every state change of every entity: only redraw
    // when our sensor, the language or the chosen entity changed (the timer keeps countdowns fresh).
    set hass(hass) {
      this._hass = hass;
      const entity = resolveEntity(this._config, hass);
      const st = hass.states[entity];
      if (st !== this._lastState || hass.language !== this._lastLanguage || entity !== this._lastEntity) {
        this._lastState = st;
        this._lastLanguage = hass.language;
        this._lastEntity = entity;
        this._render();
      }
    }

    disconnectedCallback() {
      clearInterval(this._timer);
      this._timer = null;
    }

    connectedCallback() {
      if (this._root && !this._timer) this._timer = setInterval(() => this._render(), 15000);
    }

    getCardSize() {
      return 1 + (this._config?.max_rows || 6);
    }

    _countdown(dep, now) {
      const mins = Math.round((new Date(dep.expected) - now) / 60000);
      if (mins <= 0) return this._t("now");
      if (mins < 60) return `${this._t("in")} ${mins} min`;
      return `${this._t("in")} ${Math.floor(mins / 60)} h ${mins % 60} min`;
    }

    _render() {
      if (!this._root || !this._config || !this._hass) return;
      const entity = resolveEntity(this._config, this._hass);
      const st = this._hass.states[entity];
      const title = this._config.title ?? st?.attributes.stop_name ?? "DPMK";
      const lang = pickLanguage(this._config, this._hass);
      let rows = "";
      let bar = "";
      const key = `dpmk-filter:dep:${entity}`;
      if (this._filterKey !== key) {
        this._filterKey = key;
        this._filter = loadFilter(key);
      }
      this._lineTypes = st?.attributes.line_types || {};
      const filtering = this._config.show_filter !== false && !!st && st.state !== "unavailable";
      const f = filtering ? fixFilter(this._filter, this._lineTypes) : NO_FILTER;
      if (!st) {
        rows = `<div class="empty">${entity ? `${this._t("missing")} ${esc(entity)}` : this._t("choose")}</div>`;
      } else if (st.state === "unavailable") {
        rows = `<div class="empty">${this._t("unavailable")}</div>`;
      } else {
        const now = new Date();
        if (filtering) bar = filterBar((k) => this._t(k), this._lineTypes, f);
        const deps = (st.attributes.departures || [])
          .filter((d) => new Date(d.expected) > now - 30000)
          .filter((d) => passes(f, d.line, d.type))
          .slice(0, this._config.max_rows || 6);
        rows = deps.length
          ? deps
              .map((d) => {
                const delay = d.live
                  ? d.delay_min > 0
                    ? `<span class="late">+${esc(d.delay_min)} min</span>`
                    : d.delay_min < 0
                    ? `<span class="early">${esc(d.delay_min)} min</span>`
                    : `<span class="ok">${this._t("ontime")}</span>`
                  : "";
                const live = `<span class="dot${d.live ? " on" : ""}" ${d.live ? `role="img" aria-label="${this._t("live")}" title="${this._t("live")}"` : 'aria-hidden="true"'}></span>`;
                const real = `<span class="real">${d.live ? `[${clock(d.expected, lang)}]` : ""}</span>`;
                // a place with several stops: say which stop each departure is from
                const stopName = st.attributes.multi_stop && d.stop ? d.stop : "";
                const sub = [esc(stopName), this._countdown(d, now), this._config.show_delay === false ? "" : delay]
                  .filter(Boolean)
                  .join(" · ");
                const spoken = [d.line, d.destination, stopName, this._countdown(d, now), d.live ? this._t("live") : ""]
                  .filter(Boolean)
                  .join(", ");
                const bg = /^[#\w(),.% -]+$/.test(d.bg || "") ? d.bg : "";
                const fg = /^[#\w(),.% -]+$/.test(d.fg || "") ? d.fg : "";
                return `<div class="row" role="listitem" aria-label="${esc(spoken)}">
                  <span class="line t${esc(d.type)} ${sizeClass(d.line)}" style="${bg ? `background:${esc(bg)};` : ""}${fg ? `color:${esc(fg)};` : ""}">${esc(d.line)}</span>
                  <span class="dest">${esc(d.destination)}<span class="sub">${sub}</span></span>
                  <span class="when">${live}<span class="off">${clock(d.scheduled, lang)}</span>${real}</span>
                </div>`;
              })
              .join("")
          : `<div class="empty">${this._t(f.type !== "all" || f.line ? "none_filter" : "none")}</div>`;
      }
      // built once; afterwards only the header, the filter bar and the rows are updated
      if (!this._card) this._root.innerHTML = `
        <ha-card>
          <style>
            ${BADGE_CSS}
            ${FILTER_CSS}
            .row { display:flex; align-items:center; gap:12px; padding:6px 16px; }
            .line { width:40px; height:40px; padding:0; font-size:17px; }
            .line.s3 { font-size:13px; } .line.s4 { font-size:11px; }
            .dest { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
            .sub { display:block; font-size:0.8em; color:var(--secondary-text-color); white-space:normal; }
            /* fixed columns so the times line up whether or not a live time is shown */
            .when { flex:none; display:flex; align-items:center; gap:6px; font-weight:600;
                    white-space:nowrap; font-variant-numeric:tabular-nums; }
            .off { width:3.1em; text-align:right; }
            .real { width:4.3em; text-align:left; font-weight:400; color:var(--secondary-text-color); }
            .dot { flex:none; width:8px; height:8px; border-radius:50%; background:transparent; }
            .dot.on { background:#43a047; }
            .delay { font-size:0.85em; } .late { color:#e53935; } .early { color:#fb8c00; }
            .ok { color:#43a047; } .empty { padding:12px 16px; color:var(--secondary-text-color); }
            ha-card { padding-bottom:8px; }
          </style>
          <div class="filter"></div>
          <div role="list"></div>
        </ha-card>`;
      this._card = this._root.querySelector("ha-card");
      this._card.header = title; // a property, so nothing is parsed as HTML
      updateBar(this._root, this._root.querySelector(".filter"), bar);
      this._root.querySelector("[role=list]").innerHTML = rows;
    }
  }

  /* ------------------------------------------------------------------ */
  /* Radar-style map: stop in the middle, vehicles around it             */
  /* ------------------------------------------------------------------ */
  const RING = { approaching: "#43a047", leaving: "#e53935" };
  const SPAN = 43; // % of the square from the centre to the outer ring (leaves room for badges)

  class DpmkMapCard extends HTMLElement {
    _t(key) {
      return I18N[pickLanguage(this._config, this._hass)][key];
    }

    static getConfigElement() {
      return document.createElement("dpmk-map-card-editor");
    }
    static getStubConfig(hass) {
      return {}; // no entity: the default stop or place is used
    }

    setConfig(config) {
      this._config = config;
      if (!this._root) {
        this._root = this.attachShadow({ mode: "open" });
        this._timer = setInterval(() => this._update(true), 15000);
        bindFilter(this._root, (change) => {
          this._filter = fixFilter(change(this._filter || NO_FILTER), this._lineTypes || {});
          saveFilter(this._filterKey, this._filter);
          this._update();
        });
      }
      this._build();
      this._lastState = UNSET;
      this._update();
    }

    set hass(hass) {
      this._hass = hass;
      const entity = resolveEntity(this._config, hass);
      const st = hass.states[entity];
      if (st !== this._lastState || hass.language !== this._lastLanguage || entity !== this._lastEntity) {
        this._lastState = st;
        this._lastLanguage = hass.language;
        this._lastEntity = entity;
        this._update();
      }
    }

    disconnectedCallback() {
      clearInterval(this._timer);
      this._timer = null;
    }

    connectedCallback() {
      if (this._root && !this._timer) this._timer = setInterval(() => this._update(true), 15000);
    }

    getCardSize() {
      return 6;
    }

    _build() {
      this._els = new Map();
      this._radius = null;
      this._mapKey = null;
      this._stopsKey = null;
      this._multi = false;
      this._root.innerHTML = `
        <ha-card>
          <style>
            ${BADGE_CSS}
            ${FILTER_CSS}
            .radar { position:relative; width:100%; max-width:440px; aspect-ratio:1; margin:0 auto; }
            /* simple map picture behind everything (not interactive) */
            .mapbg { position:absolute; inset:0; overflow:hidden; border-radius:12px;
                     background:var(--secondary-background-color); pointer-events:none; }
            /* tiles overlap by a hair so no seams show between them */
            .mapbg img { position:absolute; display:block; user-select:none;
                         transform:scale(1.004); transform-origin:0 0; }
            .mapattr { position:absolute; right:6px; bottom:4px; font-size:9px; padding:0 4px;
                       border-radius:4px; background:rgba(255,255,255,.7); color:#333; z-index:20001; }
            .radar.has-map .ring, .radar.has-map .north { display:none; }
            .radar.has-map.rings .ring { display:block; border-color:rgba(128,128,128,.55); }
            .radar.has-map.rings .rlabel { display:none; }
            .ring { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
                    border:1px dashed var(--divider-color); border-radius:50%; box-sizing:border-box; }
            .rlabel { position:absolute; left:50%; transform:translateX(-50%); top:-0.1em;
                      font-size:10px; padding:0 4px; color:var(--secondary-text-color);
                      background:var(--ha-card-background, var(--card-background-color)); }
            .north { position:absolute; left:50%; top:1%; transform:translateX(-50%);
                     font-size:11px; font-weight:700; color:var(--secondary-text-color); }
            .stops { position:absolute; inset:0; }
            .stop.small { width:14px; height:14px; border-width:3px; }
            .sname { position:absolute; left:50%; top:calc(100% + 4px); transform:translateX(-50%);
                     white-space:nowrap; font-size:10px; font-weight:600; padding:0 4px; border-radius:6px;
                     background:var(--ha-card-background, var(--card-background-color)); opacity:.88;
                     color:var(--primary-text-color); }
            .stop { position:absolute; width:18px; height:18px; z-index:20000;
                    transform:translate(-50%,-50%); border-radius:50%; box-sizing:border-box;
                    background:var(--primary-color); border:4px solid var(--ha-card-background, var(--card-background-color));
                    box-shadow:0 0 0 2px var(--primary-color); }
            .caption { display:flex; justify-content:center; align-items:center; gap:8px;
                       padding:2px 16px 0; font-size:13px; font-weight:600; }
            .cdot { flex:none; width:12px; height:12px; border-radius:50%; box-sizing:border-box;
                    background:var(--primary-color); border:3px solid var(--ha-card-background, var(--card-background-color));
                    box-shadow:0 0 0 2px var(--primary-color); }
            .v { position:absolute; width:0; height:0; transition:left 1.2s linear, top 1.2s linear, opacity .4s; }
            .v .line { position:absolute; left:-15px; top:-15px; width:30px; height:30px;
                       font-size:14px; box-shadow:0 1px 4px rgba(0,0,0,.45); }
            .v .line.s3 { font-size:11px; } .v .line.s4 { font-size:9px; }
            .lbl { position:absolute; left:0; top:19px; transform:translateX(-50%); white-space:nowrap;
                   font-size:11px; font-weight:600; padding:0 5px; border-radius:8px;
                   background:var(--ha-card-background, var(--card-background-color)); opacity:.92;
                   color:var(--primary-text-color); }
            .nov { position:absolute; left:0; right:0; bottom:8%; text-align:center; font-size:13px;
                   color:var(--secondary-text-color); }
            .legend { display:flex; justify-content:center; gap:18px; padding:4px 16px 8px;
                      font-size:12px; color:var(--secondary-text-color); }
            .legend i { display:inline-block; width:12px; height:12px; border-radius:4px; box-sizing:border-box;
                        vertical-align:-2px; margin-right:6px; background:#9b9c9f; border:2px solid; }
            .legend i.l { border-style:dashed; }
          </style>
          <div class="filter"></div>
          <div class="radar" role="group">
            <div class="mapbg" hidden aria-hidden="true"></div>
            <div class="mapattr" hidden>Esri, HERE, Garmin, © OpenStreetMap contributors</div>
            <div class="ring" style="width:${(2 * SPAN) / 3}%;height:${(2 * SPAN) / 3}%"><span class="rlabel"></span></div>
            <div class="ring" style="width:${(4 * SPAN) / 3}%;height:${(4 * SPAN) / 3}%"><span class="rlabel"></span></div>
            <div class="ring" style="width:${2 * SPAN}%;height:${2 * SPAN}%"><span class="rlabel"></span></div>
            <div class="north"></div>
            <div class="stops"></div>
            <div class="layer"></div>
            <div class="nov"></div>
          </div>
          <div class="caption"><span class="cdot"></span><span class="cname"></span></div>
          <div class="legend"></div>
        </ha-card>`;
      this._card = this._root.querySelector("ha-card");
      this._layer = this._root.querySelector(".layer");
    }

    /* Lay web-map tiles behind the badges so that the stop is in the centre and the outer
     * ring (`radius` metres) is SPAN % of the card width away from it. Positions are plain
     * percentages of the card, so the vehicle badges (metres from the stop) line up exactly. */
    _renderMap(a, radius) {
      const radar = this._root.querySelector(".radar");
      const wrap = this._root.querySelector(".mapbg");
      const attr = this._root.querySelector(".mapattr");
      const useMap = (this._config.background ?? "map") === "map" && a.latitude != null && a.longitude != null;
      radar.classList.toggle("has-map", useMap);
      radar.classList.toggle("rings", this._config.show_rings === true);
      wrap.hidden = attr.hidden = !useMap;
      if (!useMap) return;
      const style = this._config.map_style || "auto";
      const dark = style === "dark" || (style === "auto" && !!this._hass?.themes?.darkMode);
      const key = [a.latitude, a.longitude, radius, dark].join("|");
      if (key === this._mapKey) return;
      this._mapKey = key;

      const lat = a.latitude;
      const rad = (lat * Math.PI) / 180;
      const widthM = (2 * radius) / ((2 * SPAN) / 100); // metres across the whole square
      // zoom where a tile pixel is about half a screen pixel (sharp on phones); the Esri gray
      // base maps have real data up to zoom 16
      const mpp0 = 156543.03392 * Math.cos(rad);
      const z = Math.min(16, Math.max(10, Math.ceil(Math.log2(mpp0 / (widthM / 880)))));
      const n = 2 ** z;
      const mpp = mpp0 / n; // metres per tile pixel at this zoom
      const cx = ((a.longitude + 180) / 360) * 256 * n;
      const sin = Math.sin(rad);
      const cy = (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * 256 * n;
      const u = ((SPAN / 100) * mpp) / radius; // card widths per tile pixel
      const half = 0.5 / u; // tile pixels from the centre to the card edge
      // Esri "Canvas" gray base maps: simple roads and parks, no key needed (note: y before x)
      const layer = dark ? "World_Dark_Gray_Base" : "World_Light_Gray_Base";
      wrap.textContent = "";
      for (let x = Math.floor((cx - half) / 256); x <= Math.floor((cx + half) / 256); x++) {
        for (let y = Math.floor((cy - half) / 256); y <= Math.floor((cy + half) / 256); y++) {
          if (y < 0 || y >= n) continue;
          const xi = ((x % n) + n) % n;
          const img = new Image();
          img.alt = "";
          img.draggable = false;
          img.referrerPolicy = "no-referrer"; // do not send the Home Assistant address to the tile server
          img.src = `https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/${layer}/MapServer/tile/${z}/${y}/${xi}`;
          img.style.left = `${50 + (x * 256 - cx) * u * 100}%`;
          img.style.top = `${50 + (y * 256 - cy) * u * 100}%`;
          img.style.width = img.style.height = `${256 * u * 100}%`;
          wrap.appendChild(img);
        }
      }
    }

    _label(v, now) {
      if (v.eta) {
        const mins = Math.round((new Date(v.eta) - now) / 60000);
        return mins <= 0 ? this._t("now") : `${mins} min`;
      }
      return `${v.distance} m`;
    }

    /* The stops: one dot each, named when a place has several. Without coordinates a single
     * dot in the middle stands for the stop. */
    _renderStops(stops, radius) {
      const key = JSON.stringify([stops, radius, this._multi]);
      if (key === this._stopsKey) return;
      this._stopsKey = key;
      const layer = this._root.querySelector(".stops");
      layer.textContent = "";
      for (const s of stops.length ? stops : [{ name: "", dx: 0, dy: 0 }]) {
        const dot = document.createElement("div");
        dot.className = this._multi ? "stop small" : "stop";
        if (s.name) {
          dot.setAttribute("role", "img");
          dot.setAttribute("aria-label", s.name);
        }
        dot.style.left = `${50 + (s.dx / radius) * SPAN}%`;
        dot.style.top = `${50 - (s.dy / radius) * SPAN}%`;
        if (this._multi && s.name) {
          const n = document.createElement("span");
          n.className = "sname";
          n.textContent = s.name;
          dot.appendChild(n);
        }
        layer.appendChild(dot);
      }
    }

    _update() {
      if (!this._root || !this._config || !this._hass) return;
      const q = (s) => this._root.querySelector(s);
      const entity = resolveEntity(this._config, this._hass);
      const st = this._hass.states[entity];
      this._card.header = this._config.title ?? this._t("map_title");
      q(".radar").setAttribute("aria-label", this._card.header);
      q(".north").textContent = this._t("north");
      const legend = q(".legend");
      legend.style.display = this._config.show_legend === false ? "none" : "";
      // arriving = solid ring, leaving = dashed ring: the difference does not rely on colour alone
      legend.innerHTML = `<span><i class="a" style="border-color:${RING.approaching}"></i>${this._t("arriving")}</span>
                          <span><i class="l" style="border-color:${RING.leaving}"></i>${this._t("leaving")}</span>`;
      const key = `dpmk-filter:map:${entity}`;
      if (this._filterKey !== key) {
        this._filterKey = key;
        this._filter = loadFilter(key);
      }
      this._lineTypes = st?.attributes.line_types || {};
      const filtering = this._config.show_filter !== false && !!st && st.state !== "unavailable";
      const f = filtering ? fixFilter(this._filter, this._lineTypes) : NO_FILTER;
      updateBar(this._root, q(".filter"), filtering ? filterBar((k) => this._t(k), this._lineTypes, f) : "");
      if (!st) {
        q(".nov").textContent = entity ? `${this._t("missing")} ${entity}` : this._t("choose");
        return;
      }
      const a = st.attributes;
      q(".cname").textContent = a.stop_name || "";
      const radius = a.radius || 1500;
      this._multi = a.multi_stop === true;
      this._renderMap(a, radius);
      this._renderStops(a.stops || [], radius);
      if (radius !== this._radius) {
        this._radius = radius;
        this._root.querySelectorAll(".rlabel").forEach((el, i) => {
          const m = (radius * (i + 1)) / 3;
          el.textContent = m >= 100 ? `${Math.round(m / 50) * 50} m` : `${Math.round(m)} m`;
        });
      }

      const now = new Date();
      const vehicles = (a.vehicles || []).filter((v) => passes(f, v.line, v.type));
      const seen = new Set();
      for (const v of vehicles) {
        seen.add(v.id);
        let el = this._els.get(v.id);
        const left = 50 + (v.dx / radius) * SPAN;
        const top = 50 - (v.dy / radius) * SPAN;
        if (!el) {
          el = document.createElement("div");
          el.className = "v";
          el.innerHTML = `<div class="line"></div><div class="lbl"></div>`;
          // set the position before inserting, so a new bus appears in place instead of sliding in
          el.style.left = `${left}%`;
          el.style.top = `${top}%`;
          this._layer.appendChild(el);
          this._els.set(v.id, el);
        }
        el.style.left = `${left}%`;
        el.style.top = `${top}%`;
        // serving vehicles are drawn above the others, nearer ones above farther ones
        el.style.zIndex = String(Math.max(2, 10000 - v.distance) - (v.serves === false ? 5000 : 0));
        const b = el.firstElementChild;
        b.className = `line t${v.type} ${sizeClass(v.line)}`;
        b.textContent = v.line;
        b.style.background = v.bg || "";
        b.style.color = v.fg || "";
        // vehicles that do not serve this stop (map_scope: all): dimmed, no ring, no label
        const serves = v.serves !== false;
        const ring = serves ? RING[v.movement] : null;
        // arriving: solid ring; leaving: dashed outline (so the two differ by shape, not only colour)
        const dashed = serves && v.movement === "leaving";
        b.style.boxShadow = !serves
          ? "0 1px 3px rgba(0,0,0,.35)"
          : dashed
          ? "0 1px 4px rgba(0,0,0,.45)"
          : `0 0 0 3px ${ring || "rgba(255,255,255,.75)"}, 0 1px 4px rgba(0,0,0,.45)`;
        b.style.outline = dashed ? `3px dashed ${ring}` : "";
        b.style.outlineOffset = dashed ? "2px" : "";
        el.style.opacity = serves ? "1" : "0.5";
        const way = v.movement === "approaching" ? this._t("arriving") : v.movement === "leaving" ? this._t("leaving") : "";
        el.setAttribute("role", "img");
        el.setAttribute("aria-label", serves ? [v.line, way, this._label(v, now)].filter(Boolean).join(", ") : String(v.line));
        el.lastElementChild.textContent = serves ? this._label(v, now) : "";
        el.lastElementChild.style.display = serves ? "" : "none";
      }
      for (const [id, el] of this._els) {
        if (!seen.has(id)) {
          el.remove();
          this._els.delete(id);
        }
      }
      q(".nov").textContent =
        st.state === "unavailable" ? this._t("unavailable") : vehicles.length ? "" : this._t("no_vehicles");
    }
  }

  /* ------------------------------------------------------------------ */
  /* Editors                                                             */
  /* ------------------------------------------------------------------ */
  /* ------------------------------------------------------------------ */
  /* Route planner: connections between two stops, with a change if     */
  /* needed. The work is done by the integration (websocket command      */
  /* dpmk/plan_route); nothing leaves Home Assistant from the card.      */
  /* ------------------------------------------------------------------ */
  const ROUTE_ERRORS = {
    same_stop: "route_same",
    unknown_stop: "route_unknown",
    no_service: "route_no_service",
    unavailable: "route_unavailable",
    unknown_command: "route_no_integration",
  };
  const pad2 = (n) => String(n).padStart(2, "0");
  const nowHHMM = () => {
    const d = new Date();
    return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  };
  const colorOk = (c) => (/^[#\w(),.% -]+$/.test(c || "") ? c : "");

  /* Favourite routes. Kept in the Home Assistant user data (the same on every device of the user) when
   * it is available, and always copied to this browser; shared by all route cards on the page. */
  const FAV_STORE = "dpmk_route_favourites";
  const MAX_FAVS = 20;
  const cleanFavs = (list) =>
    (Array.isArray(list) ? list : [])
      .filter((f) => f && [f.id, f.name, f.from, f.to].every((v) => typeof v === "string") && f.id && f.from && f.to && f.from !== f.to)
      .slice(0, MAX_FAVS)
      .map((f) => ({ id: f.id.slice(0, 24), name: f.name.trim().slice(0, 40) || `${f.from} → ${f.to}`, from: f.from, to: f.to }));
  const FavStore = {
    list: null,
    hass: null,
    userData: false,
    loading: null,
    subs: new Set(),
    load(hass) {
      this.hass = hass;
      if (!this.loading) {
        this.loading = (async () => {
          let list = null;
          try {
            const r = await hass.callWS({ type: "frontend/get_user_data", key: FAV_STORE });
            this.userData = true;
            if (Array.isArray(r?.value)) list = r.value;
          } catch (e) {
            /* no user storage: this browser keeps them */
          }
          if (!list) {
            try {
              list = JSON.parse(localStorage.getItem(FAV_STORE));
            } catch (e) {
              /* none saved */
            }
          }
          this.list = cleanFavs(list);
          this.subs.forEach((f) => f());
        })();
      }
      return this.loading;
    },
    set(list) {
      this.list = cleanFavs(list);
      try {
        localStorage.setItem(FAV_STORE, JSON.stringify(this.list));
      } catch (e) {
        /* kept for this page only */
      }
      if (this.userData && this.hass) {
        this.hass.callWS({ type: "frontend/set_user_data", key: FAV_STORE, value: this.list }).catch(() => {});
      }
      this.subs.forEach((f) => f());
    },
  };

  class DpmkRouteCard extends HTMLElement {
    _t(key) {
      return I18N[pickLanguage(this._config, this._hass)][key];
    }

    static getConfigElement() {
      return document.createElement("dpmk-route-card-editor");
    }
    static getStubConfig() {
      return {};
    }

    setConfig(config) {
      this._config = config;
      if (!this._root) {
        this._root = this.attachShadow({ mode: "open" });
        this._build();
        this._timer = setInterval(() => this._search(true), 60000); // fresh delays and countdowns
        this._favSub = () => this._renderFavs();
        FavStore.subs.add(this._favSub);
      }
      this._key = `dpmk-route:${config.from_stop || ""}:${config.to_stop || ""}`;
      this._state = this._load();
      this._sync();
      this._search();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      const lang = pickLanguage(this._config, hass);
      if (lang !== this._lang) {
        this._lang = lang;
        this._sync();
      }
      FavStore.hass = hass;
      if (first) {
        this._loadStops();
        this._search();
        FavStore.load(hass);
      }
    }

    disconnectedCallback() {
      clearInterval(this._timer);
      this._timer = null;
      FavStore.subs.delete(this._favSub);
    }

    connectedCallback() {
      if (this._root && !this._timer) this._timer = setInterval(() => this._search(true), 60000);
      if (this._favSub) FavStore.subs.add(this._favSub);
    }

    getCardSize() {
      return 6;
    }

    /* what was chosen last time on this device, else the stops from the card settings */
    _load() {
      let s = {};
      try {
        s = JSON.parse(localStorage.getItem(this._key)) || {};
      } catch (e) {
        /* storage blocked: the settings are used */
      }
      return {
        from: String(s.from || this._config.from_stop || ""),
        to: String(s.to || this._config.to_stop || ""),
        mode: ["now", "depart", "arrive"].includes(s.mode) ? s.mode : "now",
        time: /^\d\d:\d\d$/.test(s.time || "") ? s.time : nowHHMM(),
        // the walk switch: what was chosen last time, else on when the card settings give a distance
        walk: s.walkSet === true ? !!s.walk : Number(this._config.walk) > 0,
        walkSet: s.walkSet === true, // only a click on the switch is remembered, not the default
      };
    }

    _save() {
      try {
        localStorage.setItem(this._key, JSON.stringify(this._state));
      } catch (e) {
        /* not remembered, still works */
      }
    }

    async _loadStops() {
      if (this._stops || this._loadingStops || !this._hass) return;
      this._loadingStops = true;
      try {
        const { stops } = await this._hass.callWS({ type: "dpmk/stops" });
        this._stops = stops;
        this._byId = new Map(stops.map((s) => [s.id, s]));
        this._byText = new Map();
        const names = new Map();
        for (const s of stops) names.set(s.name.toLowerCase(), (names.get(s.name.toLowerCase()) || []).concat(s.id));
        for (const [name, ids] of names) if (ids.length === 1) this._byText.set(name, ids[0]);
        for (const s of stops) this._byText.set(s.label.toLowerCase(), s.id);
        this._root.querySelector("datalist").innerHTML = stops.map((s) => `<option value="${esc(s.label)}"></option>`).join("");
        this._sync();
      } catch (e) {
        this._stops = null; // the integration is not loaded (yet): the search shows why
      } finally {
        this._loadingStops = false;
      }
    }

    _label(id) {
      return this._byId?.get(id)?.label || "";
    }

    _build() {
      this._seq = 0;
      this._root.innerHTML = `
        <ha-card>
          <style>
            ${BADGE_CSS}
            .form { padding:0 16px 8px; display:grid; grid-template-columns:1fr 40px; gap:8px; align-items:center; }
            .fields { display:grid; gap:8px; }
            .field { display:flex; align-items:center; gap:8px; border:1px solid var(--divider-color); border-radius:10px;
                     padding:2px 10px; background:var(--secondary-background-color); }
            .field:focus-within { outline:2px solid var(--primary-color); }
            .field span { font-size:12px; color:var(--secondary-text-color); width:2.6em; flex:none; }
            .field input { font:inherit; color:var(--primary-text-color); background:transparent; border:0; padding:8px 4px;
                           width:100%; min-width:0; outline:none; }
            .field input[aria-invalid="true"] { text-decoration:underline wavy var(--error-color, #e53935); }
            button { font:inherit; color:var(--primary-text-color); cursor:pointer; }
            .icon { width:40px; height:40px; border-radius:50%; border:1px solid var(--divider-color);
                    background:var(--card-background-color); font-size:18px; }
            .when { display:flex; gap:6px; padding:2px 16px 10px; flex-wrap:wrap; align-items:center; }
            .when button { background:transparent; border:1px solid var(--divider-color); border-radius:999px; padding:4px 12px; }
            .when button[aria-pressed="true"] { background:var(--primary-color); border-color:var(--primary-color);
                                                color:var(--text-primary-color, #fff); }
            .when button[aria-pressed="true"]::before { content:"\\2713\\00a0"; }
            .when input { font:inherit; color:var(--primary-text-color); background:transparent;
                          border:1px solid var(--divider-color); border-radius:999px; padding:3px 10px; }
            button:focus-visible, input:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
            .favs { display:flex; gap:6px; padding:0 16px 8px; align-items:center; overflow-x:auto;
                    scrollbar-width:thin; scrollbar-color:var(--divider-color) transparent; }
            .favs[hidden], .fdlg[hidden], .fundo[hidden] { display:none; }
            .favs button { flex:none; white-space:nowrap; background:transparent; border:1px solid var(--divider-color);
                           border-radius:999px; padding:4px 12px; }
            .favs button[aria-pressed="true"] { background:var(--primary-color); border-color:var(--primary-color);
                                                color:var(--text-primary-color, #fff); }
            .favs button[aria-pressed="true"]::before { content:"\\2713\\00a0"; }
            .favs button.add { color:var(--secondary-text-color); border-style:dashed; }
            .favs button:disabled { opacity:.4; cursor:default; }
            .favs.editing { flex-direction:column; align-items:stretch; overflow:visible; }
            .fi { display:flex; gap:6px; align-items:center; }
            .fi button { padding:2px 9px; border-radius:8px; }
            .fi input, .fdlg input[type="text"] { flex:1; min-width:0; font:inherit; color:var(--primary-text-color);
                    background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; padding:6px 8px; }
            .fdlg { margin:0 16px 10px; padding:10px 12px; border:1px solid var(--primary-color); border-radius:12px;
                    background:var(--secondary-background-color); }
            .fdlg label { display:flex; flex-direction:column; gap:4px; font-size:12px; color:var(--secondary-text-color); }
            .fdlg label.ck { flex-direction:row; align-items:center; gap:8px; margin-top:8px; font-size:13px; color:var(--primary-text-color); }
            .frow { display:flex; gap:8px; margin-top:10px; }
            .frow button { border:1px solid var(--divider-color); background:transparent; border-radius:8px; padding:6px 14px; }
            .frow button[data-fa="save"] { background:var(--primary-color); border-color:var(--primary-color);
                                           color:var(--text-primary-color, #fff); }
            .fundo { margin:0 16px 8px; font-size:13px; color:var(--secondary-text-color); display:flex; gap:10px; align-items:center; }
            .fundo button { border:0; background:transparent; color:var(--primary-color); font-weight:600; padding:2px 4px; }
            .conn { margin:0 12px 8px; border:1px solid var(--divider-color); border-radius:12px; padding:10px 12px; }
            .conn.best { border-color:var(--primary-color); }
            .top { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
            .times { font-size:18px; font-weight:600; font-variant-numeric:tabular-nums; }
            .dur { color:var(--secondary-text-color); font-size:13px; white-space:nowrap; }
            .legs { display:flex; align-items:center; gap:6px; margin-top:8px; flex-wrap:wrap; }
            .legs .line { width:30px; height:30px; font-size:14px; }
            .legs .line.s3 { font-size:11px; } .legs .line.s4 { font-size:9px; }
            .arrow { color:var(--secondary-text-color); }
            .detail { margin-top:6px; color:var(--secondary-text-color); font-size:13px; }
            .detail b { color:var(--primary-text-color); font-weight:600; }
            .late { color:#e53935; } .early { color:#fb8c00; } .ok { color:#43a047; }
            .tag { display:inline-block; font-size:11px; padding:1px 7px; border-radius:999px; margin-left:6px;
                   border:1px solid var(--divider-color); color:var(--secondary-text-color); font-weight:400; }
            .tag.live { border-color:#43a047; color:#43a047; margin-left:0; }
            .empty { margin:6px 16px 8px; padding:14px; border:1px dashed var(--divider-color); border-radius:12px;
                     color:var(--secondary-text-color); }
            .foot { padding:2px 16px 0; font-size:12px; color:var(--secondary-text-color); }
            ha-card { padding-bottom:10px; }
          </style>
          <div class="favs" role="group" hidden></div>
          <div class="fdlg" hidden></div>
          <div class="fundo" hidden aria-live="polite"></div>
          <div class="form">
            <div class="fields">
              <label class="field"><span class="lf"></span><input data-f="from" list="stops" autocomplete="off" spellcheck="false"></label>
              <label class="field"><span class="lt"></span><input data-f="to" list="stops" autocomplete="off" spellcheck="false"></label>
            </div>
            <button type="button" class="icon" data-swap>\u21c5</button>
          </div>
          <datalist id="stops"></datalist>
          <div class="when" role="group">
            <button type="button" data-m="now"></button>
            <button type="button" data-m="depart"></button>
            <button type="button" data-m="arrive"></button>
            <input type="time">
            <button type="button" data-walk></button>
          </div>
          <div class="results" aria-live="polite" aria-busy="false"></div>
          <div class="foot"></div>
        </ha-card>`;
      this._card = this._root.querySelector("ha-card");
      const root = this._root;
      root.addEventListener("input", (ev) => ev.target.dataset?.f && this._pick(ev.target, false));
      root.addEventListener("change", (ev) => {
        if (ev.target.dataset?.f) this._pick(ev.target, true);
        else if (ev.target.type === "time" && ev.target.value) this._set({ time: ev.target.value });
      });
      root.addEventListener("click", (ev) => {
        const b = ev.target.closest?.("button");
        if (!b) return;
        if (b.dataset.m) this._set({ mode: b.dataset.m });
        else if (b.hasAttribute("data-swap")) this._set({ from: this._state.to, to: this._state.from });
        else if (b.hasAttribute("data-walk")) this._set({ walk: !this._state.walk, walkSet: true });
      });
      // favourites: buttons carry data-fa (the action) and data-id (which favourite)
      root.addEventListener("click", (ev) => {
        const b = ev.target.closest?.("[data-fa]");
        if (b) this._fav(b.dataset.fa, b.dataset.id);
      });
      root.addEventListener("change", (ev) => {
        const el = ev.target;
        if (!el.matches?.("[data-favname]")) return;
        FavStore.set((FavStore.list || []).map((f) => (f.id === el.dataset.id ? { ...f, name: el.value.trim().slice(0, 40) || f.name } : f)));
      });
      root.addEventListener("keydown", (ev) => {
        if (!ev.target.classList?.contains("finp")) return;
        if (ev.key === "Enter") {
          ev.preventDefault();
          this._saveDlg();
        } else if (ev.key === "Escape") {
          ev.preventDefault();
          this._closeDlg();
        }
      });
    }

    /* the favourites set in the card settings (pinned) first, then the ones saved on this card */
    _allFavs() {
      const fixed = (Array.isArray(this._config.favourites) ? this._config.favourites : [])
        .map((f, i) => ({ id: `cfg${i}`, name: String(f?.name || ""), from: String(f?.from_stop || ""), to: String(f?.to_stop || ""), fixed: true }))
        .filter((f) => f.name && f.from && f.to);
      return fixed.concat(FavStore.list || []);
    }

    _stopName(id) {
      return this._byId?.get(id)?.name || id;
    }

    _renderFavs() {
      const box = this._root?.querySelector(".favs");
      if (!box || !this._state) return;
      const t = (k) => this._t(k);
      if (this._config.show_favourites === false) {
        box.hidden = true;
        this._root.querySelector(".fdlg").hidden = true;
        return;
      }
      // do not replace the list under a name that is being typed
      if (this._editing && this._root.activeElement && box.contains(this._root.activeElement)) return;
      const own = FavStore.list || [];
      box.setAttribute("aria-label", t("fav_group"));
      box.classList.toggle("editing", !!this._editing && own.length > 0);
      if (this._editing && own.length) {
        box.innerHTML =
          own
            .map(
              (f, i) =>
                `<div class="fi"><button type="button" data-fa="up" data-id="${esc(f.id)}" aria-label="${esc(t("fav_up"))}" ${i === 0 ? "disabled" : ""}>▲</button>` +
                `<button type="button" data-fa="down" data-id="${esc(f.id)}" aria-label="${esc(t("fav_down"))}" ${i === own.length - 1 ? "disabled" : ""}>▼</button>` +
                `<input type="text" data-favname data-id="${esc(f.id)}" value="${esc(f.name)}" maxlength="40" aria-label="${esc(t("fav_name"))}">` +
                `<button type="button" data-fa="del" data-id="${esc(f.id)}" aria-label="${esc(t("fav_delete"))}">🗑</button></div>`
            )
            .join("") + `<button type="button" data-fa="done">${esc(t("fav_done"))}</button>`;
        box.hidden = false;
        return;
      }
      this._editing = false;
      const { from, to } = this._state;
      const all = this._allFavs();
      let html = all
        .map(
          (f) =>
            `<button type="button" data-fa="use" data-id="${esc(f.id)}" aria-pressed="${f.from === from && f.to === to}" title="${esc(f.name)}${f.fixed ? ` (${esc(t("fav_pinned"))})` : ""}">${f.fixed ? "📌 " : ""}${esc(f.name)}</button>`
        )
        .join("");
      if (this._byId && from && to && from !== to && !all.some((f) => f.from === from && f.to === to) && own.length < MAX_FAVS) {
        html += `<button type="button" class="add" data-fa="add">${esc(t("fav_add"))}</button>`;
      }
      if (own.length) html += `<button type="button" data-fa="edit" aria-label="${esc(t("fav_edit"))}" title="${esc(t("fav_edit"))}">✎</button>`;
      box.innerHTML = html;
      box.hidden = !html;
    }

    _fav(action, id) {
      const own = (FavStore.list || []).slice();
      const i = own.findIndex((f) => f.id === id);
      switch (action) {
        case "use": {
          const f = this._allFavs().find((x) => x.id === id);
          if (f) this._set({ from: f.from, to: f.to });
          break;
        }
        case "add":
          this._openDlg();
          break;
        case "edit":
          this._editing = true;
          this._renderFavs();
          this._root.querySelector(".fi input")?.focus();
          break;
        case "done":
          this._editing = false;
          this._renderFavs();
          this._root.querySelector('[data-fa="edit"]')?.focus();
          break;
        case "up":
        case "down": {
          const j = action === "up" ? i - 1 : i + 1;
          if (i < 0 || j < 0 || j >= own.length) break;
          [own[i], own[j]] = [own[j], own[i]];
          FavStore.set(own);
          this._root.querySelector(`[data-fa="${action}"][data-id="${id}"]`)?.focus();
          break;
        }
        case "del":
          if (i >= 0) {
            own.splice(i, 1);
            this._showUndo(FavStore.list);
            FavStore.set(own);
          }
          break;
        case "undo":
          if (this._undo) FavStore.set(this._undo);
          this._hideUndo();
          break;
        case "save":
          this._saveDlg();
          break;
        case "cancel":
          this._closeDlg();
          break;
      }
    }

    _showUndo(before) {
      const t = (k) => this._t(k);
      const box = this._root.querySelector(".fundo");
      this._undo = before;
      box.innerHTML = `<span>${esc(t("fav_deleted"))}</span><button type="button" data-fa="undo">${esc(t("fav_undo"))}</button>`;
      box.hidden = false;
      clearTimeout(this._undoTimer);
      this._undoTimer = setTimeout(() => this._hideUndo(), 6000);
    }

    _hideUndo() {
      clearTimeout(this._undoTimer);
      this._undo = null;
      const box = this._root.querySelector(".fundo");
      box.hidden = true;
      box.innerHTML = "";
    }

    _openDlg() {
      const t = (k) => this._t(k);
      const { from, to } = this._state;
      const a = this._stopName(from);
      const b = this._stopName(to);
      const reverseKnown = this._allFavs().some((f) => f.from === to && f.to === from);
      const dlg = this._root.querySelector(".fdlg");
      dlg.innerHTML =
        `<label>${esc(t("fav_name"))}<input type="text" class="finp" maxlength="40" value="${esc(`${a} → ${b}`)}"></label>` +
        (reverseKnown
          ? ""
          : `<label class="ck"><input type="checkbox" class="fback" checked> ${esc(t("fav_back"))} (${esc(b)} → ${esc(a)})</label>`) +
        `<div class="frow"><button type="button" data-fa="save">${esc(t("fav_save"))}</button><button type="button" data-fa="cancel">${esc(t("fav_cancel"))}</button></div>`;
      dlg.hidden = false;
      const input = dlg.querySelector(".finp");
      input.focus();
      input.select();
    }

    _closeDlg() {
      const dlg = this._root.querySelector(".fdlg");
      dlg.hidden = true;
      dlg.innerHTML = "";
      this._root.querySelector('[data-fa="add"]')?.focus();
    }

    _saveDlg() {
      const dlg = this._root.querySelector(".fdlg");
      const input = dlg.querySelector(".finp");
      if (!input) return;
      const { from, to } = this._state;
      const a = this._stopName(from);
      const b = this._stopName(to);
      const own = (FavStore.list || []).slice();
      const newId = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
      own.push({ id: newId(), name: input.value.trim().slice(0, 40) || `${a} → ${b}`, from, to });
      if (dlg.querySelector(".fback")?.checked) own.push({ id: newId(), name: `${b} → ${a}`, from: to, to: from });
      dlg.hidden = true;
      dlg.innerHTML = "";
      FavStore.set(own);
    }

    _pick(input, commit) {
      const key = input.dataset.f;
      const text = input.value.trim().toLowerCase();
      const id = this._byText?.get(text);
      if (id) {
        input.removeAttribute("aria-invalid");
        if (this._state[key] !== id) this._set({ [key]: id }, false);
      } else if (commit) {
        if (!text) {
          input.removeAttribute("aria-invalid");
          this._set({ [key]: "" }, false);
        } else {
          input.setAttribute("aria-invalid", "true");
        }
      }
    }

    _set(change, sync = true) {
      this._state = { ...this._state, ...change };
      this._save();
      if (sync) this._sync();
      clearTimeout(this._debounce);
      this._debounce = setTimeout(() => this._search(), 250);
    }

    _sync() {
      if (!this._root || !this._config) return;
      const q = (s) => this._root.querySelector(s);
      const t = (k) => this._t(k);
      this._card.header = this._config.title ?? t("route_title");
      q(".lf").textContent = t("route_from");
      q(".lt").textContent = t("route_to");
      const swap = q("[data-swap]");
      swap.setAttribute("aria-label", t("route_swap"));
      swap.title = t("route_swap");
      for (const b of this._root.querySelectorAll("[data-m]")) {
        b.textContent = t(`route_${b.dataset.m}`);
        b.setAttribute("aria-pressed", String(this._state.mode === b.dataset.m));
      }
      const walk = q("[data-walk]");
      walk.textContent = `🚶 ${t("walk_switch")}`;
      walk.setAttribute("aria-pressed", String(!!this._state.walk));
      walk.hidden = this._config.show_walk === false;
      const time = q("input[type=time]");
      time.hidden = this._state.mode === "now";
      time.value = this._state.time;
      time.setAttribute("aria-label", t("route_time"));
      for (const key of ["from", "to"]) {
        const input = q(`[data-f=${key}]`);
        if (this._root.activeElement !== input) input.value = this._label(this._state[key]);
        input.placeholder = t(`route_pick_${key}`);
        input.setAttribute("aria-label", t(`route_${key}`));
      }
      q(".foot").textContent = t("route_note");
      this._renderFavs();
    }

    _show(html) {
      this._root.querySelector(".results").innerHTML = html;
    }

    async _search(silent = false) {
      if (!this._hass || !this._root || !this._state) return;
      clearTimeout(this._debounce);
      const t = (k) => this._t(k);
      const { from, to, mode, time } = this._state;
      const box = this._root.querySelector(".results");
      if (!from || !to) return this._show(`<div class="empty">${esc(t("route_pick"))}</div>`);
      if (from === to) return this._show(`<div class="empty">${esc(t("route_same"))}</div>`);
      if (silent && document.hidden) return;
      const seq = ++this._seq;
      if (!silent) {
        box.setAttribute("aria-busy", "true");
        if (!this._hasResults) this._show(`<div class="empty">${esc(t("route_loading"))}</div>`);
      }
      try {
        const msg = { type: "dpmk/plan_route", from, to, mode, limit: this._config.max_rows || 4 };
        if (mode !== "now") msg.time = time;
        // metres one may walk to a nearby stop at the start and the end; left out = the integration's default
        const cfgWalk = Number(this._config.walk);
        if (this._config.show_walk === false) {
          if (Number.isFinite(cfgWalk)) msg.walk = Math.max(0, Math.min(600, Math.round(cfgWalk)));
        } else {
          // the switch: on = the distance of the card settings (300 m when none is set), off = no walking
          msg.walk = this._state.walk ? Math.max(0, Math.min(600, Math.round(cfgWalk > 0 ? cfgWalk : 300))) : 0;
        }
        const result = await this._hass.callWS(msg);
        if (seq !== this._seq) return;
        this._hasResults = true;
        this._render(result);
      } catch (err) {
        if (seq !== this._seq || silent) return; // a refresh that fails keeps what is shown
        this._hasResults = false;
        this._show(`<div class="empty">${esc(t(ROUTE_ERRORS[err?.code] || "route_unavailable"))}</div>`);
      } finally {
        if (seq === this._seq) box.setAttribute("aria-busy", "false");
      }
    }

    _render(result) {
      const t = (k) => this._t(k);
      const lang = pickLanguage(this._config, this._hass);
      const list = result.connections || [];
      if (!list.length) {
        return this._show(`<div class="empty"><b>${esc(t("route_none"))}</b><br>${esc(t("route_hint"))}</div>`);
      }
      const earliest = list.length > 1 ? list.reduce((a, b) => (new Date(b.arrive) < new Date(a.arrive) ? b : a)) : null;
      const today = new Date().toDateString();
      this._show(
        list
          .map((c) => {
            const first = c.legs[0];
            let delay = "";
            if (first.live) {
              delay =
                first.delay_min > 0
                  ? `<span class="late">+${esc(first.delay_min)} min</span>`
                  : first.delay_min < 0
                  ? `<span class="early">${esc(first.delay_min)} min</span>`
                  : `<span class="ok">${esc(t("ontime"))}</span>`;
            }
            const badges = c.legs
              .map((l, i) => {
                const bg = colorOk(l.bg);
                const fg = colorOk(l.fg);
                return (
                  (i ? '<span class="arrow" aria-hidden="true">\u203a</span>' : "") +
                  `<span class="line t${esc(l.type)} ${sizeClass(l.line)}" style="${bg ? `background:${esc(bg)};` : ""}${fg ? `color:${esc(fg)};` : ""}">${esc(l.line)}</span>`
                );
              })
              .join("");
            const changes = c.changes.map((ch) => {
              const to = ch.walk ? ` \u2192 ${ch.to_stop} (${t("route_walk")} ${ch.walk} min)` : "";
              return `<b>${esc(t("route_change"))}</b> ${esc(ch.stop)}${esc(to)} \u00b7 ${esc(t("route_wait"))} ${esc(ch.wait)} min`;
            });
            const walkText = (w, key) =>
              w ? esc(t(key).replace("{min}", w.minutes).replace("{stop}", w.stop)) : "";
            const walkIn = walkText(c.walk_start, "route_walk_start");
            const walkOut = walkText(c.walk_end, "route_walk_end");
            const where = [
              walkIn ? `\ud83d\udeb6 ${walkIn}` : "",
              changes.length
                ? changes.join("<br>")
                : `<b>${esc(first.from)}</b> \u2192 ${esc(first.to)} \u00b7 ${esc(t("route_direct"))}`,
              walkOut ? `\ud83d\udeb6 ${walkOut}` : "",
            ]
              .filter(Boolean)
              .join("<br>");
            const day = new Date(c.depart).toDateString() !== today ? `<span class="tag">${esc(t("route_tomorrow"))}</span>` : "";
            const spoken = [
              `${clock(c.depart, lang)} \u2013 ${clock(c.arrive, lang)}`,
              `${c.minutes} min`,
              c.legs.map((l) => l.line).join(" \u203a "),
              c.walk_start ? t("route_walk_start").replace("{min}", c.walk_start.minutes).replace("{stop}", c.walk_start.stop) : "",
              c.changes.map((ch) => `${t("route_change")} ${ch.stop}`).join(", "),
              c.walk_end ? t("route_walk_end").replace("{min}", c.walk_end.minutes).replace("{stop}", c.walk_end.stop) : "",
              first.live ? t("live") : "",
            ]
              .filter(Boolean)
              .join(", ");
            return `<div class="conn${c === earliest ? " best" : ""}" role="group" aria-label="${esc(spoken)}">
              <div class="top"><span class="times">${clock(c.depart, lang)} \u2192 ${clock(c.arrive, lang)}${day}${c === earliest ? `<span class="tag">${esc(t("route_best"))}</span>` : ""}</span><span class="dur">${esc(c.minutes)} min</span></div>
              <div class="legs">${badges}${first.live ? ` <span class="tag live">${esc(t("live"))}</span>` : ""}</div>
              <div class="detail">${where}${delay ? ` \u00b7 ${delay}` : ""}</div>
            </div>`;
          })
          .join("")
      );
    }
  }

  /* The editor needs the stop list, which comes from the integration. */
  class DpmkRouteEditor extends HTMLElement {
    setConfig(config) {
      this._config = config;
      this._render();
    }
    set hass(hass) {
      this._hass = hass;
      if (!this._stops && !this._loading) {
        this._loading = true;
        hass
          .callWS({ type: "dpmk/stops" })
          .then((r) => (this._stops = r.stops))
          .catch(() => (this._stops = []))
          .finally(() => this._render());
      }
      this._render();
    }
    _render() {
      if (!this._hass || !this._config) return;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = (s) => I18N[pickLanguage(this._config, this._hass)][s.name] || s.name;
        this._form.addEventListener("value-changed", (ev) =>
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: ev.detail.value } }))
        );
        this.appendChild(this._form);
      }
      const stops = this._stops || [];
      const pick = (name) =>
        stops.length
          ? { name, selector: { select: { mode: "dropdown", options: stops.map((s) => ({ value: s.id, label: s.label })) } } }
          : { name, selector: { text: {} } };
      this._form.hass = this._hass;
      this._form.data = { max_rows: 4, walk: 0, show_walk: true, show_favourites: true, ...this._config };
      this._form.schema = [
        pick("from_stop"),
        pick("to_stop"),
        { name: "title", selector: { text: {} } },
        { name: "max_rows", selector: { number: { min: 1, max: 8, mode: "box" } } },
        { name: "walk", selector: { number: { min: 0, max: 600, step: 50, mode: "box", unit_of_measurement: "m" } } },
        { name: "show_walk", selector: { boolean: {} } },
        { name: "show_favourites", selector: { boolean: {} } },
        LANGUAGE_FIELD,
      ];
    }
  }

  const LANGUAGE_FIELD = {
    name: "language",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "default", label: "Z integrácie / From the integration" },
          { value: "sk", label: "Slovenčina" },
          { value: "en", label: "English" },
          { value: "auto", label: "Automaticky / Automatic" },
        ],
      },
    },
  };
  const ENTITY_FIELD = {
    name: "entity",
    selector: { entity: { domain: "sensor", device_class: "timestamp" } },
  };

  // `defaults` are what the card does when an option is left out, so the switches show the real state.
  const makeEditor = (schema, defaults = {}) =>
    class extends HTMLElement {
      setConfig(config) {
        this._config = config;
        this._render();
      }
      set hass(hass) {
        this._hass = hass;
        this._render();
      }
      _render() {
        if (!this._hass || !this._config) return;
        if (!this._form) {
          this._form = document.createElement("ha-form");
          this._form.computeLabel = (s) =>
            I18N[pickLanguage(this._config, this._hass)][s.name] || s.name;
          this._form.addEventListener("value-changed", (ev) =>
            this.dispatchEvent(
              new CustomEvent("config-changed", { detail: { config: ev.detail.value } })
            )
          );
          this.appendChild(this._form);
        }
        this._form.hass = this._hass;
        this._form.data = { ...defaults, ...this._config };
        this._form.schema = schema;
      }
    };

  const define = (name, cls) => {
    if (!customElements.get(name)) customElements.define(name, cls);
  };
  define("dpmk-departures-card", DpmkDeparturesCard);
  define("dpmk-map-card", DpmkMapCard);
  define("dpmk-route-card", DpmkRouteCard);
  define("dpmk-route-card-editor", DpmkRouteEditor);
  define(
    "dpmk-departures-card-editor",
    makeEditor([
      ENTITY_FIELD,
      { name: "title", selector: { text: {} } },
      { name: "max_rows", selector: { number: { min: 1, max: 20, mode: "box" } } },
      { name: "show_delay", selector: { boolean: {} } },
      { name: "show_filter", selector: { boolean: {} } },
      LANGUAGE_FIELD,
    ], { show_delay: true, show_filter: true })
  );
  define(
    "dpmk-map-card-editor",
    makeEditor([
      ENTITY_FIELD,
      { name: "title", selector: { text: {} } },
      { name: "show_legend", selector: { boolean: {} } },
      {
        name: "background",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "map", label: "Mapa / Map" },
              { value: "none", label: "Bez mapy / No map" },
            ],
          },
        },
      },
      {
        name: "map_style",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "auto", label: "Automaticky / Automatic" },
              { value: "light", label: "Svetlá / Light" },
              { value: "dark", label: "Tmavá / Dark" },
            ],
          },
        },
      },
      { name: "show_rings", selector: { boolean: {} } },
      { name: "show_filter", selector: { boolean: {} } },
      LANGUAGE_FIELD,
    ], { show_legend: true, show_filter: true })
  );

  window.customCards = window.customCards || [];
  // The picker cannot know the card language yet, so its entries are bilingual.
  for (const [type, name, description] of [
    [
      "dpmk-departures-card",
      "DPMK odchody / departures",
      "Najbližšie odchody DPMK Košice s aktuálnym meškaním / Upcoming DPMK Košice departures with live delays",
    ],
    [
      "dpmk-map-card",
      "DPMK mapa / map",
      "Vozidlá DPMK v okolí zastávky / DPMK vehicles around the stop, simple overview",
    ],
    [
      "dpmk-route-card",
      "DPMK plánovač trasy / route planner",
      "Spojenie medzi dvoma zastávkami, aj s prestupom / Connections between two stops, also with a change",
    ],
  ]) {
    if (!window.customCards.some((c) => c.type === type)) {
      window.customCards.push({ type, name, description, preview: false });
    }
  }
})();
