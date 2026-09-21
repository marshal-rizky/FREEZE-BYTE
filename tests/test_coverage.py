from freezebyte.coverage import Coverage


def test_counts_analyzed_and_excluded():
    coverage = Coverage(total=100)
    coverage.exclude("AAAA", "harga tidak tersedia")
    coverage.exclude("BBBB", "harga tidak tersedia")
    coverage.exclude("CCCC", "riwayat terlalu pendek")
    coverage.analyzed = 97

    result = coverage.as_dict()
    assert result["total"] == 100
    assert result["analyzed"] == 97
    assert result["excluded"] == 3
    assert result["by_reason"]["harga tidak tersedia"] == 2
    assert result["by_reason"]["riwayat terlalu pendek"] == 1


def test_excluded_symbols_are_listed_per_reason():
    coverage = Coverage(total=2)
    coverage.exclude("AAAA", "404")
    assert coverage.as_dict()["symbols"]["404"] == ["AAAA"]
