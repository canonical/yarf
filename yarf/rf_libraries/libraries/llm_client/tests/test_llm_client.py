import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from yarf.errors.yarf_errors import VQADetectionError, VQAValidationError
from yarf.rf_libraries.libraries.llm_client.LlmClient import (
    HistoryItem,
    LlmClient,
)


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
    LLM_PATH = "yarf.rf_libraries.libraries.llm_client.LlmClient"

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

        get_library_instance = (
            mock_builtin_cls.return_value.get_library_instance
        )
        get_library_instance.assert_called_once_with("VideoInput")
        assert result is sentinel

    @pytest.mark.asyncio
    async def test_grab_screenshot(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        mock_video = MagicMock()
        mock_video.grab_screenshot = AsyncMock(return_value=screenshot)

        with patch.object(
            client,
            "_get_lib_instance",
            return_value=mock_video,
        ):
            result = await client._grab_screenshot()

        assert result is screenshot
        mock_video.grab_screenshot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_grab_screenshot_raises_when_screenshot_fails(self):
        client = LlmClient()

        mock_video = MagicMock()
        mock_video.grab_screenshot = AsyncMock(return_value=None)

        with (
            patch.object(
                client,
                "_get_lib_instance",
                return_value=mock_video,
            ),
            pytest.raises(RuntimeError, match="Failed to grab screenshot"),
        ):
            await client._grab_screenshot()

    VALID_RESPONSE = json.dumps(
        {
            "corrupted": False,
            "description": "image looks normal",
        }
    )

    CORRUPTED_RESPONSE = json.dumps(
        {
            "corrupted": True,
            "description": "noise in top-left corner",
        }
    )

    OBJECT_FOUND_RESPONSE = json.dumps({"point_2d": [250, 500]})
    OBJECT_NOT_FOUND_RESPONSE = json.dumps({"point_2d": None})
    STATE_MATCH_RESPONSE = json.dumps(
        {"matches_description": True, "reasoning": "state is present"}
    )
    STATE_MISMATCH_RESPONSE = json.dumps(
        {"matches_description": False, "reasoning": "state is absent"}
    )
    CLICK_ACTION_RESPONSE = json.dumps(
        {
            "action_type": "Left Click",
            "text": None,
            "point_2d": [250, 500],
        }
    )
    WRITE_ACTION_RESPONSE = json.dumps(
        {
            "action_type": "Write",
            "text": "hello",
            "point_2d": None,
        }
    )
    WAIT_ACTION_RESPONSE = json.dumps(
        {
            "action_type": "Wait",
            "text": None,
            "point_2d": None,
        }
    )
    FINISH_ACTION_RESPONSE = json.dumps(
        {
            "description": "Task is complete",
            "action_type": "Finish",
            "text": None,
            "point_2d": None,
        }
    )

    @pytest.mark.asyncio
    async def test_valid_response(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        # LLM returns valid response on first try
        with patch.object(
            client, "prompt_llm", return_value=self.VALID_RESPONSE
        ):
            result = await client.check_for_visual_corruption(
                image=image,
            )

        assert result["corrupted"] is False
        assert result["description"] == "image looks normal"

    @pytest.mark.asyncio
    async def test_raises_on_corrupted_image(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        # LLM detects corruption
        with (
            patch.object(
                client, "prompt_llm", return_value=self.CORRUPTED_RESPONSE
            ),
            pytest.raises(VQAValidationError, match="Image is corrupted"),
        ):
            await client.check_for_visual_corruption(image=image)

    @pytest.mark.asyncio
    async def test_custom_prompt(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        # LLM returns valid response to custom prompt
        with patch.object(
            client, "prompt_llm", return_value=self.VALID_RESPONSE
        ) as mock_prompt:
            result = await client.check_for_visual_corruption(
                image=image, custom_prompt="Is this broken?"
            )

        mock_prompt.assert_called_once()
        assert mock_prompt.call_args.kwargs["prompt"] == "Is this broken?"
        assert result["corrupted"] is False

    @pytest.mark.asyncio
    async def test_grabs_screenshot_when_no_image(self, mock_post):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        # LLM returns valid response for grabbed screenshot
        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as mock_grab,
            patch.object(
                client, "prompt_llm", return_value=self.VALID_RESPONSE
            ),
        ):
            result = await client.check_for_visual_corruption()

        assert result["corrupted"] is False
        mock_grab.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_screenshot_fails(self, mock_post):
        client = LlmClient()
        exc = RuntimeError("Failed to grab screenshot")

        # LLM check raises error when screenshot cannot be grabbed
        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(side_effect=exc),
            ),
            pytest.raises(RuntimeError, match="Failed to grab screenshot"),
        ):
            await client.check_for_visual_corruption()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_json(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        # LLM returns invalid JSON
        with (
            patch.object(client, "prompt_llm", return_value="not json at all"),
            pytest.raises(
                RuntimeError,
                match="could not be validated even after correction",
            ),
        ):
            await client.check_for_visual_corruption(image=image)

    @pytest.mark.asyncio
    async def test_retries_on_wrong_type(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))
        bad = json.dumps({"corrupted": "yes", "description": "ok"})

        # LLM returns wrong type for 'corrupted' key, then corrects on retry
        with patch.object(
            client, "prompt_llm", side_effect=[bad, self.VALID_RESPONSE]
        ) as mock_prompt:
            result = await client.check_for_visual_corruption(image=image)

        assert mock_prompt.call_count == 2
        assert result["corrupted"] is False
        assert result["description"] == "image looks normal"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_response",
        [
            {"corrupted": "yes", "description": "x"},
            {"corrupted": True, "description": 123},
        ],
    )
    async def test_retries_on_wrong_value_type(self, mock_post, bad_response):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        # LLM returns wrong value type, then corrects on retry
        with patch.object(
            client,
            "prompt_llm",
            side_effect=[json.dumps(bad_response), self.VALID_RESPONSE],
        ) as mock_prompt:
            result = await client.check_for_visual_corruption(image=image)

        assert mock_prompt.call_count == 2
        assert result["corrupted"] is False

    @pytest.mark.asyncio
    async def test_raises_after_retry_fails(self, mock_post):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))
        bad = json.dumps({"corrupted": "yes", "description": "ok"})

        # LLM returns fails twice, leading to error
        with (
            patch.object(
                client, "prompt_llm", side_effect=[bad, bad]
            ) as mock_prompt,
            pytest.raises(
                RuntimeError,
                match="could not be validated even after correction",
            ),
        ):
            await client.check_for_visual_corruption(image=image)

        assert mock_prompt.call_count == 2

    @pytest.mark.asyncio
    async def test_verify_llm_json_valid(self):
        client = LlmClient()
        raw = json.dumps({"corrupted": True, "description": "ok"})
        parsed = await client._verify_llm_json_response(
            raw,
            {"corrupted": bool, "description": str},
        )
        assert parsed == {"corrupted": True, "description": "ok"}

    @pytest.mark.asyncio
    async def test_verify_llm_json_corrects_missing_keys(self):
        client = LlmClient()
        raw = json.dumps({"corrupted": True})

        # LLM returns missing keys, then corrects on retry
        with patch.object(
            client, "prompt_llm", return_value=self.VALID_RESPONSE
        ) as mock_prompt:
            parsed = await client._verify_llm_json_response(
                raw,
                {"corrupted": bool, "description": str},
            )

        mock_prompt.assert_called_once()
        assert parsed == {
            "corrupted": False,
            "description": "image looks normal",
        }

    @pytest.mark.asyncio
    async def test_verify_llm_json_corrects_wrong_type(self):
        client = LlmClient()
        raw = json.dumps({"corrupted": "yes", "description": "ok"})

        # LLM returns wrong type for 'corrupted' key, then corrects on retry
        with patch.object(
            client, "prompt_llm", return_value=self.VALID_RESPONSE
        ) as mock_prompt:
            parsed = await client._verify_llm_json_response(
                raw,
                {"corrupted": bool, "description": str},
            )

        mock_prompt.assert_called_once()
        assert parsed == {
            "corrupted": False,
            "description": "image looks normal",
        }

    @pytest.mark.asyncio
    async def test_verify_llm_json_no_braces(self):
        client = LlmClient()

        # LLM returns invalid JSON without braces, then fails on retry
        with (
            patch.object(client, "prompt_llm", return_value="still not json"),
            pytest.raises(
                RuntimeError,
                match="could not be validated even after correction",
            ),
        ):
            await client._verify_llm_json_response(
                "not json",
                {"corrupted": bool},
            )

    @pytest.mark.asyncio
    async def test_verify_llm_json_parse_error(self):
        client = LlmClient()

        # LLM returns invalid JSON with parse error, then fails on retry
        with (
            patch.object(
                client, "prompt_llm", return_value="{still not json}"
            ),
            pytest.raises(
                RuntimeError,
                match="could not be validated even after correction",
            ),
        ):
            await client._verify_llm_json_response(
                "{not json}",
                {"corrupted": bool},
            )

    @pytest.mark.asyncio
    async def test_verify_llm_json_extracts_from_text(self):
        client = LlmClient()
        raw = 'Here is the result: {"corrupted": false, "description": "ok"}'

        # LLM returns valid JSON embedded in text
        parsed = await client._verify_llm_json_response(
            raw,
            {"corrupted": bool, "description": str},
        )
        assert parsed == {"corrupted": False, "description": "ok"}

    def test_parse_llm_json_missing_keys(self):
        client = LlmClient()
        raw = json.dumps({"corrupted": True})
        _parsed, errors = client._parse_llm_json_response(
            raw,
            {"corrupted": bool, "description": str},
        )
        assert "missing keys" in errors

    def test_parse_llm_json_wrong_type(self):
        client = LlmClient()
        raw = json.dumps({"corrupted": "yes", "description": "ok"})
        _parsed, errors = client._parse_llm_json_response(
            raw,
            {"corrupted": bool, "description": str},
        )
        assert "invalid type for 'corrupted'" in errors

    def test_parse_llm_json_no_braces(self):
        client = LlmClient()
        _parsed, errors = client._parse_llm_json_response(
            "not json",
            {"corrupted": bool},
        )
        assert "does not contain valid JSON" in errors

    def test_parse_llm_json_parse_error(self):
        client = LlmClient()
        _parsed, errors = client._parse_llm_json_response(
            "{not json}",
            {"corrupted": bool},
        )
        assert "Failed to parse LLM response" in errors

    @pytest.mark.asyncio
    @patch(f"{LLM_PATH}.log_image", MagicMock())
    @patch(f"{LLM_PATH}.draw_point_on_image", MagicMock())
    async def test_get_object_position_returns_point(self):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with patch.object(
            client,
            "prompt_llm",
            return_value=self.OBJECT_FOUND_RESPONSE,
        ) as mock_prompt:
            point = await client.get_object_position("the OK button", image)

        assert point == [0.25, 0.5]
        mock_prompt.assert_called_once()
        assert mock_prompt.call_args.kwargs["image"] is image
        assert mock_prompt.call_args.kwargs["prompt"] == (
            "Find the position of this object: the OK button"
        )

    @pytest.mark.asyncio
    async def test_get_object_position_raises_when_object_not_found(self):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "prompt_llm",
                return_value=self.OBJECT_NOT_FOUND_RESPONSE,
            ),
            pytest.raises(
                VQADetectionError,
                match="Object was not found: missing thing",
            ),
        ):
            await client.get_object_position("missing thing", image)

    @pytest.mark.asyncio
    async def test_get_object_position_grabs_screenshot_when_no_image(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as mock_grab,
            patch.object(
                client,
                "prompt_llm",
                return_value=self.OBJECT_FOUND_RESPONSE,
            ) as mock_prompt,
        ):
            point = await client.get_object_position("the OK button")

        assert point == [0.25, 0.5]
        assert mock_prompt.call_args.kwargs["image"] is screenshot
        mock_grab.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_object_position_raises_when_screenshot_fails(self):
        client = LlmClient()
        exc = RuntimeError("Failed to grab screenshot")

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(side_effect=exc),
            ),
            pytest.raises(RuntimeError, match="Failed to grab screenshot"),
        ):
            await client.get_object_position("the OK button")

    @pytest.mark.asyncio
    @patch(f"{LLM_PATH}.log_image")
    @patch(f"{LLM_PATH}.draw_point_on_image")
    async def test_get_object_position_logs_point_in_debug_mode(
        self, mock_draw_image, mock_log_image
    ):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))
        annotated = Image.new("RGB", (10, 10))

        mock_draw_image.return_value = annotated
        with (
            patch.dict("os.environ", {"YARF_LOG_LEVEL": "DEBUG"}),
            patch.object(
                client,
                "prompt_llm",
                return_value=self.OBJECT_FOUND_RESPONSE,
            ),
        ):
            point = await client.get_object_position("the OK button", image)

        assert point == [0.25, 0.5]
        mock_draw_image.assert_called_once_with(
            image,
            [0.25, 0.5],
            label="the OK button",
        )
        mock_log_image.assert_called_once_with(
            annotated,
            "LLM indicated point for: the OK button",
        )

    @pytest.mark.asyncio
    async def test_assert_state_passes_when_state_matches(self):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with patch.object(
            client,
            "prompt_llm",
            return_value=self.STATE_MATCH_RESPONSE,
        ) as mock_prompt:
            result = await client.assert_state("desktop is visible", image)

        assert result is None
        mock_prompt.assert_called_once()
        assert mock_prompt.call_args.kwargs["image"] is image
        assert mock_prompt.call_args.kwargs["prompt"] == (
            "Check if this state is present on the screen: desktop is visible"
        )

    @pytest.mark.asyncio
    async def test_assert_state_raises_when_state_does_not_match(self):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "prompt_llm",
                return_value=self.STATE_MISMATCH_RESPONSE,
            ),
            pytest.raises(
                AssertionError,
                match=(
                    "State does NOT match description: desktop is visible. "
                    "Reasoning: state is absent"
                ),
            ),
        ):
            await client.assert_state("desktop is visible", image)

    @pytest.mark.asyncio
    async def test_assert_state_grabs_screenshot_when_no_image(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as mock_grab,
            patch.object(
                client,
                "prompt_llm",
                return_value=self.STATE_MATCH_RESPONSE,
            ) as mock_prompt,
        ):
            await client.assert_state("desktop is visible")

        assert mock_prompt.call_args.kwargs["image"] is screenshot
        mock_grab.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assert_state_raises_when_screenshot_fails(self):
        client = LlmClient()
        exc = RuntimeError("Failed to grab screenshot")

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(side_effect=exc),
            ),
            pytest.raises(RuntimeError, match="Failed to grab screenshot"),
        ):
            await client.assert_state("desktop is visible")

    @pytest.mark.asyncio
    async def test_assert_state_uses_custom_system_prompt(self):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with patch.object(
            client,
            "prompt_llm",
            return_value=self.STATE_MATCH_RESPONSE,
        ) as mock_prompt:
            await client.assert_state(
                "desktop is visible",
                image,
                custom_system_prompt="Only answer JSON.",
            )

        assert mock_prompt.call_args.kwargs["system_prompt"] == (
            "Only answer JSON."
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "task, response_attr, expected_action",
        [
            (
                "click OK",
                "CLICK_ACTION_RESPONSE",
                {
                    "action_type": "Left Click",
                    "text": None,
                    "point_2d": [250, 500],
                },
            ),
            (
                "type hello",
                "WRITE_ACTION_RESPONSE",
                {
                    "action_type": "Write",
                    "text": "hello",
                    "point_2d": None,
                },
            ),
            (
                "wait",
                "WAIT_ACTION_RESPONSE",
                {
                    "action_type": "Wait",
                    "text": None,
                    "point_2d": None,
                },
            ),
        ],
    )
    async def test_get_single_gui_action_returns_action(
        self, task, response_attr, expected_action
    ):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch(f"{self.LLM_PATH}.log_image"),
            patch(f"{self.LLM_PATH}.draw_point_on_image"),
            patch.object(
                client,
                "prompt_llm",
                return_value=getattr(self, response_attr),
            ) as mock_prompt,
        ):
            action = await client.get_single_gui_action(task, image)

        assert action == expected_action
        mock_prompt.assert_called_once()
        assert mock_prompt.call_args.kwargs["image"] is image
        assert mock_prompt.call_args.kwargs["prompt"] == task

    @pytest.mark.asyncio
    async def test_get_single_gui_action_returns_write_action(self):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with patch.object(
            client,
            "prompt_llm",
            return_value=self.WRITE_ACTION_RESPONSE,
        ):
            action = await client.get_single_gui_action("type hello", image)

        assert action == {
            "action_type": "Write",
            "text": "hello",
            "point_2d": None,
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "task, response, expected_error",
        [
            (
                "type hello",
                {
                    "action_type": "Write",
                    "text": None,
                    "point_2d": None,
                },
                "Write actions must include text.",
            ),
            (
                "fail the task",
                {
                    "action_type": "Failed",
                    "text": None,
                    "point_2d": None,
                },
                "LLM indicated action can't be completed: fail the task",
            ),
            (
                "click OK",
                {
                    "action_type": "Left Click",
                    "text": None,
                    "point_2d": None,
                },
                "Left Click actions must include a point.",
            ),
        ],
    )
    async def test_get_single_gui_action_rejects_invalid_action(
        self, task, response, expected_error
    ):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "prompt_llm",
                return_value=json.dumps(response),
            ),
            pytest.raises(ValueError, match=expected_error),
        ):
            await client.get_single_gui_action(task, image)

    @pytest.mark.asyncio
    async def test_get_single_gui_action_grabs_screenshot_when_no_image(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as mock_grab,
            patch.object(
                client,
                "prompt_llm",
                return_value=self.CLICK_ACTION_RESPONSE,
            ) as mock_prompt,
        ):
            action = await client.get_single_gui_action("click OK")

        assert action["point_2d"] == [250, 500]
        assert mock_prompt.call_args.kwargs["image"] is screenshot
        mock_grab.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "task, response_attr",
        [
            ("click OK", "CLICK_ACTION_RESPONSE"),
            ("type hello", "WRITE_ACTION_RESPONSE"),
        ],
    )
    async def test_get_single_gui_action_logs_screenshot_in_debug(
        self, task, response_attr
    ):
        client = LlmClient()
        image = Image.new("RGB", (10, 10))

        with (
            patch.dict("os.environ", {"YARF_LOG_LEVEL": "DEBUG"}),
            patch(f"{self.LLM_PATH}.log_image") as mock_log_image,
            patch(f"{self.LLM_PATH}.draw_point_on_image") as mock_draw_point,
            patch.object(
                client,
                "prompt_llm",
                return_value=getattr(self, response_attr),
            ),
        ):
            await client.get_single_gui_action(task, image)

        mock_draw_point.assert_not_called()
        mock_log_image.assert_called_once_with(
            image,
            msg="Screenshot provided to LLM for GUI action decision",
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "action_type, expected_buttons",
        [
            ("Left Click", ["LEFT"]),
            ("Right Click", ["RIGHT"]),
            ("Double Click", ["LEFT", "LEFT"]),
        ],
    )
    async def test_execute_gui_action_pointer_actions(
        self, action_type, expected_buttons
    ):
        client = LlmClient()
        mock_hid = MagicMock()
        mock_hid.move_pointer_to_proportional = AsyncMock()
        mock_hid.click_pointer_button = AsyncMock()

        with (
            patch.object(client, "_get_lib_instance", return_value=mock_hid),
            patch(f"{self.LLM_PATH}.asyncio.sleep", AsyncMock()),
        ):
            await client.execute_gui_action(
                {
                    "action_type": action_type,
                    "text": None,
                    "point_2d": [250, 500],
                }
            )

        mock_hid.move_pointer_to_proportional.assert_awaited_once_with(
            0.25, 0.5
        )
        click_args = mock_hid.click_pointer_button.await_args_list
        assert [call.args[0] for call in click_args] == expected_buttons

    @pytest.mark.asyncio
    async def test_execute_gui_action_writes_text(self):
        client = LlmClient()
        mock_hid = MagicMock()
        mock_hid.type_string = AsyncMock()

        with patch.object(client, "_get_lib_instance", return_value=mock_hid):
            await client.execute_gui_action(
                {
                    "action_type": "Write",
                    "text": "hello",
                    "point_2d": None,
                }
            )

        mock_hid.type_string.assert_awaited_once_with("hello")

    @pytest.mark.asyncio
    async def test_execute_gui_action_waits(self):
        client = LlmClient()

        with patch(f"{self.LLM_PATH}.asyncio.sleep", AsyncMock()) as sleep:
            await client.execute_gui_action(
                {
                    "action_type": "Wait",
                    "text": None,
                    "point_2d": None,
                }
            )

        sleep.assert_awaited_once_with(5)

    @pytest.mark.asyncio
    async def test_execute_gui_action_rejects_unsupported_action_defensively(
        self,
    ):
        client = LlmClient()

        with (
            patch.object(client, "validate_gui_action"),
            pytest.raises(
                ValueError,
                match="Unsupported GUI action: Unsupported",
            ),
        ):
            await client.execute_gui_action(
                {
                    "action_type": "Unsupported",
                    "text": None,
                    "point_2d": None,
                }
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "action, expected_error",
        [
            (
                {
                    "action_type": "Write",
                    "text": None,
                    "point_2d": None,
                },
                "Write actions must include text.",
            ),
            (
                {
                    "action_type": "Finish",
                    "text": None,
                    "point_2d": None,
                },
                "Unsupported GUI action: Finish",
            ),
        ],
    )
    async def test_execute_gui_action_rejects_invalid_action(
        self, action, expected_error
    ):
        client = LlmClient()
        mock_hid = MagicMock()

        with (
            patch.object(client, "_get_lib_instance", return_value=mock_hid),
            pytest.raises(ValueError, match=expected_error),
        ):
            await client.execute_gui_action(action)

    @pytest.mark.asyncio
    async def test_execute_gui_action_logs_screenshot_in_debug(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))
        annotated = Image.new("RGB", (10, 10))
        mock_hid = MagicMock()
        mock_hid.move_pointer_to_proportional = AsyncMock()
        mock_hid.click_pointer_button = AsyncMock()
        mock_video = MagicMock()
        mock_video.grab_screenshot = AsyncMock(return_value=screenshot)

        def get_library(name):
            return {"HID": mock_hid, "VideoInput": mock_video}[name]

        with (
            patch.dict("os.environ", {"YARF_LOG_LEVEL": "DEBUG"}),
            patch.object(
                client,
                "_get_lib_instance",
                side_effect=get_library,
            ),
            patch(f"{self.LLM_PATH}.asyncio.sleep", AsyncMock()),
            patch(
                f"{self.LLM_PATH}.draw_point_on_image",
                return_value=annotated,
            ) as mock_draw_point,
            patch(f"{self.LLM_PATH}.log_image") as mock_log_image,
        ):
            await client.execute_gui_action(
                {
                    "action_type": "Left Click",
                    "text": None,
                    "point_2d": [250, 500],
                }
            )

        assert mock_video.grab_screenshot.await_count == 2
        mock_draw_point.assert_called_once_with(
            screenshot,
            [0.25, 0.5],
            label="Left Click",
        )
        mock_log_image.assert_any_call(
            annotated,
            "LLM indicated action point for: Left Click",
        )
        mock_log_image.assert_any_call(
            image=screenshot,
            msg="Screenshot after executing action",
        )

    def test_history_item_stringifies_action_with_step(self):
        item = HistoryItem(
            step=2,
            action={"action_type": "Wait", "point_2d": None},
        )

        assert str(item) == (
            'Step 2:\n{\n  "action_type": "Wait",\n'
            '  "point_2d": null\n}'
        )

    @pytest.mark.asyncio
    async def test_multiple_step_action_stops_on_finish(self):
        client = LlmClient()
        history_item = HistoryItem(
            step=1,
            action={
                "description": "Task is complete",
                "action_type": "Finish",
                "text": None,
                "point_2d": None,
            },
        )

        with patch.object(
            client,
            "_run_step",
            AsyncMock(return_value=history_item),
        ) as run_step:
            await client.multiple_step_action(
                "open settings",
                custom_system_prompt="Custom prompt",
                max_steps=3,
            )

        run_step.assert_awaited_once()
        assert run_step.await_args.args[0] == 1
        assert "Main task:\nopen settings" in run_step.await_args.args[1]
        assert run_step.await_args.kwargs["system_prompt"] == "Custom prompt"

    @pytest.mark.asyncio
    async def test_multiple_step_action_includes_history_in_next_prompt(self):
        client = LlmClient()
        first = HistoryItem(
            step=1,
            action={
                "description": "Wait for loading",
                "action_type": "Wait",
                "text": None,
                "point_2d": None,
            },
        )
        second = HistoryItem(
            step=2,
            action={
                "description": "Task is complete",
                "action_type": "Finish",
                "text": None,
                "point_2d": None,
            },
        )

        with patch.object(
            client,
            "_run_step",
            AsyncMock(side_effect=[first, second]),
        ) as run_step:
            await client.multiple_step_action("wait for desktop", max_steps=2)

        second_prompt = run_step.await_args_list[1].args[1]
        assert "Step 1:" in second_prompt
        assert '"description": "Wait for loading"' in second_prompt
        assert '"action_type": "Wait"' in second_prompt

    @pytest.mark.asyncio
    async def test_multiple_step_action_raises_when_max_steps_exhausted(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))
        history_item = HistoryItem(
            step=1,
            action={
                "description": "Still loading",
                "action_type": "Wait",
                "text": None,
                "point_2d": None,
            },
        )

        with (
            patch.object(
                client,
                "_run_step",
                AsyncMock(return_value=history_item),
            ),
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as grab_screenshot,
            patch(f"{self.LLM_PATH}.log_image") as mock_log_image,
            pytest.raises(
                RuntimeError,
                match="without reaching Finish action after max_steps=1",
            ),
        ):
            await client.multiple_step_action("wait forever", max_steps=1)

        grab_screenshot.assert_awaited_once()
        mock_log_image.assert_called_once_with(
            screenshot,
            msg="Final screenshot after multiple step action",
        )

    @pytest.mark.asyncio
    async def test_run_step_executes_non_finish_action(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))
        action = {
            "description": "Wait for loading",
            "action_type": "Wait",
            "text": None,
            "point_2d": None,
        }

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as grab_screenshot,
            patch.object(
                client, "prompt_llm", return_value=json.dumps(action)
            ),
            patch.object(
                client,
                "execute_gui_action",
                AsyncMock(),
            ) as execute_action,
        ):
            item = await client._run_step(3, "next action", "system prompt")

        grab_screenshot.assert_awaited_once()
        execute_action.assert_awaited_once_with(action, "Wait for loading")
        assert item == HistoryItem(step=3, action=action)

    @pytest.mark.asyncio
    async def test_run_step_returns_finish_without_executing_action(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))
        action = json.loads(self.FINISH_ACTION_RESPONSE)

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ),
            patch.object(
                client,
                "prompt_llm",
                return_value=self.FINISH_ACTION_RESPONSE,
            ),
            patch.object(
                client,
                "execute_gui_action",
                AsyncMock(),
            ) as execute_action,
        ):
            item = await client._run_step(1, "next action", "system prompt")

        execute_action.assert_not_awaited()
        assert item == HistoryItem(step=1, action=action)

    @pytest.mark.asyncio
    async def test_run_step_logs_screenshot_in_debug_mode(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))
        action = json.loads(self.FINISH_ACTION_RESPONSE)

        with (
            patch.dict("os.environ", {"YARF_LOG_LEVEL": "DEBUG"}),
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ),
            patch.object(
                client,
                "prompt_llm",
                return_value=self.FINISH_ACTION_RESPONSE,
            ),
            patch(f"{self.LLM_PATH}.log_image") as mock_log_image,
        ):
            item = await client._run_step(5, "next action", "system prompt")

        mock_log_image.assert_called_once_with(
            screenshot,
            msg="Screenshot for step 5",
        )
        assert item == HistoryItem(step=5, action=action)

    @pytest.mark.asyncio
    async def test_run_step_retries_and_raises_after_three_failures(self):
        client = LlmClient()
        screenshot = Image.new("RGB", (10, 10))

        with (
            patch.object(
                client,
                "_grab_screenshot",
                AsyncMock(return_value=screenshot),
            ) as grab_screenshot,
            patch.object(client, "prompt_llm", return_value="not json"),
            pytest.raises(
                RuntimeError,
                match=(
                    "Failed to get a valid action from the LLM after "
                    "3 attempts on step 4."
                ),
            ),
        ):
            await client._run_step(4, "next action", "system prompt")

        assert grab_screenshot.await_count == 3
