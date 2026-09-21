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

function renderPriceChart(container, data) {
  const rows = data.rows.slice().sort((a, b) => a.date.localeCompare(b.date));
  const W = 900, H = 380, PAD = { top: 24, right: 20, bottom: 40, left: 64 };
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

  // Shading jendela beku. Confirmed dan inferred dibedakan secara visual.
  //
  // Label ditempatkan dalam dua tahap. Jendela yang berdekatan -- ALKA punya
  // jendela 27 Juli dan 29 Juli yang hampir bersentuhan -- akan menabrakkan
  // labelnya kalau semuanya dipasang di baris yang sama, dan jendela di tepi
  // kanan akan terpotong batas viewBox. Jadi setiap label dijepit ke dalam
  // area plot lalu diturunkan satu baris sampai tidak lagi bertabrakan.
  const CHAR_W = 5.2;   // perkiraan lebar karakter pada font-size 10px
  const LABEL_GAP = 6;  // jarak minimum antar label di baris yang sama
  const ROW_H = 13;
  const placed = [];    // { row, from, to } dalam koordinat viewBox

  data.windows.forEach((win) => {
    const from = indexOf(win.start_date);
    const to = indexOf(win.end_date);
    if (from < 0 || to < 0) return;
    const left = x(from);
    const width = Math.max(x(to) - left, 3);
    svg.appendChild(
      el("rect", {
        x: left,
        y: PAD.top,
        width: width,
        height: plotH,
        class: win.confirmed ? "freeze-band confirmed" : "freeze-band inferred",
      })
    );

    const text = win.confirmed ? "beku (terkonfirmasi)" : "volume nol (tersimpulkan)";
    const halfW = (text.length * CHAR_W) / 2;
    // Jepit ke dalam area plot supaya label tepi tidak terpotong.
    const cx = Math.min(
      Math.max(left + width / 2, PAD.left + halfW),
      W - PAD.right - halfW
    );
    const span = { from: cx - halfW - LABEL_GAP, to: cx + halfW + LABEL_GAP };

    let row = 0;
    while (
      placed.some((p) => p.row === row && p.from < span.to && span.from < p.to)
    ) {
      row += 1;
    }
    placed.push({ row, from: span.from, to: span.to });

    svg.appendChild(
      el(
        "text",
        { x: cx, y: PAD.top + 14 + row * ROW_H, class: "freeze-label" },
        text
      )
    );
  });

  // Sumbu Y
  for (let i = 0; i <= 4; i += 1) {
    const value = yMin + ((yMax - yMin) * i) / 4;
    svg.appendChild(
      el("line", { x1: PAD.left, y1: y(value), x2: W - PAD.right, y2: y(value), class: "grid" })
    );
    svg.appendChild(
      el("text", { x: PAD.left - 8, y: y(value) + 4, class: "axis-label y" },
        Math.round(value).toLocaleString("id-ID"))
    );
  }

  // Sumbu X: tampilkan setiap baris ke-5 supaya tidak bertumpuk
  rows.forEach((row, i) => {
    if (i % 5 !== 0) return;
    svg.appendChild(
      el("text", { x: x(i), y: H - PAD.bottom + 18, class: "axis-label x" },
        row.date.slice(5))
    );
  });

  const path = rows.map((r, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(r.close)}`).join(" ");
  svg.appendChild(el("path", { d: path, class: "price-line" }));

  rows.forEach((row, i) => {
    const dot = el("circle", { cx: x(i), cy: y(row.close), r: 3, class: "price-dot" });
    dot.appendChild(
      el("title", {}, `${row.date}\nclose ${row.close.toLocaleString("id-ID")}\nvolume ${row.volume.toLocaleString("id-ID")}`)
    );
    svg.appendChild(dot);
  });

  container.innerHTML = "";
  container.appendChild(svg);
}

window.renderPriceChart = renderPriceChart;
