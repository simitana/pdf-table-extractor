from __future__ import annotations

import io

import pandas as pd

from ..core.models import TableOut


def to_csv(table: TableOut) -> bytes:
    frame = pd.DataFrame(table.rows, columns=table.headers)
    return frame.to_csv(index=False).encode("utf-8-sig")


def to_excel(tables: list[TableOut]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for table in tables:
            frame = pd.DataFrame(table.rows, columns=table.headers)
            sheet_name = f"p{table.page_number}_t{table.table_index + 1}"[:31]
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()
