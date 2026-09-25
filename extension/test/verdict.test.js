const test = require("node:test");
const assert = require("node:assert/strict");
const { verdict, isStale, LABELS } = require("../src/verdict.js");

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
  symbol: "CCSI", tier, ret_10d: 0.4966, vol_ratio: 0.99, as_of: "2026-09-18",
  flags: null, ...extra,
});

test("senyap and unknown tiers give no verdict", () => {
  assert.equal(verdict(entry("senyap"), thresholds, NOW), null);
  assert.equal(verdict(entry("lainnya"), thresholds, NOW), null);
  assert.equal(verdict(null, thresholds, NOW), null);
});

test("tinggi carries the label and the raw counts", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.equal(v.label, "Di zona suspensi");
  assert.match(v.evidence, /38 dari 55 kejadian/);
  assert.match(v.evidence, /0 dari 58 emiten pembanding/);
  assert.match(v.move, /49,7%/);
});

test("sedang says approaching, never medium risk", () => {
  const v = verdict(entry("sedang", { ret_10d: 0.25 }), thresholds, NOW);
  assert.equal(v.label, LABELS.sedang);
  assert.equal(v.label, "Mendekati zona suspensi");
  assert.ok(!JSON.stringify(v).toLowerCase().includes("risiko sedang"));
  assert.match(v.evidence, /31,6%/);
});

test("caveat states counts are not chances and carries the disclaimer", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.match(v.caveat, /bukan peluang/);
  assert.match(v.caveat, /Bukan saran investasi/);
});

test("evidence url deep-links the symbol", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.equal(v.evidenceUrl, "https://x.test/site/#pantau?symbol=CCSI");
});

test("staleness flips after the configured days", () => {
  assert.equal(isStale("2026-09-18", NOW, 7), false);
  assert.equal(isStale("2026-09-10", NOW, 7), true);
  assert.equal(isStale("bukan-tanggal", NOW, 7), true);
  assert.equal(verdict(entry("tinggi", { as_of: "2026-09-01" }), thresholds, NOW).stale, true);
});

test("tinggi headline states the event count without a chance", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.equal(v.headline, "Sehari sebelum suspensi, 38 dari 55 kejadian terlihat seperti ini");
});

test("sedang headline states the zone threshold as a return", () => {
  const v = verdict(entry("sedang", { ret_10d: 0.25 }), thresholds, NOW);
  assert.equal(v.headline, "Batas zona: naik 31,6%");
  assert.ok(!v.headline.toLowerCase().includes("risiko sedang"));
});
