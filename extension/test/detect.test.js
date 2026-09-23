const test = require("node:test");
const assert = require("node:assert/strict");
const { symbolFromUrl, findSymbols } = require("../src/detect.js");

const list = new Set(["CCSI", "ALKA", "BUMI"]);

test("stockbit symbol page", () => {
  assert.deepEqual(symbolFromUrl("https://stockbit.com/symbol/CCSI"),
    { site: "stockbit", symbol: "CCSI" });
  assert.deepEqual(symbolFromUrl("https://stockbit.com/symbol/ccsi/chartbit?x=1"),
    { site: "stockbit", symbol: "CCSI" });
  assert.equal(symbolFromUrl("https://stockbit.com/stream"), null);
  assert.equal(symbolFromUrl("https://stockbit.com/symbol/CCSIX"), null);
});

test("tradingview idx symbol page", () => {
  assert.deepEqual(symbolFromUrl("https://www.tradingview.com/symbols/IDX-ALKA/"),
    { site: "tradingview", symbol: "ALKA" });
  assert.deepEqual(symbolFromUrl("https://id.tradingview.com/symbols/IDX-ALKA/"),
    { site: "tradingview", symbol: "ALKA" });
  assert.equal(symbolFromUrl("https://www.tradingview.com/symbols/NASDAQ-AAPL/"), null);
});

test("google finance idx quote", () => {
  assert.deepEqual(symbolFromUrl("https://www.google.com/finance/quote/BUMI:IDX?hl=id"),
    { site: "google-finance", symbol: "BUMI" });
  assert.equal(symbolFromUrl("https://www.google.com/finance/quote/AAPL:NASDAQ"), null);
});

test("unknown sites give nothing", () => {
  assert.equal(symbolFromUrl("https://example.com/symbol/CCSI"), null);
  assert.equal(symbolFromUrl("bukan url"), null);
});

test("finds whitelisted tickers in running text with their index", () => {
  assert.deepEqual(findSymbols("Saham CCSI naik, BBCA turun.", list),
    [{ symbol: "CCSI", index: 6 }]);
});

test("finds tickers written with the exchange suffix", () => {
  assert.deepEqual(findSymbols("lihat CCSI.JK hari ini", list),
    [{ symbol: "CCSI", index: 6 }]);
});

test("ignores common four-letter caps words not in the whitelist", () => {
  assert.deepEqual(findSymbols("BUMN dan RUPS dan IHSG", list), []);
});

test("rejects a ticker inside a run of more than three caps words", () => {
  assert.deepEqual(findSymbols("BEI SUSPENSI SAHAM ALKA HARI INI", list), []);
});

test("accepts a ticker next to at most two other caps words", () => {
  assert.deepEqual(findSymbols("BEI suspensi ALKA hari ini", list),
    [{ symbol: "ALKA", index: 13 }]);
  assert.deepEqual(findSymbols("BEI ALKA IDX naik", list),
    [{ symbol: "ALKA", index: 4 }]);
});

test("does not match inside longer words", () => {
  assert.deepEqual(findSymbols("CCSIX dan XCCSI", list), []);
});
