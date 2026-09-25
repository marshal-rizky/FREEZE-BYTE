// Lapisan overlay: satu-satunya modul yang menyentuh halaman, dan itu pun
// hanya menambah SATU elemen host di <html>. DOM halaman tidak pernah
// diubah -- situs SPA seperti Stockbit memiliki DOM-nya sendiri, dan span
// yang disisipkan ke text node akan ditimpa atau membuat render-nya error.
// Saham yang sedang dibuka (Lapis 0) tampil sebagai strip di atas-tengah
// yang menciut jadi pil.
//
// Posisi lencana diukur dari Range di teks halaman dan diukur ulang saat
// scroll, resize, dan scan ulang, paling banyak sekali per frame.
(function (root) {
  const MAX_BADGES = 60;
  const MARGIN = 16;
  const COLLAPSE_AFTER_MS = 6000;

  const CSS = `
    :host { all: initial; }
    .mark {
      position: fixed; left: 0; top: 0; pointer-events: none;
      background: transparent; padding: 0; border-radius: 3px; box-sizing: border-box;
    }
    .mark.tinggi { border: 1.5px solid #f2555a; }
    .mark.sedang { border: 1.5px solid #e0a43a; }
    .mark[hidden] { display: none; }
    .glyph {
      position: absolute; top: -14px; right: -12px; pointer-events: auto;
      width: 16px; height: 16px; padding: 0; margin: 0; box-sizing: border-box;
      display: flex; align-items: center; justify-content: center;
      background: transparent; border: 0; cursor: pointer;
      font: 700 11px/1 system-ui, sans-serif; color: #f2555a;
    }
    .glyph.sedang { color: #e0a43a; }
    .card {
      position: fixed; left: 50%; right: auto; top: 140px;
      transform: translateX(-50%); width: min(360px, calc(100vw - 32px));
      max-height: calc(100vh - 156px); overflow: auto;
      pointer-events: auto; background: #0e131d; color: #eaf0f9;
      border: 1px solid rgba(255,255,255,.14); border-radius: 14px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 18px 40px rgba(0,0,0,.5);
      padding: 16px; font: 400 13px/1.45 system-ui, sans-serif;
    }
    .card[hidden] { display: none; }
    .card h2 { font-size: 15px; margin: 0 0 4px; }
    .card .label.tinggi { color: #ff8a8e; }
    .card .label.sedang { color: #f2c46d; }
    .card p { margin: 8px 0; }
    .card .caveat, .card .stale { color: #9aa7bb; font-size: 12px; }
    .card .stale { color: #f2c46d; }
    .card a { color: #8ab8ff; }
    .card ul { margin: 6px 0; padding-left: 18px; color: #c5cfdd; }
    .card .close {
      position: absolute; right: 10px; top: 8px; background: none; border: 0;
      color: #9aa7bb; font-size: 18px; cursor: pointer;
    }
    .pin {
      position: fixed; top: 56px; left: 50%; transform: translateX(-50%);
      pointer-events: auto; font: 400 13px/1.35 system-ui, sans-serif; color: #fff;
    }
    .pin[data-state="collapsed"] .strip { display: none; }
    .pin[data-state="expanded"] .pill { display: none; }
    .strip {
      box-sizing: border-box; width: min(680px, calc(100vw - 32px));
      display: flex; align-items: center; gap: 12px; padding: 11px 14px;
      border-radius: 14px; border: 1px solid transparent;
    }
    .pin.tinggi .strip { background: rgba(58,13,16,.95); border-color: #f2555a;
      box-shadow: 0 0 0 6px rgba(242,85,90,.18), 0 18px 40px rgba(0,0,0,.35); }
    .pin.sedang .strip { background: rgba(51,37,10,.95); border-color: #e0a43a;
      box-shadow: 0 0 0 6px rgba(224,164,58,.18), 0 18px 40px rgba(0,0,0,.35); }
    .strip .tri { font-size: 22px; line-height: 1; }
    .pin.tinggi .tri { color: #ff6b70; }
    .pin.sedang .tri { color: #f2c46d; }
    .strip .text { min-width: 0; }
    .strip .sym { font-weight: 800; font-size: 17px; letter-spacing: .02em; }
    .strip .lbl { font-weight: 700; font-size: 15px; margin-left: 8px; }
    .pin.tinggi .lbl { color: #ffd9da; }
    .pin.sedang .lbl { color: #ffe7b8; }
    .strip .sub { font-size: 12px; color: rgba(255,255,255,.72); margin-top: 2px; }
    .strip .go, .strip .x {
      background: transparent; color: #fff; cursor: pointer; font: inherit;
    }
    .strip .go { margin-left: auto; font-size: 12px; white-space: nowrap;
      border: 1px solid rgba(255,255,255,.35); padding: 4px 9px; border-radius: 10px; }
    .strip .x { border: 0; font-size: 18px; line-height: 1; color: rgba(255,255,255,.6); padding: 2px 4px; }
    .pill {
      display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
      padding: 5px 12px; border-radius: 999px; border: 1px solid transparent;
      font: 700 12px/1 system-ui, sans-serif; white-space: nowrap;
      box-shadow: 0 6px 18px rgba(0,0,0,.3); animation: fb-fade 240ms ease-out;
    }
    .pin.tinggi .pill { background: rgba(58,13,16,.95); border-color: #f2555a; color: #ffd9da; }
    .pin.sedang .pill { background: rgba(51,37,10,.95); border-color: #e0a43a; color: #ffe7b8; }
    .pin .strip { animation: fb-fade 240ms ease-out; }
    .pin.fresh .strip { animation: fb-enter 420ms cubic-bezier(0.16, 1, 0.3, 1); }
    .pin.fresh.tinggi .strip {
      animation: fb-enter 420ms cubic-bezier(0.16, 1, 0.3, 1),
                 fb-pulse 900ms ease-out 420ms 2;
    }
    @keyframes fb-enter {
      from { opacity: 0; transform: translateY(-12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fb-fade { from { opacity: 0; } to { opacity: 1; } }
    @keyframes fb-pulse {
      0% { box-shadow: 0 0 0 6px rgba(242,85,90,.35), 0 18px 40px rgba(0,0,0,.35); }
      100% { box-shadow: 0 0 0 18px rgba(242,85,90,0), 0 18px 40px rgba(0,0,0,.35); }
    }
    @media (prefers-reduced-motion: reduce) {
      .pin .strip, .pin.fresh .strip, .pin.fresh.tinggi .strip, .pill { animation: none; }
    }
  `;

  const FLAG_LABELS = {
    float_under_25: "Free float di bawah 25%",
    single_entity_70: "Satu pihak memegang lebih dari 70%",
    insider_1m_sell: "Orang dalam menjual dalam sebulan terakhir",
    at_52w_high: "Di puncak 52 minggu",
  };

  const esc = (s) => String(s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function cardHtml(v) {
    const flags = v.flags
      ? Object.keys(FLAG_LABELS).filter((k) => v.flags[k]).map((k) => `<li>${FLAG_LABELS[k]}</li>`)
      : [];
    return `
      <button class="close" type="button" aria-label="Tutup">&times;</button>
      <h2>${esc(v.symbol)}</h2>
      <div class="label ${esc(v.tier)}">${esc(v.label)}</div>
      <p><strong>${esc(v.move)}</strong></p>
      <p>${esc(v.evidence)}</p>
      ${flags.length ? `<p>Kondisi sekarang:</p><ul>${flags.join("")}</ul>` : ""}
      ${v.stale ? `<p class="stale">Data per ${esc(v.asOf)} &mdash; sudah lebih dari seminggu.</p>`
                : `<p class="caveat">Data per ${esc(v.asOf)}.</p>`}
      <p class="caveat">${esc(v.caveat)}</p>
      <p><a href="${esc(v.evidenceUrl)}" target="_blank" rel="noopener">Lihat buktinya</a></p>`;
  }

  function createOverlay(doc) {
    const win = doc.defaultView;
    const host = doc.createElement("freeze-byte-overlay");
    host.style.cssText =
      "position:fixed;inset:0;pointer-events:none;z-index:2147483647;display:block;";
    host.dataset.badges = "0";
    const shadow = host.attachShadow({ mode: "closed" });
    shadow.innerHTML = `<style>${CSS}</style><div class="layer"></div><div class="top"></div><div class="card" hidden></div>`;
    doc.documentElement.appendChild(host);

    const layer = shadow.querySelector(".layer");
    const card = shadow.querySelector(".card");
    const top = shadow.querySelector(".top");
    let pinned = null;   // { symbol, el, timer }
    let built = 0;
    host.dataset.pinned = "";
    host.dataset.pinnedBuilt = "0";
    let items = [];
    let frame = 0;

    function openCard(v) {
      card.innerHTML = cardHtml(v);
      card.hidden = false;
      card.querySelector(".close").addEventListener("click", () => { card.hidden = true; });
    }

    function makeMark(v) {
      // Bingkai (.mark) punya pointer-events: none -- klik dan seleksi teks
      // menembusnya ke halaman di baliknya. Satu-satunya target klik adalah
      // glyph kecil di pojok kanan atasnya.
      const mark = doc.createElement("div");
      mark.className = `mark ${v.tier}`;

      const glyph = doc.createElement("button");
      glyph.type = "button";
      glyph.className = `glyph ${v.tier}`;
      glyph.textContent = v.tier === "tinggi" ? "▲" : "△";
      glyph.title = `${v.symbol} · ${v.label}`;
      glyph.setAttribute("aria-label", `${v.symbol} · ${v.label}`);
      glyph.addEventListener("click", (event) => {
        event.stopPropagation();
        openCard(v);
      });
      mark.appendChild(glyph);

      layer.appendChild(mark);
      return mark;
    }

    function setPinnedState(state) {
      pinned.el.dataset.state = state;
      host.dataset.pinned = `${pinned.symbol}:${state}`;
    }

    function dropPinned() {
      if (!pinned) return;
      pinned.timer.cancel();
      pinned.el.remove();
      pinned = null;
      host.dataset.pinned = "";
    }

    // Strip Lapis 0: satu per halaman, di atas-tengah. Dibuat sekali per
    // simbol -- scan ulang dengan simbol yang sama tidak menyentuhnya, supaya
    // animasi masuk tidak berulang dan keadaan penuh/pil tidak ter-reset.
    function buildPinned(v) {
      const tri = v.tier === "tinggi" ? "▲" : "△";
      const stale = v.stale ? ` · data per ${esc(v.asOf)}` : "";
      const el = doc.createElement("div");
      el.className = `pin ${v.tier} fresh`;
      el.innerHTML = `
        <div class="strip" role="status">
          <span class="tri">${tri}</span>
          <div class="text">
            <div><span class="sym">${esc(v.symbol)}</span><span class="lbl">${esc(v.label)}</span></div>
            <div class="sub">${esc(v.move)} · ${esc(v.headline)}${stale}</div>
          </div>
          <button class="go" type="button">Detail ›</button>
          <button class="x" type="button" aria-label="Ciutkan">×</button>
        </div>
        <button class="pill" type="button">${tri} ${esc(v.symbol)} · ${esc(v.label)}</button>`;
      top.appendChild(el);

      const timer = root.FreezeByte.createCollapseTimer(() => {
        el.classList.remove("fresh");
        setPinnedState("collapsed");
      }, COLLAPSE_AFTER_MS);
      pinned = { symbol: v.symbol, el, timer };
      built += 1;
      host.dataset.pinnedBuilt = String(built);
      setPinnedState("expanded");

      const strip = el.querySelector(".strip");
      strip.addEventListener("mouseenter", () => timer.hold());
      strip.addEventListener("mouseleave", () => timer.release());
      el.querySelector(".go").addEventListener("click", (event) => {
        event.stopPropagation();
        openCard(v);
      });
      el.querySelector(".x").addEventListener("click", (event) => {
        event.stopPropagation();
        timer.collapseNow();
      });
      el.querySelector(".pill").addEventListener("click", (event) => {
        event.stopPropagation();
        el.classList.remove("fresh");   // buka lagi tanpa denyut
        setPinnedState("expanded");
        timer.start();
      });
      timer.start();
    }

    function syncPinned(item) {
      if (!item) { dropPinned(); return; }
      if (pinned && pinned.symbol === item.verdict.symbol) return;
      dropPinned();
      buildPinned(item.verdict);
    }

    function rectOf(item) {
      return item.range ? item.range.getBoundingClientRect() : null;
    }

    function place() {
      frame = 0;
      const vw = win.innerWidth;
      const vh = win.innerHeight;
      let visible = 0;
      for (const item of items) {
        const rect = rectOf(item);
        let off = !rect || rect.width === 0 ||
          rect.bottom < 0 || rect.top > vh || rect.right < 0 || rect.left > vw;
        if (!off) {
          // Teks bisa ada di layout (rect valid) tapi tertutup elemen lain
          // (mis. logo situs) -- elementFromPoint di titik tengah rect
          // memastikan lencana hanya nempel di teks yang benar-benar di atas.
          const cx = rect.left + rect.width / 2;
          const cy = rect.top + rect.height / 2;
          const hit = doc.elementFromPoint(cx, cy);
          const parent = item.range.startContainer.parentElement;
          // hit.contains(parent) sendirian gampang jebol: body/html selalu
          // "berisi" parent apa pun, jadi scrim full-page (mis. body::after
          // fixed inset:0) akan lolos sebagai "ancestor" padahal itu justru
          // yang menutupi. Cabang leluhur hanya berlaku kalau hit bukan
          // body/html.
          const onOwner = hit === host ||
            (parent != null && (parent.contains(hit) ||
              (hit != null && hit !== doc.body && hit !== doc.documentElement &&
                hit.contains(parent))));
          if (!onOwner) off = true;
        }
        item.el.hidden = off;
        if (off) continue;
        // Bingkai tepat di kotak ticker -- tidak menutupi kata sesudahnya.
        item.el.style.width = `${Math.round(rect.width + 4)}px`;
        item.el.style.height = `${Math.round(rect.height + 2)}px`;
        item.el.style.transform =
          `translate(${Math.round(rect.left - 2)}px, ${Math.round(rect.top - 1)}px)`;
        visible += 1;
      }
      host.dataset.badges = String(visible + (pinned ? 1 : 0));
    }

    function schedule() {
      if (!frame) frame = win.requestAnimationFrame(place);
    }

    function setItems(next) {
      syncPinned(next.find((item) => item.pinned) || null);
      layer.textContent = "";
      items = next.filter((item) => item.range).slice(0, MAX_BADGES).map((item) => ({
        ...item,
        el: makeMark(item.verdict),
      }));
      schedule();
    }

    win.addEventListener("scroll", schedule, { passive: true, capture: true });
    win.addEventListener("resize", schedule, { passive: true });
    return { setItems, schedule, host };
  }

  root.FreezeByte = Object.assign(root.FreezeByte || {}, { createOverlay });
})(globalThis);
