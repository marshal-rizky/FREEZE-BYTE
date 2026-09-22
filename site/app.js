const fmtPct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(1).replace(".", ",")}%`;

// Warna hanya menegaskan tanda yang sudah tertulis di angkanya, jadi pembaca
// yang tidak membedakan warna tidak kehilangan informasi apa pun.
const sign = (v) =>
  v === null || v === undefined ? "" : v > 0 ? " pos" : v < 0 ? " neg" : "";

const pctCell = (v) => `<td class="num${sign(v)}">${fmtPct(v)}</td>`;

/* Sel angka + batang diverging.
 *
 * Angkanya bertinta biasa, bukan hijau/merah: teks memakai token teks, dan
 * warna dibawa mark di sebelahnya. Di tabel 55 baris, mewarnai tiap digit
 * membuat kolomnya berkedip dan besarannya tetap tidak terbaca. Batang
 * membawa dua hal sekaligus -- tanda lewat arah dari garis tengah, besaran
 * lewat panjang. */
const barCell = (v, max) => {
  if (v === null || v === undefined) return `<td class="num">—</td>`;
  const w = max > 0 ? Math.min(Math.abs(v) / max, 1) * 50 : 0;
  const side = v < 0 ? "down" : "up";
  return `<td class="num">${fmtPct(v)}
    <span class="bar" aria-hidden="true"><i class="${side}" style="width:${w}%"></i></span>
  </td>`;
};

const ratio = (v) =>
  v === null || v === undefined ? "—" : `${v.toFixed(1).replace(".", ",")}&times;`;

const wrapTable = (head, body) =>
  `<div class="table-wrap"><table><thead>${head}</thead><tbody>${body}</tbody></table></div>`;

async function load(name) {
  const response = await fetch(`../data/web/${name}.json`);
  if (!response.ok) throw new Error(`gagal memuat ${name}.json`);
  return response.json();
}

function annotate(container, alka) {
  const confirmed = alka.windows.filter((w) => w.confirmed);
  const cards = [];

  const reopened = confirmed.filter((w) => w.reopen_return !== null);
  if (reopened.length) {
    const last = reopened[reopened.length - 1];
    cards.push({
      value: fmtPct(last.reopen_return),
      // M3: end_date adalah hari terakhir jendela BEKU, bukan hari saham
      // benar-benar dibuka kembali (itu baris pertama setelahnya). Label
      // "jendela berakhir" supaya tanggalnya tidak dibaca sebagai tanggal
      // reopen.
      label: `perubahan harga saat dibuka kembali (jendela berakhir ${last.end_date})`,
    });
  }

  if (alka.pre_freeze_rally_return !== null && alka.pre_freeze_rally_return !== undefined) {
    cards.push({
      value: fmtPct(alka.pre_freeze_rally_return),
      label: `kenaikan harga ${alka.pre_freeze_rally_rows} hari bursa sebelum dibekukan`,
    });
  }

  cards.push({ value: confirmed.length, label: "jendela beku terkonfirmasi di window ini" });

  const inferred = alka.windows.length - confirmed.length;
  if (inferred > 0) {
    cards.push({ value: inferred, label: "jendela tersimpulkan dari volume nol saja" });
  }

  container.innerHTML = cards
    .map((c) => `<div class="tile"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
    .join("");
}

const CATEGORY_LABELS = {
  lonjakan_harga: "Lonjakan harga / cooling down",
  papan_pemantauan_khusus: "Papan Pemantauan Khusus >1 tahun",
  kelangsungan_usaha: "Ketidakpastian kelangsungan usaha",
  keterbukaan_informasi: "Keterbukaan informasi / laporan keuangan",
  suspensi_berkepanjangan: "Suspensi berjalan lebih dari 6 bulan",
  ketentuan_pencatatan: "Belum memenuhi ketentuan pencatatan bursa",
  aksi_korporasi_delisting: "Aksi korporasi menuju delisting",
  lainnya: "Lainnya",
  tanpa_alasan: "Tanpa keterangan alasan",
};

/* ---------- Bento ikhtisar ----------
 * Empat kartu, masing-masing membawa cuplikan datanya sendiri dan membuka
 * panel penuh saat diklik. Seluruh angkanya dibaca dari JSON; tidak ada yang
 * ditulis tangan di sini.
 */
