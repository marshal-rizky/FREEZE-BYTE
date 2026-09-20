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


def test_empty_tag_list_is_a_real_answer_not_an_exclusion():
    """Nol tag berarti kita tahu jawabannya nol. Itu bukan data hilang."""
    result = extract({"overview": {"tags": []}})
    assert result["available"] is True
    assert result["tags"] == []
    assert result["float_under_25"] is False


def test_payload_without_a_tags_key_is_counted_as_an_exclusion():
    """Bentuk yang tidak dikenali tidak boleh tampil sebagai emiten bersih."""
    assert extract({"unexpected_shape": 1})["available"] is False
    assert extract({"overview": {"market_cap": 123}})["available"] is False


def test_flat_payload_without_an_overview_wrapper_still_works():
    result = extract({"tags": ["52-w-high"], "listing_board": "Main"})
    assert result["available"] is True
    assert result["at_52w_high"] is True
    assert result["listing_board"] == "Main"


def test_absent_market_cap_and_listing_board_stay_none():
    result = extract({"overview": {"tags": ["52-w-high"]}})
    assert result["market_cap"] is None
    assert result["listing_board"] is None
