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

from yarf.errors.yarf_errors import VQAValidationError
from yarf.lib.images.utils import to_base64
from yarf.rf_libraries.libraries.image.utils import draw_point_on_image, log_image
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
            RuntimeError: If the screenshot could not be grabbed or if the LLM
                response is invalid.
            VQAValidationError: If the image is assessed as corrupted by the
                LLM.
        """
        if image is None:
            platform_video_input = self._get_lib_instance("VideoInput")
            if (image := await platform_video_input.grab_screenshot()) is None:
                raise RuntimeError("Failed to grab screenshot.")

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
        self,
        llm_output: str,
        required_keys: dict[str, type],
    ) -> dict[str, Any]:
        """
        Verify that the LLM response is a valid JSON object with the required
        keys and expected types. If there are validation errors, an attempt is
        made to correct the

        Args:
            result: The raw string response from the LLM.
            required_keys: A dict mapping keys to their expected types.

        Returns:
            The parsed JSON object if it is valid.
        """

        parsed_output, errors = self._parse_llm_json_response(
            llm_output, required_keys
        )

        if errors:
            logger.warn(
                f"LLM response had validation errors: {errors}\n"
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
            error_messages = (
                f"LLM response does not contain valid JSON: {llm_output}"
            )
            return {}, error_messages

        try:
            parsed_output: dict[str, Any] = json.loads(
                llm_output[json_start : json_end + 1]
            )
        except json.JSONDecodeError:
            error_messages = (
                f"Failed to parse LLM response as JSON: {llm_output}"
            )
            return {}, error_messages

        error_messages = ""
        missing_keys = required_keys.keys() - parsed_output.keys()
        if missing_keys:
            error_messages += (
                "LLM returned an invalid response format; missing keys: "
                f"{sorted(missing_keys)}. Response: {parsed_output}"
            )

        for key, value in parsed_output.items():
            if key in required_keys and not isinstance(
                value, required_keys[key]
            ):
                error_messages += (
                    f"LLM returned an invalid type for '{key}'; "
                    f"expected {required_keys[key].__name__}, "
                    f"got {type(value).__name__}."
                )

        return parsed_output, error_messages

    @keyword
    async def get_object_position(
        self,
        description: str,
        image: Image.Image | str | None = None,
        custom_system_prompt: str | None = None,
    ) -> list[Any]:
        """
        Get the position of an object on the screen.

        Args:
            description: Description of the object to locate.
            image: Image to inspect. If omitted, a screenshot is grabbed.
            custom_system_prompt: Optional system prompt override.

        Returns:
            The model point as ``[x, y]`` on a 1000x1000 grid, or
            ``[-100, -100]`` if the object was not found.
        """
        if image is None:
            platform_video_input = self._get_lib_instance("VideoInput")
            if (image := await platform_video_input.grab_screenshot()) is None:
                raise RuntimeError("Failed to grab screenshot.")

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
            raise VQAValidationError(f"Object was not found: {description}")

        # Normalize the point to have relative coordinates
        point = [coord / 1000 for coord in point]

        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            image = draw_point_on_image(image, point, label=description)
            log_image(image, f"LLM indicated point for: {description}")

        return point
