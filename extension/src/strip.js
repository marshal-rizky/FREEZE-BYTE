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
