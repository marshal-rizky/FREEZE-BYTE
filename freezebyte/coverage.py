"""Akumulator pengecualian.

Setiap pengecualian dihitung dan ditampilkan, tidak pernah dibuang diam-diam.
Menampilkan angka ini yang membuat produk terbaca jujur.
"""
from collections import defaultdict


class Coverage:
    def __init__(self, total: int):
        self.total = total
        self.analyzed = 0
        self._excluded: dict[str, list[str]] = defaultdict(list)

    def exclude(self, symbol: str, reason: str) -> None:
        self._excluded[reason].append(symbol)

    @property
    def excluded_count(self) -> int:
        return sum(len(symbols) for symbols in self._excluded.values())

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "analyzed": self.analyzed,
            "excluded": self.excluded_count,
            "by_reason": {r: len(s) for r, s in self._excluded.items()},
            "symbols": {r: sorted(s) for r, s in self._excluded.items()},
        }
