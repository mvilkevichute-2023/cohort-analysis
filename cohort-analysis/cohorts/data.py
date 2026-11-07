"""Загрузка CSV в DuckDB и выполнение SQL-запросов из папки sql/."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
DATA_DIR = ROOT / "data"
TABLES = ("customers", "orders", "marketing")


def connect(data_dir: Path = DATA_DIR) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{data_dir / (t + '.csv')}')")
    return con


def query(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    return con.execute((SQL_DIR / name).read_text(encoding="utf-8")).df()
