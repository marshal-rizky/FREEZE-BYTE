// Deteksi simbol. Murni: menjawab "simbol apa, di mana", tidak tahu apa pun
// soal risiko maupun DOM.
//
// Lapis 0 membaca simbol yang sedang DILIHAT dari URL. Lapis 1 menyapu teks
// dan hanya menerima kode yang ada di daftar putih -- daftar putih itulah
// yang membuat pola empat huruf kapital aman dipakai di situs mana pun.
(function (root) {
  // Setiap pola diverifikasi terhadap situs aslinya (Task 9) sebelum rilis.
  const URL_RULES = [
    { site: "stockbit",
      pattern: /^https:\/\/(?:www\.)?stockbit\.com\/symbol\/([A-Za-z]{4})(?:[\/?#]|$)/ },
    { site: "tradingview",
      pattern: /^https:\/\/(?:[a-z]{2,3}\.)?tradingview\.com\/symbols\/IDX-([A-Za-z]{4})(?:[\/?#]|$)/ },
    { site: "google-finance",
      pattern: /^https:\/\/www\.google\.com\/finance\/quote\/([A-Za-z]{4}):IDX(?:[\/?#]|$)/ },
  ];

  function symbolFromUrl(url) {
    for (const rule of URL_RULES) {
      const match = rule.pattern.exec(String(url));
      if (match) return { site: rule.site, symbol: match[1].toUpperCase() };
    }
    return null;
  }

  const TICKER = /\b[A-Z]{4}\b/g;
  // Kata "kapital" untuk keperluan deteksi judul: huruf besar, angka, dan
  // tanda baca, minimal dua karakter, minimal satu huruf.
  const CAPS_WORD = /^[A-Z0-9&.,:;!?()'"\-]{2,}$/;
  const MAX_CAPS_RUN = 3;

  const isCapsWord = (word) => CAPS_WORD.test(word) && /[A-Z]/.test(word);

  function capsRunLength(tokens, i) {
    let n = 1;
    for (let j = i - 1; j >= 0 && isCapsWord(tokens[j].word); j -= 1) n += 1;
    for (let j = i + 1; j < tokens.length && isCapsWord(tokens[j].word); j += 1) n += 1;
    return n;
  }

  function findSymbols(text, whitelist) {
    const found = [];
    let tokens = null;
    for (const match of text.matchAll(TICKER)) {
      const symbol = match[0];
      if (!whitelist.has(symbol)) continue;
      if (!tokens) {
        tokens = Array.from(text.matchAll(/\S+/g),
          (m) => ({ start: m.index, end: m.index + m[0].length, word: m[0] }));
      }
      const i = tokens.findIndex((t) => t.start <= match.index && match.index < t.end);
      // Judul ALL CAPS ("BEI SUSPENSI SAHAM ALKA") membuat kata biasa terlihat
      // seperti kode; kode di tengah rentetan kapital panjang ditolak.
      if (i >= 0 && capsRunLength(tokens, i) > MAX_CAPS_RUN) continue;
      found.push({ symbol, index: match.index });
    }
    return found;
  }

  const api = { symbolFromUrl, findSymbols, URL_RULES };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
