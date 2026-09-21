const fmtPct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(1).replace(".", ",")}%`;

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
    .map((c) => `<div class="annotation"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
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

function renderReasons(container, distribution) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  const rows = Object.entries(distribution)
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => {
      const label = CATEGORY_LABELS[key] || key;
      const pct = ((count / total) * 100).toFixed(1).replace(".", ",");
      return `<tr><td>${label}</td><td>${count}</td><td>${pct}%</td></tr>`;
    })
    .join("");

  container.innerHTML = `
    <p>Alasan resmi dari ${total} record suspensi.</p>
    <table><thead><tr><th>Alasan</th><th>Jumlah</th><th>Proporsi</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function renderEvents(container, events) {
  const rows = events
    .map((e) => {
      const pdf = e.pdf_url
        ? `<a href="${e.pdf_url}" target="_blank" rel="noopener">pengumuman IDX</a>`
        : "—";
      return `<tr>
        <td><strong>${e.symbol}</strong></td>
        <td>${e.suspension_date}</td>
        <td>${fmtPct(e.features.ret_10d)}</td>
        <td>${e.features.vol_ratio === null ? "—" : e.features.vol_ratio.toFixed(1).replace(".", ",")}&times;</td>
        <td>${fmtPct(e.reopen_return)}</td>
        <td>${pdf}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <p>Kondisi setiap emiten pada hari bursa terakhir sebelum dibekukan.
       Setiap baris tertaut ke PDF pengumuman resmi IDX.</p>
    <table><thead><tr>
      <th>Emiten</th><th>Tanggal suspensi</th><th>Return 10 baris</th>
      <th>Rasio volume</th><th>Saat dibuka</th><th>Bukti</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
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

  const rows = watchlist
    .map((row) => {
      const rate = lookup[row.bucket];
      let rateCell = `<span class="insufficient">sampel tidak cukup</span>`;
      if (rate && rate.sufficient) {
        // C2: n_frozen_within_30d di sini SELALU sama dengan jumlah anggota
        // bucket yang berasal dari arm kejadian (frozen_within_30d dipatok
        // True untuk seluruh arm kejadian dan tidak pernah True untuk
        // kontrol di bawah definisi pick_controls saat ini). Jadi angka ini
        // adalah komposisi sampel case-control, bukan frekuensi pembekuan
        // yang teramati di populasi pasar -- lihat caveat di bawah tabel.
        rateCell = `${rate.n_events} dari ${rate.n} emiten di bucket ini adalah
                    kejadian suspensi, sisanya kontrol. Sampel disusun berpasangan
                    (${baserates.n_events} kejadian, ${baserates.n_controls} kontrol),
                    jadi angka ini membedakan kelompok &mdash; bukan frekuensi populasi.`;
      }
      return `<tr>
        <td><strong>${row.symbol}</strong><br>${chips(row.structural)}</td>
        <td>${fmtPct(row.features.ret_10d)}</td>
        <td>${row.features.vol_ratio === null ? "—" : row.features.vol_ratio.toFixed(1).replace(".", ",")}&times;</td>
        <td>${row.features.prior_freeze_count}</td>
        <td>${rateCell}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <table><thead><tr>
      <th>Emiten dan kondisi struktural</th><th>Return 10 baris</th>
      <th>Rasio volume</th><th>Pernah beku</th><th>Komposisi kelompoknya</th>
    </tr></thead><tbody>${rows}</tbody></table>
    <p class="caveat">Bucket dengan kurang dari ${baserates.min_sample} kejadian
      ditampilkan sebagai "sampel tidak cukup", bukan angka. Kolom terakhir
      BUKAN base rate populasi: sampel forensik disusun berpasangan 1:1
      (${baserates.n_events} kejadian, ${baserates.n_controls} kontrol) by
      design, sehingga pecahan kejadian di tiap bucket bergravitasi ke
      sekitar 50% terlepas dari seberapa jarang pembekuan sungguhan terjadi
      di pasar &mdash; base rate pembekuan yang sebenarnya jauh lebih rendah
      dari itu. Penanda "kondisi sekarang" berarti nilai itu diambil hari
      ini, bukan pada tanggal historis &mdash; tag emiten tidak tersedia
      secara historis.</p>`;
}

function renderCoverage(container, coverage, meta) {
  // I1: tiga angka yang bisa dijumlahkan pembaca sendiri -- total record
  // suspensi (592-an), berapa yang masuk sampel forensik ~120 (60 kejadian +
  // 60 kontrol, dibatasi anggaran kredit API), dan dari situ berapa yang
  // benar-benar bisa dianalisis versus gugur. Semua dibaca dari JSON, tidak
  // ada angka yang ditulis tangan di sini.
  const reasons = Object.entries(coverage.by_reason)
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `<tr><td>${reason}</td><td>${count}</td></tr>`)
    .join("");

  const watchlist = coverage.watchlist || { total: 0, analyzed: 0, excluded: 0, by_reason: {} };
  const watchlistReasons = Object.entries(watchlist.by_reason)
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `<tr><td>${reason}</td><td>${count}</td></tr>`)
    .join("");
  const watchlistSection = watchlist.total > 0
    ? `<h3>Kandidat daftar pantau</h3>
       <p>Terpisah dari sampel forensik di atas: dari
          <strong>${watchlist.total}</strong> <em>kandidat daftar pantau</em>
          (bukan record suspensi), <strong>${watchlist.analyzed}</strong>
          bisa dianalisis dan <strong>${watchlist.excluded}</strong> gugur.</p>
       <table><thead><tr><th>Alasan gugur (kandidat daftar pantau)</th><th>Jumlah</th></tr></thead>
       <tbody>${watchlistReasons}</tbody></table>`
    : `<h3>Kandidat daftar pantau</h3>
       <p class="caveat">Belum ada kandidat daftar pantau yang diproses pada build ini.</p>`;

  container.innerHTML = `
    <p>Dari <strong>${coverage.total_suspension_records}</strong> record suspensi,
       <strong>${coverage.total}</strong> masuk sampel forensik
       (${coverage.sample_events} kejadian + ${coverage.sample_controls} kontrol,
       dibatasi anggaran kredit API). Dari <strong>${coverage.total}</strong> itu,
       <strong>${coverage.analyzed}</strong> bisa dianalisis dan
       <strong>${coverage.excluded}</strong> gugur.</p>
    <table><thead><tr><th>Alasan gugur (sampel forensik)</th><th>Jumlah</th></tr></thead>
    <tbody>${reasons}</tbody></table>
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
        <td>${label}</td><td>${stats.n}</td><td>${fmtPct(stats.p25)}</td>
        <td><strong>${fmtPct(stats.median)}</strong></td><td>${fmtPct(stats.p75)}</td>
        <td>${fmtPct(stats.max)}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <h3>Return 10 baris bursa: kejadian dibanding kontrol</h3>
    <table><thead><tr>
      <th>Kelompok</th><th>n</th><th>p25</th><th>median</th><th>p75</th><th>maks</th>
    </tr></thead><tbody>${rows}</tbody></table>
    <p class="caveat">${distribution.control_definition}</p>`;
}

