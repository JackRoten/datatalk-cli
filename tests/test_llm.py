"""Unit tests for datatalk.llm module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from datatalk.llm import LiteLLMProvider


@pytest.fixture
def provider():
    return LiteLLMProvider("test-model")


# --- __init__ ---


class TestInit:
    def test_stores_model(self):
        p = LiteLLMProvider("gpt-4o")
        assert p.model == "gpt-4o"

    def test_different_models(self):
        p = LiteLLMProvider("ollama/llama3.1")
        assert p.model == "ollama/llama3.1"


# --- _clean_sql ---


class TestCleanSql:
    def test_plain_sql(self, provider):
        assert provider._clean_sql("SELECT * FROM events") == "SELECT * FROM events"

    def test_sql_in_code_block(self, provider):
        sql = "```sql\nSELECT * FROM events\n```"
        assert provider._clean_sql(sql) == "SELECT * FROM events"

    def test_sql_in_plain_code_block(self, provider):
        sql = "```\nSELECT * FROM events\n```"
        assert provider._clean_sql(sql) == "SELECT * FROM events"

    def test_sql_with_surrounding_text(self, provider):
        sql = "Here is the query:\n```sql\nSELECT COUNT(*) FROM events\n```\nThis returns the count."
        assert provider._clean_sql(sql) == "SELECT COUNT(*) FROM events"

    def test_strips_whitespace(self, provider):
        assert provider._clean_sql("  SELECT 1  ") == "SELECT 1"

    def test_multiline_sql_in_code_block(self, provider):
        sql = "```sql\nSELECT *\nFROM events\nWHERE id = 1\n```"
        result = provider._clean_sql(sql)
        assert "SELECT *" in result
        assert "WHERE id = 1" in result

    def test_code_block_no_language_tag_single_line(self, provider):
        sql = "```\nSELECT 1\n```"
        assert provider._clean_sql(sql) == "SELECT 1"

    def test_empty_code_block(self, provider):
        sql = "```\n```"
        # Edge case: empty code block
        result = provider._clean_sql(sql)
        assert result == ""


# --- _clean_litellm_error ---


class TestCleanLitellmError:
    def test_removes_litellm_prefix(self, provider):
        msg = "litellm.AuthenticationError: AuthenticationError: OpenAIException - The api_key is invalid"
        result = provider._clean_litellm_error(msg)
        assert "litellm" not in result.lower()

    def test_removes_exception_prefix(self, provider):
        msg = "OpenAIException - Connection refused"
        result = provider._clean_litellm_error(msg)
        assert "OpenAIException" not in result

    def test_preserves_meaningful_message(self, provider):
        msg = "litellm.RateLimitError: RateLimitError: AnthropicException - Rate limit exceeded"
        result = provider._clean_litellm_error(msg)
        assert "exceeded" in result.lower()

    def test_returns_original_if_cleaned_is_empty(self, provider):
        # If all text gets cleaned away, return original
        msg = "SomeError: "
        result = provider._clean_litellm_error(msg)
        # Should not be empty
        assert result

    def test_simple_error_passthrough(self, provider):
        msg = "Connection timeout after 30 seconds"
        result = provider._clean_litellm_error(msg)
        assert "timeout" in result.lower()


# --- to_sql ---


class TestToSql:
    @patch("datatalk.llm.litellm.completion")
    def test_calls_litellm_with_model(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "```sql\nSELECT * FROM events\n```"
        mock_completion.return_value = mock_response

        provider.to_sql("show all data", "id (INT), name (VARCHAR)")

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "test-model"

    @patch("datatalk.llm.litellm.completion")
    def test_returns_cleaned_sql(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "```sql\nSELECT COUNT(*) FROM events\n```"
        mock_completion.return_value = mock_response

        result = provider.to_sql("how many rows?", "id (INT)")
        assert result == "SELECT COUNT(*) FROM events"

    @patch("datatalk.llm.litellm.completion")
    def test_includes_schema_in_prompt(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "SELECT 1"
        mock_completion.return_value = mock_response

        provider.to_sql("test", "id (INT), name (VARCHAR)")

        call_kwargs = mock_completion.call_args[1]
        prompt = call_kwargs["messages"][0]["content"]
        assert "id (INT), name (VARCHAR)" in prompt

    @patch("datatalk.llm.litellm.completion")
    def test_includes_question_in_prompt(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "SELECT 1"
        mock_completion.return_value = mock_response

        provider.to_sql("what is the average price?", "price (DOUBLE)")

        prompt = mock_completion.call_args[1]["messages"][0]["content"]
        assert "what is the average price?" in prompt

    @patch("datatalk.llm.litellm.completion")
    def test_raises_on_none_content(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_completion.return_value = mock_response

        with pytest.raises(ValueError, match="No content returned"):
            provider.to_sql("test", "id (INT)")

    @patch("datatalk.llm.litellm.completion")
    def test_raises_cleaned_error_on_api_failure(self, mock_completion, provider):
        mock_completion.side_effect = Exception(
            "litellm.AuthenticationError: AuthenticationError: Invalid API key"
        )

        with pytest.raises(ValueError) as exc_info:
            provider.to_sql("test", "id (INT)")
        assert "litellm" not in str(exc_info.value).lower()

    @patch("datatalk.llm.litellm.completion")
    @patch.dict("os.environ", {"MODEL_TEMPERATURE": "0.5"})
    def test_uses_custom_temperature(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "SELECT 1"
        mock_completion.return_value = mock_response

        provider.to_sql("test", "id (INT)")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.5

    @patch("datatalk.llm.litellm.completion")
    def test_default_temperature(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "SELECT 1"
        mock_completion.return_value = mock_response

        # Ensure MODEL_TEMPERATURE is not set
        with patch.dict("os.environ", {}, clear=False):
            if "MODEL_TEMPERATURE" in os.environ:
                del os.environ["MODEL_TEMPERATURE"]
            provider.to_sql("test", "id (INT)")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.1

    @patch("datatalk.llm.litellm.completion")
    def test_max_tokens(self, mock_completion, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "SELECT 1"
        mock_completion.return_value = mock_response

        provider.to_sql("test", "id (INT)")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["max_tokens"] == 500
