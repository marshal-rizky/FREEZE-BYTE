const test = require("node:test");
const assert = require("node:assert/strict");
const { anchorFor, ANCHORS } = require("../src/anchors.js");

const fakeDoc = (map) => ({
  querySelector(sel) {
    if (sel === "!!invalid") throw new Error("SyntaxError");
    return map[sel] || null;
  },
});

test("sites without a selector give no anchor", () => {
  assert.equal(anchorFor("tradingview", fakeDoc({})), null);
  assert.equal(anchorFor("tidak-dikenal", fakeDoc({})), null);
});

test("a configured selector returns the element it finds", () => {
  ANCHORS.testsite = ".harga";
  const el = { tag: "span" };
  assert.equal(anchorFor("testsite", fakeDoc({ ".harga": el })), el);
  delete ANCHORS.testsite;
});

test("a missing or invalid selector degrades to null, never throws", () => {
  ANCHORS.testsite = "!!invalid";
  assert.equal(anchorFor("testsite", fakeDoc({})), null);
  ANCHORS.testsite = ".tidak-ada";
  assert.equal(anchorFor("testsite", fakeDoc({})), null);
  delete ANCHORS.testsite;
});