function renderBento(container, ctx) {
  const { alka, coverage, distribution, watchlist } = ctx;

  const reasons = Object.entries(coverage.reason_distribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  const reasonMax = reasons.length ? reasons[0][1] : 1;
  const minibars = reasons
    .map(([key, n]) => `
      <div class="minibar">
        <span class="name">${CATEGORY_LABELS[key] || key}</span>
        <span class="n">${n}</span>
        <span class="track"><i class="fill" style="width:${(n / reasonMax) * 100}%"></i></span>
      </div>`)
    .join("");

  const top = watchlist
    .slice()
    .sort((a, b) => (b.features.ret_10d ?? -Infinity) - (a.features.ret_10d ?? -Infinity))
    .slice(0, 3)
    .map((r) => `
      <div>
        <span class="sym">${r.symbol}</span>
        <span class="val${sign(r.features.ret_10d)}">${fmtPct(r.features.ret_10d)}</span>
      </div>`)
    .join("");

  const eventStats = summarise((distribution.events || []).map((i) => i.ret_10d));
  const pct = coverage.total ? Math.round((coverage.analyzed / coverage.total) * 100) : 0;

  container.innerHTML = `
    <button class="bento-card lg" data-goto="alka" type="button">
      <div class="top">
        <span class="label">Studi kasus &middot; ${alka.symbol}</span>
        <span class="go">Buka &rarr;</span>
      </div>
      <div class="stat">${fmtPct(alka.pre_freeze_rally_return)}</div>
      <div class="stat-note">kenaikan ${alka.pre_freeze_rally_rows} hari bursa, lalu dibekukan bursa</div>
      <div id="bento-spark"></div>
    </button>

    <button class="bento-card sm" data-goto="anatomi" type="button">
      <div class="top">
        <span class="label">Anatomi</span>
        <span class="go">Buka &rarr;</span>
      </div>
      <div class="stat">${coverage.total_suspension_records}</div>
      <div class="stat-note">record suspensi IDX, alasan resmi terbanyak</div>
      <div class="minibars">${minibars}</div>
    </button>

    <button class="bento-card" data-goto="pantau" type="button">
      <div class="top">
        <span class="label">Pantau hari ini</span>
        <span class="go">Buka &rarr;</span>
      </div>
      <div class="stat">${watchlist.length}</div>
      <div class="stat-note">emiten dengan kondisi menyerupai kejadian lampau</div>
      <div class="minilist">${top}</div>
    </button>

    <button class="bento-card" data-goto="coverage" type="button">
      <div class="top">
        <span class="label">Coverage</span>
        <span class="go">Buka &rarr;</span>
      </div>
      <div class="stat">${coverage.analyzed}<span style="color:var(--ink-3);font-size:.5em"> / ${coverage.total}</span></div>
      <div class="stat-note">sampel forensik yang benar-benar bisa dianalisis${
        eventStats ? `, median kenaikan sebelum dibekukan ${fmtPct(eventStats.median)}` : ""
      }</div>
      <div class="meter">
        <span class="track"><i class="fill" style="width:${pct}%"></i></span>
        <div class="legend"><span>${pct}% dianalisis</span><span>${coverage.excluded} gugur</span></div>
      </div>
    </button>`;

  const spark = container.querySelector("#bento-spark");
  if (spark) renderSparkline(spark, alka);
}

function renderReasons(container, distribution) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  const rows = Object.entries(distribution)
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => {
      const pct = ((count / total) * 100).toFixed(1).replace(".", ",");
      return `<tr><td>${CATEGORY_LABELS[key] || key}</td><td class="num">${count}</td><td class="num">${pct}%</td></tr>`;
    })
    .join("");

  container.innerHTML = `
    <h3>Alasan resmi</h3>
    ${wrapTable(`<tr><th>Alasan</th><th class="num">Jumlah</th><th class="num">Proporsi</th></tr>`, rows)}`;
}

