"""
This module provides the Robot Framework library for interacting with an LLM
server using OpenAPI.
"""

import asyncio
import functools
import inspect
import json
import os
import re
import textwrap
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

import requests
from PIL import Image
from robot.api import logger
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import is_truthy

from yarf.errors.yarf_errors import VQADetectionError, VQAValidationError
from yarf.lib.images.utils import to_base64
from yarf.lib.llm_tracing import (
    AGENT,
    CHAIN,
    LLM,
    PARSER,
    TOOL,
    LlmTracer,
    as_outputs,
    describe,
    llm_attributes,
)
from yarf.rf_libraries.libraries.hid_base import HidBase
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


# GUI actions that target a point on the screen
POINTER_ACTIONS = {
    "Left Click",
    "Right Click",
    "Double Click",
    "Scroll Down",
    "Scroll Up",
}
# Mouse wheel steps per Scroll action
SCROLL_STEPS = 5
# Common key names used by LLMs, mapped to X keysyms
KEY_ALIASES = {
    "ctrl": "Control_L",
    "control": "Control_L",
    "alt": "Alt_L",
    "shift": "Shift_L",
    "super": "Super_L",
    "win": "Super_L",
    # Browser/Playwright meaning (Windows key), not the X Meta keysym on Alt
    "meta": "Super_L",
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "tab": "Tab",
    "space": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    # Canonical xkb names, required by the Mir keyboard (VNC accepts both)
    "pageup": "Prior",
    "page_up": "Prior",
    "pagedown": "Next",
    "page_down": "Next",
    "home": "Home",
    "end": "End",
}


