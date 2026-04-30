"""
This module provides the Robot Framework library for interacting with an LLM
server using OpenAPI.
"""

import asyncio
import json
import os
import textwrap
from typing import Any

import requests
from PIL import Image
from robot.api import logger
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from yarf.errors.yarf_errors import VQADetectionError, VQAValidationError
from yarf.lib.images.utils import to_base64
from yarf.rf_libraries.libraries.image.utils import (
    draw_point_on_image,
    log_image,
    normalize_point,
)
from yarf.vendor.RPA.recognition.utils import to_image


@library
class LlmClient:
    """
    This class provides the Robot interface for llm interactions with an LLM
    server.
    """

    # Define the parameters for the LLM client here if needed
    def __init__(self) -> None:
        self.model: str = "qwen3-vl:2b-instruct"
        self.server_url: str = "http://localhost:11434/v1"
        self.endpoint: str = "/chat/completions"
        self.max_tokens: int = 32768

    @keyword
    def configure_llm_client(self, **kwargs: Any) -> None:
        """
        Configure the LLM client with the given parameters.

        Args:
            **kwargs: Configuration parameters for the LLM client.

        Raises:
            TypeError: If unknown parameters are provided.
            ValueError: If parameter values are of incorrect type.
        """
        config_fields = {"model", "server_url", "endpoint", "max_tokens"}

        unknown = set(kwargs) - config_fields
        if unknown:
            raise TypeError(
                f"Unknown argument(s): {', '.join(sorted(unknown))}. "
                f"Allowed: {', '.join(sorted(config_fields))}"
            )

        for k, v in kwargs.items():
            # Set the attribute if it's a valid configuration field
            # taking care of type conversion if necessary
            field_type = type(getattr(self, k))
            try:
                setattr(self, k, field_type(v))
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid value for {k}: {v}. "
                    f"Expected type {field_type.__name__}"
                )

    @keyword
    def prompt_llm(
        self,
        prompt: str,
        image: Image.Image | str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Send a prompt (text-only or text+image) to the LLM and get the
        response.

        Args:
            prompt: The text prompt to send to the LLM.
            image: Optional image (PIL Image or path) to include in the prompt.
            system_prompt: Optional system prompt to guide the LLM.

        Returns:
            The response from the LLM.
        """
        messages: list[dict[str, Any]] = []

        # Include system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Build the content for the user message
        content: list[dict[str, Any]] = []

        # Always include the text prompt
        content.append({"type": "text", "text": prompt})

        # If an image is provided, include it in the message
        if image is not None:
            pil_image = to_image(image)
            image_base64 = self._encode_image(pil_image)
            content.append(
                {"type": "image_url", "image_url": {"url": image_base64}}
            )

        messages.append({"role": "user", "content": content})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }

        response = requests.post(
            f"{self.server_url}{self.endpoint}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
        data = response.json()

        msg = data["choices"][0]["message"]

        # If the response contains reasoning, log it
        if "reasoning" in msg:
            logger.info(msg["reasoning"])

        return msg["content"]

    def _encode_image(self, image: Image.Image) -> str:
        """
        Reads an image file and returns a base64 string.

        Args:
            image: The image to encode.
        Returns:
            The base64 encoded image string.
        """

        b64 = to_base64(image)
        return f"data:image/png;base64,{b64}"

    def _get_lib_instance(self, lib_name: str) -> Any:
        """
        Helper function to get an instance of a library imported in Robot
        Framework.

        Args:
            lib_name: The name of the library to get an instance of.

        Returns:
            An instance of the specified library.
        """
        return BuiltIn().get_library_instance(lib_name)

    async def _grab_screenshot(self) -> Image.Image:
        """
        Helper function to grab a screenshot using the VideoInput library.

        Returns:
            A PIL Image of the screenshot.

        Raises:
            RuntimeError: If the screenshot could not be grabbed.
        """
        platform_video_input = self._get_lib_instance("VideoInput")
        image = await platform_video_input.grab_screenshot()
        if image is None:
            raise RuntimeError("Failed to grab screenshot.")
        return image

    @keyword
    async def check_for_visual_corruption(
        self,
        image: Image.Image | str | None = None,
        custom_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Detect if an image is corrupted.

        Args:
            image: The image to check. If no image is provided, a new
                screenshot is grabbed.
            custom_prompt: Optional custom prompt to guide the LLM.

        Returns:
            A dict containing the LLM's assessment of whether the image is
            corrupted and a description.

        Raises:
            VQAValidationError: If the image is assessed as corrupted by the
                LLM.
        """
        if image is None:
            image = await self._grab_screenshot()

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=custom_prompt or "Detect if the image is corrupted.",
            image=image,
            system_prompt=textwrap.dedent("""
            You are a helpful assistant that can understand images and texts.
            You have to assess if the provided image is corrupted or not.
            This will probably be shown as noise in some parts of the image.
            Output your answer in pure JSON format with the followings only:
            1. corrupted: a boolean indicating if the image is corrupted
            2. description: a short description (on 1 line)
            Example output: {"corrupted": true, "description": "..."}.
            Do not add markdown syntax or any other text.
            """),
        )

        required_keys = {"corrupted": bool, "description": str}

        parsed = await self._verify_llm_json_response(
            llm_output, required_keys
        )

        if parsed["corrupted"]:
            log_image(
                image, "Corrupted image detected: " + parsed["description"]
            )
            raise VQAValidationError(
                f"Image is corrupted: {parsed['description']}"
            )
        return parsed

    async def _verify_llm_json_response(
        self, llm_output: str, required_keys: dict[str, type]
    ) -> dict[str, Any]:
        """
        Verify that the LLM response is a valid JSON object with the required
        keys and expected types. If there are validation errors, it tries to
        correct its previous response, then validates the corrected JSON.

        Args:
            llm_output: The raw string response from the LLM.
            required_keys: A dict mapping keys to their expected types.

        Returns:
            The parsed JSON object if it is valid.

        Raises:
            RuntimeError: If the LLM response cannot be validated even after
                correction attempts.
        """

        parsed_output, errors = self._parse_llm_json_response(
            llm_output, required_keys
        )

        if errors:
            logger.warn(
                f"LLM response had validation errors: \n{errors}\n"
                "Trying to fix them with a verification prompt"
            )

            corrected_output = await asyncio.to_thread(
                self.prompt_llm,
                prompt=textwrap.dedent(f"""
                Please correct the previous response and output the correct
                JSON.
                Previous response: {llm_output}
                Error details: {errors}
                """),
                system_prompt=textwrap.dedent("""
                Your task is to understand error outputs and try to fix them
                by understanding the response.
                Rules:
                 - You have to make sure the output is a valid JSON and follows
                   the required schema.
                 - The output must be the JSON object without any extra text or
                   markdown.
                 - All the brackets and quotes must be properly closed.
                """),
            )

            parsed_output, verifier_errors = self._parse_llm_json_response(
                corrected_output, required_keys
            )

            if verifier_errors:
                msg = textwrap.dedent(f"""
                    LLM response could not be validated even after correction.
                    Original response: {llm_output}
                    Errors: {errors}
                    Corrected response: {corrected_output}
                    Errors: {verifier_errors}
                    """)
                raise RuntimeError(msg)

        return parsed_output

    def _parse_llm_json_response(
        self, llm_output: str, required_keys: dict[str, type]
    ) -> tuple[dict[str, Any], str]:
        """
        Parse the LLM output as JSON and validate it against the required keys
        and their expected types.

        Args:
            llm_output: The raw string response from the LLM.
            required_keys: A dict mapping keys to their expected types.
        Returns:
            A tuple containing the parsed JSON object and a string of error
            messages (empty if no errors).
        """
        json_start = llm_output.find("{")
        json_end = llm_output.rfind("}")
        if json_start == -1 or json_end == -1:
            error = f"LLM response does not contain valid JSON: {llm_output}"
            return {}, error

        try:
            parsed_output: dict[str, Any] = json.loads(
                llm_output[json_start : json_end + 1]
            )
        except json.JSONDecodeError:
            error = f"Failed to parse LLM response as JSON: {llm_output}"
            return {}, error

        error_messages: list[str] = []
        missing_keys = required_keys.keys() - parsed_output.keys()
        if missing_keys:
            error_messages.append(
                "LLM returned an invalid response format; missing keys: "
                f"{sorted(missing_keys)}. Response: {parsed_output}"
            )

        for key, value in parsed_output.items():
            if key in required_keys and not isinstance(
                value, required_keys[key]
            ):
                error_messages.append(
                    f"LLM returned an invalid type for '{key}'; "
                    f"expected {required_keys[key].__name__}, "
                    f"got {type(value).__name__}."
                )

        return parsed_output, "\n".join(error_messages)

    @keyword
    async def get_object_position(
        self,
        description: str,
        image: Image.Image | str | None = None,
        custom_system_prompt: str | None = None,
    ) -> list[Any]:
        """
        Get the position of an object on the screen in relative coordinates.

        Args:
            description: Description of the object to locate.
            image: Image to inspect. If omitted, a screenshot is grabbed.
            custom_system_prompt: Optional system prompt override.

        Returns:
            The object position as normalized relative coordinates
            ``[x, y]``, where each value is typically in the range ``0..1``.


        Raises:
            VQADetectionError: If the LLM indicates that the object was not
        """
        if image is None:
            image = await self._grab_screenshot()

        system_prompt = textwrap.dedent("""
            You are a GUI agent. Find the position of an object on the screen
            from a description and a screenshot.

            Return only a valid JSON object with this exact schema:
            {
                "point_2d": [x, y]
            }

            Use a 1000x1000 coordinate grid where [0, 0] is the top-left and
            [1000, 1000] is the bottom-right of the image.

            If the object is not found, return {"point_2d": [-100, -100]}.
            Do not add markdown syntax or any other text.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=f"Find the position of this object: {description}",
            image=image,
            system_prompt=custom_system_prompt or system_prompt,
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {"point_2d": list},
        )
        point = parsed["point_2d"]

        logger.info(f"LLM indicated point: {point}")
        if point == [-100, -100]:
            raise VQADetectionError(f"Object was not found: {description}")

        # Normalize the point to have relative coordinates
        point = normalize_point(point)

        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            image = draw_point_on_image(image, point, label=description)
            log_image(image, f"LLM indicated point for: {description}")

        return point

    @keyword
    async def assert_state(
        self,
        description: str,
        image: Image.Image | str | None = None,
        custom_system_prompt: str | None = None,
    ) -> None:
        """
        Assert that the screen matches a state description.

        Args:
            description: Description of the expected screen state.
            image: Image to inspect. If omitted, a screenshot is grabbed.
            custom_system_prompt: Optional system prompt override.

        Raises:
            AssertionError: If the state does not match the description.
        """

        if image is None:
            image = await self._grab_screenshot()

        system_prompt = textwrap.dedent("""
            You are a GUI agent. Check whether the screenshot matches the
            description of an expected screen state.

            Return only a valid JSON object with this exact schema:
            {
                "matches_description": true | false,
                "reasoning": "explanation of why the state is present or not"
            }
            Do not add markdown syntax or any other text.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=(
                f"Check if this state is present on the screen: {description}"
            ),
            image=image,
            system_prompt=custom_system_prompt or system_prompt,
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {"matches_description": bool, "reasoning": str},
        )

        if not parsed["matches_description"]:
            log_image(image=image, msg="Current state")
            raise AssertionError(
                f"State does NOT match description: {description}. "
                f"Reasoning: {parsed['reasoning']}"
            )

    @keyword
    async def get_single_gui_action(
        self,
        task: str,
        image: Image.Image | str | None = None,
        custom_system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Get a single GUI action from the LLM.

        Args:
            task: The task description to provide to the LLM.
            image: Image to inspect. If omitted, a screenshot is grabbed.
            custom_system_prompt: Optional system prompt override.

        Returns:
            The next GUI action as returned by the LLM. For pointer-based
            actions, `point_2d` contains the raw coordinates from the LLM's
            1000x1000 grid.
        Raises:
            ValueError: If the LLM response contains an unsupported action type
                or is missing required fields.
        """

        if image is None:
            image = await self._grab_screenshot()

        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            log_image(
                image, msg="Screenshot provided to LLM for GUI action decision"
            )

        system_prompt = textwrap.dedent("""
            You are a GUI agent. You are given a task and a screenshot of the
            screen. Choose exactly one next action.

            Available actions:

            action_type: Left Click, text: null, point_2d: [x, y]
                Explanation: Left click a specific UI element and provide
                coordinates on a 1000x1000 grid.

            action_type: Right Click, text: null, point_2d: [x, y]
                Explanation: Right click a specific UI element and provide
                coordinates on a 1000x1000 grid.

            action_type: Double Click, text: null, point_2d: [x, y]
                Explanation: Double click a specific UI element and provide
                coordinates on a 1000x1000 grid.

            action_type: Write, text: Text to enter, point_2d: [-100, -100]
                Explanation: Type text without moving the pointer.

            Return only a valid JSON object with this exact schema:
            {
                "action_type": "one of the available action types",
                "text": "text to be written, or null if not applicable",
                "point_2d": [x, y]
            }

            Rules:
            - Return point_2d on a 1000x1000 grid where [0, 0] is the top-left
              and [1000, 1000] is the bottom-right of the image.
            - Use [-100, -100] when coordinates are not applicable.
            - Do not add markdown syntax or any other text.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=task,
            image=image,
            system_prompt=custom_system_prompt or system_prompt,
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {"action_type": str, "point_2d": list},
        )
        action_type = parsed["action_type"]
        allowed_actions = {
            "Left Click",
            "Right Click",
            "Double Click",
            "Write",
        }
        if action_type not in allowed_actions:
            raise ValueError(f"Unsupported GUI action: {action_type}")

        if action_type == "Write":
            if not isinstance(parsed.get("text"), str):
                raise ValueError("Write actions must include text.")
            return parsed

        if parsed["point_2d"] == [-100.0, -100.0]:
            raise ValueError(f"{action_type} actions must include a point.")

        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            point = normalize_point(parsed["point_2d"])
            annotated = draw_point_on_image(image, point, label=action_type)
            log_image(annotated, f"LLM indicated action point for: {task}")

        return parsed

    @keyword
    async def execute_gui_action(self, action: dict[str, Any]) -> None:
        """
        Execute a GUI action as specified by the LLM response.

        Args:
            action: A dict containing the action_type, text, and point_2d.

        Raises:
            ValueError: If the action type is unsupported or if required fields
                are missing.
        """

        hid = self._get_lib_instance("HID")
        action_type = action["action_type"]
        logger.info(f"Executing action: {action_type}")

        if action_type in {"Left Click", "Right Click", "Double Click"}:
            x, y = normalize_point(action["point_2d"])
            await hid.move_pointer_to_proportional(x, y)
            await asyncio.sleep(0.5)

            if action_type == "Left Click":
                await hid.click_pointer_button("LEFT")
            elif action_type == "Right Click":
                await hid.click_pointer_button("RIGHT")
            elif action_type == "Double Click":
                await hid.click_pointer_button("LEFT")
                await asyncio.sleep(0.1)
                await hid.click_pointer_button("LEFT")

        elif action_type == "Write":
            if not isinstance(action.get("text"), str):
                raise ValueError("Write actions must include text.")
            await hid.type_string(action["text"])

        else:
            raise ValueError(f"Unsupported GUI action: {action_type}")

        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            # Wait for a moment to let the screen update after the action
            await asyncio.sleep(1)
            image = await self._grab_screenshot()
            logger.info(f"Executed action: {action_type}")
            log_image(image=image, msg="Screenshot after executing action")
