"""Kurva tenggang dan holdout temporal. Fungsi murni tanpa I/O.

Definisinya mengikuti scripts/report_discovery.py persis: tercile dihitung
dari gabungan kejadian dan kontrol; as_of kejadian adalah hari bursa
terakhir sebelum tanggal suspensi; as_of kontrol adalah baris berdagang
terakhir di window-nya. T-1 adalah as_of itu sendiri; T-k adalah baris
berdagang ke-(k-1) sebelum as_of.
"""
from dataclasses import dataclass
from datetime import date
from typing import Callable

from freezebyte import scoring
from freezebyte.baserates import terciles
from freezebyte.features import ret_n
from freezebyte.freeze import as_date

MIN_TRADING_ROWS = 21
LAGS = (1, 3, 5, 10)
TRAIN_FRACTION = 2 / 3
MISSING = "tidak_terukur"


@dataclass(frozen=True)
class Sample:
    symbol: str
    role: str          # "event" atau "control"
    anchor_date: date  # tanggal suspensi kejadian, atau milik pasangannya
    as_of: date
    rows: tuple


def build_samples(
    manifest: dict,
    load_rows: Callable[[str, list[str]], list[dict] | None],
) -> tuple[list[Sample], list[tuple[str, str]]]:
    entries = (
        [("event", e, e["suspension_date"]) for e in manifest["events"]]
        + [("control", c, c["paired_suspension_date"]) for c in manifest["controls"]]
    )
    samples, skipped = [], []

    for role, entry, anchor in entries:
        symbol = entry["symbol"]
        rows = load_rows(symbol, entry["window"])
        if not rows:
            skipped.append((symbol, "tidak ada baris"))
            continue

        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            skipped.append((symbol, f"hanya {len(trading)} baris berdagang"))
            continue

        if role == "event":
            before = [r for r in trading if as_date(r["date"]) < as_date(anchor)]
            if not before:
                skipped.append((symbol, "tidak ada hari bursa sebelum suspensi"))
                continue
            as_of = as_date(before[-1]["date"])
        else:
            as_of = as_date(trading[-1]["date"])

        samples.append(Sample(symbol, role, as_date(anchor), as_of, tuple(ordered)))

    return samples, skipped


def ret10_at_lag(sample: Sample, lag: int) -> float | None:
    """ret_10d dengan titik akhir mundur lag-1 hari bursa dari as_of.

    Langkah mundurnya melewati baris ber-volume nol (hari beku bukan hari
    bursa), lalu ret_n dihitung persis seperti di produksi.
    """
    trading = [r for r in sample.rows
               if r["volume"] and as_date(r["date"]) <= sample.as_of]
    index = len(trading) - lag
    if index < 0:
        return None
    return ret_n(list(sample.rows), as_date(trading[index]["date"]), 10)


def _empty_counts() -> dict:
    return {scoring.TINGGI: 0, scoring.SEDANG: 0, scoring.SENYAP: 0, MISSING: 0}


def lead_time_curve(samples: list[Sample], lags=LAGS, upper: float | None = None,
                    near: float = scoring.NEAR_ZONE_LOWER) -> list[dict]:
    """Ambang tetap untuk semua jarak -- ekstensi juga memakai ambang tetap."""
    curve = []
    for lag in lags:
        counts = {"event": _empty_counts(), "control": _empty_counts()}
        for sample in samples:
            value = ret10_at_lag(sample, lag)
            key = MISSING if value is None else scoring.tier(value, upper=upper, near=near)
            counts[sample.role][key] += 1
        curve.append({"lag": lag, "events": counts["event"], "controls": counts["control"]})
    return curve


