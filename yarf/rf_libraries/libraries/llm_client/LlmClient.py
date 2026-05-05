"""
This module provides the Robot Framework library for interacting with an LLM
server using OpenAPI.
"""

import asyncio
import json
import os
import textwrap
from dataclasses import dataclass
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


@dataclass
class HistoryItem:
    step: int
    action: dict[str, Any]

    def __str__(self) -> str:
        return f"Step {self.step}:\n{json.dumps(self.action, indent=2)}"


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

        required_keys: dict[str, list[type]] = {
            "corrupted": [bool],
            "description": [str],
        }

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
        required_keys: dict[str, list[type]],
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

    def _format_expected_types(self, expected_types: list[type]) -> str:
        return " | ".join(t.__name__ for t in expected_types)

    def _parse_llm_json_response(
        self,
        llm_output: str,
        required_keys: dict[str, list[type]],
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

        for key, expected_types in required_keys.items():
            if key not in parsed_output:
                continue

            value = parsed_output[key]

            if not isinstance(value, tuple(expected_types)):
                error_messages.append(
                    f"LLM returned an invalid type for '{key}'; "
                    f"expected {self._format_expected_types(expected_types)}, "
                    f"got {type(value).__name__}."
                )

        return parsed_output, "\n".join(error_messages)

    @keyword
    async def get_object_position(
        self,
        description: str,
        image: Image.Image | str | None = None,
        custom_system_prompt: str | None = None,
    ) -> list[float]:
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
            You are a GUI localization agent. Given an object description and a
            screenshot, identify the object's location in the screenshot.

            Return only a valid JSON object with this exact schema:
            {"point_2d": [x, y]}
            or:
            {"point_2d": null}
            if the object is not present or not confidently identified.

            Rules:
            - Use a normalized 1000x1000 coordinate grid, where [0, 0] is the
              top-left of the screenshot and [1000, 1000] is the bottom-right.
            - Return the approximate center point of the described object.
            - Coordinates must be integers.
            - If the object is partially visible, return the center of the
              visible portion.
            - If multiple matching objects are present, return the best match
              based on the description and surrounding context.
            - If the object is not visible, or you are not confident it is
              present, return: {"point_2d": null}
            - Do not guess. Prefer null over a low-confidence false
              positive.
            - Do not include markdown, explanations, comments, or any text
              outside the JSON object.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=f"Find the position of this object: {description}",
            image=image,
            system_prompt=custom_system_prompt or system_prompt,
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {"point_2d": [list, type(None)]},
        )
        point = parsed["point_2d"]

        logger.info(f"LLM indicated point: {point}")
        if point is None:
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
            {"matches_description": [bool], "reasoning": [str]},
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

            action_type: Write, text: Text to enter, point_2d: null
                Explanation: Type text without moving the pointer.

            action_type: Failed, text: null, point_2d: null
                Explanation: An action is impossible and cannot be performed.
                This should whenever the model can't determine a valid action.

            Return only a valid JSON object with this exact schema:
            {
                "action_type": "one of the available action types",
                "text": "text to be written, or null if not applicable",
                "point_2d": "[x, y], or null if not applicable"
            }

            Rules:
            - Return point_2d on a 1000x1000 grid where [0, 0] is the top-left
              and [1000, 1000] is the bottom-right of the image.
            - Use null when coordinates are not applicable.
            - Do not add markdown syntax or any other text.
            - If you determine that the task cannot be completed, return:
              {"action_type": "Failed", "text": null, "point_2d": null}.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=task,
            image=image,
            system_prompt=custom_system_prompt or system_prompt,
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {
                "action_type": [str],
                "point_2d": [list, type(None)],
                "text": [str, type(None)],
            },
        )

        self.validate_gui_action(parsed, task)
        return parsed

    def validate_gui_action(self, action: dict[str, Any], task: str) -> None:
        """
        Validate a GUI action dictionary.

        Args:
            action: A dict containing action_type, text, and point_2d.
            task: The task description provided to the LLM.

        Raises:
            ValueError: If the action type is unsupported or if required fields
                are missing.
        """

        allowed_actions = {
            "Left Click",
            "Right Click",
            "Double Click",
            "Write",
            "Wait",
            "Failed",
        }

        action_type = action["action_type"]
        if action_type not in allowed_actions:
            raise ValueError(f"Unsupported GUI action: {action_type}")

        if action_type == "Failed":
            raise ValueError(
                f"LLM indicated action can't be completed: {task}."
            )

        if action_type == "Write" and not isinstance(action.get("text"), str):
            raise ValueError("Write actions must include text.")

        if action_type in {
            "Left Click",
            "Right Click",
            "Double Click",
        } and not isinstance(action.get("point_2d"), list):
            raise ValueError(f"{action_type} actions must include a point.")

    @keyword
    async def execute_gui_action(
        self, action: dict[str, Any], description: str = ""
    ) -> None:
        """
        Execute a GUI action as specified by the LLM response.

        Args:
            action: A dict containing the action_type, text, and point_2d.
            description: The description provided to the LLM.

        Raises:
            ValueError: If the action type is unsupported or if required fields
                are missing.
        """

        self.validate_gui_action(action, description)
        action_type = action["action_type"]

        logger.info(f"Executing action: {action}")

        if action_type in {"Left Click", "Right Click", "Double Click"}:
            hid = self._get_lib_instance("HID")
            x, y = normalize_point(action["point_2d"])
            # For click actions, draw the point on the image and log it before
            # executing
            if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
                image = await self._grab_screenshot()
                label = action.get("description", action_type)
                annotated = draw_point_on_image(image, [x, y], label=label)
                log_image(
                    annotated,
                    f"LLM indicated action point for: {label}",
                )

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
            hid = self._get_lib_instance("HID")
            await hid.type_string(action["text"])

        elif action_type == "Wait":
            # For now, this is a fixed wait.
            await asyncio.sleep(5)

        else:
            raise ValueError(f"Unsupported GUI action: {action_type}")

        if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
            # Wait for a moment to let the screen update after the action
            await asyncio.sleep(1)
            image = await self._grab_screenshot()
            logger.info(f"Executed action: {action_type}")
            log_image(image=image, msg="Screenshot after executing action")

    @keyword
    async def multiple_step_action(
        self,
        task: str,
        custom_system_prompt: str | None = None,
        max_steps: int = 50,
    ) -> None:
        """
        Perform a multiple step action by prompting the LLM iteratively until a
        "Finish" action is returned.

        Args:
            task: The task description to complete.
            custom_system_prompt: Optional system prompt override.
            max_steps: Number of actions to attempt before stopping.

        Raises:
            RuntimeError: If the LLM cannot finish within ``max_steps``.
        """

        system_prompt = textwrap.dedent("""
        You are a GUI navigation agent controlling a computer from screenshots.

        You receive:
        - The user's main task.
        - A screenshot of the current UI.
        - A list of actions already performed.

        Your job:
        Return exactly one next action that advances the task.

        Available actions:

        action_type: Left Click, text: null, point_2d: [x, y]
        Explanation: Left click a specific UI element and provide coordinates
        on a 1000x1000 grid.

        action_type: Right Click, text: null, point_2d: [x, y]
        Explanation: Right click a specific UI element and provide coordinates
        on a 1000x1000 grid.

        action_type: Double Click, text: null, point_2d: [x, y]
        Explanation: Double click a specific UI element and provide coordinates
        on a 1000x1000 grid.

        action_type: Write, text: Text to enter, point_2d: null
        Explanation: Type text using the keyboard. Use this only when a text
        field is already focused.

        action_type: Wait, text: null, point_2d: null
        Explanation: Wait briefly when the UI is loading, processing,
        animating, or a task is not ready yet.

        action_type: Finish, text: null, point_2d: null
        Explanation: Mark the task as completed when the visible UI confirms
        the goal is done.

        Coordinate rules:
        - point_2d is normalized to a 1000x1000 grid relative to the
          screenshot.
        - [0, 0] is the top-left of the screenshot.
        - [1000, 1000] is the bottom-right of the screenshot.
        - For pointer actions, choose the center of the target UI element.
        - For Write, Wait, and Finish, always use null.

        Behavior rules:
        - Each step should contain a description of the chosen action to help
          guide the next step.
        - Be deliberate. Prefer one precise action at a time.
        - Do not repeat the same failed click endlessly; use history to adjust.
        - If a field must be typed into, first click/focus it, then on the next
          step use Write.
        - If the screen is changing or a result is loading, use Wait.
        - Usually, to open a folder, you would double click it. To open a
          context menu, you would right click it.
        - Use Finish only when the task is visibly complete or impossible to
          improve further.
        - Do not include explanations, markdown, code fences, comments, or
          extra keys.

        Return only a valid JSON object with this exact schema:
        {
            "description": "brief description for the chosen action",
            "action_type": "one of the available action types",
            "text": "text to be written, or null",
            "point_2d": [x, y]
        }
        """)

        user_prompt_template = textwrap.dedent("""
        Main task:
        {task}

        Action history:
        {history}

        Decide the next single action. Return only valid JSON.
        """)

        logger.info(f"Starting multiple step action sequence for task: {task}")

        history: list[HistoryItem] = []
        for step in range(1, max_steps + 1):
            llm_prompt = user_prompt_template.format(
                task=task,
                history="\n".join(str(item) for item in history),
            )
            history_item = await self._run_step(
                step,
                llm_prompt,
                system_prompt=custom_system_prompt or system_prompt,
            )
            history.append(history_item)

            if history_item.action["action_type"] == "Finish":
                logger.info(
                    f"Task finished successfully in {step} steps. History:\n"
                    + "\n".join(str(item) for item in history)
                )
                return

        # Grab a final screenshot to log the end state
        image = await self._grab_screenshot()
        log_image(image, msg="Final screenshot after multiple step action")

        raise RuntimeError(
            "Multiple step action sequence completed without reaching Finish "
            f"action after max_steps={max_steps}."
        )

    async def _run_step(
        self, step: int, prompt: str, system_prompt: str
    ) -> HistoryItem:
        """
        Run a single step of the multiple step action sequence with retries.

        Args:
            step: The current step number (for logging).
            prompt: The prompt to send to the LLM for this step.
            system_prompt: The system prompt to guide the LLM's response.

        Returns:
            A HistoryItem containing the executed action for this step.

        Raises:
            RuntimeError: If a valid action cannot be obtained from the LLM
                after multiple attempts.
        """

        MAX_ATTEMPTS = 3

        for attempt in range(MAX_ATTEMPTS):
            try:
                # Grab a screnshot at the start of each step
                image = await self._grab_screenshot()

                # Log the screenshot for debugging
                if os.getenv("YARF_LOG_LEVEL") == "DEBUG":
                    log_image(image, msg=f"Screenshot for step {step}")

                # Get the next action from the LLM
                logger.info("Prompt to LLM:\n" + prompt)
                llm_output = await asyncio.to_thread(
                    self.prompt_llm,
                    prompt=prompt,
                    image=image,
                    system_prompt=system_prompt,
                )
                logger.info(f"LLM proposed action: {llm_output}")

                # Verify and parse the LLM response
                action = await self._verify_llm_json_response(
                    llm_output,
                    {
                        "description": [str],
                        "action_type": [str],
                        "text": [str, type(None)],
                        "point_2d": [list, type(None)],
                    },
                )

                if action["action_type"] != "Finish":
                    description = action.get("description", "No description")
                    await self.execute_gui_action(action, description)
                    await asyncio.sleep(1)

                return HistoryItem(step=step, action=action)

            except Exception as e:
                logger.error(
                    "Error parsing LLM response on step "
                    f"{step}, attempt {attempt + 1}: {e}"
                )

        raise RuntimeError(
            "Failed to get a valid action from the LLM after "
            f"{MAX_ATTEMPTS} attempts on step {step}."
        )
