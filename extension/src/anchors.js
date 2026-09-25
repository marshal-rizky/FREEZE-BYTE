// Jangkar penempatan per situs. Selector di sini HANYA memutuskan di mana
// lencana dipaku -- tidak pernah dipakai untuk deteksi. Kalau selector
// meleset (markup situs berubah), lencana jatuh ke pojok: bergeser, tidak
// hilang.
(function (root) {
  const ANCHORS = {
    stockbit: null, // diisi di Task 9 dari halaman Stockbit asli
  };

  function anchorFor(site, doc) {
    const selector = ANCHORS[site];
    if (!selector) return null;
    try {
      return doc.querySelector(selector);
    } catch (err) {
      return null;
    }
  }

  const api = { anchorFor, ANCHORS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
