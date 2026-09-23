"""Tingkat peringatan dari fitur. Fungsi murni.

Satu-satunya tempat tingkat diputuskan. Ekstensi dan halaman bukti membaca
hasilnya dari JSON, tidak menghitung ulang.
"""
from freezebyte import baserates

TINGGI = "tinggi"
SEDANG = "sedang"
SENYAP = "senyap"

# Batas bawah SEDANG. Pilihan tetap proyek ini, bukan hasil estimasi: data
# tidak mendukung tingkat risiko tengah (r1 dan r2 praktis identik), jadi
# SEDANG berarti "mendekati ambang", bukan kelas risiko tersendiri.
NEAR_ZONE_LOWER = 0.20


def upper_bound() -> float:
    """Batas atas tercile ret_10d. Dibaca saat dipanggil, bukan saat impor,
    supaya nilai baru dari report_discovery.py langsung berlaku."""
    return baserates.RET10_TERCILES[1]


def tier(ret_10d: float | None, upper: float | None = None,
         near: float = NEAR_ZONE_LOWER) -> str:
    """TINGGI memakai >= supaya sama persis dengan bucket r3."""
    if ret_10d is None:
        return SENYAP
    if upper is None:
        upper = upper_bound()
    if ret_10d >= upper:
        return TINGGI
    if ret_10d >= near:
        return SEDANG
    return SENYAP
