// Lapisan gerak.
//
// Seluruh berkas ini tidak melakukan apa pun kalau pembaca meminta gerak
// dikurangi. Satu gerbang di atas, bukan pengecualian yang ditempel per
// efek -- efek yang lupa didaftarkan adalah cara paling umum janji itu
// bocor.
(function () {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) return;

  const raf = (fn) => requestAnimationFrame(fn);
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  // Expo-out: melesat lalu mengendap.
  const easeOut = (t) => 1 - Math.pow(1 - t, 4);

  /* ---------- 1. Angka menghitung naik ----------
   * Hanya simpul teks PERTAMA yang dianimasikan, jadi "113 / 120" tetap
   * menghitung 113 dan membiarkan "/ 120" apa adanya. Nilai akhirnya
   * dipasang dari teks aslinya, bukan dari hasil interpolasi -- pembulatan
   * tidak boleh mengubah angka yang tersaji.
   */
  function countUp(el, delay) {
    const node = el.firstChild;
    if (!node || node.nodeType !== 3) return;

    // Teks asli disimpan sekali dan tidak pernah dibaca ulang dari DOM.
    // Berpindah panel memanggil wire() lagi; tanpa penjaga ini, pembacaan
    // kedua menangkap angka yang SEDANG dihitung -- "2,4%" di tengah jalan
    // menuju "9,9%" -- lalu menjadikannya target baru, dan nilai yang
    // tersaji rusak permanen. Angka di layar harus sama dengan angka di
    // JSON, jadi ini bukan cacat kosmetik.
    if (el.dataset.counted) return;
    el.dataset.counted = "1";

    const original = node.nodeValue;
    const match = original.match(/-?[\d.]+,?\d*/);
    if (!match) return;

    const raw = match[0];
    const target = parseFloat(raw.replace(/\./g, "").replace(",", "."));
    if (!isFinite(target)) return;
    const decimals = (raw.split(",")[1] || "").length;
    const fmt = (v) =>
      v.toLocaleString("id-ID", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

    node.nodeValue = original.replace(raw, fmt(0));
    const DURATION = 1100;
    let start = null;

    const step = (now) => {
      if (start === null) start = now;
      const t = clamp((now - start) / DURATION, 0, 1);
      node.nodeValue = original.replace(raw, fmt(target * easeOut(t)));
      if (t < 1) raf(step);
      else node.nodeValue = original;   // mendarat tepat di teks asli
    };
    setTimeout(() => raf(step), delay);
  }

  /* ---------- 2. Kemunculan bertahap ---------- */
  function stagger(nodes, base, gap) {
    nodes.forEach((el, i) => {
      if (el.dataset.risen) return;
      el.dataset.risen = "1";
      el.style.animation = `rise 620ms cubic-bezier(0.16,1,0.3,1) ${base + i * gap}ms both`;
    });
  }

  /* ---------- 3. Kaca miring mengikuti pointer ----------
   * Rotasi dijaga kecil. Lewat sekitar 8 derajat, teks di permukaan mulai
   * terbaca meleot dan kartunya berubah dari "kaca" jadi "mainan".
   */
  const MAX_TILT = 7;

  function tiltable(card) {
    if (card.dataset.tilt) return;
    card.dataset.tilt = "1";
    let frame = null;

    const onMove = (event) => {
      if (frame) return;
      frame = raf(() => {
        frame = null;
        const r = card.getBoundingClientRect();
        const px = (event.clientX - r.left) / r.width;
        const py = (event.clientY - r.top) / r.height;
        card.style.transform =
          `perspective(900px) rotateX(${(0.5 - py) * MAX_TILT}deg) ` +
          `rotateY(${(px - 0.5) * MAX_TILT}deg) translateY(-3px) scale(1.012)`;
        // Kilau bergerak ke arah kursor, seperti cahaya menyapu kaca.
        card.style.setProperty("--gx", `${px * 100}%`);
        card.style.setProperty("--gy", `${py * 100}%`);
      });
    };

    const onLeave = () => {
      if (frame) { cancelAnimationFrame(frame); frame = null; }
      card.style.transform = "";
      card.style.removeProperty("--gx");
      card.style.removeProperty("--gy");
    };

    card.addEventListener("pointermove", onMove);
    card.addEventListener("pointerleave", onLeave);
    // Umpan balik tekan hadir saat pointer turun, bukan saat dilepas.
    card.addEventListener("pointerdown", () => card.classList.add("pressed"));
    card.addEventListener("pointerup", () => card.classList.remove("pressed"));
    card.addEventListener("pointercancel", () => card.classList.remove("pressed"));
  }

  /* ---------- 4. Tarikan magnetis ---------- */
  function magnetic(el, strength) {
    if (el.dataset.magnetic) return;
    el.dataset.magnetic = "1";
    let frame = null;
    el.addEventListener("pointermove", (event) => {
      if (frame) return;
      frame = raf(() => {
        frame = null;
        const r = el.getBoundingClientRect();
        const dx = (event.clientX - (r.left + r.width / 2)) / r.width;
        const dy = (event.clientY - (r.top + r.height / 2)) / r.height;
        el.style.transform = `translate(${dx * strength}px, ${dy * strength}px)`;
      });
    });
    el.addEventListener("pointerleave", () => {
      if (frame) { cancelAnimationFrame(frame); frame = null; }
      el.style.transform = "";
    });
  }

  /* ---------- 5. Sorot mengikuti kursor di kanvas ---------- */
  function spotlight() {
    const canvas = document.querySelector(".canvas");
    if (!canvas) return;
    let frame = null;
    canvas.addEventListener("pointermove", (event) => {
      if (frame) return;
      frame = raf(() => {
        frame = null;
        document.body.style.setProperty("--mx", `${event.clientX}px`);
        document.body.style.setProperty("--my", `${event.clientY}px`);
      });
    });
  }

  /* ---------- 6. Garis grafik menggambar dirinya ----------
   * getTotalLength() mengembalikan 0 pada subtree yang display:none, jadi
   * pengukurannya harus terjadi setelah panelnya aktif -- bukan saat
   * grafiknya dirender.
   */
  function drawChart() {
    const pane = document.querySelector(".pane[data-active]");
    if (!pane) return;
    const line = pane.querySelector(".price-line");
    if (!line || line.classList.contains("draw")) return;

    const len = line.getTotalLength();
    if (!(len > 0)) return;
    line.style.setProperty("--len", len);
    line.classList.add("draw");

    pane.querySelectorAll(".price-area").forEach((n) => n.classList.add("draw"));
    pane.querySelectorAll("rect.freeze-band").forEach((n, i) => {
      n.classList.add("enter");
      n.style.animationDelay = `${140 + i * 90}ms`;
    });
  }

  /* ---------- Pemasangan ---------- */
  function wire() {
    drawChart();
    stagger(Array.from(document.querySelectorAll(".rail nav a")), 120, 55);
    document.querySelectorAll(".rail nav a, .back").forEach((el) => magnetic(el, 4));

    const cards = Array.from(document.querySelectorAll(".bento-card"));
    stagger(cards, 260, 110);
    cards.forEach(tiltable);
    cards.forEach((c, i) => {
      const stat = c.querySelector(".stat");
      if (stat) countUp(stat, 420 + i * 110);
    });

    document.querySelectorAll(".tile").forEach((t, i) => {
      if (t.dataset.risen) return;
      t.dataset.risen = "1";
      t.style.animation = `rise 620ms cubic-bezier(0.16,1,0.3,1) ${i * 90}ms both`;
      const v = t.querySelector(".value");
      if (v) countUp(v, 120 + i * 90);
    });

    // Baris tabel muncul bertahap, dibatasi dua belas baris pertama: di
    // luar itu penundaannya menumpuk jadi jeda baca, bukan lagi sambutan.
    document.querySelectorAll(".table-wrap tbody tr").forEach((tr, i) => {
      if (i > 11 || tr.dataset.risen) return;
      tr.dataset.risen = "1";
      tr.style.animation = `rise 420ms cubic-bezier(0.16,1,0.3,1) ${i * 28}ms both`;
    });

    document.querySelectorAll(".card").forEach((c, i) => {
      if (c.dataset.risen) return;
      c.dataset.risen = "1";
      c.style.animation = `rise 560ms cubic-bezier(0.16,1,0.3,1) ${i * 45}ms both`;
    });

    // Batang dan meter tumbuh dari nol. Lebar tujuannya juga dikunci sekali
    // -- pemanggilan kedua akan membaca "0" yang baru saja dipasang dan
    // membekukan batangnya di nol.
    document.querySelectorAll(".minibar .fill, .meter .fill, .bar i").forEach((f, i) => {
      if (f.dataset.grown) return;
      f.dataset.grown = "1";
      const w = f.style.width;
      f.style.width = "0";
      setTimeout(() => {
        f.style.transition = "width 900ms cubic-bezier(0.16,1,0.3,1)";
        f.style.width = w;
      }, 420 + Math.min(i, 20) * 35);
    });
  }

  spotlight();
  document.addEventListener("freezebyte:ready", wire);
  // Berpindah panel merender ulang isinya, jadi pemasangannya diulang.
  window.addEventListener("hashchange", () => setTimeout(wire, 30));
})();
