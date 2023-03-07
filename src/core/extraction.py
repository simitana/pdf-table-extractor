from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber

from .exceptions import ExtractionFailedError


@dataclass
class ExtractedTable:
    page_number: int
    table_index: int
    headers: list[str]
    rows: list[list[Any]]
    confidence: float

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.headers)


TABLE_SETTINGS_VARIANTS: list[dict[str, Any]] = [
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "text", "horizontal_strategy": "text"},
    {"vertical_strategy": "lines", "horizontal_strategy": "text"},
]


def extract_tables(pdf_path: Path) -> list[ExtractedTable]:
    try:
        with pdfplumber.open(pdf_path) as document:
            extracted: list[ExtractedTable] = []
            for page_number, page in enumerate(document.pages, start=1):
                extracted.extend(_extract_page_tables(page, page_number))
            return extracted
    except Exception as exc:
        raise ExtractionFailedError(str(exc)) from exc


def _extract_page_tables(page: Any, page_number: int) -> list[ExtractedTable]:
    best_raw_tables: list[list[list[Any]]] = []
    best_score = -1.0

    for table_settings in TABLE_SETTINGS_VARIANTS:
        raw_tables = page.extract_tables(table_settings=table_settings)
        score = sum(_score_raw_table(t) for t in raw_tables)
        if raw_tables and score > best_score:
            best_score = score
            best_raw_tables = raw_tables

    tables: list[ExtractedTable] = []
    for index, raw_table in enumerate(best_raw_tables):
        cleaned = _clean_raw_table(raw_table)
        if cleaned is None:
            continue
        headers, rows = cleaned
        tables.append(
            ExtractedTable(
                page_number=page_number,
                table_index=index,
                headers=headers,
                rows=rows,
                confidence=_score_raw_table(raw_table),
            )
        )
    return tables


def _score_raw_table(raw_table: list[list[Any]]) -> float:
    if not raw_table or len(raw_table) < 2:
        return 0.0

    column_counts = [len(row) for row in raw_table]
    most_common_count = max(set(column_counts), key=column_counts.count)
    consistency = column_counts.count(most_common_count) / len(column_counts)

    total_cells = sum(column_counts)
    filled_cells = sum(1 for row in raw_table for cell in row if cell and str(cell).strip())
    density = filled_cells / total_cells if total_cells else 0.0

    return round(consistency * 0.6 + density * 0.4, 4)


def _clean_raw_table(raw_table: list[list[Any]]) -> tuple[list[str], list[list[Any]]] | None:
    if len(raw_table) < 2:
        return None

    header_row, *data_rows = raw_table
    headers = [_normalize_cell(cell) or f"column_{i + 1}" for i, cell in enumerate(header_row)]

    seen: dict[str, int] = {}
    unique_headers: list[str] = []
    for header in headers:
        count = seen.get(header, 0)
        seen[header] = count + 1
        unique_headers.append(header if count == 0 else f"{header}_{count}")

    rows = [
        [_normalize_cell(cell) for cell in row]
        for row in data_rows
        if any(_normalize_cell(cell) for cell in row)
    ]

    if not rows:
        return None

    width = len(unique_headers)
    normalized_rows = [_pad_row(row, width) for row in rows]

    return unique_headers, normalized_rows


def _pad_row(row: list[Any], width: int) -> list[Any]:
    if len(row) < width:
        return row + [None] * (width - len(row))
    return row[:width]


def _normalize_cell(cell: Any) -> str | None:
    if cell is None:
        return None
    text = str(cell).replace("\n", " ").strip()
    return text or None
