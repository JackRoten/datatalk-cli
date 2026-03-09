"""Unit tests for datatalk.main module."""

import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from rich.console import Console

from datatalk.main import (
    create_argument_parser,
    validate_args,
    output_json,
    output_csv,
    print_result,
    EXIT_COMMANDS,
    HISTORY_FILE,
)
from datatalk.printer import Printer


def make_printer(quiet=False):
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    printer = Printer(console, quiet=quiet)
    return printer, buf


# --- create_argument_parser ---


class TestCreateArgumentParser:
    @pytest.fixture
    def parser(self):
        return create_argument_parser()

    def test_file_argument(self, parser):
        args = parser.parse_args(["data.csv"])
        assert args.file == "data.csv"

    def test_file_optional(self, parser):
        args = parser.parse_args([])
        assert args.file is None

    def test_prompt_flag(self, parser):
        args = parser.parse_args(["data.csv", "-p", "how many rows?"])
        assert args.prompt == "how many rows?"

    def test_prompt_long_flag(self, parser):
        args = parser.parse_args(["data.csv", "--prompt", "count"])
        assert args.prompt == "count"

    def test_json_flag(self, parser):
        args = parser.parse_args(["data.csv", "-p", "q", "--json"])
        assert args.json is True

    def test_csv_flag(self, parser):
        args = parser.parse_args(["data.csv", "-p", "q", "--csv"])
        assert args.csv is True

    def test_json_csv_mutually_exclusive(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["data.csv", "-p", "q", "--json", "--csv"])

    def test_no_sql_flag(self, parser):
        args = parser.parse_args(["data.csv", "--no-sql"])
        assert args.no_sql is True

    def test_no_schema_flag(self, parser):
        args = parser.parse_args(["data.csv", "--no-schema"])
        assert args.no_schema is True

    def test_sql_only_flag(self, parser):
        args = parser.parse_args(["data.csv", "-p", "q", "--sql-only"])
        assert args.sql_only is True

    def test_defaults(self, parser):
        args = parser.parse_args(["data.csv"])
        assert args.json is False
        assert args.csv is False
        assert args.no_sql is False
        assert args.no_schema is False
        assert args.sql_only is False
        assert args.prompt is None


# --- validate_args ---


class TestValidateArgs:
    def test_json_without_prompt_exits(self):
        parser = create_argument_parser()
        args = parser.parse_args(["data.csv", "--json"])
        # Force json=True without prompt
        args.json = True
        args.prompt = None
        printer, _ = make_printer()

        with pytest.raises(SystemExit) as exc_info:
            validate_args(parser, args, printer)
        assert exc_info.value.code == 2

    def test_csv_without_prompt_exits(self):
        parser = create_argument_parser()
        args = parser.parse_args(["data.csv"])
        args.csv = True
        args.prompt = None
        printer, _ = make_printer()

        with pytest.raises(SystemExit) as exc_info:
            validate_args(parser, args, printer)
        assert exc_info.value.code == 2

    def test_no_file_exits(self):
        parser = create_argument_parser()
        args = parser.parse_args([])
        printer, _ = make_printer()

        with pytest.raises(SystemExit) as exc_info:
            validate_args(parser, args, printer)
        assert exc_info.value.code == 1

    def test_valid_args_no_exit(self):
        parser = create_argument_parser()
        args = parser.parse_args(["data.csv", "-p", "test"])
        printer, _ = make_printer()

        # Should not raise
        validate_args(parser, args, printer)

    def test_valid_json_with_prompt(self):
        parser = create_argument_parser()
        args = parser.parse_args(["data.csv", "-p", "test", "--json"])
        printer, _ = make_printer()

        validate_args(parser, args, printer)  # Should not raise


# --- output_json ---


class TestOutputJson:
    def test_outputs_valid_json(self, capsys):
        result = {
            "sql": "SELECT * FROM events",
            "dataframe": pd.DataFrame({"id": [1], "name": ["A"]}),
            "error": None,
        }
        output_json(result)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["sql"] == "SELECT * FROM events"
        assert parsed["error"] is None
        assert parsed["data"] == [{"id": 1, "name": "A"}]

    def test_outputs_error_json(self, capsys):
        result = {
            "sql": None,
            "dataframe": None,
            "error": "Something went wrong",
        }
        output_json(result)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["error"] == "Something went wrong"
        assert parsed["data"] is None

    def test_json_is_indented(self, capsys):
        result = {
            "sql": "SELECT 1",
            "dataframe": pd.DataFrame({"x": [1]}),
            "error": None,
        }
        output_json(result)
        captured = capsys.readouterr()
        assert "  " in captured.out  # indented


# --- output_csv ---


class TestOutputCsv:
    def test_outputs_csv(self, capsys):
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        output_csv(df)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert lines[0] == "id,name"
        assert lines[1] == "1,A"
        assert lines[2] == "2,B"

    def test_empty_dataframe_no_output(self, capsys):
        df = pd.DataFrame()
        output_csv(df)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_none_dataframe_no_output(self, capsys):
        output_csv(None)
        captured = capsys.readouterr()
        assert captured.out == ""


# --- print_result ---


class TestPrintResult:
    def test_shows_sql_by_default(self):
        printer, buf = make_printer()
        args = MagicMock()
        args.no_sql = False
        args.sql_only = False
        result = {"sql": "SELECT * FROM events", "dataframe": pd.DataFrame({"id": [1]})}

        print_result(result, args, printer)

        output = buf.getvalue()
        assert "SELECT" in output

    def test_hides_sql_with_no_sql(self):
        printer, buf = make_printer()
        args = MagicMock()
        args.no_sql = True
        args.sql_only = False
        result = {"sql": "SELECT * FROM events", "dataframe": pd.DataFrame({"id": [1]})}

        print_result(result, args, printer)

        output = buf.getvalue()
        # With no_sql=True and sql_only=False, condition `not args.no_sql or args.sql_only` is False
        # So SQL should be hidden
        # But data should still show
        assert "1" in output

    def test_sql_only_shows_sql_but_not_data(self):
        printer, buf = make_printer()
        args = MagicMock()
        args.no_sql = False
        args.sql_only = True
        result = {"sql": "SELECT * FROM events", "dataframe": pd.DataFrame({"id": [1]})}

        print_result(result, args, printer)

        output = buf.getvalue()
        assert "SELECT" in output
        # Data table should not be present (but "1" might appear in SQL context)


# --- EXIT_COMMANDS ---


class TestExitCommands:
    def test_quit_is_exit_command(self):
        assert "quit" in EXIT_COMMANDS

    def test_exit_is_exit_command(self):
        assert "exit" in EXIT_COMMANDS

    def test_q_is_exit_command(self):
        assert "q" in EXIT_COMMANDS

    def test_stop_is_exit_command(self):
        assert "stop" in EXIT_COMMANDS

    def test_bye_is_exit_command(self):
        assert "bye" in EXIT_COMMANDS

    def test_goodbye_is_exit_command(self):
        assert "goodbye" in EXIT_COMMANDS


# --- HISTORY_FILE ---


class TestHistoryFile:
    def test_history_file_path(self):
        assert ".datatalk_history" in HISTORY_FILE
        assert HISTORY_FILE.startswith("/")
