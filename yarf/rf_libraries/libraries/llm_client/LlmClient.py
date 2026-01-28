"""
This module provides the Robot interface for llm interactions with ollama.
"""

from typing import Any

import requests
from PIL import Image
from robot.api.deco import keyword, library

from yarf.rf_libraries.libraries.image.utils import to_base64
from yarf.vendor.RPA.recognition.utils import to_image


@library
class LlmClient:
    """
    This class provides the Robot interface for llm interactions with ollama.
    """

    # Define the parameters for the LLM client here if needed
    def __init__(self) -> None:
        self.model: str = "qwen3-vl:2b-instruct"
        self.server_url: str = "http://localhost:11434"
        self.endpoint: str = "/v1/chat/completions"
        self.max_tokens: int = 10000

    @keyword
    def prompt_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Send a text prompt to the LLM and get the response.

        Args:
            prompt: The text prompt to send to the LLM.
            system_prompt: An optional system prompt to guide the LLM.

        Returns:
            The response from the LLM.
        """

        messages: list[dict[str, Any]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }

        response = requests.post(
            f"{self.server_url}{self.endpoint}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    @keyword
    def prompt_image(
        self,
        prompt: str,
        image: Image.Image | str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Send a text and image prompt to the LLM and get the response.

        Args:
            prompt: The text prompt to send to the LLM.
            image: The path to the image file to include in the prompt.
            system_prompt: An optional system prompt to guide the LLM.

        Returns:
            The response from the LLM.
        """
        pil_image = to_image(image)

        image_base64 = self._encode_image(pil_image)

        messages: list[dict[str, Any]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_base64}},
                ],
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }

        response = requests.post(
            f"{self.server_url}{self.endpoint}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

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
