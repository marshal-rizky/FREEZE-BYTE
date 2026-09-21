// Router view berbasis hash.
//
// Halaman ini satu dokumen, tapi dibaca sebagai beberapa layar. Hash dipakai
// -- bukan state di memori -- supaya tombol back browser berfungsi, tiap view
// bisa ditautkan langsung, dan memuat ulang halaman tidak membuang posisi
// pembaca. Bentuk hash: "#alka" atau "#anatomi/kejadian".
(function () {
  const DEFAULT_VIEW = "beranda";
  const DEFAULT_TAB = "alasan";

  const views = Array.from(document.querySelectorAll(".view"));
  const navLinks = Array.from(document.querySelectorAll(".segmented a[data-view]"));
  const tabLinks = Array.from(document.querySelectorAll(".segmented a[data-tab]"));
  const tabPanels = Array.from(document.querySelectorAll(".tab-panel"));
  if (!views.length) return;

  const viewNames = new Set(views.map((v) => v.dataset.view));
  const tabNames = new Set(tabPanels.map((p) => p.dataset.tab));

  function parse() {
    const raw = location.hash.replace(/^#/, "");
    const [view, tab] = raw.split("/");
    return {
      view: viewNames.has(view) ? view : DEFAULT_VIEW,
      tab: tabNames.has(tab) ? tab : DEFAULT_TAB,
    };
  }

  // Pemuatan ulang animasi: elemen yang sudah punya [data-active] tidak akan
  // memutar ulang animasi masuknya, jadi atributnya dilepas dan dipasang lagi
  // setelah satu frame.
  function activate(el, group) {
    group.forEach((n) => n.removeAttribute("data-active"));
    void el.offsetWidth;
    el.setAttribute("data-active", "");
  }

  function apply(options) {
    const { view, tab } = parse();

    const target = views.find((v) => v.dataset.view === view);
    if (target && !target.hasAttribute("data-active")) {
      activate(target, views);
      target.scrollTop = 0;
      // Fokus dipindahkan supaya pembaca layar dan navigasi papan ketik ikut
      // berpindah, bukan tertinggal di view sebelumnya. preventScroll menjaga
      // agar pemindahan fokus tidak menggeser halaman dengan sendirinya.
      if (options && options.focus) {
        try { target.focus({ preventScroll: true }); } catch (e) { target.focus(); }
      }
    }

    navLinks.forEach((a) => {
      if (a.dataset.view === view) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });

    const panel = tabPanels.find((p) => p.dataset.tab === tab);
    if (panel && !panel.hasAttribute("data-active")) activate(panel, tabPanels);

    tabLinks.forEach((a) => {
      if (a.dataset.tab === tab) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  window.addEventListener("hashchange", () => apply({ focus: true }));

  // Tautan ke view yang sedang aktif tidak memicu hashchange, jadi klik pada
  // sub-tab dari view yang sama ditangani langsung.
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;
    if (link.getAttribute("href") === location.hash) {
      event.preventDefault();
      apply({ focus: true });
    }
  });

  if (!location.hash) location.replace("#" + DEFAULT_VIEW);
  apply({ focus: false });
})();
