// Tingkat -> bunyi lencana. Murni: tidak menyentuh DOM dan tidak menyimpan
// angka ambang. Ambang dan hitungan dibaca dari thresholds.json, yang
// digenerate dari freezebyte/baserates.py -- satu sumber kebenaran.
(function (root) {
  const LABELS = {
    tinggi: "Di zona suspensi",
    sedang: "Mendekati zona suspensi",
  };
  const DAY_MS = 86400000;

  const pct = (v) =>
    (v * 100).toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";

  function isStale(asOf, now, days) {
    const then = Date.parse(asOf + "T00:00:00Z");
    if (Number.isNaN(then)) return true;
    return now - then > days * DAY_MS;
  }

  function verdict(entry, thresholds, now) {
    if (!entry || !Object.prototype.hasOwnProperty.call(LABELS, entry.tier)) return null;
    const counts = thresholds.counts[entry.tier];
    const n = thresholds.n;

    const evidence = entry.tier === "tinggi"
      ? `Sehari sebelum suspensi, profil ini muncul pada ${counts.events} dari ` +
        `${n.events} kejadian suspensi, dan pada ${counts.controls} dari ` +
        `${n.controls} emiten pembanding.`
      : `Belum di zona. Batas zona: naik ${pct(thresholds.upper)} dalam 10 hari ` +
        `bursa. Sehari sebelum suspensi, ${counts.events} dari ${n.events} ` +
        `kejadian suspensi berada di rentang ini.`;

    // Satu baris untuk strip Lapis 0. Hitungan, bukan peluang.
    const headline = entry.tier === "tinggi"
      ? `Sehari sebelum suspensi, ${counts.events} dari ${n.events} kejadian terlihat seperti ini`
      : `Batas zona: naik ${pct(thresholds.upper)}`;

    return {
      tier: entry.tier,
      label: LABELS[entry.tier],
      symbol: entry.symbol,
      move: `Naik ${pct(entry.ret_10d)} dalam 10 hari bursa`,
      evidence,
      headline,
      caveat: "Hitungan sampel kejadian dan pembanding, bukan peluang. " +
              "Bukan saran investasi.",
      stale: isStale(entry.as_of, now, thresholds.stale_after_days),
      asOf: entry.as_of,
      evidenceUrl: `${thresholds.evidence_url}#pantau?symbol=${entry.symbol}`,
      flags: entry.flags,
    };
  }

  // Keadaan strip Lapis 0 untuk saham yang sedang dibuka, apa pun tingkatnya.
  // Tidak ada kata "aman" sebagai penilaian: data hanya menyatakan saham tidak
  // di zona tempat IDX biasanya bertindak karena lonjakan harga. verdict() di
  // atas tidak berubah -- tanda di dalam teks tetap hanya TINGGI/SEDANG.
  function pinnedVerdict(entry, symbol, thresholds, now, universeSize) {
    if (entry && Object.prototype.hasOwnProperty.call(LABELS, entry.tier)) {
      return verdict(entry, thresholds, now);
    }
    if (entry && entry.tier === "senyap") {
      const r = entry.ret_10d;
      const move = r === null || r === undefined
        ? null
        : r < 0
          ? `Turun ${pct(-r)} dalam 10 hari bursa`
          : `Naik ${pct(r)} dalam 10 hari bursa`;
      return {
        tier: "luar",
        label: "Di luar zona suspensi",
        symbol: entry.symbol,
        move,
        evidence: `Kenaikan 10 hari bursa masih di bawah batas zona ` +
                  `(naik ${pct(thresholds.upper)}). ` +
                  `Suspensi karena alasan lain tetap bisa terjadi.`,
        headline: "Belum melonjak seperti saham yang biasanya disuspensi. Bukan berarti aman.",
        caveat: "Hitungan sampel kejadian dan pembanding, bukan peluang. " +
                "Bukan saran investasi.",
        stale: isStale(entry.as_of, now, thresholds.stale_after_days),
        asOf: entry.as_of,
        evidenceUrl: `${thresholds.evidence_url}#pantau?symbol=${entry.symbol}`,
        flags: entry.flags,
      };
    }
    return {
      tier: "tidak",
      label: "Tidak dipantau",
      symbol,
      move: null,
      headline: `FREEZE BYTE aktif. Saham ini di luar ${universeSize} emiten yang ` +
                `dipantau. Tidak dikenali, bukan berarti aman.`,
      evidenceUrl: null,
    };
  }

  const api = { verdict, pinnedVerdict, isStale, LABELS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
