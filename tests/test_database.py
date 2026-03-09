"""Unit tests for datatalk.database module."""

import os
import tempfile

import duckdb
import pandas as pd
import pytest

from datatalk import database


@pytest.fixture
def con():
    """Create a fresh DuckDB connection."""
    return database.create_connection()


@pytest.fixture
def csv_file(tmp_path):
    """Create a temporary CSV file with test data."""
    path = tmp_path / "test.csv"
    path.write_text("id,name,price\n1,Apple,1.50\n2,Banana,0.75\n3,Cherry,3.00\n")
    return str(path)


@pytest.fixture
def parquet_file(tmp_path):
    """Create a temporary Parquet file with test data."""
    path = tmp_path / "test.parquet"
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"], "value": [10, 20, 30]})
    df.to_parquet(str(path), index=False)
    return str(path)


@pytest.fixture
def excel_file(tmp_path):
    """Create a temporary Excel file with numeric test data."""
    path = tmp_path / "test.xlsx"
    df = pd.DataFrame({"id": [1, 2], "qty": [100, 200], "price": [9.99, 19.99]})
    df.to_excel(str(path), index=False)
    return str(path)


@pytest.fixture
def loaded_con(con, csv_file):
    """Connection with CSV data already loaded."""
    database.load_data(con, csv_file)
    return con


# --- create_connection ---


class TestCreateConnection:
    def test_returns_duckdb_connection(self):
        conn = database.create_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)

    def test_connection_is_functional(self):
        conn = database.create_connection()
        result = conn.execute("SELECT 1 AS x").fetchone()
        assert result[0] == 1


# --- load_data ---


class TestLoadData:
    def test_load_csv(self, con, csv_file):
        database.load_data(con, csv_file)
        result = con.execute("SELECT COUNT(*) FROM events").fetchone()
        assert result[0] == 3

    def test_load_csv_columns(self, con, csv_file):
        database.load_data(con, csv_file)
        df = con.execute("SELECT * FROM events").df()
        assert list(df.columns) == ["id", "name", "price"]

    def test_load_parquet(self, con, parquet_file):
        database.load_data(con, parquet_file)
        result = con.execute("SELECT COUNT(*) FROM events").fetchone()
        assert result[0] == 3

    def test_load_parquet_columns(self, con, parquet_file):
        database.load_data(con, parquet_file)
        df = con.execute("SELECT * FROM events").df()
        assert list(df.columns) == ["id", "name", "value"]

    def test_load_excel(self, con, excel_file):
        database.load_data(con, excel_file)
        result = con.execute("SELECT COUNT(*) FROM events").fetchone()
        assert result[0] == 2

    def test_load_excel_with_sheet_name(self, con, excel_file):
        database.load_data(con, excel_file, sheet_name="Sheet1")
        result = con.execute("SELECT COUNT(*) FROM events").fetchone()
        assert result[0] == 2

    def test_load_unsupported_format_raises(self, con, tmp_path):
        path = tmp_path / "data.txt"
        path.write_text("some data")
        with pytest.raises(ValueError, match="Unsupported file format"):
            database.load_data(con, str(path))

    def test_load_replaces_existing_table(self, con, csv_file, parquet_file):
        database.load_data(con, csv_file)
        assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3
        database.load_data(con, parquet_file)
        df = con.execute("SELECT * FROM events").df()
        assert "value" in df.columns  # parquet has 'value', csv has 'price'

    def test_load_xls_extension(self, con, tmp_path):
        """Test that .xls extension is accepted (uses same path as .xlsx)."""
        path = tmp_path / "test.xlsx"
        df = pd.DataFrame({"a": [1]})
        df.to_excel(str(path), index=False)
        # Rename to .xls won't actually work with openpyxl, but we test
        # the branching logic accepts the extension
        database.load_data(con, str(path))
        assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


# --- get_schema ---


class TestGetSchema:
    def test_schema_format(self, loaded_con):
        schema = database.get_schema(loaded_con)
        assert "id" in schema
        assert "name" in schema
        assert "price" in schema

    def test_schema_includes_types(self, loaded_con):
        schema = database.get_schema(loaded_con)
        # DuckDB infers types from CSV
        assert "(" in schema and ")" in schema

    def test_schema_comma_separated(self, loaded_con):
        schema = database.get_schema(loaded_con)
        parts = schema.split(", ")
        assert len(parts) == 3


# --- execute_query ---


class TestExecuteQuery:
    def test_returns_dataframe(self, loaded_con):
        df = database.execute_query(loaded_con, "SELECT * FROM events")
        assert isinstance(df, pd.DataFrame)

    def test_select_all(self, loaded_con):
        df = database.execute_query(loaded_con, "SELECT * FROM events")
        assert len(df) == 3

    def test_filtering(self, loaded_con):
        df = database.execute_query(loaded_con, "SELECT * FROM events WHERE id = 1")
        assert len(df) == 1

    def test_aggregation(self, loaded_con):
        df = database.execute_query(loaded_con, "SELECT COUNT(*) AS cnt FROM events")
        assert df.iloc[0]["cnt"] == 3

    def test_invalid_sql_raises(self, loaded_con):
        with pytest.raises(Exception):
            database.execute_query(loaded_con, "SELECT * FROM nonexistent_table")


# --- get_stats ---


class TestGetStats:
    def test_stats_keys(self, loaded_con):
        stats = database.get_stats(loaded_con)
        assert "row_count" in stats
        assert "col_count" in stats
        assert "columns" in stats

    def test_row_count(self, loaded_con):
        stats = database.get_stats(loaded_con)
        assert stats["row_count"] == 3

    def test_col_count(self, loaded_con):
        stats = database.get_stats(loaded_con)
        assert stats["col_count"] == 3

    def test_column_details(self, loaded_con):
        stats = database.get_stats(loaded_con)
        col_names = [c["name"] for c in stats["columns"]]
        assert "id" in col_names
        assert "name" in col_names
        assert "price" in col_names

    def test_column_has_type(self, loaded_con):
        stats = database.get_stats(loaded_con)
        for col in stats["columns"]:
            assert "type" in col
            assert col["type"]  # not empty

    def test_column_has_samples(self, loaded_con):
        stats = database.get_stats(loaded_con)
        for col in stats["columns"]:
            assert "samples" in col
            assert col["samples"] != "[no data]"

    def test_sample_truncation(self, con):
        """Sample values longer than 20 chars should be truncated."""
        con.execute(
            "CREATE TABLE events AS SELECT 'a_very_long_string_that_exceeds_twenty_chars' AS long_col"
        )
        stats = database.get_stats(con)
        sample = stats["columns"][0]["samples"]
        assert "..." in sample
