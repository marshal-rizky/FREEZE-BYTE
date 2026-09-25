# Pinned Strip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the small corner badge for the stock the user is viewing with a large top-center strip that collapses to a pill after 6 seconds.

**Architecture:** `verdict.js` gains a `headline` string so all copy stays in the tested module. A new pure module `strip.js` owns the collapse timer. `overlay.js` renders the pinned item as a strip/pill in its own container that survives rescans while the symbol is unchanged. The unused Stockbit anchor module is deleted.

**Tech Stack:** Vanilla JS (no build, no npm), Manifest V3, Node 24 `node --test`, Playwright MCP for the browser check.

**Spec:** `docs/superpowers/specs/2026-09-25-pinned-strip-design.md`

## Global Constraints

- Branch: `feat/pinned-strip`. Do not push or merge.
- Badge copy: TINGGI `"Di zona suspensi"`, SEDANG `"Mendekati zona suspensi"`. The words `"risiko sedang"` never appear. No probability or chance-of-freezing percentage anywhere; a stock's own return and the zone's return threshold may be shown as percentages.
- The extension makes no network requests besides reading its own two JSON files. The page DOM is never written; everything lives in the one closed-shadow host on `<html>`.
- Strip timing: expanded 6000 ms, then collapse. Enter 420 ms `cubic-bezier(0.16, 1, 0.3, 1)` from `translateY(-12px)` + opacity 0. TINGGI pulses the ring twice (2 × 900 ms) after entering; SEDANG never pulses. Collapse/re-expand transitions 240 ms ease-out. `prefers-reduced-motion: reduce` removes all of these animations; timer behaviour is unchanged.
- Strip position: `position: fixed; top: 56px; left: 50%; transform: translateX(-50%)`; strip width `min(680px, calc(100vw - 32px))`.
- Colours: TINGGI background `rgba(58,13,16,.95)`, border `#f2555a`, ring `0 0 0 6px rgba(242,85,90,.18)`, glyph `#ff6b70`; SEDANG background `rgba(51,37,10,.95)`, border `#e0a43a`, ring `0 0 0 6px rgba(224,164,58,.18)`, glyph `#f2c46d`.
- Rescans with the same pinned symbol must not rebuild the strip or reset its expanded/collapsed state.
- Comments and user-facing strings in Indonesian, matching existing code. Commit messages in English, Conventional Commits, a blank line, then exactly `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests: `node --test "extension/test/*.test.js"` and `python -m pytest` both pass at the end of every task.
- Never run anything under `scripts/` (paid API credits). Never print `.env`. Do not commit `.playwright-mcp/`.

## File Structure

```
extension/src/verdict.js        MOD  add `headline`
extension/src/strip.js          NEW  createCollapseTimer, pure
extension/src/overlay.js        MOD  pinned item -> strip/pill; drop anchor positioning
extension/src/content.js        MOD  stop calling FB.anchorFor
extension/src/anchors.js        DEL
extension/manifest.json         MOD  anchors.js -> strip.js in content_scripts
extension/src/popup.js          MOD  anchors.js -> strip.js in SCRIPTS
extension/test/verdict.test.js  MOD  headline tests
extension/test/strip.test.js    NEW
extension/test/anchors.test.js  DEL
extension/test/harness.html     MOD  anchors.js -> strip.js
extension/test/harness-pinned.html NEW
docs/superpowers/specs/2026-09-22-freeze-byte-extension-design.md  MOD  §6 Lapis 2, §11, §14
docs/user-testing.md, docs/SUBMISSION.md                           MOD  anchor lines
```

---

### Task 1: Headline copy and collapse timer

**Files:**
- Modify: `extension/src/verdict.js`
- Create: `extension/src/strip.js`
- Test: `extension/test/verdict.test.js`, `extension/test/strip.test.js`

**Interfaces:**
- Consumes: existing `verdict(entry, thresholds, now)` in `extension/src/verdict.js` and its private `pct(v)` helper.
- Produces:
  - `verdict(...)` result gains `headline: string`.
  - `createCollapseTimer(onCollapse: () => void, delay: number, timers?: { setTimeout, clearTimeout }) -> { start(), hold(), release(), collapseNow(), cancel() }`, exported from `extension/src/strip.js` via the same UMD pattern as `detect.js` (`module.exports` in Node, `globalThis.FreezeByte` in the browser).

- [ ] **Step 1: Write the failing headline tests**

Append to `extension/test/verdict.test.js` (it already defines `thresholds`, `NOW`, and `entry(tier, extra)`):

```js
test("tinggi headline states the event count without a chance", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.equal(v.headline, "Sehari sebelum suspensi, 38 dari 55 kejadian terlihat seperti ini");
});