def temporal_holdout(samples: list[Sample], train_fraction: float = TRAIN_FRACTION,
                     near: float = scoring.NEAR_ZONE_LOWER,
                     shipped_upper: float | None = None) -> dict:
    """Tercile dari kejadian tertua, diuji pada kejadian terbaru.

    Pemisahnya tanggal, bukan indeks, supaya kontrol ikut sisi kejadian
    pasangannya (anchor_date kontrol = tanggal suspensi pasangannya).

    `shipped_upper`, kalau diisi, menghitung ulang tangkapan uji yang sama
    dengan ambang yang benar-benar dipakai ekstensi -- ambang itu dipasang
    dari seluruh data (termasuk split uji ini), jadi angkanya tidak boleh
    disamakan begitu saja dengan hasil refit di atas.
    """
    events = sorted((s for s in samples if s.role == "event"),
                    key=lambda s: (s.anchor_date, s.symbol))
    # round() dulu: 6 * (2/3) di float adalah 3.9999999999999996, dan int()
    # langsung akan memotongnya jadi 3.
    cut = int(round(len(events) * train_fraction, 9))
    if cut < 3 or cut >= len(events):
        raise ValueError("kejadian terlalu sedikit untuk holdout temporal")
    boundary = events[cut].anchor_date

    train = [s for s in samples if s.anchor_date < boundary]
    test = [s for s in samples if s.anchor_date >= boundary]
    values = [v for v in (ret10_at_lag(s, 1) for s in train) if v is not None]
    _, upper = terciles(values)

    def caught(role: str, threshold: float) -> dict:
        group = [s for s in test if s.role == role]
        hits = 0
        for s in group:
            value = ret10_at_lag(s, 1)
            if value is not None and scoring.tier(value, upper=threshold, near=near) == scoring.TINGGI:
                hits += 1
        return {"n": len(group), "tinggi": hits}

    result = {
        "boundary_date": boundary.isoformat(),
        "upper": upper,
        "train": {"events": sum(1 for s in train if s.role == "event"),
                  "controls": sum(1 for s in train if s.role == "control")},
        "test_events": caught("event", upper),
        "test_controls": caught("control", upper),
    }
    if shipped_upper is not None:
        result["shipped"] = {
            "upper": shipped_upper,
            "test_events": caught("event", shipped_upper),
            "test_controls": caught("control", shipped_upper),
        }
    return result


def _measured(counts: dict) -> int:
    return counts[scoring.TINGGI] + counts[scoring.SEDANG] + counts[scoring.SENYAP]


def render_markdown(curve: list[dict], holdout: dict, upper: float, near: float,
                    skipped: list[tuple[str, str]]) -> str:
    """Laporan untuk docs/validation/lead-time.md. Hitungan, bukan persentase."""
    lines = [
        "# Kurva tenggang dan holdout temporal",
        "",
        "Digenerate oleh `scripts/report_validation.py`. Jangan disunting tangan.",
        "",
        f"Ambang TINGGI: `ret_10d` ≥ {upper:.6f}. Ambang SEDANG: "
        f"{near:.2f} ≤ `ret_10d` < {upper:.6f} (batas bawah dipilih tetap, "
        "bukan diestimasi). Ambang yang sama dipakai di semua jarak.",
        "",
        "## Kurva tenggang",
        "",
        "| Jarak | Kejadian TINGGI | Kejadian SEDANG | Kejadian terukur "
        "| Kontrol TINGGI | Kontrol SEDANG | Kontrol terukur |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in curve:
        e, c = row["events"], row["controls"]
        lines.append(
            f"| T−{row['lag']} | {e['tinggi']} | {e['sedang']} | {_measured(e)} "
            f"| {c['tinggi']} | {c['sedang']} | {_measured(c)} |"
        )
    missing = [(row["lag"], row["events"][MISSING] + row["controls"][MISSING])
               for row in curve if row["events"][MISSING] + row["controls"][MISSING]]
    if missing:
        lines += ["", "Tidak terukur (riwayat terlalu pendek untuk jarak itu): "
                  + ", ".join(f"T−{lag}: {n}" for lag, n in missing) + "."]

    te, tc = holdout["test_events"], holdout["test_controls"]
    lines += [
        "",
        "## Holdout temporal",
        "",
        f"Tercile dihitung dari {holdout['train']['events']} kejadian dan "
        f"{holdout['train']['controls']} kontrol dengan tanggal suspensi sebelum "
        f"{holdout['boundary_date']}. Ambang TINGGI hasilnya: {holdout['upper']:.6f}.",
        "",
        f"- Kejadian uji yang tertangkap TINGGI: {te['tinggi']} dari {te['n']}.",
        f"- Kontrol uji yang salah tertangkap TINGGI: {tc['tinggi']} dari {tc['n']}.",
        "",
        "Sampel ini case-control 1:1. Hitungan di atas bukan peluang sebuah "
        "saham dibekukan.",
    ]
    if "shipped" in holdout:
        sh = holdout["shipped"]
        ste, stc = sh["test_events"], sh["test_controls"]
        lines += [
            "",
            f"Ambang yang sungguh dipakai ekstensi ({sh['upper']:.6f}) berbeda dari "
            "ambang refit di atas, karena ambang yang dipakai ekstensi dipasang dari "
            "data yang mencakup split uji ini juga. Pada ambang itu, kejadian uji yang "
            f"tertangkap TINGGI: {ste['tinggi']} dari {ste['n']}. Kontrol uji yang "
            f"salah tertangkap TINGGI: {stc['tinggi']} dari {stc['n']}.",
        ]
    if skipped:
        lines += ["", "## Gugur", ""]
        lines += [f"- {symbol}: {reason}" for symbol, reason in skipped]
    return "\n".join(lines) + "\n"