function renderRegulatoryContext(container) {
  container.innerHTML = `
    <h3>Kenapa Papan Pemantauan Khusus penting dibaca di sini</h3>
    <p>Sejak 25 Maret 2024 seluruh saham di Papan Pemantauan Khusus (notasi
      <strong>X</strong>) diperdagangkan lewat Full Call Auction &mdash; lelang berkala,
      bukan tawar-menawar kontinu. Likuiditas turun, order tidak langsung tereksekusi,
      dan batas bawah harga dilonggarkan sampai Rp1.</p>
    <p>Ada sekitar 11 kriteria masuk dan cukup memenuhi satu. Pemicu tersering adalah
      harga rata-rata 6 bulan di bawah sekitar Rp51, likuiditas sangat tipis selama
      6 bulan, opini auditor disclaimer, dan ekuitas negatif. Notasi lain yang sering
      menyertai: <strong>B</strong> permohonan pailit atau PKPU, <strong>E</strong>
      ekuitas negatif, <strong>L</strong> belum menyampaikan laporan keuangan,
      <strong>M</strong> sedang PKPU, <strong>S</strong> tidak ada pendapatan usaha.</p>
    <p class="caveat">Status Papan Pemantauan Khusus <strong>bukan field</strong> di
      Sectors API. <code>listing_board</code> INPS berbunyi "Development" padahal INPS
      disuspensi justru karena berada di papan pemantauan khusus lebih dari satu tahun.
      Status itu hanya bisa disimpulkan dari teks alasan resmi, dan itulah yang
      dilakukan klasifikasi di atas. Jalur eskalasi yang terlihat di data:
      papan pemantauan khusus &rarr; 1 tahun &rarr; suspensi.</p>`;
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

  renderSection("alka-chart", (c) => renderPriceChart(c, alka));
  renderSection("alka-annotations", (c) => annotate(c, alka));
  renderSection("reason-distribution", (c) => renderReasons(c, coverage.reason_distribution));
  renderSection("regulatory-context", (c) => renderRegulatoryContext(c));
  renderSection("distribution-compare", (c) => renderDistribution(c, distribution));
  renderSection("event-table", (c) => renderEvents(c, events));
  renderSection("watchlist-table", (c) => renderWatchlist(c, watchlist, baserates));
  renderSection("coverage-report", (c) => renderCoverage(c, coverage, meta));
}

main().catch((err) => {
  // Kegagalan di sini berarti load() (fetch JSON) sendiri gagal -- misalnya
  // dibuka lewat file:// tanpa server lokal -- sebelum satu pun bagian
  // sempat dirender. Banner di atas <main>, bukan ditimpakan ke slot grafik.
  const banner = document.createElement("div");
  banner.className = "error-banner";
  banner.textContent = `Gagal memuat halaman: ${err.message}`;
  document.querySelector("main").prepend(banner);
});
