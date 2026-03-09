"""Unit tests for datatalk.query module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from rich.console import Console

from datatalk import database
from datatalk.llm import LiteLLMProvider
from datatalk.printer import Printer
from datatalk.query import process_query


@pytest.fixture
def con():
    """DuckDB connection with test data loaded."""
    conn = database.create_connection()
    conn.execute("CREATE TABLE events AS SELECT 1 AS id, 'Test' AS name, 9.99 AS price")
    return conn


@pytest.fixture
def printer():
    return Printer(Console(), quiet=True)


@pytest.fixture
def mock_provider():
    return MagicMock(spec=LiteLLMProvider)


class TestProcessQuery:
    def test_successful_query(self, mock_provider, con, printer):
        mock_provider.to_sql.return_value = "SELECT * FROM events"

        result = process_query(mock_provider, "show all", "id (INT)", con, printer)

        assert result["sql"] == "SELECT * FROM events"
        assert result["error"] is None
        assert isinstance(result["dataframe"], pd.DataFrame)
        assert len(result["dataframe"]) == 1

    def test_aggregation_query(self, mock_provider, con, printer):
        mock_provider.to_sql.return_value = "SELECT COUNT(*) AS cnt FROM events"

        result = process_query(mock_provider, "how many?", "id (INT)", con, printer)

        assert result["error"] is None
        assert result["dataframe"].iloc[0]["cnt"] == 1

    def test_llm_error_returns_error_dict(self, mock_provider, con, printer):
        mock_provider.to_sql.side_effect = ValueError("API key invalid")

        result = process_query(mock_provider, "test", "id (INT)", con, printer)

        assert result["error"] == "API key invalid"
        assert result["sql"] is None
        assert result["dataframe"] is None

    def test_sql_execution_error_returns_error_dict(self, mock_provider, con, printer):
        mock_provider.to_sql.return_value = "SELECT * FROM nonexistent"

        result = process_query(mock_provider, "test", "id (INT)", con, printer)

        assert result["error"] is not None
        assert result["sql"] is None
        assert result["dataframe"] is None

    def test_calls_provider_with_question_and_schema(self, mock_provider, con, printer):
        mock_provider.to_sql.return_value = "SELECT 1"

        process_query(mock_provider, "my question", "id (INT), name (VARCHAR)", con, printer)

        mock_provider.to_sql.assert_called_once_with("my question", "id (INT), name (VARCHAR)")

    def test_prints_decorative_messages(self, mock_provider, con):
        """Verify decorative status messages are emitted."""
        mock_printer = MagicMock(spec=Printer)
        mock_provider.to_sql.return_value = "SELECT 1"

        process_query(mock_provider, "test", "id (INT)", con, mock_printer)

        # Should print "Analyzing..." and "Executing..." messages
        assert mock_printer.decorative.call_count == 2

    def test_error_skips_second_decorative(self, mock_provider, con):
        """If LLM fails, only the first decorative message is printed."""
        mock_printer = MagicMock(spec=Printer)
        mock_provider.to_sql.side_effect = Exception("fail")

        process_query(mock_provider, "test", "id (INT)", con, mock_printer)

        # Only "Analyzing..." printed, not "Executing..."
        assert mock_printer.decorative.call_count == 1
