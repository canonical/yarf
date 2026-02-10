from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from yarf.rf_libraries.libraries.llm_client.LlmClient import LlmClient


@pytest.fixture(autouse=True)
def mock_post():
    with patch(
        "yarf.rf_libraries.libraries.llm_client.LlmClient.requests.post"
    ) as p:
        yield p


@pytest.fixture(autouse=True)
def mock_logger():
    with patch("yarf.rf_libraries.libraries.llm_client.LlmClient.logger") as p:
        yield p


class TestLlmClient:
    def _mock_response(
        self, content: str = "ok", reasoning: str | None = None
    ) -> MagicMock:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        json_data = {"choices": [{"message": {"content": content}}]}
        if reasoning:
            json_data["choices"][0]["message"]["reasoning"] = reasoning
        resp.json = MagicMock(return_value=json_data)
        return resp

    def test_configure_llm_client_valid(self):
        client = LlmClient()
        client.configure_llm_client(
            model="custom-model",
            server_url="http://example.com",
            endpoint="/custom/endpoint",
            max_tokens=1000,
        )
        assert client.model == "custom-model"
        assert client.server_url == "http://example.com"
        assert client.endpoint == "/custom/endpoint"
        assert client.max_tokens == 1000

    def test_configure_llm_client_unknown_param(self):
        client = LlmClient()
        with pytest.raises(TypeError) as exc:
            client.configure_llm_client(unknown_param="value")
        assert "Unknown argument(s): unknown_param" in str(exc.value)

    def test_configure_llm_client_invalid_type(self):
        client = LlmClient()
        with pytest.raises(ValueError) as exc:
            client.configure_llm_client(max_tokens="not_an_int")
        assert (
            "Invalid value for max_tokens: not_an_int. Expected type int"
            in str(exc.value)
        )

    def test_prompt_text_without_system_prompt(self, mock_post):
        mock_client = MagicMock()
        mock_post.return_value = self._mock_response("hello")

        result = LlmClient.prompt_llm(mock_client, "Say hi")

        assert result == "hello"
        mock_post.assert_called_once()

        # Validate request arguments
        _, kwargs = mock_post.call_args
        assert kwargs["headers"] == {"Content-Type": "application/json"}
        assert kwargs["json"]["model"] == mock_client.model
        assert kwargs["json"]["max_tokens"] == mock_client.max_tokens

        messages = kwargs["json"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == [{"type": "text", "text": "Say hi"}]

        # Ensure status check is executed
        mock_post.return_value.raise_for_status.assert_called_once()

    def test_prompt_text_with_system_prompt(self, mock_post):
        mock_client = MagicMock()
        mock_post.return_value = self._mock_response("hello")

        result = LlmClient.prompt_llm(
            mock_client, "Say hi", system_prompt="You are a helpful assistant."
        )

        assert result == "hello"
        mock_post.assert_called_once()

        # Validate request arguments
        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == [{"type": "text", "text": "Say hi"}]

    def test_prompt_with_image(self, mock_post):
        mock_client = MagicMock()
        mock_post.return_value = self._mock_response("hello")

        image = Image.new("RGB", (10, 10))
        result = LlmClient.prompt_llm(
            mock_client, "Describe the image", image=image
        )

        assert result == "hello"
        mock_post.assert_called_once()

        # Validate request arguments
        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Describe the image"
        assert content[1]["type"] == "image_url"

        assert content[1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )

    def test_prompt_with_reasoning(self, mock_post):
        mock_client = MagicMock()
        mock_post.return_value = self._mock_response(
            "hello", reasoning="This is the reasoning behind the answer."
        )

        with patch(
            "yarf.rf_libraries.libraries.llm_client.LlmClient.logger"
        ) as mock_logger:
            result = LlmClient.prompt_llm(mock_client, "Ask with reasoning")

            assert result == "hello"
            mock_logger.info.assert_called_once_with(
                "This is the reasoning behind the answer."
            )

    def test_encode_image(self):
        mock_client = MagicMock()
        image = Image.new("RGB", (10, 10))
        encoded = LlmClient._encode_image(mock_client, image)
        assert encoded.startswith("data:image/png;base64,")
