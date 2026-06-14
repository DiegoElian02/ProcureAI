"""Utilities to load and profile structured business files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@dataclass(frozen=True)
class DatasetProfile:
    rows: int
    columns: list[str]
    numeric_columns: list[str]
    date_columns: list[str]
    recognized_columns: dict[str, str]


DATE_COLUMN_HINTS = ("date", "fecha", "day", "month", "year")


COLUMN_ALIASES = {
    "date": ["date", "fecha", "invoice_date", "order_date"],
    "provider": ["provider", "supplier", "vendor", "proveedor"],
    "product": ["product", "item", "sku", "producto"],
    "revenue": ["revenue", "sales", "ventas", "income", "ingresos"],
    "cost": ["cost", "cogs", "costo", "expense_cost"],
    "spend": ["spend", "gasto", "amount", "invoice_amount", "purchase_amount"],
    "quantity": ["quantity", "qty", "cantidad", "units"],
}


def load_file(uploaded_file: BinaryIO, filename: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Formato no soportado. Sube un archivo CSV, XLSX o XLS.")

    if suffix == ".csv":
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if df.empty:
        raise ValueError("El archivo no tiene datos para analizar.")

    df.columns = [str(column).strip() for column in df.columns]
    return df


def profile_dataset(df: pd.DataFrame) -> DatasetProfile:
    """Return a simple profile with recognized business columns."""
    normalized = {column.lower().strip().replace(" ", "_"): column for column in df.columns}
    recognized: dict[str, str] = {}

    for canonical_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                recognized[canonical_name] = normalized[alias]
                break

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    date_columns: list[str] = []
    for column in df.columns:
        normalized_column = column.lower().strip().replace(" ", "_")
        looks_like_date = normalized_column in COLUMN_ALIASES["date"] or any(
            hint in normalized_column for hint in DATE_COLUMN_HINTS
        )
        if column in numeric_columns or not looks_like_date:
            continue

        parsed = pd.to_datetime(df[column], errors="coerce", format="mixed")
        if parsed.notna().mean() >= 0.7:
            date_columns.append(column)

    return DatasetProfile(
        rows=len(df),
        columns=df.columns.tolist(),
        numeric_columns=numeric_columns,
        date_columns=date_columns,
        recognized_columns=recognized,
    )
