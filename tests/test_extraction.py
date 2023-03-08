from __future__ import annotations

from src.core.extraction import _clean_raw_table, _normalize_cell, _score_raw_table


def test_normalize_cell_strips_whitespace_and_newlines() -> None:
    assert _normalize_cell("  Hello\nWorld  ") == "Hello World"


def test_normalize_cell_returns_none_for_empty() -> None:
    assert _normalize_cell("   ") is None
    assert _normalize_cell(None) is None


def test_score_raw_table_rewards_consistent_columns() -> None:
    consistent = [["a", "b"], ["1", "2"], ["3", "4"]]
    inconsistent = [["a", "b"], ["1"], ["3", "4", "5"]]
    assert _score_raw_table(consistent) > _score_raw_table(inconsistent)


def test_score_raw_table_handles_short_tables() -> None:
    assert _score_raw_table([]) == 0.0
    assert _score_raw_table([["a", "b"]]) == 0.0


def test_clean_raw_table_deduplicates_headers() -> None:
    raw = [["Name", "Name"], ["Alice", "Bob"]]
    headers, rows = _clean_raw_table(raw)
    assert headers == ["Name", "Name_1"]
    assert rows == [["Alice", "Bob"]]


def test_clean_raw_table_drops_empty_rows() -> None:
    raw = [["Name", "Age"], ["Alice", "30"], [None, None]]
    headers, rows = _clean_raw_table(raw)
    assert rows == [["Alice", "30"]]


def test_clean_raw_table_returns_none_when_no_data_rows() -> None:
    assert _clean_raw_table([["Name", "Age"]]) is None


def test_clean_raw_table_pads_short_rows() -> None:
    raw = [["Name", "Age", "City"], ["Alice", "30"]]
    headers, rows = _clean_raw_table(raw)
    assert rows == [["Alice", "30", None]]
