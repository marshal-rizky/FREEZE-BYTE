// Grafik harga SVG tanpa dependensi. Jendela beku diberi shading.
const NS = "http://www.w3.org/2000/svg";

function el(name, attrs, text) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs || {})) {
    node.setAttribute(key, value);
  }
  if (text !== undefined) node.textContent = text;
  return node;
}

const idFmt = (n) => n.toLocaleString("id-ID");

/* Kurva monotonik Fritsch-Carlson.
 *
 * Spline Catmull-Rom yang biasa dipakai untuk "menghaluskan" grafik akan
 * overshoot di sekitar titik balik yang tajam -- dan di grafik harga itu
 * berarti menggambar harga yang tidak pernah terjadi. Interpolasi monotonik
 * tidak pernah melewati nilai data di antara dua titik, jadi kurvanya halus
 * tanpa mengarang angka. ALKA punya lompatan +97% dalam enam baris; persis
 * bentuk yang membuat spline naif meleset.
 */
function monotonePath(pts) {
  if (pts.length < 2) return pts.length ? `M${pts[0].x},${pts[0].y}` : "";

  const n = pts.length;
  const dx = [], dy = [], delta = [];
  for (let i = 0; i < n - 1; i += 1) {
    dx[i] = pts[i + 1].x - pts[i].x;
    dy[i] = pts[i + 1].y - pts[i].y;
    delta[i] = dx[i] === 0 ? 0 : dy[i] / dx[i];
  }

  const m = [delta[0]];
  for (let i = 1; i < n - 1; i += 1) {
    if (delta[i - 1] * delta[i] <= 0) m[i] = 0;
    else m[i] = (delta[i - 1] + delta[i]) / 2;
  }
  m[n - 1] = delta[n - 2];

  for (let i = 0; i < n - 1; i += 1) {
    if (delta[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
    const a = m[i] / delta[i];
    const b = m[i + 1] / delta[i];
    const s = a * a + b * b;
    if (s > 9) {
      const tau = 3 / Math.sqrt(s);
      m[i] = tau * a * delta[i];
      m[i + 1] = tau * b * delta[i];
    }
  }

  let d = `M${pts[0].x},${pts[0].y}`;
  for (let i = 0; i < n - 1; i += 1) {
    const h = dx[i] / 3;
    d += ` C${pts[i].x + h},${pts[i].y + m[i] * h}` +
         ` ${pts[i + 1].x - h},${pts[i + 1].y - m[i + 1] * h}` +
         ` ${pts[i + 1].x},${pts[i + 1].y}`;
  }
  return d;
}

function renderPriceChart(container, data, readout) {
  const rows = data.rows.slice().sort((a, b) => a.date.localeCompare(b.date));
  // PAD.top menyediakan tempat untuk tiga baris label jendela di ATAS area
  // plot. Label tidak boleh masuk ke dalam plot: di sanalah bandnya sendiri
  // berada, dan teks di atas band merah sulit dibaca.
  const W = 900, H = 360, PAD = { top: 50, right: 20, bottom: 40, left: 64 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const closes = rows.map((r) => r.close);
  const yMin = Math.min(...closes) * 0.95;
  const yMax = Math.max(...closes) * 1.05;

  // M1: rows.length - 1 is 0 for a single-row series, which would divide by
  // zero and produce NaN coordinates for every point.
  const x = (i) => PAD.left + (i / (rows.length - 1 || 1)) * plotW;
  const y = (v) => PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
  const indexOf = (date) => rows.findIndex((r) => r.date === date);

  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    class: "price-chart",
    role: "img",
    "aria-label": `Grafik harga ${data.symbol} dengan jendela pembekuan ditandai`,
  });

  const defs = el("defs", {});
  const grad = el("linearGradient", {
    id: "priceFill", x1: "0", y1: "0", x2: "0", y2: "1",
  });
  grad.appendChild(el("stop", { offset: "0", "stop-color": "#5b9dff", "stop-opacity": "0.26" }));
  grad.appendChild(el("stop", { offset: "1", "stop-color": "#5b9dff", "stop-opacity": "0" }));
  defs.appendChild(grad);
  svg.appendChild(defs);

  // Sumbu Y lebih dulu supaya garis bantu tidak menimpa data.
  for (let i = 0; i <= 4; i += 1) {
    const value = yMin + ((yMax - yMin) * i) / 4;
    svg.appendChild(
      el("line", { x1: PAD.left, y1: y(value), x2: W - PAD.right, y2: y(value), class: "grid" })
    );
    svg.appendChild(
      el("text", { x: PAD.left - 10, y: y(value) + 4, class: "axis-label y" }, idFmt(Math.round(value)))
    );
  }

  // Shading jendela beku. Confirmed dan inferred dibedakan secara visual.
  //
  // Label ditempatkan dalam dua tahap. Jendela yang berdekatan -- ALKA punya
  // jendela 27 Juli dan 29 Juli yang hampir bersentuhan -- akan menabrakkan
  // labelnya kalau semuanya dipasang di baris yang sama, dan jendela di tepi
  // kanan akan terpotong batas viewBox. Jadi setiap label dijepit ke dalam
  // area plot lalu diturunkan satu baris sampai tidak lagi bertabrakan.
  const CHAR_W = 5.2;   // perkiraan lebar karakter pada font-size 10px
  const LABEL_GAP = 6;  // jarak minimum antar label di baris yang sama
  const ROW_H = 12;
  const LABEL_TOP = PAD.top - 28;  // baris pertama, dihitung dari atas plot
  const placed = [];    // { row, from, to } dalam koordinat viewBox

  data.windows.forEach((win) => {
    const from = indexOf(win.start_date);
    const to = indexOf(win.end_date);
    if (from < 0 || to < 0) return;
    const left = x(from);
    const width = Math.max(x(to) - left, 3);
    const kind = win.confirmed ? "confirmed" : "inferred";

    svg.appendChild(
      el("rect", {
        x: left, y: PAD.top, width: width, height: plotH,
        class: `freeze-band ${kind}`,
      })
    );
    // Tepi kiri dan kanan ditegaskan supaya batas jendela terbaca persis,
    // dan supaya gaya garis (putus vs padat) ikut membedakan statusnya.
    [left, left + width].forEach((edge) => {
      svg.appendChild(
        el("line", {
          x1: edge, y1: PAD.top, x2: edge, y2: PAD.top + plotH,
          class: `freeze-band ${kind}-edge`,
        })
      );
    });

    const text = win.confirmed ? "beku (terkonfirmasi)" : "volume nol (tersimpulkan)";
    const halfW = (text.length * CHAR_W) / 2;
    // Jepit ke dalam area plot supaya label tepi tidak terpotong.
    const cx = Math.min(
      Math.max(left + width / 2, PAD.left + halfW),
      W - PAD.right - halfW
    );
    const span = { from: cx - halfW - LABEL_GAP, to: cx + halfW + LABEL_GAP };

    let row = 0;
    while (placed.some((p) => p.row === row && p.from < span.to && span.from < p.to)) {
      row += 1;
    }
    placed.push({ row, from: span.from, to: span.to });

    svg.appendChild(
      el("text", { x: cx, y: LABEL_TOP + row * ROW_H, class: `freeze-label ${kind}` }, text)
    );
  });

  // Sumbu X: tampilkan setiap baris ke-5 supaya tidak bertumpuk
  rows.forEach((row, i) => {
    if (i % 5 !== 0) return;
    svg.appendChild(
      el("text", { x: x(i), y: H - PAD.bottom + 20, class: "axis-label x" }, row.date.slice(5))
    );
  });

  const pts = rows.map((r, i) => ({ x: x(i), y: y(r.close) }));
  const line = monotonePath(pts);
  svg.appendChild(
    el("path", {
      d: `${line} L${pts[pts.length - 1].x},${PAD.top + plotH} L${pts[0].x},${PAD.top + plotH} Z`,
      class: "price-area",
    })
  );
  svg.appendChild(el("path", { d: line, class: "price-line" }));

  // Crosshair. Umpan balik muncul saat pointer bergerak, bukan setelah klik,
  // dan mengikuti pointer 1:1 sepanjang gerakan.
  const cross = el("line", {
    x1: 0, y1: PAD.top, x2: 0, y2: PAD.top + plotH, class: "crosshair", opacity: "0",
  });
  const dot = el("circle", { cx: 0, cy: 0, r: 4.5, class: "focus-dot", opacity: "0" });
  svg.appendChild(cross);
  svg.appendChild(dot);

  const blank = "&nbsp;";
  const show = (i) => {
    const row = rows[i];
    cross.setAttribute("x1", x(i));
    cross.setAttribute("x2", x(i));
    cross.setAttribute("opacity", "1");
    dot.setAttribute("cx", x(i));
    dot.setAttribute("cy", y(row.close));
    dot.setAttribute("opacity", "1");
    if (readout) {
      const frozen = row.volume === 0;
      readout.innerHTML =
        `<span>${row.date}</span>` +
        `<span>tutup <strong>${idFmt(row.close)}</strong></span>` +
        `<span>volume <strong>${frozen ? "0 — tidak ada transaksi" : idFmt(row.volume)}</strong></span>`;
    }
  };
  const hide = () => {
    cross.setAttribute("opacity", "0");
    dot.setAttribute("opacity", "0");
    if (readout) readout.innerHTML = blank;
  };

  const hit = el("rect", {
    x: PAD.left, y: PAD.top, width: plotW, height: plotH, class: "hit",
  });
  hit.addEventListener("pointermove", (event) => {
    const box = svg.getBoundingClientRect();
    // Koordinat pointer dipetakan balik ke ruang viewBox; lebar SVG di layar
    // berubah-ubah mengikuti lebar kartu.
    const vx = ((event.clientX - box.left) / box.width) * W;
    const ratio = (vx - PAD.left) / plotW;
    const i = Math.max(0, Math.min(rows.length - 1, Math.round(ratio * (rows.length - 1))));
    show(i);
  });
  hit.addEventListener("pointerleave", hide);
  svg.appendChild(hit);

  container.innerHTML = "";
  container.appendChild(svg);
  if (readout) readout.innerHTML = blank;
}

window.renderPriceChart = renderPriceChart;
