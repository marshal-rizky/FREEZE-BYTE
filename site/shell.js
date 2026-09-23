// Router panel berbasis hash.
//
// Hash dipakai -- bukan state di memori -- supaya tombol back browser
// berfungsi, tiap panel bisa ditautkan langsung, dan memuat ulang halaman
// tidak membuang posisi pembaca.
(function () {
  const DEFAULT = "ikhtisar";

  const panes = Array.from(document.querySelectorAll(".pane"));
  const links = Array.from(document.querySelectorAll(".rail nav a[data-pane]"));
  if (!panes.length) return;

  const names = new Set(panes.map((p) => p.dataset.pane));
  const parse = () => {
    const raw = location.hash.replace(/^#/, "");
    const [name, query = ""] = raw.split("?");
    return {
      name: names.has(name) ? name : DEFAULT,
      params: new URLSearchParams(query),
    };
  };

  function apply(options) {
    const route = parse();
    const name = route.name;
    window.freezebyteRoute = route;
    const target = panes.find((p) => p.dataset.pane === name);

    if (target && !target.hasAttribute("data-active")) {
      // Atribut dilepas lalu dipasang lagi setelah reflow, kalau tidak
      // elemen yang sudah aktif tidak akan memutar ulang animasi masuknya.
      panes.forEach((p) => p.removeAttribute("data-active"));
      void target.offsetWidth;
      target.setAttribute("data-active", "");
      target.scrollTop = 0;
      // Fokus dipindahkan supaya pembaca layar dan navigasi papan ketik ikut
      // berpindah. preventScroll menjaga agar pemindahan fokus tidak
      // menggeser tata letak dengan sendirinya.
      if (options && options.focus) {
        try { target.focus({ preventScroll: true }); } catch (e) { target.focus(); }
      }
    }

    links.forEach((a) => {
      if (a.dataset.pane === name) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });

    document.dispatchEvent(new CustomEvent("freezebyte:route", { detail: route }));
  }

  window.addEventListener("hashchange", () => apply({ focus: true }));

  // Kartu bento adalah tombol, bukan tautan -- ia membungkus grafik dan
  // daftar, dan menaruh blok semacam itu di dalam <a> bukan markup yang sah.
  // Jadi klik-nya diteruskan ke hash secara manual.
  document.addEventListener("click", (event) => {
    const card = event.target.closest("[data-goto]");
    if (card) {
      location.hash = "#" + card.dataset.goto;
      return;
    }
    // Tautan ke panel yang sedang aktif tidak memicu hashchange.
    const link = event.target.closest('a[href^="#"]');
    if (link && link.getAttribute("href") === location.hash) {
      event.preventDefault();
      apply({ focus: true });
    }
  });

  if (!location.hash) location.replace("#" + DEFAULT);
  apply({ focus: false });

  // Bento baru ada setelah data termuat; penandanya disetel ulang supaya
  // panel aktif tidak kehilangan sorotan di rail.
  document.addEventListener("freezebyte:ready", () => apply({ focus: false }));
})();
