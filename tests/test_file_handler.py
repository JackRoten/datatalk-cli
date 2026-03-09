"""Unit tests for datatalk.file_handler module."""

from io import StringIO
from unittest.mock import patch

import pandas as pd
import pytest
from rich.console import Console

from datatalk.file_handler import (
    detect_excel_sheets,
    preview_sheet,
    display_sheet_preview,
    select_excel_sheet,
)
from datatalk.printer import Printer


def make_printer(quiet=False):
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    printer = Printer(console, quiet=quiet)
    return printer, buf


@pytest.fixture
def single_sheet_excel(tmp_path):
    """Excel file with one sheet."""
    path = tmp_path / "single.xlsx"
    df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
    df.to_excel(str(path), index=False, sheet_name="Data")
    return str(path)


@pytest.fixture
def multi_sheet_excel(tmp_path):
    """Excel file with multiple sheets."""
    path = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(str(path)) as writer:
        pd.DataFrame({"id": [1], "name": ["Alice"]}).to_excel(writer, sheet_name="Users", index=False)
        pd.DataFrame({"product": ["Widget"], "price": [9.99]}).to_excel(writer, sheet_name="Products", index=False)
        pd.DataFrame({"order_id": [100]}).to_excel(writer, sheet_name="Orders", index=False)
    return str(path)


# --- detect_excel_sheets ---


class TestDetectExcelSheets:
    def test_single_sheet(self, single_sheet_excel):
        sheets = detect_excel_sheets(single_sheet_excel)
        assert sheets == ["Data"]

    def test_multiple_sheets(self, multi_sheet_excel):
        sheets = detect_excel_sheets(multi_sheet_excel)
        assert sheets == ["Users", "Products", "Orders"]

    def test_returns_list(self, single_sheet_excel):
        result = detect_excel_sheets(single_sheet_excel)
        assert isinstance(result, list)


# --- preview_sheet ---


class TestPreviewSheet:
    def test_returns_dataframe(self, single_sheet_excel):
        df = preview_sheet(single_sheet_excel, "Data")
        assert isinstance(df, pd.DataFrame)

    def test_limited_rows(self, tmp_path):
        path = tmp_path / "big.xlsx"
        df = pd.DataFrame({"x": range(100)})
        df.to_excel(str(path), index=False)
        preview = preview_sheet(str(path), "Sheet1", max_rows=3)
        assert len(preview) == 3

    def test_returns_correct_columns(self, multi_sheet_excel):
        df = preview_sheet(multi_sheet_excel, "Products")
        assert "product" in df.columns
        assert "price" in df.columns


# --- display_sheet_preview ---


class TestDisplaySheetPreview:
    def test_displays_sheet_name(self):
        printer, buf = make_printer()
        df = pd.DataFrame({"col": [1, 2]})
        display_sheet_preview(printer, "MySheet", df)
        assert "MySheet" in buf.getvalue()

    def test_displays_data(self):
        printer, buf = make_printer()
        df = pd.DataFrame({"name": ["Alice"]})
        display_sheet_preview(printer, "Sheet1", df)
        assert "Alice" in buf.getvalue()

    def test_suppressed_when_quiet(self):
        printer, buf = make_printer(quiet=True)
        df = pd.DataFrame({"name": ["Alice"]})
        display_sheet_preview(printer, "Sheet1", df)
        assert buf.getvalue() == ""


# --- select_excel_sheet ---


class TestSelectExcelSheet:
    def test_single_sheet_returns_none(self, single_sheet_excel):
        printer, _ = make_printer()
        result = select_excel_sheet(single_sheet_excel, printer)
        assert result is None

    def test_multi_sheet_valid_selection(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", return_value="2"):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Products"

    def test_multi_sheet_first_selection(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", return_value="1"):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Users"

    def test_multi_sheet_last_selection(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", return_value="3"):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Orders"

    def test_eof_returns_first_sheet(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", side_effect=EOFError):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Users"

    def test_keyboard_interrupt_returns_first_sheet(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Users"

    def test_invalid_then_valid_input(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", side_effect=["abc", "0", "2"]):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Products"

    def test_empty_input_retries(self, multi_sheet_excel):
        printer, _ = make_printer()
        with patch("builtins.input", side_effect=["", "", "1"]):
            result = select_excel_sheet(multi_sheet_excel, printer)
        assert result == "Users"

    def test_shows_sheet_list(self, multi_sheet_excel):
        printer, buf = make_printer()
        with patch("builtins.input", return_value="1"):
            select_excel_sheet(multi_sheet_excel, printer)
        output = buf.getvalue()
        assert "Users" in output
        assert "Products" in output
        assert "Orders" in output
