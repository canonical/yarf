# LlmClient

<p>This class provides the Robot interface for llm interactions with an LLM server.</p>

- **Type**: LIBRARY
- **Scope**: TEST

## Keywords

### Assert State

<p>Assert that the screen matches a state description.</p>
<p>Args: description: Description of the expected screen state. image: Image to inspect. If omitted, a screenshot is grabbed. custom_system_prompt: Optional system prompt override.</p>
<p>Raises: AssertionError: If the state does not match the description.</p>

#### Positional and named arguments

| Name                 | Type   | Default Value | Kind                | Required |
| -------------------- | ------ | ------------- | ------------------- | -------- |
| description          | string |               | POSITIONAL_OR_NAMED | Yes      |
| image                | None   | None          | POSITIONAL_OR_NAMED | No       |
| custom_system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       |

<hr style="border:1px solid grey">

### Check For Visual Corruption

<p>Detect if an image is corrupted.</p>
<p>Args: image: The image to check. If no image is provided, a new screenshot is grabbed. custom_prompt: Optional custom prompt to guide the LLM.</p>
<p>Returns: A dict containing the LLM's assessment of whether the image is corrupted and a description.</p>
<p>Raises: VQAValidationError: If the image is assessed as corrupted by the LLM.</p>

### Return

{'name': 'dict', 'typedoc': 'dictionary', 'nested': \[{'name': 'str', 'typedoc': 'string', 'nested': [], 'union': False}, {'name': 'Any', 'typedoc': 'Any', 'nested': [], 'union': False}\], 'union': False}

#### Positional and named arguments

| Name          | Type | Default Value | Kind                | Required |
| ------------- | ---- | ------------- | ------------------- | -------- |
| image         | None | None          | POSITIONAL_OR_NAMED | No       |
| custom_prompt | None | None          | POSITIONAL_OR_NAMED | No       |

<hr style="border:1px solid grey">

### Configure Llm Client

<p>Configure the LLM client with the given parameters.</p>
<p>Args: **kwargs: Configuration parameters for the LLM client.</p>
<p>Raises: TypeError: If unknown parameters are provided. ValueError: If parameter values are of incorrect type.</p>

#### Positional and named arguments

| Name   | Type | Default Value | Kind      | Required |
| ------ | ---- | ------------- | --------- | -------- |
| kwargs | Any  |               | VAR_NAMED | No       |

<hr style="border:1px solid grey">

### Execute Gui Action

<p>Execute a GUI action as specified by the LLM response.</p>
<p>Args: action: A dict containing the action_type, text, and point_2d.</p>
<p>Raises: ValueError: If the action type is unsupported or if required fields are missing.</p>

#### Positional and named arguments

| Name   | Type       | Default Value | Kind                | Required |
| ------ | ---------- | ------------- | ------------------- | -------- |
| action | dictionary |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Get Object Position

<p>Get the position of an object on the screen in relative coordinates.</p>
<p>Args: description: Description of the object to locate. image: Image to inspect. If omitted, a screenshot is grabbed. custom_system_prompt: Optional system prompt override.</p>
<p>Returns: The object position as normalized relative coordinates <code>[x, y]</code>, where each value is typically in the range <code>0..1</code>.</p>
<p>Raises: VQAValidationError: If the LLM indicates that the object was not</p>

### Return

{'name': 'list', 'typedoc': 'list', 'nested': \[{'name': 'Any', 'typedoc': 'Any', 'nested': [], 'union': False}\], 'union': False}

#### Positional and named arguments

| Name                 | Type   | Default Value | Kind                | Required |
| -------------------- | ------ | ------------- | ------------------- | -------- |
| description          | string |               | POSITIONAL_OR_NAMED | Yes      |
| image                | None   | None          | POSITIONAL_OR_NAMED | No       |
| custom_system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       |

<hr style="border:1px solid grey">

### Get Single Gui Action

<p>Get a single GUI action from the LLM.</p>
<p>Args: task: The task description to provide to the LLM. image: Image to inspect. If omitted, a screenshot is grabbed. custom_system_prompt: Optional system prompt override.</p>
<p>Returns: The next GUI action as returned by the LLM. For pointer-based actions, <span class="name">point_2d</span> contains the raw coordinates from the LLM's 1000x1000 grid. Raises: ValueError: If the LLM response contains an unsupported action type or is missing required fields.</p>

### Return

{'name': 'dict', 'typedoc': 'dictionary', 'nested': \[{'name': 'str', 'typedoc': 'string', 'nested': [], 'union': False}, {'name': 'Any', 'typedoc': 'Any', 'nested': [], 'union': False}\], 'union': False}

#### Positional and named arguments

| Name                 | Type   | Default Value | Kind                | Required |
| -------------------- | ------ | ------------- | ------------------- | -------- |
| task                 | string |               | POSITIONAL_OR_NAMED | Yes      |
| image                | None   | None          | POSITIONAL_OR_NAMED | No       |
| custom_system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       |

<hr style="border:1px solid grey">

### Prompt Llm

<p>Send a prompt (text-only or text+image) to the LLM and get the response.</p>
<p>Args: prompt: The text prompt to send to the LLM. image: Optional image (PIL Image or path) to include in the prompt. system_prompt: Optional system prompt to guide the LLM.</p>
<p>Returns: The response from the LLM.</p>

### Return

{'name': 'str', 'typedoc': 'string', 'nested': [], 'union': False}

#### Positional and named arguments

| Name          | Type   | Default Value | Kind                | Required |
| ------------- | ------ | ------------- | ------------------- | -------- |
| prompt        | string |               | POSITIONAL_OR_NAMED | Yes      |
| image         | None   | None          | POSITIONAL_OR_NAMED | No       |
| system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       |
