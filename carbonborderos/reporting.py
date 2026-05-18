from __future__ import annotations

from io import BytesIO

import pandas as pd


def to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in tables.items():
            safe_name = name[:31].replace("/", "_")
            df.to_excel(writer, index=False, sheet_name=safe_name)
            workbook = writer.book
            worksheet = writer.sheets[safe_name]
            money_fmt = workbook.add_format({"num_format": "€#,##0"})
            num_fmt = workbook.add_format({"num_format": "#,##0.00"})
            pct_fmt = workbook.add_format({"num_format": "0.00%"})
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#1F2937", "font_color": "#FFFFFF"})
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
                width = max(12, min(42, len(str(value)) + 4))
                worksheet.set_column(col_num, col_num, width)
                if "eur" in str(value).lower() or "cost" in str(value).lower() or "value" in str(value).lower():
                    worksheet.set_column(col_num, col_num, width, money_fmt)
                elif "percent" in str(value).lower():
                    worksheet.set_column(col_num, col_num, width, pct_fmt)
                elif any(k in str(value).lower() for k in ["tonnes", "emissions", "risk", "score"]):
                    worksheet.set_column(col_num, col_num, width, num_fmt)
    return output.getvalue()
