// Merangkai deteksi, vonis, dan overlay di satu halaman. Tidak memanggil
// jaringan apa pun selain membaca dua berkas JSON milik ekstensi sendiri.
(async function () {
  const FB = globalThis.FreezeByte;
  if (!FB || globalThis.__freezeByteLoaded) return;
  globalThis.__freezeByteLoaded = true;

  const readJson = async (path) => {
    const response = await fetch(chrome.runtime.getURL(path));
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  };

  let universe, thresholds;
  try {
    [universe, thresholds] = await Promise.all([
      readJson("data/universe.json"), readJson("data/thresholds.json"),
    ]);
  } catch (err) {
    console.error("FREEZE BYTE: data ekstensi gagal dimuat; ekstensi diam.", err);
    return;
  }

  const now = Date.now();
  const verdicts = new Map();
  for (const entry of universe.symbols) {
    const v = FB.verdict(entry, thresholds, now);
    if (v) verdicts.set(entry.symbol, v);
  }
  if (!verdicts.size) return;

  const whitelist = new Set(verdicts.keys());
  const overlay = FB.createOverlay(document);
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "INPUT", "SELECT", "OPTION"]);
  const MAYBE_TICKER = /[A-Z]{4}/;

  function scan() {
    const items = [];

    const focused = FB.symbolFromUrl(location.href);
    if (focused && verdicts.has(focused.symbol)) {
      items.push({
        pinned: true,
        anchor: FB.anchorFor(focused.site, document),
        verdict: verdicts.get(focused.symbol),
      });
    }

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || SKIP.has(parent.tagName) || parent.isContentEditable) {
          return NodeFilter.FILTER_REJECT;
        }
        // Kontainer yang disembunyikan/dikolaps (mis. tinggi 0, display:none)
        // tetap punya Range dengan rect non-nol -- checkVisibility menyaring
        // teks yang memang tidak terlihat pembaca.
        if (typeof parent.checkVisibility === "function" &&
            !parent.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) {
          return NodeFilter.FILTER_REJECT;
        }
        return MAYBE_TICKER.test(node.nodeValue)
          ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      for (const hit of FB.findSymbols(node.nodeValue, whitelist)) {
        const range = document.createRange();
        range.setStart(node, hit.index);
        range.setEnd(node, hit.index + hit.symbol.length);
        items.push({ range, verdict: verdicts.get(hit.symbol) });
      }
    }

    overlay.setItems(items);
  }

  // Debounce 400ms tetap ada supaya mutasi beruntun tidak memicu scan
  // berkali-kali, tapi maxWait 1500ms memaksa scan tetap jalan di halaman
  // yang bermutasi lebih rapat dari itu terus-menerus (mis. feed yang
  // di-append tiap detik) -- debounce polos tidak akan pernah reda di sana.
  const rescan = FB.debounceMaxWait(scan, 400, 1500);
  new MutationObserver(() => {
    // Posisi lencana mengikuti layout antar-scan juga, bukan hanya saat scan
    // ulang selesai.
    overlay.schedule();
    rescan();
  }).observe(document.body, {
    childList: true, subtree: true, characterData: true,
  });
  scan();
})();
