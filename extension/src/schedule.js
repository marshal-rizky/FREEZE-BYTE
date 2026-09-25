// Debounce dengan batas tunggu maksimum. Murni: tidak tahu apa pun soal DOM.
//
// Debounce polos menunda sampai `wait` ms sepi -- kalau panggilan datang
// lebih rapat dari itu terus-menerus, fn tidak pernah jalan. `maxWait`
// memaksa fn jalan paling lambat `maxWait` ms sejak panggilan pertama di
// rentetan itu, berapa pun rapatnya panggilan berikutnya.
(function (root) {
  function debounceMaxWait(fn, wait, maxWait, clock) {
    clock = clock || {
      setTimeout: (f, ms) => setTimeout(f, ms),
      clearTimeout: (id) => clearTimeout(id),
    };

    let waitTimer = null;
    let maxTimer = null;

    function fire() {
      clock.clearTimeout(waitTimer);
      clock.clearTimeout(maxTimer);
      waitTimer = null;
      maxTimer = null;
      fn();
    }

    return function trigger() {
      clock.clearTimeout(waitTimer);
      waitTimer = clock.setTimeout(fire, wait);
      if (maxTimer === null) {
        maxTimer = clock.setTimeout(fire, maxWait);
      }
    };
  }

  const api = { debounceMaxWait };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
