"""
This module provides the Robot Framework library for interacting with an LLM
server using OpenAPI.
"""

import asyncio
import json
from typing import Any

import requests
from PIL import Image
from robot.api import logger
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from yarf.lib.images.utils import to_base64
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
            image: The image to check (PIL Image or path). If no image is provided, a new screenshot is grabbed.
            custom_prompt: Optional custom prompt to guide the LLM.

        Returns:
            A dict containing the LLM's assessment of whether the image is
            corrupted, a description, and the number of votes.

        Raises:
            ValueError: If the screenshot could not be grabbed or if the LLM response is invalid.
        """
        if image is None:
            platform_video_input = self._get_lib_instance("VideoInput")
            if (image := await platform_video_input.grab_screenshot()) is None:
                raise ValueError("Failed to grab screenshot.")

        result = await asyncio.to_thread(
            self.prompt_llm,
            prompt=custom_prompt or "Detect if the image is corrupted.",
            image=image,
            system_prompt="""
            You are a helpful assistant that can understand images and texts.
            You have to assess if the provided image is corrupted or not.
            This will probably be shown as noise in some parts of the image.
            Output your answer in dict format with a short description (on 1 line)
            and the confidence score. Return JSON only.
            Example: {"corrupted": true, "description": "..."}.
            """,
        )

        required_keys = {
            "corrupted": bool,
            "description": str,
        }
        parsed, error_messages = self._verify_llm_json_response(
            result, required_keys, expected_types
        )
        if len(error_messages) > 0:
            result = await asyncio.to_thread(
                self.prompt_llm,
                prompt=f"""
                Please correct the previous response and output the correct JSON.
                Previous response: {result}
                Error details: {error_messages}
                """,
                system_prompt="""
                You are a helpful assistant that can understand error outputs.
                Output your answer in JSON format only.
                Example: {"corrupted": true, "description": "..."}.
                """,
            )
            parsed, _ = self._verify_llm_json_response(
                result, required_keys, expected_types
            )

        return parsed

    def _verify_llm_json_response(
        self,
        result: str,
        required_keys: set[str],
        expected_types: dict[str, type],
    ) -> tuple[dict[str, Any], str]:
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Failed to parse LLM response as JSON: {result}"
            ) from exc

        error_messages = ""
        missing_keys = required_keys - parsed.keys()
        if missing_keys:
            error_messages += (
                "LLM returned an invalid response format; missing keys: "
                f"{sorted(missing_keys)}. Response: {parsed}"
            )

        for key, expected in expected_types.items():
            if not isinstance(parsed[key], expected):
                error_messages += (
                    f"LLM returned an invalid type for '{key}'; "
                    f"expected {expected.__name__}, "
                    f"got {type(parsed[key]).__name__}."
                )

        logger.warn(f"LLM response validation errors: {error_messages}")
        return parsed, error_messages
