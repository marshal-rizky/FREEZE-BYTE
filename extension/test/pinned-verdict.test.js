const test = require("node:test");
const assert = require("node:assert/strict");
const { verdict, pinnedVerdict } = require("../src/verdict.js");

const thresholds = {
  upper: 0.315874,
  near_lower: 0.2,
  counts: { tinggi: { events: 38, controls: 0 }, sedang: { events: 3, controls: 2 } },
  n: { events: 55, controls: 58 },
  evidence_url: "https://x.test/site/",
  stale_after_days: 7,
};
const NOW = Date.parse("2026-09-20T00:00:00Z");
const entry = (tier, extra = {}) => ({
  symbol: "AGII", tier, ret_10d: 0.189, vol_ratio: 1.0, as_of: "2026-09-18",
  flags: null, ...extra,
});

test("tinggi and sedang pass through verdict() unchanged", () => {
  for (const tier of ["tinggi", "sedang"]) {
    const e = entry(tier);
    assert.deepEqual(pinnedVerdict(e, "AGII", thresholds, NOW, 73), verdict(e, thresholds, NOW));
  }
});

test("senyap becomes the out-of-zone state, never a safety claim", () => {
  const v = pinnedVerdict(entry("senyap"), "AGII", thresholds, NOW, 73);
  assert.equal(v.tier, "luar");
  assert.equal(v.label, "Di luar zona suspensi");
  assert.equal(v.move, "Naik 18,9% dalam 10 hari bursa");
  assert.equal(v.headline,
    "Belum melonjak seperti saham yang biasanya disuspensi. Bukan berarti aman.");
  assert.equal(v.evidence,
    "Kenaikan 10 hari bursa masih di bawah batas zona (naik 31,6%). " +
    "Suspensi karena alasan lain tetap bisa terjadi.");
  assert.equal(v.evidenceUrl, "https://x.test/site/#pantau?symbol=AGII");
  assert.match(v.caveat, /Bukan saran investasi/);
  assert.equal(v.stale, false);
});

test("a falling out-of-zone stock says turun, not naik minus", () => {
  const v = pinnedVerdict(entry("senyap", { ret_10d: -0.042 }), "AGII", thresholds, NOW, 73);
  assert.equal(v.move, "Turun 4,2% dalam 10 hari bursa");
});

test("an out-of-zone stock without a return has no move line", () => {
  const v = pinnedVerdict(entry("senyap", { ret_10d: null }), "AGII", thresholds, NOW, 73);
  assert.equal(v.move, null);
});

test("an unwatched symbol says it is not recognised, with no evidence link", () => {
  const v = pinnedVerdict(null, "BBCA", thresholds, NOW, 73);
  assert.equal(v.tier, "tidak");
  assert.equal(v.label, "Tidak dipantau");
  assert.equal(v.symbol, "BBCA");
  assert.equal(v.move, null);
  assert.equal(v.headline,
    "FREEZE BYTE aktif. Saham ini di luar 73 emiten yang dipantau. " +
    "Tidak dikenali, bukan berarti aman.");
  assert.equal(v.evidenceUrl, null);
});

test("no pinned state ever says risiko sedang", () => {
  const all = [
    pinnedVerdict(entry("tinggi"), "AGII", thresholds, NOW, 73),
    pinnedVerdict(entry("sedang"), "AGII", thresholds, NOW, 73),
    pinnedVerdict(entry("senyap"), "AGII", thresholds, NOW, 73),
    pinnedVerdict(null, "BBCA", thresholds, NOW, 73),
  ];
  assert.ok(!JSON.stringify(all).toLowerCase().includes("risiko sedang"));
});
