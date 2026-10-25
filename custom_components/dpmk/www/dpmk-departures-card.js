/* DPMK Košice Lovelace cards (both live in this one file):
 *   type: custom:dpmk-departures-card   entity: sensor.<stop>_next_departure
 *   type: custom:dpmk-map-card          entity: sensor.<stop>_next_departure
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
      none: "Žiadne ďalšie odchody",
      missing: "Entita nebola nájdená:",
      choose: "Nenašiel sa žiadny senzor DPMK. Pridajte zastávku v integrácii DPMK Košice.",
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
      none: "No upcoming departures",
      missing: "Entity not found:",
      choose: "No DPMK sensor found. Add a stop in the DPMK Košice integration.",
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

  const clock = (iso, lang) =>
    new Date(iso).toLocaleTimeString(lang === "en" ? "en-GB" : "sk-SK", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

  const sizeClass = (line) => (line.length <= 2 ? "" : line.length === 3 ? "s3" : "s4");


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
      if (!this._root) {
        this._root = this.attachShadow({ mode: "open" });
        this._timer = setInterval(() => this._render(), 15000);
      }
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
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
      if (!st) {
        rows = `<div class="empty">${entity ? `${this._t("missing")} ${entity}` : this._t("choose")}</div>`;
      } else {
        const now = new Date();
        const deps = (st.attributes.departures || [])
          .filter((d) => new Date(d.expected) > now - 30000)
          .slice(0, this._config.max_rows || 6);
        rows = deps.length
          ? deps
              .map((d) => {
                const delay = d.live
                  ? d.delay_min > 0
                    ? `<span class="late">+${d.delay_min} min</span>`
                    : d.delay_min < 0
                    ? `<span class="early">${d.delay_min} min</span>`
                    : `<span class="ok">${this._t("ontime")}</span>`
                  : "";
                const live = `<span class="dot${d.live ? " on" : ""}" title="live"></span>`;
                const real = `<span class="real">${d.live ? `[${clock(d.expected, lang)}]` : ""}</span>`;
                // a place with several stops: say which stop each departure is from
                const stopName = st.attributes.multi_stop && d.stop ? d.stop : "";
                const sub = [stopName, this._countdown(d, now), this._config.show_delay === false ? "" : delay]
                  .filter(Boolean)
                  .join(" · ");
                return `<div class="row">
                  <span class="line t${d.type} ${sizeClass(d.line)}" style="${d.bg ? `background:${d.bg};` : ""}${d.fg ? `color:${d.fg};` : ""}">${d.line}</span>
                  <span class="dest">${d.destination}<span class="sub">${sub}</span></span>
                  <span class="when">${live}<span class="off">${clock(d.scheduled, lang)}</span>${real}</span>
                </div>`;
              })
              .join("")
          : `<div class="empty">${this._t("none")}</div>`;
      }
      this._root.innerHTML = `
        <ha-card header="${title}">
          <style>
            ${BADGE_CSS}
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
          ${rows}
        </ha-card>`;
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
      }
      this._build();
      this._update();
    }

    set hass(hass) {
      this._hass = hass;
      const st = hass.states[resolveEntity(this._config, hass)];
      if (st !== this._lastState) {
        this._lastState = st;
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
            .legend i { display:inline-block; width:10px; height:10px; border-radius:3px;
                        vertical-align:-1px; margin-right:6px; background:#9b9c9f; }
          </style>
          <div class="radar">
            <div class="mapbg" hidden></div>
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
      q(".north").textContent = this._t("north");
      const legend = q(".legend");
      legend.style.display = this._config.show_legend === false ? "none" : "";
      legend.innerHTML = `<span><i style="background:${RING.approaching}"></i>${this._t("arriving")}</span>
                          <span><i style="background:${RING.leaving}"></i>${this._t("leaving")}</span>`;
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
      const vehicles = a.vehicles || [];
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
        b.style.boxShadow = serves
          ? `0 0 0 3px ${ring || "rgba(255,255,255,.75)"}, 0 1px 4px rgba(0,0,0,.45)`
          : "0 1px 3px rgba(0,0,0,.35)";
        el.style.opacity = serves ? "1" : "0.5";
        el.lastElementChild.textContent = serves ? this._label(v, now) : "";
        el.lastElementChild.style.display = serves ? "" : "none";
      }
      for (const [id, el] of this._els) {
        if (!seen.has(id)) {
          el.remove();
          this._els.delete(id);
        }
      }
      q(".nov").textContent = vehicles.length ? "" : this._t("no_vehicles");
    }
  }

  /* ------------------------------------------------------------------ */
  /* Editors                                                             */
  /* ------------------------------------------------------------------ */
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

  const makeEditor = (schema) =>
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
        this._form.data = this._config;
        this._form.schema = schema;
      }
    };

  const define = (name, cls) => {
    if (!customElements.get(name)) customElements.define(name, cls);
  };
  define("dpmk-departures-card", DpmkDeparturesCard);
  define("dpmk-map-card", DpmkMapCard);
  define(
    "dpmk-departures-card-editor",
    makeEditor([
      ENTITY_FIELD,
      { name: "title", selector: { text: {} } },
      { name: "max_rows", selector: { number: { min: 1, max: 20, mode: "box" } } },
      { name: "show_delay", selector: { boolean: {} } },
      LANGUAGE_FIELD,
    ])
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
      LANGUAGE_FIELD,
    ])
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
  ]) {
    if (!window.customCards.some((c) => c.type === type)) {
      window.customCards.push({ type, name, description, preview: false });
    }
  }
})();