function renderEvents(container, events) {
  // Skala batang dipatok ke besaran terbesar yang benar-benar ada di kolom
  // ini, jadi panjangnya bisa dibandingkan antar baris.
  const maxRet = Math.max(...events.map((e) => Math.abs(e.features.ret_10d ?? 0)), 0);
  const maxReopen = Math.max(...events.map((e) => Math.abs(e.reopen_return ?? 0)), 0);

  const rows = events
    .map((e) => {
      const pdf = e.pdf_url
        ? `<a href="${e.pdf_url}" target="_blank" rel="noopener">pengumuman IDX</a>`
        : "—";
      return `<tr>
        <td><strong>${e.symbol}</strong></td>
        <td class="num">${e.suspension_date}</td>
        ${barCell(e.features.ret_10d, maxRet)}
        <td class="num">${ratio(e.features.vol_ratio)}</td>
        ${barCell(e.reopen_return, maxReopen)}
        <td>${pdf}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <h3>Daftar kejadian</h3>
    ${wrapTable(
      `<tr><th>Emiten</th><th class="num">Tanggal suspensi</th>
       <th class="num">Return 10 baris</th><th class="num">Rasio volume</th>
       <th class="num">Saat dibuka</th><th>Bukti</th></tr>`, rows)}
    <p class="row-count">${events.length} kejadian</p>`;
}

const STRUCTURAL_LABELS = {
  float_under_25: "float &lt;25%",
  single_entity_70: "satu entitas &ge;70%",
  insider_1m_sell: "insider menjual 1 bulan",
  at_52w_high: "di puncak 52 minggu",
};

function chips(structural) {
  return Object.entries(STRUCTURAL_LABELS)
    .filter(([key]) => structural[key])
    .map(([, label]) => `<span class="chip now">${label} &middot; kondisi sekarang</span>`)
    .join("");
}

function renderWatchlist(container, watchlist, baserates) {
  if (!watchlist.length) {
    container.innerHTML = `<p class="insufficient">Tidak ada kandidat yang lolos
      syarat data pada build terakhir.</p>`;
    return;
  }

  const lookup = Object.fromEntries(baserates.buckets.map((b) => [b.bucket, b]));

  // Satu kartu per emiten. Penjelasan komposisi kelompoknya sama bentuknya
  // untuk setiap emiten; mengulangnya utuh di enam belas baris sekaligus
  // adalah yang membuat bagian ini terbaca sebagai dinding teks. Sekarang ia
  // ada di balik pengungkap -- tetap tersedia, tidak lagi dipaksakan.
  const cards = watchlist
    .map((row) => {
      const rate = lookup[row.bucket];
      const enough = rate && rate.sufficient;
      let detail = `<p class="insufficient">Bucket ini belum punya cukup sampel
                    untuk dibandingkan.</p>`;
      if (enough) {
        // C2: n_frozen_within_30d di sini SELALU sama dengan jumlah anggota
        // bucket yang berasal dari arm kejadian (frozen_within_30d dipatok
        // True untuk seluruh arm kejadian dan tidak pernah True untuk
        // kontrol di bawah definisi pick_controls saat ini). Jadi angka ini
        // adalah komposisi sampel case-control, bukan frekuensi pembekuan
        // yang teramati di populasi pasar -- lihat caveat di bawah grid.
        detail = `<p>${rate.n_events} dari ${rate.n} emiten di bucket ini adalah
                  kejadian suspensi, sisanya kontrol.</p>`;
      }
      return `<article class="card">
        <div class="sym">
          <strong>${row.symbol}</strong>
          <span class="ret${sign(row.features.ret_10d)}">${fmtPct(row.features.ret_10d)}</span>
        </div>
        <div class="meta">
          <span>vol ${ratio(row.features.vol_ratio)}</span>
          <span>pernah beku ${row.features.prior_freeze_count}</span>
        </div>
        ${chips(row.structural)}
        <details>
          <summary>${enough ? "komposisi kelompoknya" : "sampel tidak cukup"}</summary>
          ${detail}
        </details>
      </article>`;
    })
    .join("");

  container.innerHTML = `
    <div class="card-grid">${cards}</div>
    <p class="row-count">${watchlist.length} emiten</p>
    <p class="caveat">Komposisi kelompok <strong>bukan base rate populasi</strong>:
      sampel disusun berpasangan 1:1 (${baserates.n_events} kejadian,
      ${baserates.n_controls} kontrol), jadi pecahannya bergravitasi ke sekitar
      50% dan base rate pembekuan sesungguhnya jauh lebih rendah. Bucket dengan
      kurang dari ${baserates.min_sample} kejadian tidak diberi angka. Penanda
      "kondisi sekarang" berarti nilainya diambil hari ini &mdash; tag emiten
      tidak tersedia secara historis.</p>`;
}

function renderCoverage(container, coverage, meta) {
  // I1: tiga angka yang bisa dijumlahkan pembaca sendiri -- total record
  // suspensi (592-an), berapa yang masuk sampel forensik ~120 (60 kejadian +
  // 60 kontrol, dibatasi anggaran kredit API), dan dari situ berapa yang
  // benar-benar bisa dianalisis versus gugur. Semua dibaca dari JSON, tidak
  // ada angka yang ditulis tangan di sini.
  const reasons = Object.entries(coverage.by_reason)
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `<tr><td>${reason}</td><td class="num">${count}</td></tr>`)
    .join("");

  const watchlist = coverage.watchlist || { total: 0, analyzed: 0, excluded: 0, by_reason: {} };
  const watchlistReasons = Object.entries(watchlist.by_reason)
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `<tr><td>${reason}</td><td class="num">${count}</td></tr>`)
    .join("");
  const watchlistSection = watchlist.total > 0
    ? `<h3>Kandidat daftar pantau</h3>
       <p>Terpisah dari sampel forensik: dari <strong>${watchlist.total}</strong>
          kandidat, <strong>${watchlist.analyzed}</strong> dianalisis,
          <strong>${watchlist.excluded}</strong> gugur.</p>
       ${wrapTable(`<tr><th>Alasan gugur (kandidat daftar pantau)</th><th class="num">Jumlah</th></tr>`, watchlistReasons)}`
    : `<h3>Kandidat daftar pantau</h3>
       <p class="caveat">Belum ada kandidat daftar pantau yang diproses pada build ini.</p>`;

  container.innerHTML = `
    <p><strong>${coverage.total_suspension_records}</strong> record suspensi,
       <strong>${coverage.total}</strong> masuk sampel forensik
       (${coverage.sample_events} kejadian + ${coverage.sample_controls} kontrol,
       dibatasi anggaran kredit API). Dari jumlah itu
       <strong>${coverage.analyzed}</strong> dianalisis,
       <strong>${coverage.excluded}</strong> gugur.</p>
    ${wrapTable(`<tr><th>Alasan gugur (sampel forensik)</th><th class="num">Jumlah</th></tr>`, reasons)}
    ${watchlistSection}
    <p class="caveat">${coverage.sample_note}</p>
    <p class="caveat">Data dibangun ${meta.built_at}.
       Jendela yang hanya disimpulkan dari volume nol tidak pernah masuk statistik;
       jendela itu hanya tampil sebagai konteks pada grafik per emiten.</p>`;
}