test("sedang headline states the zone threshold as a return", () => {
  const v = verdict(entry("sedang", { ret_10d: 0.25 }), thresholds, NOW);
  assert.equal(v.headline, "Batas zona: naik 31,6%");
  assert.ok(!v.headline.toLowerCase().includes("risiko sedang"));
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test "extension/test/*.test.js"`
Expected: the two new tests FAIL (`headline` is `undefined`); all others pass.

- [ ] **Step 3: Add `headline` to `extension/src/verdict.js`**

Inside `verdict()`, after the `evidence` constant, add:

```js
    // Satu baris untuk strip Lapis 0. Hitungan, bukan peluang.
    const headline = entry.tier === "tinggi"
      ? `Sehari sebelum suspensi, ${counts.events} dari ${n.events} kejadian terlihat seperti ini`
      : `Batas zona: naik ${pct(thresholds.upper)}`;
```

and add `headline,` to the returned object directly after `evidence,`.

- [ ] **Step 4: Run to verify they pass**

Run: `node --test "extension/test/*.test.js"`
Expected: all pass.

- [ ] **Step 5: Write the failing timer tests**

Create `extension/test/strip.test.js`:

```js
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
```

- [ ] **Step 6: Run to verify they fail**

Run: `node --test "extension/test/*.test.js"`
Expected: strip tests FAIL with `Cannot find module '../src/strip.js'`.

- [ ] **Step 7: Create `extension/src/strip.js`**

```js
// Timer penciutan strip Lapis 0. Murni: tidak tahu apa pun soal DOM.
// Strip tampil penuh selama `delay`, lalu onCollapse dipanggil. Kursor di
// atas strip menahan hitungan mundur; begitu kursor keluar, hitungan mulai
// lagi dari awal supaya pembaca tidak kehilangan strip tepat setelah
// selesai membaca.
(function (root) {
  function createCollapseTimer(onCollapse, delay, timers) {
    const t = timers || {
      setTimeout: (fn, ms) => setTimeout(fn, ms),
      clearTimeout: (id) => clearTimeout(id),
    };
    let id = null;
    let held = false;

    const clear = () => {
      if (id !== null) { t.clearTimeout(id); id = null; }
    };

    function start() {
      clear();
      held = false;
      id = t.setTimeout(() => { id = null; onCollapse(); }, delay);
    }
    function hold() { held = true; clear(); }
    function release() {
      if (!held) return;
      held = false;
      start();
    }
    function collapseNow() { held = false; clear(); onCollapse(); }
    function cancel() { held = false; clear(); }

    return { start, hold, release, collapseNow, cancel };
  }

  const api = { createCollapseTimer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
```

- [ ] **Step 8: Run all tests**

Run: `node --test "extension/test/*.test.js"` and `python -m pytest`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add extension/src/verdict.js extension/src/strip.js extension/test/verdict.test.js extension/test/strip.test.js
git commit -m "feat(extension): add the strip headline and a collapse timer

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Render the pinned strip and drop the anchor module

**Files:**
- Modify: `extension/src/overlay.js`, `extension/src/content.js`, `extension/manifest.json`, `extension/src/popup.js`, `extension/test/harness.html`
- Delete: `extension/src/anchors.js`, `extension/test/anchors.test.js`
- Create: `extension/test/harness-pinned.html`
- Modify docs: `docs/superpowers/specs/2026-09-22-freeze-byte-extension-design.md`, `docs/user-testing.md`, `docs/SUBMISSION.md`

**Interfaces:**
- Consumes: `verdict(...).headline` and `createCollapseTimer(...)` from Task 1 via `globalThis.FreezeByte`.
- Produces:
  - `createOverlay(doc).setItems(items)` accepts at most one item with `pinned: true` (shape `{ pinned: true, verdict }`, no `anchor`) plus range items as before.
  - Test hooks on the host element (the shadow root is closed): `host.dataset.badges` (visible marks + 1 if a strip/pill exists), `host.dataset.pinned` = `"<SYMBOL>:expanded"` / `"<SYMBOL>:collapsed"` / `""`, `host.dataset.pinnedBuilt` = number of strips created so far (string).
  - Content-script load order everywhere: `src/detect.js, src/verdict.js, src/strip.js, src/overlay.js, src/schedule.js, src/content.js`.

- [ ] **Step 1: Remove the anchor module and its loaders**

```bash
git rm extension/src/anchors.js extension/test/anchors.test.js
```

In `extension/manifest.json` `content_scripts[0].js`, in `extension/src/popup.js` `SCRIPTS`, and in `extension/test/harness.html` (`<script src="../src/anchors.js">`), replace `anchors.js` with `strip.js` in the same position (before `overlay.js`).

In `extension/src/content.js`, replace the pinned push with:

```js
    if (focused && verdicts.has(focused.symbol)) {
      items.push({ pinned: true, verdict: verdicts.get(focused.symbol) });
    }
```

Run: `node --test "extension/test/*.test.js"`
Expected: all pass (anchors tests are gone).

- [ ] **Step 2: Add strip CSS to `extension/src/overlay.js`**

Append inside the `CSS` template string, before its closing backtick:

```css
    .pin {
      position: fixed; top: 56px; left: 50%; transform: translateX(-50%);
      pointer-events: auto; font: 400 13px/1.35 system-ui, sans-serif; color: #fff;
    }
    .pin[data-state="collapsed"] .strip { display: none; }
    .pin[data-state="expanded"] .pill { display: none; }
    .strip {
      box-sizing: border-box; width: min(680px, calc(100vw - 32px));
      display: flex; align-items: center; gap: 12px; padding: 11px 14px;
      border-radius: 14px; border: 1px solid transparent;
    }
    .pin.tinggi .strip { background: rgba(58,13,16,.95); border-color: #f2555a;
      box-shadow: 0 0 0 6px rgba(242,85,90,.18), 0 18px 40px rgba(0,0,0,.35); }
    .pin.sedang .strip { background: rgba(51,37,10,.95); border-color: #e0a43a;
      box-shadow: 0 0 0 6px rgba(224,164,58,.18), 0 18px 40px rgba(0,0,0,.35); }
    .strip .tri { font-size: 22px; line-height: 1; }
    .pin.tinggi .tri { color: #ff6b70; }
    .pin.sedang .tri { color: #f2c46d; }
    .strip .text { min-width: 0; }
    .strip .sym { font-weight: 800; font-size: 17px; letter-spacing: .02em; }
    .strip .lbl { font-weight: 700; font-size: 15px; margin-left: 8px; }
    .pin.tinggi .lbl { color: #ffd9da; }
    .pin.sedang .lbl { color: #ffe7b8; }
    .strip .sub { font-size: 12px; color: rgba(255,255,255,.72); margin-top: 2px; }
    .strip .go, .strip .x {
      background: transparent; color: #fff; cursor: pointer; font: inherit;
    }
    .strip .go { margin-left: auto; font-size: 12px; white-space: nowrap;
      border: 1px solid rgba(255,255,255,.35); padding: 4px 9px; border-radius: 10px; }
    .strip .x { border: 0; font-size: 18px; line-height: 1; color: rgba(255,255,255,.6); padding: 2px 4px; }
    .pill {
      display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
      padding: 5px 12px; border-radius: 999px; border: 1px solid transparent;
      font: 700 12px/1 system-ui, sans-serif; white-space: nowrap;
      box-shadow: 0 6px 18px rgba(0,0,0,.3); animation: fb-fade 240ms ease-out;
    }
    .pin.tinggi .pill { background: rgba(58,13,16,.95); border-color: #f2555a; color: #ffd9da; }
    .pin.sedang .pill { background: rgba(51,37,10,.95); border-color: #e0a43a; color: #ffe7b8; }
    .pin .strip { animation: fb-fade 240ms ease-out; }
    .pin.fresh .strip { animation: fb-enter 420ms cubic-bezier(0.16, 1, 0.3, 1); }
    .pin.fresh.tinggi .strip {
      animation: fb-enter 420ms cubic-bezier(0.16, 1, 0.3, 1),
                 fb-pulse 900ms ease-out 420ms 2;
    }
    @keyframes fb-enter {
      from { opacity: 0; transform: translateY(-12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fb-fade { from { opacity: 0; } to { opacity: 1; } }
    @keyframes fb-pulse {
      0% { box-shadow: 0 0 0 6px rgba(242,85,90,.35), 0 18px 40px rgba(0,0,0,.35); }
      100% { box-shadow: 0 0 0 18px rgba(242,85,90,0), 0 18px 40px rgba(0,0,0,.35); }
    }
    @media (prefers-reduced-motion: reduce) {
      .pin .strip, .pin.fresh .strip, .pin.fresh.tinggi .strip, .pill { animation: none; }
    }
```

- [ ] **Step 3: Render the strip in `extension/src/overlay.js`**

Add this constant next to `MAX_BADGES`:

```js
  const COLLAPSE_AFTER_MS = 6000;
```

Change the shadow markup line in `createOverlay` to add a container for the strip that `setItems` never clears:

```js
    shadow.innerHTML = `<style>${CSS}</style><div class="layer"></div><div class="top"></div><div class="card" hidden></div>`;
```

and after `const card = shadow.querySelector(".card");` add:

```js
    const top = shadow.querySelector(".top");
    let pinned = null;   // { symbol, el, timer }
    let built = 0;
    host.dataset.pinned = "";
    host.dataset.pinnedBuilt = "0";
```

Delete the `makeBadge` function and the `rectOf` anchor branch; `rectOf` becomes:

```js
    function rectOf(item) {
      return item.range ? item.range.getBoundingClientRect() : null;
    }
```

Add these functions inside `createOverlay`, after `makeMark`:

```js
    function setPinnedState(state) {
      pinned.el.dataset.state = state;
      host.dataset.pinned = `${pinned.symbol}:${state}`;
    }

    function dropPinned() {
      if (!pinned) return;
      pinned.timer.cancel();
      pinned.el.remove();
      pinned = null;
      host.dataset.pinned = "";
    }

    // Strip Lapis 0: satu per halaman, di atas-tengah. Dibuat sekali per
    // simbol -- scan ulang dengan simbol yang sama tidak menyentuhnya, supaya
    // animasi masuk tidak berulang dan keadaan penuh/pil tidak ter-reset.
    function buildPinned(v) {
      const tri = v.tier === "tinggi" ? "▲" : "△";
      const stale = v.stale ? ` · data per ${esc(v.asOf)}` : "";
      const el = doc.createElement("div");
      el.className = `pin ${v.tier} fresh`;
      el.innerHTML = `
        <div class="strip" role="status">
          <span class="tri">${tri}</span>
          <div class="text">
            <div><span class="sym">${esc(v.symbol)}</span><span class="lbl">${esc(v.label)}</span></div>
            <div class="sub">${esc(v.move)} · ${esc(v.headline)}${stale}</div>
          </div>
          <button class="go" type="button">Detail ›</button>
          <button class="x" type="button" aria-label="Ciutkan">×</button>
        </div>
        <button class="pill" type="button">${tri} ${esc(v.symbol)} · ${esc(v.label)}</button>`;
      top.appendChild(el);

      const timer = root.FreezeByte.createCollapseTimer(() => {
        el.classList.remove("fresh");
        setPinnedState("collapsed");
      }, COLLAPSE_AFTER_MS);
      pinned = { symbol: v.symbol, el, timer };
      built += 1;
      host.dataset.pinnedBuilt = String(built);
      setPinnedState("expanded");

      const strip = el.querySelector(".strip");
      strip.addEventListener("mouseenter", () => timer.hold());
      strip.addEventListener("mouseleave", () => timer.release());
      el.querySelector(".go").addEventListener("click", (event) => {
        event.stopPropagation();
        openCard(v);
      });
      el.querySelector(".x").addEventListener("click", (event) => {
        event.stopPropagation();
        timer.collapseNow();
      });
      el.querySelector(".pill").addEventListener("click", (event) => {
        event.stopPropagation();
        el.classList.remove("fresh");   // buka lagi tanpa denyut
        setPinnedState("expanded");
        timer.start();
      });
      timer.start();
    }

    function syncPinned(item) {
      if (!item) { dropPinned(); return; }
      if (pinned && pinned.symbol === item.verdict.symbol) return;
      dropPinned();
      buildPinned(item.verdict);
    }
```

Replace `place()`'s loop head so it no longer handles pinned items, and count the strip:

```js
    function place() {
      frame = 0;
      const vw = win.innerWidth;
      const vh = win.innerHeight;
      let visible = 0;
      for (const item of items) {
        const rect = rectOf(item);
        let off = !rect || rect.width === 0 ||
          rect.bottom < 0 || rect.top > vh || rect.right < 0 || rect.left > vw;
```

Keep the rest of the loop body as it is, but delete the `if (item.pinned && !rect) { ... continue; }` block, change the hit-test guard from `if (!off && item.range && !item.pinned)` to `if (!off)`, and delete the final `else { ... rect.right + 4 ... }` branch so only the range branch remains. Change the last line of `place()` to:

```js
      host.dataset.badges = String(visible + (pinned ? 1 : 0));
```

Replace `setItems` with:

```js
    function setItems(next) {
      syncPinned(next.find((item) => item.pinned) || null);
      layer.textContent = "";
      items = next.filter((item) => item.range).slice(0, MAX_BADGES).map((item) => ({
        ...item,
        el: makeMark(item.verdict),
      }));
      schedule();
    }
```

Delete the now-unused `.badge` CSS rules (`.badge`, `.badge.tinggi`, `.badge.sedang`, `.badge::before`, `.badge.sedang::before`, `.badge[hidden]`). Keep `MARGIN` (the card uses it).

Update the header comment of `overlay.js` to mention the strip in one sentence: "Saham yang sedang dibuka (Lapis 0) tampil sebagai strip di atas-tengah yang menciut jadi pil."

Run: `node --test "extension/test/*.test.js"` — Expected: all pass.

- [ ] **Step 4: Create `extension/test/harness-pinned.html`**

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <title>FREEZE BYTE harness pinned</title>
  <style>
    body { margin: 0; font: 16px/1.6 Georgia, serif; background: #fff; color: #131722; }
    nav { display: flex; gap: 16px; align-items: center; padding: 14px 20px; border-bottom: 1px solid #ddd; }
    nav .cta { margin-left: auto; background: #2962ff; color: #fff; padding: 4px 12px; border-radius: 16px; }
    main { max-width: 760px; margin: 24px auto; padding: 0 16px; }
  </style>
</head>
<body>
  <nav><b>SitusSaham</b><span>Pasar</span><span>Berita</span><span class="cta" id="cta">Mulai</span></nav>
  <main>
    <h1>PT Contoh AAAA Tbk</h1>
    <p>Halaman simbol tiruan. Deteksi URL tidak bisa jalan di localhost, jadi
       strip Lapis 0 dipasang langsung lewat createOverlay().setItems().</p>
  </main>
  <script>
    document.addEventListener("DOMContentLoaded", () => {
      window.__bodyBefore = document.body.innerHTML;
    });
  </script>
  <script src="../src/verdict.js"></script>
  <script src="../src/strip.js"></script>
  <script src="../src/overlay.js"></script>
  <script>
    (async () => {
      const FB = globalThis.FreezeByte;
      const [universe, thresholds] = await Promise.all([
        fetch("fixtures/universe.json").then((r) => r.json()),
        fetch("fixtures/thresholds.json").then((r) => r.json()),
      ]);
      const now = Date.parse("2026-09-20T00:00:00Z");
      const v = (s) => FB.verdict(universe.symbols.find((e) => e.symbol === s), thresholds, now);
      const overlay = FB.createOverlay(document);
      window.__host = overlay.host;
      window.__rescan = () => overlay.setItems([{ pinned: true, verdict: v("AAAA") }]);
      window.__switch = () => overlay.setItems([{ pinned: true, verdict: v("BBBB") }]);
      window.__clear = () => overlay.setItems([]);
      window.__rescan();
    })();
  </script>
</body>
</html>
```

- [ ] **Step 5: Browser check with Playwright MCP**

Start (background): `python -m http.server 8731 --directory extension`. Open `http://localhost:8731/test/harness-pinned.html` and evaluate after ~300 ms:

```js
() => ({ ...window.__host.dataset, bodyUnchanged: document.body.innerHTML === window.__bodyBefore })
```

Expected: `pinned: "AAAA:expanded"`, `pinnedBuilt: "1"`, `badges: "1"`, `bodyUnchanged: true`. Take a screenshot: a wide red strip centred under the nav reading "AAAA  Di zona suspensi" with "Naik 52,0% dalam 10 hari bursa · Sehari sebelum suspensi, 38 dari 55 kejadian terlihat seperti ini", not covering the "Mulai" button.

Then:
1. Evaluate `window.__rescan()` three times, then the dataset again → `pinnedBuilt` still `"1"`, `pinned` still `"AAAA:expanded"`.
2. Wait 6500 ms → `pinned: "AAAA:collapsed"`, `badges: "1"`. Screenshot shows the pill "▲ AAAA · Di zona suspensi".
3. Click the pill by coordinates (it is centred horizontally, ~70 px from the top; use `mcp__plugin_playwright_playwright__browser_run_code_unsafe` with `await page.mouse.click(x, y)` where `x = viewport width / 2`, `y = 68`) → `pinned: "AAAA:expanded"`.
4. Evaluate `window.__switch()` → `pinned: "BBBB:expanded"`, `pinnedBuilt: "2"`; screenshot shows the amber strip "BBBB  Mendekati zona suspensi" with "Batas zona: naik 31,6%".
5. Evaluate `window.__clear()` → `pinned: ""`, `badges: "0"`.
6. Reload `http://localhost:8731/test/harness.html` (the original harness) and confirm its old expectations still hold: `badges` `"2"` at top, `"1"` after scrolling to the bottom.

Stop the server.

- [ ] **Step 6: Update docs that mention the anchor**

- `docs/superpowers/specs/2026-09-22-freeze-byte-extension-design.md`: replace the whole "**Lapis 2 — jangkar Stockbit.**" paragraph in §6 with: "**Lapis 0 tampil sebagai strip.** Saham yang dideteksi dari URL ditampilkan sebagai strip di atas-tengah yang menciut jadi pil setelah 6 detik; rinciannya di `2026-09-25-pinned-strip-design.md`. Tidak ada selector per situs." In the §11 table, delete the row "Selector jangkar Stockbit meleset". In §14, delete the checklist line about the Stockbit anchor. Also update §5's file tree only if it lists `anchors.js` (it does not today; leave as is if absent).
- `docs/user-testing.md`: replace the line starting with "Jangkar Stockbit:" with "Strip Lapis 0: tampil penuh, menciut jadi pil setelah 6 detik, pil membuka lagi saat diklik, tidak menutupi tombol navbar situs: [ya/tidak]."
- `docs/SUBMISSION.md`: in the "Sisa pekerjaan" list, remove the Stockbit anchor selector item.
- Run `git grep -n -i "anchors.js\|anchorFor\|jangkar" -- extension docs README.md` and fix any remaining live reference outside `docs/superpowers/plans/` (plans are historical records; leave them).

- [ ] **Step 7: Run all tests and commit**

Run: `node --test "extension/test/*.test.js"` and `python -m pytest` — Expected: all pass.

```bash
git add -A extension docs/superpowers/specs/2026-09-22-freeze-byte-extension-design.md docs/user-testing.md docs/SUBMISSION.md
git commit -m "feat(extension): show the viewed stock as a collapsing top-center strip

Replaces the corner badge, which covered site buttons and read too small
on video. Removes the never-filled Stockbit anchor module.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Before committing, run `git status --short` and make sure `.playwright-mcp/` and `dist/` are not staged.

---

### Task 3: Check in real Chrome (human)

- [ ] **Step 1:** The user reloads the extension in `chrome://extensions` and opens `https://www.tradingview.com/symbols/IDX-CCSI/`: a red strip appears top-center under the nav, does not cover "Get started", pulses twice, collapses to a pill after about 6 seconds; clicking the pill reopens it; "Detail ›" opens the card.
- [ ] **Step 2:** `https://www.tradingview.com/symbols/IDX-MITI/`: amber strip, no pulse, headline "Batas zona: naik 31,8%".
- [ ] **Step 3:** `https://www.tradingview.com/symbols/IDX-BBCA/`: no strip, no pill.
- [ ] **Step 4:** Record the result in `docs/user-testing.md` under the strip line and commit:

```bash
git add docs/user-testing.md
git commit -m "docs: record the strip check in real Chrome

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