@dataclass
class LlmUsage:
    """
    Accumulated resource usage of LLM requests.

    Attributes:
        enabled: Whether requests are recorded.
        requests: Number of recorded requests, excluding retries.
        retries: Number of retries of transient server errors.
        inference_time: Summed wall-clock time of the requests in seconds,
            counting only the final attempt of each request.
        prompt_tokens: Number of input tokens, including image tokens.
        completion_tokens: Number of output tokens, including reasoning.
        reasoning_tokens: Number of output tokens spent on reasoning.
        total_tokens: Total number of tokens processed.
        cost: Cost reported by the server (OpenRouter credits), if any.
        nano_aiu: Copilot billing units (nano AI units), if any.
    """

    enabled: bool = False
    requests: int = 0
    retries: int = 0
    inference_time: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost: float | None = None
    nano_aiu: int | None = None

    @staticmethod
    def parse(data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract the usage of a chat completions or responses API reply.

        Args:
            data: The JSON response from the server.

        Returns:
            A dict with the prompt, completion, reasoning and total token
            counts, the cost and the nano AIU, None if not reported.
        """
        usage = data.get("usage") or {}
        details = (
            usage.get("completion_tokens_details")
            or usage.get("output_tokens_details")
            or {}
        )
        return {
            "prompt_tokens": (
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            ),
            "completion_tokens": (
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or 0
            ),
            "reasoning_tokens": details.get("reasoning_tokens") or 0,
            "total_tokens": usage.get("total_tokens") or 0,
            "cost": usage.get("cost"),
            "nano_aiu": (data.get("copilot_usage") or {}).get(
                "total_nano_aiu"
            ),
        }

    def record(
        self, data: dict[str, Any], inference_time: float, attempts: int = 1
    ) -> None:
        """
        Add the usage of a chat completions or responses API reply, if enabled.

        Args:
            data: The JSON response from the server.
            inference_time: Wall-clock time of the final attempt in seconds.
            attempts: Number of HTTP requests sent, including retries.
        """
        if not self.enabled:
            return

        usage = self.parse(data)
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        cost = usage["cost"]
        nano_aiu = usage["nano_aiu"]

        self.requests += 1
        self.retries += attempts - 1
        self.inference_time += inference_time
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.reasoning_tokens += usage["reasoning_tokens"]
        self.total_tokens += usage["total_tokens"]
        if cost is not None:
            self.cost = (self.cost or 0.0) + cost
        if nano_aiu is not None:
            self.nano_aiu = (self.nano_aiu or 0) + nano_aiu

        logger.info(
            f"LLM request usage: {prompt_tokens} prompt tokens, "
            f"{completion_tokens} completion tokens, "
            f"{inference_time:.2f}s, cost {cost}, nano AIU {nano_aiu}"
        )

    def summary(self) -> dict[str, Any]:
        """
        Get the accumulated usage.

        Returns:
            A dict with the number of requests, token counts, inference
            time, output throughput and cost.

        Raises:
            RuntimeError: If usage collection is disabled.
        """
        if not self.enabled:
            raise RuntimeError(
                "LLM usage collection is disabled, enable it with "
                "'Configure Llm Client    collect_usage=True'."
            )
        return {
            "requests": self.requests,
            "retries": self.retries,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
            "inference_time": self.inference_time,
            "output_tokens_per_second": (
                self.completion_tokens / self.inference_time
                if self.inference_time
                else 0.0
            ),
            "cost": self.cost,
            "nano_aiu": self.nano_aiu,
        }


# Presets for hosted OpenAI-compatible providers. The API key is read from
# the environment variable to keep it out of Robot logs.
PROVIDERS: dict[str, dict[str, str]] = {
    "openrouter": {
        "server_url": "https://openrouter.ai/api/v1",
        "endpoint": "/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "copilot": {
        "server_url": "https://api.githubcopilot.com",
        "endpoint": "/chat/completions",
        "api_key_env": "GITHUB_TOKEN",
    },
    "gemini": {
        "server_url": (
            "https://generativelanguage.googleapis.com/v1beta/openai"
        ),
        "endpoint": "/chat/completions",
        "api_key_env": "GEMINI_API_KEY",
    },
}

# Transient server errors (rate limits, gateway errors) and retry delays
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)
GRID_SIZE = 1000
# Model families trained on one coordinate system: the 1000x1000 grid or the
# screenshot pixels. They answer in it but label point_frame unreliably, so
# they are only asked for it and their reported frame is ignored. Keys have
# no separators, as providers name the same model with "-", "_" or ".".
NATIVE_FRAMES = {"qwen3": "grid", "qwen2vl": "grid", "qwen25vl": "pixels"}

F = TypeVar("F", bound=Callable[..., Any])


def keyword_name(func_name: str) -> str:
    """
    Get the Robot keyword name of a function.

    Args:
        func_name: The function name, e.g. ``click_pointer_button``.

    Returns:
        The keyword name, e.g. ``Click Pointer Button``.
    """
    return func_name.strip("_").replace("_", " ").title()


def _traced(span_type: str) -> Callable[[F], F]:
    """
    Record a keyword as a span named after it, with its arguments as inputs and
    its return value as outputs.

    Args:
        span_type: The MLflow span type.

    Returns:
        The decorator, for both sync and async keywords.
    """

    def decorator(func: F) -> F:
        name = keyword_name(func.__name__)
        signature = inspect.signature(func)

        def inputs(*args: Any, **kwargs: Any) -> dict[str, Any]:
            bound = signature.bind(*args, **kwargs).arguments
            return {k: describe(v) for k, v in bound.items() if k != "self"}

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(
                self: "LlmClient", *args: Any, **kwargs: Any
            ) -> Any:
                with self.tracer.span(
                    name, span_type, inputs(self, *args, **kwargs)
                ) as span:
                    result = await func(self, *args, **kwargs)
                    if result is not None:
                        span.set_outputs(as_outputs(result))
                    return result

            return cast(F, async_wrapper)

        @functools.wraps(func)
        def wrapper(self: "LlmClient", *args: Any, **kwargs: Any) -> Any:
            with self.tracer.span(
                name, span_type, inputs(self, *args, **kwargs)
            ) as span:
                result = func(self, *args, **kwargs)
                if result is not None:
                    span.set_outputs(as_outputs(result))
                return result

        return cast(F, wrapper)

    return decorator


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
        self.api_key_env: str = "YARF_LLM_API_KEY"
        self.image_format: str = "WEBP"
        self.experiment: str = "yarf"
        self.usage = LlmUsage()
        self.tracer = LlmTracer()

    @keyword
    def configure_llm_client(self, **kwargs: Any) -> None:
        """
        Configure the LLM client with the given parameters.

        Supported parameters are ``model``, ``server_url``, ``endpoint``,
        ``max_tokens``, ``api_key_env``, ``image_format``, ``collect_usage``,
        ``tracing``, ``experiment`` and ``provider``.

        ``provider`` applies a preset for a hosted service, which explicit
        parameters override:
        - ``openrouter``: OpenRouter, key read from ``OPENROUTER_API_KEY``.
        - ``copilot``: GitHub Copilot, key read from ``GITHUB_TOKEN``
          (e.g. ``export GITHUB_TOKEN=$(gh auth token)``).
        - ``gemini``: Google Gemini API, key read from ``GEMINI_API_KEY``.

        The API key is sent as a bearer token and read from the environment
        variable named by ``api_key_env`` (default ``YARF_LLM_API_KEY``),
        so that it never appears in the Robot logs. No ``Authorization``
        header is sent if the variable is unset.

        Models that only support the OpenAI Responses API can be used by
        setting ``endpoint=/responses``. For models that do not accept WEBP
        images, set ``image_format`` to ``PNG`` or ``JPEG``.

        Set ``collect_usage=True`` to record the token usage, inference time
        and cost of each request, see `Get Llm Usage`. It is off by default.

        Set ``tracing=True`` to record each LLM keyword as an MLflow trace,
        in the experiment named by ``experiment`` (default ``yarf``). A trace
        shows the prompts and screenshots sent to the model, its answers,
        token usage, latency, response parsing and the GUI actions taken.
        Traces are tagged with the Robot suite and test, grouped in one
        session per test, and get automatic feedback such as
        ``keyword_passed`` and ``valid_json_first_try``. Attach your own with
        `Log Llm Feedback` and `Log Llm Expectation`, and judge them with
        `Evaluate Llm Traces`. Tracing requires ``pip install yarf[mlflow]``.
        Traces are sent to ``MLFLOW_TRACKING_URI`` if set, otherwise to
        ``mlflow.db`` in the Robot output directory, viewed with
        ``mlflow ui --backend-store-uri sqlite:///<outdir>/mlflow.db``.

        Args:
            **kwargs: Configuration parameters for the LLM client.

        Raises:
            TypeError: If unknown parameters are provided.
            ValueError: If parameter values are of incorrect type or the
                provider is unknown.

        Example:
            | Configure Llm Client
            | ...    model=qwen3-vl:2b-instruct
            | ...    server_url=http://localhost:11434/v1
            | Configure Llm Client    provider=copilot    model=gpt-4.1
            | Configure Llm Client    provider=openrouter
            | ...    model=qwen/qwen3-vl-8b-instruct
            | Configure Llm Client    provider=gemini    model=gemini-2.5-flash
            | Configure Llm Client    collect_usage=True
            | Configure Llm Client    tracing=True    experiment=installer
        """
        config_fields = {
            "model",
            "server_url",
            "endpoint",
            "max_tokens",
            "api_key_env",
            "image_format",
            "collect_usage",
            "tracing",
            "experiment",
            "provider",
        }

        unknown = set(kwargs) - config_fields
        if unknown:
            raise TypeError(
                f"Unknown argument(s): {', '.join(sorted(unknown))}. "
                f"Allowed: {', '.join(sorted(config_fields))}"
            )

        provider = kwargs.pop("provider", None)
        if provider is not None:
            if provider not in PROVIDERS:
                raise ValueError(
                    f"Unknown provider: {provider}. "
                    f"Allowed: {', '.join(sorted(PROVIDERS))}"
                )
            kwargs = {**PROVIDERS[provider], **kwargs}

        if "collect_usage" in kwargs:
            self.usage.enabled = is_truthy(kwargs.pop("collect_usage"))

        tracing = kwargs.pop("tracing", None)
        if tracing is not None:
            tracing = is_truthy(tracing)
        elif "experiment" in kwargs:
            tracing = self.tracer.enabled

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

        if tracing:
            self.tracer.enable(self.experiment)
        elif tracing is not None:
            self.tracer.enabled = False

    @keyword
    @_traced(CHAIN)
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

        Example:
            | ${answer}=    Prompt Llm    Describe the screen
            | ${image}=    Grab Screenshot
            | ${answer}=    Prompt Llm    What is shown?    ${image}
        """
        image_url = None
        if image is not None:
            image_url = self._encode_image(to_image(image))

        uses_responses_api = self.endpoint.rstrip("/").endswith("/responses")
        payload: dict[str, Any] = {"model": self.model}
        content: list[dict[str, Any]]
        if uses_responses_api:
            content = [{"type": "input_text", "text": prompt}]
            if image_url:
                content.append({"type": "input_image", "image_url": image_url})
            payload["input"] = [{"role": "user", "content": content}]
            payload["max_output_tokens"] = self.max_tokens
            if system_prompt:
                payload["instructions"] = system_prompt
        else:
            messages: list[dict[str, Any]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            content = [{"type": "text", "text": prompt}]
            if image_url:
                content.append(
                    {"type": "image_url", "image_url": {"url": image_url}}
                )
            messages.append({"role": "user", "content": content})
            payload["messages"] = messages
            payload["max_tokens"] = self.max_tokens

        headers = {"Content-Type": "application/json"}
        api_key = os.getenv(self.api_key_env)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        with self.tracer.span(
            self.endpoint.strip("/"), LLM, inputs=payload
        ) as span:
            for attempt, delay in enumerate((*RETRY_DELAYS, None), start=1):
                start = time.perf_counter()
                response = requests.post(
                    f"{self.server_url}{self.endpoint}",
                    headers=headers,
                    json=payload,
                    timeout=600,
                )
                inference_time = time.perf_counter() - start
                if response.status_code not in RETRY_STATUS or delay is None:
                    break
                logger.warn(
                    f"LLM server returned {response.status_code}, "
                    f"retrying in {delay}s"
                )
                time.sleep(delay)
            response.raise_for_status()
            data = response.json()
            span.set_outputs(data)
            span.set_attributes(
                llm_attributes(
                    self.model, LlmUsage.parse(data), inference_time, attempt
                )
            )
        self.usage.record(data, inference_time, attempts=attempt)

        if uses_responses_api:
            return "".join(
                part["text"]
                for item in data["output"]
                if item["type"] == "message"
                for part in item["content"]
                if part["type"] == "output_text"
            )

        msg = data["choices"][0]["message"]

        # If the response contains reasoning, log it
        if "reasoning" in msg:
            logger.info(msg["reasoning"])

        return msg.get("content") or ""

    @keyword
    def get_llm_usage(self) -> dict[str, Any]:
        """
        Get the accumulated usage of all LLM requests made by this library
        instance, e.g. during the current test. Requires ``collect_usage=True``
        in `Configure Llm Client`.

        ``inference_time`` is the summed wall-clock time of the requests in
        seconds, including network latency. Retries of transient server
        errors are counted separately in ``retries``; only the final attempt
        of each request counts in ``requests`` and ``inference_time``. ``cost``
        (OpenRouter credits) and ``nano_aiu`` (Copilot billing units) are
        ``None`` if the server does not report them.

        Returns:
            A dict with the model, number of requests and retries, token
            counts, inference time, output throughput and cost.

        Example:
            | Configure Llm Client    collect_usage=True
            | ${usage}=    Get Llm Usage
            | Log    ${usage}[total_tokens]
        """
        return {"model": self.model, **self.usage.summary()}

    @keyword
    def log_llm_feedback(
        self, name: str, value: Any, rationale: str | None = None
    ) -> None:
        """
        Attach a feedback, a judgement of the result, to the last LLM trace of
        the current test. Requires ``tracing=True`` in `Configure Llm Client`.

        MLflow aggregates feedback per name, e.g. to compare the accuracy of
        prompts or models across runs.

        Args:
            name: The feedback name.
            value: The feedback value, e.g. a boolean or a score.
            rationale: Optional explanation of the value.

        Example:
            | ${point}=    Get Object Position    the OK button
            | ${ok}=    Evaluate    0.4 < ${point}[0] < 0.6
            | Log Llm Feedback    found_ok_button    ${ok}
        """
        self.tracer.log_feedback(name, value, rationale)

    @keyword
    def log_llm_expectation(self, name: str, value: Any) -> None:
        """
        Attach an expectation, the ground truth, to the last LLM trace of the
        current test. Requires ``tracing=True`` in `Configure Llm Client`.

        Expectations turn traces into an evaluation dataset, e.g. for judges
        that compare the output with the expected facts.

        Args:
            name: The expectation name.
            value: The expected value.

        Example:
            | ${action}=    Get Single Gui Action    click the OK button
            | Log Llm Expectation    expected_action    Left Click
        """
        self.tracer.log_expectation(name, value)

    @keyword
    def evaluate_llm_traces(
        self,
        *guidelines: str,
        judge_model: str | None = None,
        scope: str = "suite",
        screenshots: bool = True,
    ) -> dict[str, Any]:
        """
        Evaluate the LLM traces against guidelines with an LLM judge, and
        against their expected tool calls. Requires ``tracing=True`` in
        `Configure Llm Client`.

        The judge reads the keyword inputs and outputs of each trace, the GUI
        actions it took in order, and looks at the screenshots sent to the
        model, then decides whether they follow all the guidelines. Its
        verdict and rationale are attached to the traces as a ``guidelines``
        feedback, and the evaluation is logged as an MLflow run. Traces
        without an LLM request, such as those of `Execute Gui Action`, are not
        judged. An answer other than yes or no is recorded as an error, and
        left out of the metrics.

        The trajectory of the traces with an ``expected_tool_calls``
        expectation, see `Log Llm Expectation`, is checked without an LLM:
        the HID keywords called by the GUI actions must match the expected
        ones, in order. An expected call is a keyword name, e.g. ``Click
        Pointer Button``, or a dict with a ``name`` and the ``arguments`` to
        compare, e.g. ``{"name": "Type String", "arguments": {"string":
        "42"}}``. The result is a ``tool_calls`` feedback, with the
        mismatches as rationale. Guidelines are optional when such
        expectations are logged.

        Seeing the screenshots requires a vision model as the judge. Set
        ``screenshots=False`` for a text-only judge, or to save tokens on
        traces with many screenshots, e.g. from `Multiple Step Action`.

        By default the judge is the configured model on the configured
        server. Any MLflow model URI can be used instead, e.g.
        ``openai:/gpt-4.1-mini``, with the provider credentials in the
        environment, e.g. ``OPENAI_API_KEY`` and ``OPENAI_BASE_URL``. Judges
        are called one at a time, unless ``MLFLOW_GENAI_EVAL_MAX_WORKERS`` and
        ``MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS`` are set.

        Args:
            *guidelines: The rules that the keyword outputs must follow.
            judge_model: Optional MLflow model URI of the judge.
            scope: The traces to judge: those of the current ``test``,
                ``suite`` or of the whole ``run``.
            screenshots: Whether the judge sees the screenshots sent to the
                model.

        Returns:
            The evaluation metrics, e.g. ``guidelines/mean`` for the share of
            traces that follow the guidelines, ``tool_calls/mean`` for the
            share of traces with the expected tool calls.

        Example:
            | ${metrics}=    Evaluate Llm Traces
            | ...    The reasoning must describe the visible window.
            | ...    A missing object must not be reported as found.
            | Should Be True    ${metrics}[guidelines/mean] >= 0.8
            | Evaluate Llm Traces    The answer is polite.    screenshots=False
            | Multiple Step Action    compute 6 times 7
            | Log Llm Expectation    expected_tool_calls
            | ...    ${{["Move Pointer To Proportional", "Click Pointer Button"] * 4}}
            | ${metrics}=    Evaluate Llm Traces    scope=test
            | Should Be Equal As Numbers    ${metrics}[tool_calls/mean]    1
        """
        judge_env: dict[str, str | None] = {}
        if judge_model is None:
            judge_model = f"openai:/{self.model}"
            judge_env = {
                "OPENAI_BASE_URL": self.server_url,
                # Takes precedence over OPENAI_BASE_URL
                "OPENAI_API_BASE": None,
                "OPENAI_API_KEY": os.getenv(self.api_key_env) or "unused",
            }
        return self.tracer.evaluate(
            list(guidelines), judge_model, scope, judge_env, screenshots
        )

    def _encode_image(self, image: Image.Image) -> str:
        """
        Reads an image file and returns a base64 string.

        Args:
            image: The image to encode.
        Returns:
            The base64 encoded image string.
        """

        b64 = to_base64(image, format=self.image_format)
        return f"data:image/{self.image_format.lower()};base64,{b64}"

    def _coordinate_prompt(self, prompt: str, image: Image.Image) -> str:
        """
        Fill in the ``{coordinate_rule}`` placeholder of a system prompt.

        Args:
            prompt: The system prompt.
            image: The screenshot sent with the prompt.

        Returns:
            The prompt, telling the model the screenshot size and to report
            the coordinate frame of its points; models with a native
            coordinate system are only asked for that one.
        """
        native = self._native_frame()
        width, height = image.size
        if native == "grid":
            rule = (
                "Give point_2d on a normalized 1000x1000 grid over the "
                "screenshot, where [0, 0] is the top-left and [1000, 1000] "
                "the bottom-right. Set point_frame to null."
            )
            return prompt.replace("{coordinate_rule}", rule)
        if native == "pixels":
            rule = (
                f"Give point_2d in pixels of the {width}x{height} "
                "screenshot, where [0, 0] is the top-left and "
                f"[{width}, {height}] the bottom-right. Set point_frame to "
                "null."
            )
            return prompt.replace("{coordinate_rule}", rule)
        rule = (
            "Give point_2d on a 1000x1000 grid over the screenshot, where "
            "[0, 0] is the top-left and [1000, 1000] the bottom-right, and "
            "set point_frame to [1000, 1000]. The screenshot is "
            f"{width}x{height} pixels: if you give point_2d in its pixels "
            f"instead, set point_frame to [{width}, {height}]. Use null for "
            "both when no point applies."
        )
        return prompt.replace("{coordinate_rule}", rule)

    def _native_frame(self) -> str | None:
        """
        Get the coordinate system the model is trained on, if it belongs to a
        family in NATIVE_FRAMES.

        Returns:
            "grid", "pixels", or None if the model reports its frame.
        """
        model = re.sub(r"[-._]", "", self.model.lower())
        return next(
            (
                kind
                for family, kind in NATIVE_FRAMES.items()
                if family in model
            ),
            None,
        )

    def _to_proportional(
        self, response: dict[str, Any], image: Image.Image
    ) -> list[float] | None:
        """
        Convert the ``point_2d`` of a model response from its ``point_frame``
        to proportional coordinates. Models with a native coordinate system are
        read in it, whatever frame they report.

        Args:
            response: The parsed model response.
            image: The screenshot sent with the prompt.

        Returns:
            The point as proportional ``[x, y]``, or None if there is no
            point.
        """
        point = response.get("point_2d")
        if point is None:
            return None
        grid = (GRID_SIZE, GRID_SIZE)
        native = self._native_frame()
        if native == "grid":
            frame = grid
        elif native == "pixels":
            frame = image.size
        else:
            frame = response.get("point_frame") or grid
        return normalize_point(point, frame)

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
    @_traced(CHAIN)
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

        Example:
            | ${result}=    Check For Visual Corruption
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
        self.tracer.set_outputs(parsed)

        if parsed["corrupted"]:
            log_image(
                image, "Corrupted image detected: " + parsed["description"]
            )
            self.tracer.log_image(image, "Corrupted image")
            raise VQAValidationError(
                f"Image is corrupted: {parsed['description']}"
            )
        return parsed

    @_traced(PARSER)
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
        self.tracer.feedback(
            "valid_json_first_try", not errors, rationale=errors
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
        # Models often omit nullable keys instead of writing null, but unknown
        # keys (e.g. bbox_2d for point_2d) need the correction path instead.
        if parsed_output.keys() <= required_keys.keys():
            for key, expected_types in required_keys.items():
                if type(None) in expected_types:
                    parsed_output.setdefault(key, None)

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
    @_traced(CHAIN)
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

        Example:
            | ${point}=    Get Object Position    the Continue button
        """
        if image is None:
            image = await self._grab_screenshot()
        else:
            image = to_image(image)

        system_prompt = textwrap.dedent("""
            You are a GUI localization agent. Given an object description and a
            screenshot, identify the object's location in the screenshot.

            Return only a valid JSON object with this exact schema:
            {"point_2d": [x, y], "point_frame": [width, height]}
            or:
            {"point_2d": null, "point_frame": null}
            if the object is not present or not confidently identified.

            Rules:
            - {coordinate_rule}
            - Return the approximate center point of the described object.
            - Coordinates must be integers.
            - If the object is partially visible, return the center of the
              visible portion.
            - If multiple matching objects are present, return the best match
              based on the description and surrounding context.
            - If the object is not visible, or you are not confident it is
              present, return: {"point_2d": null, "point_frame": null}
            - Do not guess. Prefer null over a low-confidence false
              positive.
            - Do not include markdown, explanations, comments, or any text
              outside the JSON object.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=f"Find the position of this object: {description}",
            image=image,
            system_prompt=self._coordinate_prompt(
                custom_system_prompt or system_prompt, image
            ),
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {
                "point_2d": [list, type(None)],
                "point_frame": [list, type(None)],
            },
        )
        logger.info(f"LLM response: {llm_output}")
        point = self._to_proportional(parsed, image)
        if point is None:
            raise VQADetectionError(f"Object was not found: {description}")

        debug = os.getenv("YARF_LOG_LEVEL") == "DEBUG"
        if debug or self.tracer.enabled:
            annotated = draw_point_on_image(image, point, label=description)
            if debug:
                log_image(annotated, f"LLM indicated point for: {description}")
            self.tracer.log_image(annotated, "LLM indicated point")

        return point

    @keyword
    @_traced(CHAIN)
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

        Example:
            | Assert State    a Continue button is visible
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
        self.tracer.set_outputs(parsed)

        if not parsed["matches_description"]:
            log_image(image=image, msg="Current state")
            self.tracer.log_image(image, "Current state")
            raise AssertionError(
                f"State does NOT match description: {description}. "
                f"Reasoning: {parsed['reasoning']}"
            )

    @keyword
    @_traced(CHAIN)
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
            The next GUI action, a dict with ``action_type``, ``text`` and
            ``point``. For pointer-based actions, ``point`` is the
            proportional ``[x, y]`` position on the screenshot, e.g.
            ``[0.5, 0.5]`` for its center; otherwise it is None.

        Example:
            | ${action}=    Get Single Gui Action    click the Continue button
        """

        if image is None:
            image = await self._grab_screenshot()
        else:
            image = to_image(image)

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
                its coordinates.

            action_type: Right Click, text: null, point_2d: [x, y]
                Explanation: Right click a specific UI element and provide
                its coordinates.

            action_type: Double Click, text: null, point_2d: [x, y]
                Explanation: Double click a specific UI element and provide
                its coordinates.

            action_type: Write, text: Text to enter, point_2d: null
                Explanation: Type text without moving the pointer.

            action_type: Scroll Down, text: null, point_2d: [x, y]
                Explanation: Scroll down with the mouse wheel over the given
                point to reveal content below the visible area.

            action_type: Scroll Up, text: null, point_2d: [x, y]
                Explanation: Scroll up with the mouse wheel over the given
                point to reveal content above the visible area.

            action_type: Press Key, text: Key name, point_2d: null
                Explanation: Press a key or a key combination, using X keysym
                names joined by "+", e.g. "Return", "Escape", "Tab" or
                "Control_L+l".

            action_type: Failed, text: null, point_2d: null
                Explanation: An action is impossible and cannot be performed.
                This should whenever the model can't determine a valid action.

            Return only a valid JSON object with this exact schema:
            {
                "action_type": "one of the available action types",
                "text": "text to write or key to press, or null if not applicable",
                "point_2d": [x, y],
                "point_frame": [width, height]
            }

            Rules:
            - {coordinate_rule}
            - Use null when coordinates are not applicable.
            - Do not add markdown syntax or any other text.
            - If you determine that the task cannot be completed, return:
              {"action_type": "Failed", "text": null, "point_2d": null,
              "point_frame": null}.
            """)

        llm_output = await asyncio.to_thread(
            self.prompt_llm,
            prompt=task,
            image=image,
            system_prompt=self._coordinate_prompt(
                custom_system_prompt or system_prompt, image
            ),
        )

        parsed = await self._verify_llm_json_response(
            llm_output,
            {
                "action_type": [str],
                "point_2d": [list, type(None)],
                "point_frame": [list, type(None)],
                "text": [str, type(None)],
            },
        )
        logger.info(f"LLM proposed action: {llm_output}")

        action = {
            "action_type": parsed["action_type"],
            "text": parsed["text"],
            "point": self._to_proportional(parsed, image),
        }
        self.validate_gui_action(action, task)
        return action

    def validate_gui_action(self, action: dict[str, Any], task: str) -> None:
        """
        Validate a GUI action dictionary.

        Args:
            action: A dict containing action_type, text, and point.
            task: The task description provided to the LLM.

        Raises:
            ValueError: If the action type is unsupported or if required fields
                are missing.
        """

        allowed_actions = POINTER_ACTIONS | {
            "Write",
            "Press Key",
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

        if action_type in {"Write", "Press Key"} and not isinstance(
            action.get("text"), str
        ):
            raise ValueError(f"{action_type} actions must include text.")

        if action_type == "Press Key" and not all(
            key.strip() for key in action["text"].split("+")
        ):
            raise ValueError(
                f"Invalid key combination for Press Key: {action['text']!r}"
            )

        if action_type in POINTER_ACTIONS and not isinstance(
            action.get("point"), list
        ):
            raise ValueError(f"{action_type} actions must include a point.")

    @keyword
    @_traced(CHAIN)
    async def execute_gui_action(
        self, action: dict[str, Any], description: str = ""
    ) -> None:
        """
        Execute a GUI action as specified by the LLM response.

        When tracing, each HID keyword the action calls is recorded as a tool
        call with its arguments, e.g. ``Move Pointer To Proportional`` then
        ``Click Pointer Button`` for a ``Left Click``.

        Args:
            action: A dict containing the action_type, text and point, the
                proportional ``[x, y]`` position on the screen, e.g.
                ``[0.5, 0.5]`` for its center.
            description: The description provided to the LLM.

        Raises:
            ValueError: If the action type is unsupported or if required fields
                are missing.

        Example:
            | ${action}=    Get Single Gui Action    click the Continue button
            | Execute Gui Action    ${action}    click the Continue button
            | ${action}=    Create Dictionary    action_type=Left Click
            | ...    text=${None}    point=${{[0.5, 0.5]}}
            | Execute Gui Action    ${action}
        """
        self.validate_gui_action(action, description)
        action_type = action["action_type"]
        debug = os.getenv("YARF_LOG_LEVEL") == "DEBUG"
        capture = debug or self.tracer.enabled

        logger.info(f"Executing action: {action}")

        if action_type in POINTER_ACTIONS:
            x, y = normalize_point(action["point"], (1, 1))
            if capture:
                image = await self._grab_screenshot()
                label = action.get("description", action_type)
                annotated = draw_point_on_image(image, [x, y], label=label)
                if debug:
                    log_image(
                        annotated,
                        f"LLM indicated action point for: {label}",
                    )
                self.tracer.log_image(annotated, "Action point")

            await self._hid("move_pointer_to_proportional", x, y)
            await asyncio.sleep(0.5)

            if action_type == "Left Click":
                await self._hid("click_pointer_button", "LEFT")
            elif action_type == "Right Click":
                await self._hid("click_pointer_button", "RIGHT")
            elif action_type == "Double Click":
                await self._hid("click_pointer_button", "LEFT")
                await asyncio.sleep(0.1)
                await self._hid("click_pointer_button", "LEFT")
            elif action_type == "Scroll Down":
                await self._hid("scroll_pointer_wheel", SCROLL_STEPS)
            elif action_type == "Scroll Up":
                await self._hid("scroll_pointer_wheel", -SCROLL_STEPS)

        elif action_type == "Write":
            await self._hid("type_string", action["text"])

        elif action_type == "Press Key":
            await self._hid(
                "keys_combo",
                [
                    KEY_ALIASES.get(key.strip().lower(), key.strip())
                    for key in action["text"].split("+")
                ],
            )

        elif action_type == "Wait":
            # For now, this is a fixed wait.
            await asyncio.sleep(5)

        else:
            raise ValueError(f"Unsupported GUI action: {action_type}")

        if capture:
            # Wait for a moment to let the screen update after the action
            await asyncio.sleep(1)
            image = await self._grab_screenshot()
            if debug:
                logger.info(f"Executed action: {action_type}")
                log_image(image=image, msg="Screenshot after executing action")
            self.tracer.log_image(image, "Screenshot after action")

    async def _hid(self, method: str, *args: Any) -> None:
        """
        Call a keyword of the HID library, recorded as a tool call named after
        the keyword, with its arguments as inputs.

        Args:
            method: The name of the HID method, e.g. ``click_pointer_button``.
            *args: The arguments of the keyword.
        """
        hid = self._get_lib_instance("HID")
        # Bound on HidBase, as the platform libraries share its signatures
        arguments = (
            inspect.signature(getattr(HidBase, method))
            .bind(hid, *args)
            .arguments
        )
        arguments.pop("self")
        with self.tracer.span(keyword_name(method), TOOL, inputs=arguments):
            await getattr(hid, method)(*args)

    @keyword
    @_traced(AGENT)
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

        Example:
            | Multiple Step Action    click the Continue button    max_steps=10
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
        Explanation: Left click a specific UI element and provide its
        coordinates.

        action_type: Right Click, text: null, point_2d: [x, y]
        Explanation: Right click a specific UI element and provide its
        coordinates.

        action_type: Double Click, text: null, point_2d: [x, y]
        Explanation: Double click a specific UI element and provide its
        coordinates.

        action_type: Write, text: Text to enter, point_2d: null
        Explanation: Type text using the keyboard. Use this only when a text
        field is already focused.

        action_type: Press Key, text: Key name, point_2d: null
        Explanation: Press a key or a key combination, using X keysym names
        joined by "+", e.g. "Return" to submit a field, "Escape", "Tab" or
        "Control_L+l".

        action_type: Scroll Down, text: null, point_2d: [x, y]
        Explanation: Scroll down with the mouse wheel over the given point to
        reveal content below the visible area.

        action_type: Scroll Up, text: null, point_2d: [x, y]
        Explanation: Scroll up with the mouse wheel over the given point to
        reveal content above the visible area.

        action_type: Wait, text: null, point_2d: null
        Explanation: Wait briefly when the UI is loading, processing,
        animating, or a task is not ready yet.

        action_type: Finish, text: null, point_2d: null
        Explanation: Mark the task as completed when the visible UI confirms
        the goal is done.

        Coordinate rules:
        - {coordinate_rule}
        - For pointer actions, choose the center of the target UI element.
        - For Write, Press Key, Wait, and Finish, always use null.

        Behavior rules:
        - Each step should contain a description of the chosen action to help
          guide the next step.
        - Be deliberate. Prefer one precise action at a time.
        - Do not repeat the same failed click endlessly; use history to adjust.
        - If a field must be typed into, first click/focus it, then on the next
          step use Write. Check the typed text in the next screenshot, then
          submit it with Press Key "Return" if needed.
        - If the target is not visible, e.g. a button below the visible
          area, use Scroll Down or Scroll Up over the area that contains it.
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
            "text": "text to write or key to press, or null",
            "point_2d": [x, y],
            "point_frame": [width, height]
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
            with self.tracer.span(
                f"Step {step}", CHAIN, inputs={"prompt": llm_prompt}
            ) as span:
                history_item = await self._run_step(
                    step,
                    llm_prompt,
                    system_prompt=custom_system_prompt or system_prompt,
                )
                span.set_outputs(history_item.action)
            history.append(history_item)
            self.tracer.set_outputs(
                {"actions": [item.action for item in history]}
            )

            if history_item.action["action_type"] == "Finish":
                self.tracer.feedback("steps", step)
                logger.info(
                    f"Task finished successfully in {step} steps. History:\n"
                    + "\n".join(str(item) for item in history)
                )
                return

        # Grab a final screenshot to log the end state
        image = await self._grab_screenshot()
        log_image(image, msg="Final screenshot after multiple step action")
        self.tracer.log_image(image, "Final screenshot")

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
                    system_prompt=self._coordinate_prompt(
                        system_prompt, image
                    ),
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
                        "point_frame": [list, type(None)],
                    },
                )
                if action["action_type"] != "Finish":
                    description = action.get("description", "No description")
                    # The history keeps the model's own coordinates
                    await self.execute_gui_action(
                        {
                            **action,
                            "point": self._to_proportional(action, image),
                        },
                        description,
                    )
                    await asyncio.sleep(1)

                return HistoryItem(step=step, action=action)

            except Exception as e:
                logger.error(
                    "Error while processing step "
                    f"{step}, attempt {attempt + 1}: {e}"
                )

        raise RuntimeError(
            "Failed to get a valid action from the LLM after "
            f"{MAX_ATTEMPTS} attempts on step {step}."
        )
