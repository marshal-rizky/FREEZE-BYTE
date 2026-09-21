// Menandai bagian mana yang sedang dibaca.
//
// Halaman ini satu gulungan panjang, jadi pertanyaan "saya ada di mana"
// harus punya jawaban yang terlihat setiap saat. IntersectionObserver
// dipakai supaya penandanya ikut posisi gulir tanpa handler scroll yang
// jalan di setiap frame.
(function () {
  const links = Array.from(document.querySelectorAll(".nav-links a"));
  if (!links.length || !("IntersectionObserver" in window)) return;

  const byId = new Map(
    links.map((a) => [a.getAttribute("href").slice(1), a])
  );
  const sections = Array.from(byId.keys())
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  if (!sections.length) return;

  const visible = new Set();

  const paint = () => {
    // Kalau dua bagian sama-sama terlihat, yang paling atas yang menang --
    // itu yang sedang dibaca.
    let current = null;
    for (const section of sections) {
      if (visible.has(section.id)) { current = section.id; break; }
    }
    links.forEach((a) => {
      const id = a.getAttribute("href").slice(1);
      if (id === current) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) visible.add(entry.target.id);
        else visible.delete(entry.target.id);
      });
      paint();
    },
    // Margin atas mengimbangi tinggi nav supaya bagian dianggap aktif saat
    // judulnya benar-benar lewat di bawah chrome, bukan saat masih tertutup.
    { rootMargin: "-20% 0px -60% 0px", threshold: 0 }
  );

  sections.forEach((section) => observer.observe(section));
})();
