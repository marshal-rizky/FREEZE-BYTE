const test = require("node:test");
const assert = require("node:assert/strict");
const { debounceMaxWait } = require("../src/schedule.js");

// Jam palsu: setTimeout/clearTimeout yang dikendalikan manual lewat advance(),
// tidak menyentuh timer sungguhan sama sekali.
function makeFakeClock() {
  let now = 0;
  let nextId = 0;
  const timers = new Map();
  const clock = {
    setTimeout(fn, ms) {
      nextId += 1;
      timers.set(nextId, { due: now + ms, fn });
      return nextId;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
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
  return { clock, advance };
}

test("a single call fires once after wait", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const trigger = debounceMaxWait(() => { calls += 1; }, 400, 1500, clock);

  trigger();
  advance(399);
  assert.equal(calls, 0);
  advance(1);
  assert.equal(calls, 1);
  advance(5000);
  assert.equal(calls, 1);
});

test("a steady stream of calls every 100ms still fires at least once per maxWait", () => {
  const { clock, advance } = makeFakeClock();
  let calls = 0;
  const trigger = debounceMaxWait(() => { calls += 1; }, 400, 1500, clock);

  // Sepatu 100ms, celah 400ms tidak pernah terbuka -- debounce polos tidak
  // akan pernah jalan. maxWait 1500ms harus tetap memaksanya jalan.
  for (let i = 0; i < 14; i += 1) { // 14 * 100ms = 1400ms
    trigger();
    advance(100);
  }
  assert.equal(calls, 0);
  trigger();
  advance(100); // total 1500ms sejak panggilan pertama
  assert.equal(calls, 1);

  for (let i = 0; i < 14; i += 1) {
    trigger();
    advance(100);
  }
  trigger();
  advance(100); // maxWait kedua tercapai
  assert.equal(calls, 2);
});
