"""Bucketing kejadian dan perhitungan base rate. Fungsi murni.

Pembekuan adalah peristiwa jarang, jadi framing yang benar bersifat kondisional
dan berbasis frekuensi, bukan prediksi individual.
"""
import statistics
from dataclasses import dataclass
from datetime import date

# Batas tercile dihitung dari distribusi yang benar-benar teramati pada
# 2026-09-24 oleh scripts/report_discovery.py, dari dataset 595 record
# suspensi: 60 kejadian suspensi + 60 emiten kontrol, 112 di antaranya punya
# riwayat perdagangan cukup panjang (8 gugur -- LCKM 13 baris, INCF 10 baris,
# ZINC 13 baris, WBSA 20 baris, dan BSWD 15 baris berdagang; BIMA, ADCP, dan
# DIGI nol baris).
# Angka ini TIDAK dikarang di muka. Untuk menghitung ulang setelah menarik data
# baru, jalankan scripts/report_discovery.py lalu salin hasilnya ke sini.
RET10_TERCILES: tuple[float, float] = (-0.030303, 0.318182)
VOL_TERCILES: tuple[float, float] = (0.742330, 1.719077)

MIN_SAMPLE = 10
UNKNOWN_BUCKET = "unknown"


@dataclass(frozen=True)
class Event:
    symbol: str
    as_of: date
    features: dict
    frozen_within_30d: bool
    reopen_return: float | None


@dataclass(frozen=True)
class BaseRate:
    bucket: str
    n: int
    n_frozen_within_30d: int
    median_reopen_return: float | None
    sufficient: bool


def terciles(values: list[float]) -> tuple[float, float]:
    """Dua batas yang membagi nilai jadi tiga kelompok seukuran."""
    clean = sorted(v for v in values if v is not None)
    if len(clean) < 3:
        raise ValueError("butuh minimal 3 nilai untuk menghitung tercile")
    cut = statistics.quantiles(clean, n=3, method="inclusive")
    return (cut[0], cut[1])


def _tercile_label(value: float, bounds: tuple[float, float], prefix: str) -> str:
    low, high = bounds
    if value < low:
        return f"{prefix}1"
    if value < high:
        return f"{prefix}2"
    return f"{prefix}3"


def bucket(features: dict) -> str:
    ret10 = features.get("ret_10d")
    vol = features.get("vol_ratio")
    if ret10 is None or vol is None:
        return UNKNOWN_BUCKET
    return _tercile_label(ret10, RET10_TERCILES, "r") + _tercile_label(
        vol, VOL_TERCILES, "v"
    )


def base_rate(events: list[Event], target: str) -> BaseRate:
    """Frekuensi kondisional untuk satu bucket.

    n_frozen_within_30d dihitung dalam 30 hari KALENDER sejak as_of, bukan
    30 baris bursa, supaya bisa dibandingkan dengan tanggal suspensi resmi apa adanya.
    Penandaan itu dilakukan di build.py; fungsi ini hanya menjumlahkan.
    """
    matching = [e for e in events if bucket(e.features) == target]
    reopens = [e.reopen_return for e in matching if e.reopen_return is not None]

    return BaseRate(
        bucket=target,
        n=len(matching),
        n_frozen_within_30d=sum(1 for e in matching if e.frozen_within_30d),
        median_reopen_return=statistics.median(reopens) if reopens else None,
        sufficient=len(matching) >= MIN_SAMPLE,
    )
