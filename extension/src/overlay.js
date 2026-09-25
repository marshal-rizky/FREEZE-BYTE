// Lapisan overlay: satu-satunya modul yang menyentuh halaman, dan itu pun
// hanya menambah SATU elemen host di <html>. DOM halaman tidak pernah
// diubah -- situs SPA seperti Stockbit memiliki DOM-nya sendiri, dan span
// yang disisipkan ke text node akan ditimpa atau membuat render-nya error.
//
// Posisi lencana diukur dari Range di teks halaman dan diukur ulang saat
// scroll, resize, dan scan ulang, paling banyak sekali per frame.
(function (root) {
  const MAX_BADGES = 60;
  const MARGIN = 16;

  const CSS = `
    :host { all: initial; }
    .badge {
      position: fixed; left: 0; top: 0; pointer-events: auto; cursor: pointer;
      font: 600 11px/1 system-ui, sans-serif; letter-spacing: .01em;
      padding: 4px 7px; border-radius: 999px; border: 1px solid transparent;
      white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,.35);
    }
    .badge.tinggi { background: #3a0d10; color: #ffd9da; border-color: #f2555a; }
    .badge.sedang { background: #33250a; color: #ffe7b8; border-color: #e0a43a; }
    .badge::before { content: "\\25B2  "; }
    .badge.sedang::before { content: "\\25B3  "; }
    .badge[hidden] { display: none; }
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
      position: fixed; right: ${MARGIN}px; top: ${MARGIN}px; width: 320px;
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
    shadow.innerHTML = `<style>${CSS}</style><div class="layer"></div><div class="card" hidden></div>`;
    doc.documentElement.appendChild(host);

    const layer = shadow.querySelector(".layer");
    const card = shadow.querySelector(".card");
    let items = [];
    let frame = 0;

    function openCard(v) {
      card.innerHTML = cardHtml(v);
      card.hidden = false;
      card.querySelector(".close").addEventListener("click", () => { card.hidden = true; });
    }

    function makeBadge(v) {
      const badge = doc.createElement("button");
      badge.type = "button";
      badge.className = `badge ${v.tier}`;
      badge.textContent = `${v.symbol} · ${v.label}`;
      badge.addEventListener("click", (event) => {
        event.stopPropagation();
        openCard(v);
      });
      layer.appendChild(badge);
      return badge;
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

    function rectOf(item) {
      if (item.range) return item.range.getBoundingClientRect();
      if (item.anchor && item.anchor.isConnected) return item.anchor.getBoundingClientRect();
      return null;
    }

    function place() {
      frame = 0;
      const vw = win.innerWidth;
      const vh = win.innerHeight;
      let visible = 0;
      for (const item of items) {
        const rect = rectOf(item);
        if (item.pinned && !rect) {
          // Lapis 0 tanpa jangkar: pojok kanan atas.
          item.el.hidden = false;
          item.el.style.transform =
            `translate(${vw - item.el.offsetWidth - MARGIN}px, ${MARGIN}px)`;
          visible += 1;
          continue;
        }
        let off = !rect || rect.width === 0 ||
          rect.bottom < 0 || rect.top > vh || rect.right < 0 || rect.left > vw;
        if (!off && item.range && !item.pinned) {
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
        if (item.range) {
          // Bingkai tepat di kotak ticker -- tidak menutupi kata sesudahnya.
          item.el.style.width = `${Math.round(rect.width + 4)}px`;
          item.el.style.height = `${Math.round(rect.height + 2)}px`;
          item.el.style.transform =
            `translate(${Math.round(rect.left - 2)}px, ${Math.round(rect.top - 1)}px)`;
        } else {
          item.el.style.transform =
            `translate(${Math.round(rect.right + 4)}px, ${Math.round(rect.top - 3)}px)`;
        }
        visible += 1;
      }
      host.dataset.badges = String(visible);
    }

    function schedule() {
      if (!frame) frame = win.requestAnimationFrame(place);
    }

    function setItems(next) {
      layer.textContent = "";
      items = next.slice(0, MAX_BADGES).map((item) => ({
        ...item,
        el: item.range ? makeMark(item.verdict) : makeBadge(item.verdict),
      }));
      schedule();
    }

    win.addEventListener("scroll", schedule, { passive: true, capture: true });
    win.addEventListener("resize", schedule, { passive: true });
    return { setItems, schedule, host };
  }

  root.FreezeByte = Object.assign(root.FreezeByte || {}, { createOverlay });
})(globalThis);
