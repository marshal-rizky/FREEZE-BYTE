const test = require("node:test");
const assert = require("node:assert/strict");
const { matchesAnyPattern } = require("../src/patterns.js");

test("path wildcard matches a prefix, not the whole origin", () => {
  assert.equal(
    matchesAnyPattern("https://www.google.com/finance/quote/BBCA:IDX",
      ["https://www.google.com/finance/*"]),
    true);
  assert.equal(
    matchesAnyPattern("https://www.google.com/search?q=x",
      ["https://www.google.com/finance/*"]),
    false);
});

test("*. subdomain wildcard matches any subdomain", () => {
  assert.equal(
    matchesAnyPattern("https://id.tradingview.com/x", ["https://*.tradingview.com/*"]),
    true);
});

test("exact host matches only that host", () => {
  assert.equal(
    matchesAnyPattern("https://stockbit.com/symbol/BBCA", ["https://stockbit.com/*"]),
    true);
  assert.equal(
    matchesAnyPattern("https://evil.com/stockbit.com/*", ["https://stockbit.com/*"]),
    false);
});

test("no pattern in the list matching gives false", () => {
  assert.equal(matchesAnyPattern("https://example.com/", ["https://stockbit.com/*"]), false);
});
