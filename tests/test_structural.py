from freezebyte.structural import extract


INPS_OVERVIEW = {
    "overview": {
        "listing_board": "Development",
        "market_cap": 1234567890,
        "tags": ["52-w-high", "90-d-high", "insider-1-month-sell",
                 "public-float-under-25", "single-entity-holding-70", "ytd-high"],
    }
}


def test_extract_reads_every_structural_flag_from_tags():
    result = extract(INPS_OVERVIEW)
    assert result["float_under_25"] is True
    assert result["single_entity_70"] is True
    assert result["insider_1m_sell"] is True
    assert result["at_52w_high"] is True
    assert result["available"] is True


def test_missing_tag_means_false_not_unknown():
    result = extract({"overview": {"tags": ["52-w-high"]}})
    assert result["at_52w_high"] is True
    assert result["float_under_25"] is False


def test_none_overview_marks_unavailable_and_flags_are_false():
    result = extract(None)
    assert result["available"] is False
    assert result["float_under_25"] is False
    assert result["tags"] == []


def test_listing_board_is_carried_through_but_is_not_special_board_status():
    """listing_board INPS berbunyi Development padahal INPS disuspensi karena
    berada di Papan Pemantauan Khusus. Field ini bukan status PPK."""
    assert extract(INPS_OVERVIEW)["listing_board"] == "Development"