function summarise(values) {
  // M2: `at()` below uses a nearest-rank percentile over whatever n happens
  // to land here. Fine for the two ~60-item pooled arms this is called on
  // (events vs. controls) where n is large enough for p25/p75 to mean
  // something; do not reuse this for a per-bucket breakdown, where n can be
  // single digits and nearest-rank on a handful of points is misleading.
  const clean = values.filter((v) => v !== null && v !== undefined).sort((a, b) => a - b);
  if (!clean.length) return null;
  const at = (p) => clean[Math.min(clean.length - 1, Math.floor(p * clean.length))];
  return { n: clean.length, p25: at(0.25), median: at(0.5), p75: at(0.75), max: clean[clean.length - 1] };
}

function renderDistribution(container, distribution) {
  const groups = [
    ["Sebelum dibekukan", distribution.events],
    ["Kelompok kontrol", distribution.controls],
  ];

  const rows = groups
    .map(([label, items]) => {
      const stats = summarise(items.map((i) => i.ret_10d));
      if (!stats) return `<tr><td>${label}</td><td colspan="5" class="insufficient">tidak ada data</td></tr>`;
      return `<tr>
        <td>${label}</td><td class="num">${stats.n}</td>${pctCell(stats.p25)}
        <td class="num${sign(stats.median)}"><strong>${fmtPct(stats.median)}</strong></td>
        ${pctCell(stats.p75)}${pctCell(stats.max)}
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <h3>Return 10 baris bursa: kejadian dibanding kontrol</h3>
    ${wrapTable(
      `<tr><th>Kelompok</th><th class="num">n</th><th class="num">p25</th>
       <th class="num">median</th><th class="num">p75</th>
       <th class="num">maks</th></tr>`, rows)}
    <p class="caveat">${distribution.control_definition}</p>`;
}

function renderRegulatoryContext(container) {
  container.innerHTML = `
    <h3>Kenapa Papan Pemantauan Khusus penting dibaca di sini</h3>
    <p>Sejak 25 Maret 2024 seluruh saham di Papan Pemantauan Khusus (notasi
      <strong>X</strong>) diperdagangkan lewat Full Call Auction &mdash; lelang berkala,
      bukan tawar-menawar kontinu. Likuiditas turun, order tidak langsung tereksekusi,
      dan batas bawah harga dilonggarkan sampai Rp1.</p>
    <p>Sekitar 11 kriteria masuk, cukup memenuhi satu. Tersering: harga rata-rata
      6 bulan di bawah Rp51, likuiditas sangat tipis, opini auditor disclaimer,
      ekuitas negatif. Notasi penyerta &mdash; <strong>B</strong> pailit/PKPU,
      <strong>E</strong> ekuitas negatif, <strong>L</strong> laporan keuangan
      terlambat, <strong>M</strong> sedang PKPU, <strong>S</strong> tanpa
      pendapatan usaha.</p>
    <p class="caveat">Status ini <strong>bukan field</strong> di Sectors API.
      <code>listing_board</code> INPS berbunyi "Development" padahal INPS disuspensi
      justru karena berada di papan pemantauan khusus lebih dari setahun, jadi
      statusnya hanya bisa disimpulkan dari teks alasan resmi. Jalur eskalasi yang
      terlihat di data: papan pemantauan khusus &rarr; 1 tahun &rarr; suspensi.</p>`;
}

// I6: setiap render dibungkus try/catch sendiri, menulis kegagalan ke
// container bagiannya sendiri saja -- supaya satu bagian yang gagal tidak
// menimpa grafik yang sudah berhasil digambar atau membuat enam bagian lain
// tampil kosong tanpa keterangan.
function renderSection(id, render) {
  const container = document.getElementById(id);
  if (!container) return;
  try {
    render(container);
  } catch (err) {
    container.textContent = `Gagal merender bagian ini: ${err.message}`;
  }
}

async function main() {
  const [alka, events, baserates, watchlist, coverage, meta, distribution] =
    await Promise.all([
      load("alka"), load("events"), load("baserates"), load("watchlist"),
      load("coverage"), load("meta"), load("distribution"),
    ]);

  renderSection("bento", (c) => renderBento(c, { alka, coverage, distribution, watchlist }));
  renderSection("alka-chart", (c) =>
    renderPriceChart(c, alka, document.getElementById("alka-readout")));
  renderSection("alka-annotations", (c) => annotate(c, alka));
  renderSection("reason-distribution", (c) => renderReasons(c, coverage.reason_distribution));
  renderSection("regulatory-context", (c) => renderRegulatoryContext(c));
  renderSection("distribution-compare", (c) => renderDistribution(c, distribution));
  renderSection("event-table", (c) => renderEvents(c, events));
  renderSection("watchlist-table", (c) => renderWatchlist(c, watchlist, baserates));
  renderSection("coverage-report", (c) => renderCoverage(c, coverage, meta));

  document.dispatchEvent(new CustomEvent("freezebyte:ready"));
}

main().catch((err) => {
  // Kegagalan di sini berarti load() (fetch JSON) sendiri gagal -- misalnya
  // dibuka lewat file:// tanpa server lokal -- sebelum satu pun bagian
  // sempat dirender.
  const banner = document.createElement("div");
  banner.className = "error-banner";
  banner.textContent = `Gagal memuat halaman: ${err.message}`;
  const host = document.querySelector("#pane-ikhtisar") || document.querySelector(".canvas");
  if (host) host.prepend(banner);
});
