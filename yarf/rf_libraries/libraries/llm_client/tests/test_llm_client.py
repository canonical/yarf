import json
from unittest.mock import AsyncMock, MagicMock, patch

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

    @pytest.mark.parametrize(
        "kwargs, exc_type, match",
        [
            (
                {"unknown_param": "value"},
                TypeError,
                "Unknown argument\\(s\\): unknown_param",
            ),
            (
                {"max_tokens": "not_an_int"},
                ValueError,
                "Invalid value for max_tokens: not_an_int. Expected type int",
            ),
        ],
    )
    def test_configure_llm_client_error(self, kwargs, exc_type, match):
        client = LlmClient()
        with pytest.raises(exc_type, match=match):
            client.configure_llm_client(**kwargs)

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

    def test_get_lib_instance(self):
        client = LlmClient()
        sentinel = object()
        with patch(
            "yarf.rf_libraries.libraries.llm_client.LlmClient.BuiltIn"
        ) as mock_builtin_cls:
            mock_builtin_cls.return_value.get_library_instance.return_value = (
                sentinel
            )
            result = client._get_lib_instance("VideoInput")

        mock_builtin_cls.return_value.get_library_instance.assert_called_once_with(
            "VideoInput"
        )
        assert result is sentinel

    VALID_RESPONSE = json.dumps(
        {
            "corrupted": True,
            "description": "noise in top-left corner",
            "votes": 7,
        }
    )

    @pytest.mark.asyncio
    async def test_valid_response(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with patch(
            "yarf.rf_libraries.libraries.llm_client.LlmClient"
            ".asyncio.to_thread",
            return_value=self.VALID_RESPONSE,
        ):
            result = await client.detect_corrupted_image(image=image)

        assert result["corrupted"] is True
        assert result["description"] == "noise in top-left corner"
        assert result["votes"] == 7

    @pytest.mark.asyncio
    async def test_custom_prompt(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with patch(
            "yarf.rf_libraries.libraries.llm_client.LlmClient"
            ".asyncio.to_thread",
            return_value=self.VALID_RESPONSE,
        ) as mock_thread:
            await client.detect_corrupted_image(
                image=image, custom_prompt="Is this broken?"
            )

        mock_thread.assert_called_once()
        assert mock_thread.call_args.kwargs["prompt"] == ("Is this broken?")

    @pytest.mark.asyncio
    async def test_grabs_screenshot_when_no_image(self, mock_post):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        mock_video = MagicMock()
        mock_video.grab_screenshot = AsyncMock(return_value=screenshot)

        with (
            patch.object(
                client,
                "_get_lib_instance",
                return_value=mock_video,
            ),
            patch(
                "yarf.rf_libraries.libraries.llm_client.LlmClient"
                ".asyncio.to_thread",
                return_value=self.VALID_RESPONSE,
            ),
        ):
            result = await client.detect_corrupted_image()

        assert result["corrupted"] is True
        mock_video.grab_screenshot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_screenshot_fails(self, mock_post):
        client = LlmClient()

        mock_video = MagicMock()
        mock_video.grab_screenshot = AsyncMock(return_value=None)

        with (
            patch.object(
                client,
                "_get_lib_instance",
                return_value=mock_video,
            ),
            pytest.raises(ValueError, match="Failed to grab screenshot"),
        ):
            await client.detect_corrupted_image()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_json(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch(
                "yarf.rf_libraries.libraries.llm_client.LlmClient"
                ".asyncio.to_thread",
                return_value="not json at all",
            ),
            pytest.raises(ValueError, match="Failed to parse LLM response"),
        ):
            await client.detect_corrupted_image(image=image)

    @pytest.mark.asyncio
    async def test_raises_on_non_dict_json(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch(
                "yarf.rf_libraries.libraries.llm_client.LlmClient"
                ".asyncio.to_thread",
                return_value=json.dumps([1, 2, 3]),
            ),
            pytest.raises(ValueError, match="non-dict JSON response"),
        ):
            await client.detect_corrupted_image(image=image)

    @pytest.mark.asyncio
    async def test_raises_on_missing_keys(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch(
                "yarf.rf_libraries.libraries.llm_client.LlmClient"
                ".asyncio.to_thread",
                return_value=json.dumps({"corrupted": True}),
            ),
            pytest.raises(ValueError, match="missing keys"),
        ):
            await client.detect_corrupted_image(image=image)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_response, match",
        [
            (
                {"corrupted": "yes", "description": "x", "votes": 1},
                "invalid type for 'corrupted'",
            ),
            (
                {"corrupted": True, "description": 123, "votes": 1},
                "invalid type for 'description'",
            ),
            (
                {"corrupted": True, "description": "x", "votes": "a"},
                "invalid type for 'votes'",
            ),
        ],
    )
    async def test_raises_on_wrong_value_type(
        self, mock_post, bad_response, match
    ):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch(
                "yarf.rf_libraries.libraries.llm_client.LlmClient"
                ".asyncio.to_thread",
                return_value=json.dumps(bad_response),
            ),
            pytest.raises(ValueError, match=match),
        ):
            await client.detect_corrupted_image(image=image)
