const test = require("node:test");
const assert = require("node:assert/strict");
const { createCollapseTimer } = require("../src/strip.js");

// Jam palsu yang sama polanya dengan schedule.test.js.
function makeFakeClock() {
  let now = 0;
  let nextId = 0;
  const timers = new Map();
  const clock = {
    setTimeout(fn, ms) { nextId += 1; timers.set(nextId, { due: now + ms, fn }); return nextId; },
    clearTimeout(id) { timers.delete(id); },
  };
  function advance(ms) {
    const target = now + ms;
    for (;;) {
      let next = null;
      for (const [id, t] of timers) {
        if (t.due <= target && (!next || t.due < next.due)) next = { id, ...t };
      }
      if (!next) break;
      timers.delete(next.id);
      now = next.due;
      next.fn();
    }
    now = target;
  }
  return { clock, advance, pending: () => timers.size };
}

test("collapses exactly once after the delay", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const t = createCollapseTimer(() => { calls += 1; }, 6000, clock);
  t.start();
  advance(5999);
  assert.equal(calls, 0);
  advance(1);
  assert.equal(calls, 1);
  advance(20000);
  assert.equal(calls, 1);
});

test("hold stops the countdown and release restarts it in full", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const t = createCollapseTimer(() => { calls += 1; }, 6000, clock);
  t.start();
  advance(5000);
  t.hold();
  advance(60000);
  assert.equal(calls, 0);
  t.release();
  advance(5999);
  assert.equal(calls, 0);
  advance(1);
  assert.equal(calls, 1);
});

test("release without a prior hold does nothing", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const t = createCollapseTimer(() => { calls += 1; }, 6000, clock);
  t.start();
  advance(3000);
  t.release();
  advance(3000);
  assert.equal(calls, 1);
});

test("collapseNow fires once and cancels the pending timer", () => {
  const { clock, advance, pending } = makeFakeClock();
  let calls = 0;
  const t = createCollapseTimer(() => { calls += 1; }, 6000, clock);
  t.start();
  t.collapseNow();
  assert.equal(calls, 1);
  assert.equal(pending(), 0);
  advance(10000);
  assert.equal(calls, 1);
});

test("cancel never fires", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const t = createCollapseTimer(() => { calls += 1; }, 6000, clock);
  t.start();
  t.cancel();
  advance(10000);
  assert.equal(calls, 0);
});

test("start again restarts the countdown", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const t = createCollapseTimer(() => { calls += 1; }, 6000, clock);
  t.start();
  advance(4000);
  t.start();
  advance(4000);
  assert.equal(calls, 0);
  advance(2000);
  assert.equal(calls, 1);
});
