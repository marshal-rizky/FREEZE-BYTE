const fmtPct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(1).replace(".", ",")}%`;

async function load(name) {
  const response = await fetch(`../data/web/${name}.json`);
  if (!response.ok) throw new Error(`gagal memuat ${name}.json`);
  return response.json();
}

function annotate(container, alka) {
  const confirmed = alka.windows.filter((w) => w.confirmed);
  const cards = [];

  const reopened = confirmed.filter((w) => w.reopen_return !== null);
  if (reopened.length) {
    const last = reopened[reopened.length - 1];
    cards.push({
      value: fmtPct(last.reopen_return),
      label: `perubahan harga saat dibuka kembali (${last.end_date})`,
    });
  }

  cards.push({ value: confirmed.length, label: "jendela beku terkonfirmasi di window ini" });

  const inferred = alka.windows.length - confirmed.length;
  if (inferred > 0) {
    cards.push({ value: inferred, label: "jendela tersimpulkan dari volume nol saja" });
  }

  container.innerHTML = cards
    .map((c) => `<div class="annotation"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
    .join("");
}

async function main() {
  const alka = await load("alka");
  renderPriceChart(document.getElementById("alka-chart"), alka);
  annotate(document.getElementById("alka-annotations"), alka);
}

main().catch((err) => {
  document.getElementById("alka-chart").textContent = err.message;
});
