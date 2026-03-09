"""Unit tests for datatalk.printer module."""

from io import StringIO
from unittest.mock import MagicMock

import pandas as pd
import pytest
from rich.console import Console

from datatalk.printer import (
    Printer,
    print_logo,
    print_configuration_help,
    print_file_required_help,
    print_stats,
    print_query_results,
)


def make_printer(quiet=False):
    """Create a Printer that captures output."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    printer = Printer(console, quiet=quiet)
    return printer, buf


# --- Printer class ---


class TestPrinter:
    def test_decorative_shown_when_not_quiet(self):
        printer, buf = make_printer(quiet=False)
        printer.decorative("hello")
        assert "hello" in buf.getvalue()

    def test_decorative_suppressed_when_quiet(self):
        printer, buf = make_printer(quiet=True)
        printer.decorative("hello")
        assert "hello" not in buf.getvalue()

    def test_result_shown_when_not_quiet(self):
        printer, buf = make_printer(quiet=False)
        printer.result("result text")
        assert "result text" in buf.getvalue()

    def test_result_shown_when_quiet(self):
        printer, buf = make_printer(quiet=True)
        printer.result("result text")
        assert "result text" in buf.getvalue()

    def test_quiet_flag_stored(self):
        printer, _ = make_printer(quiet=True)
        assert printer.quiet is True

    def test_not_quiet_flag_stored(self):
        printer, _ = make_printer(quiet=False)
        assert printer.quiet is False


# --- print_logo ---


class TestPrintLogo:
    def test_logo_shown_when_not_quiet(self):
        printer, buf = make_printer(quiet=False)
        print_logo(printer)
        assert "DATATALK" in buf.getvalue().upper() or "██" in buf.getvalue()

    def test_logo_suppressed_when_quiet(self):
        printer, buf = make_printer(quiet=True)
        print_logo(printer)
        assert buf.getvalue() == ""


# --- print_configuration_help ---


class TestPrintConfigurationHelp:
    def test_shows_model_instructions(self):
        printer, buf = make_printer(quiet=False)
        print_configuration_help(printer)
        output = buf.getvalue()
        assert "LLM_MODEL" in output or "LLM" in output.upper()

    def test_shows_popular_models(self):
        printer, buf = make_printer(quiet=False)
        print_configuration_help(printer)
        output = buf.getvalue()
        assert "gpt-4o" in output
        assert "ollama" in output.lower()


# --- print_file_required_help ---


class TestPrintFileRequiredHelp:
    def test_shows_usage(self):
        printer, buf = make_printer(quiet=False)
        print_file_required_help(printer)
        output = buf.getvalue()
        assert "dtalk" in output

    def test_shows_supported_formats(self):
        printer, buf = make_printer(quiet=False)
        print_file_required_help(printer)
        output = buf.getvalue()
        assert "CSV" in output
        assert "Parquet" in output


# --- print_stats ---


class TestPrintStats:
    @pytest.fixture
    def sample_stats(self):
        return {
            "row_count": 100,
            "col_count": 3,
            "columns": [
                {"name": "id", "type": "INTEGER", "samples": "1, 2, 3"},
                {"name": "name", "type": "VARCHAR", "samples": "Alice, Bob, Carol"},
                {"name": "price", "type": "DOUBLE", "samples": "9.99, 19.99, 29.99"},
            ],
        }

    def test_shows_row_count(self, sample_stats):
        printer, buf = make_printer(quiet=False)
        print_stats(sample_stats, printer)
        assert "100" in buf.getvalue()

    def test_shows_column_count(self, sample_stats):
        printer, buf = make_printer(quiet=False)
        print_stats(sample_stats, printer)
        assert "3" in buf.getvalue()

    def test_shows_column_names(self, sample_stats):
        printer, buf = make_printer(quiet=False)
        print_stats(sample_stats, printer)
        output = buf.getvalue()
        assert "id" in output
        assert "name" in output
        assert "price" in output

    def test_suppressed_when_quiet(self, sample_stats):
        printer, buf = make_printer(quiet=True)
        print_stats(sample_stats, printer)
        assert buf.getvalue() == ""

    def test_no_schema_hides_columns(self, sample_stats):
        printer, buf = make_printer(quiet=False)
        print_stats(sample_stats, printer, show_schema=False)
        output = buf.getvalue()
        # Row count shown but not column table
        assert "100" in output
        # Column type info should not be in a table
        assert "INTEGER" not in output


# --- print_query_results ---


class TestPrintQueryResults:
    def test_shows_data(self):
        printer, buf = make_printer(quiet=False)
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        print_query_results(df, printer)
        output = buf.getvalue()
        assert "A" in output
        assert "B" in output

    def test_empty_dataframe_shows_no_results(self):
        printer, buf = make_printer(quiet=False)
        df = pd.DataFrame({"id": []})
        print_query_results(df, printer)
        assert "No results found" in buf.getvalue()

    def test_truncates_at_limit(self):
        printer, buf = make_printer(quiet=False)
        df = pd.DataFrame({"id": range(50)})
        print_query_results(df, printer, limit=5)
        output = buf.getvalue()
        assert "..." in output
        assert "Showing first 5 of 50 rows" in output

    def test_no_truncation_within_limit(self):
        printer, buf = make_printer(quiet=False)
        df = pd.DataFrame({"id": range(3)})
        print_query_results(df, printer, limit=20)
        output = buf.getvalue()
        assert "Showing first" not in output

    def test_default_limit_is_20(self):
        printer, buf = make_printer(quiet=False)
        df = pd.DataFrame({"id": range(25)})
        print_query_results(df, printer)
        assert "Showing first 20 of 25 rows" in buf.getvalue()
