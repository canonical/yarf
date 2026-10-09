# LlmClient

<p>This class provides the Robot interface for llm interactions with an LLM server.</p>

- **Type**: LIBRARY
- **Scope**: TEST

## Keywords

### Assert State

<p>Assert that the screen matches a state description.</p>

#### Return

```
None
```

#### Raises

- `AssertionError`: If the state does not match the description.

#### Positional and named arguments

| Name                 | Type   | Default Value | Kind                | Required | Documentation                                          |
| -------------------- | ------ | ------------- | ------------------- | -------- | ------------------------------------------------------ |
| description          | string |               | POSITIONAL_OR_NAMED | Yes      | Description of the expected screen state.              |
| image                | None   | None          | POSITIONAL_OR_NAMED | No       | Image to inspect. If omitted, a screenshot is grabbed. |
| custom_system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       | Optional system prompt override.                       |

#### Example

```robotframework
Assert State    a Continue button is visible
```

<hr style="border:1px solid grey">

### Check For Visual Corruption

<p>Detect if an image is corrupted.</p>

#### Return

```
dictionary[string, Any]
```

<p>A dict containing the LLM's assessment of whether the image is corrupted and a description.</p>

#### Raises

- `VQAValidationError`: If the image is assessed as corrupted by the LLM.

#### Positional and named arguments

| Name          | Type | Default Value | Kind                | Required | Documentation                                                             |
| ------------- | ---- | ------------- | ------------------- | -------- | ------------------------------------------------------------------------- |
| image         | None | None          | POSITIONAL_OR_NAMED | No       | The image to check. If no image is provided, a new screenshot is grabbed. |
| custom_prompt | None | None          | POSITIONAL_OR_NAMED | No       | Optional custom prompt to guide the LLM.                                  |

#### Example

```robotframework
${result}=    Check For Visual Corruption
```

<hr style="border:1px solid grey">

### Configure Llm Client

<p>Configure the LLM client with the given parameters.</p>
<p>Supported parameters are <code>model</code>, <code>server_url</code>, <code>endpoint</code>, <code>max_tokens</code>, <code>api_key_env</code>, <code>image_format</code>, <code>collect_usage</code> and <code>provider</code>.</p>
<p><code>provider</code> applies a preset for a hosted service, which explicit parameters override:</p>
<ul>
<li><code>openrouter</code>: OpenRouter, key read from <code>OPENROUTER_API_KEY</code>.</li>
<li><code>copilot</code>: GitHub Copilot, key read from <code>GITHUB_TOKEN</code> (e.g. <code>export GITHUB_TOKEN=$(gh auth token)</code>).</li>
</ul>
<p>The API key is sent as a bearer token and read from the environment variable named by <code>api_key_env</code> (default <code>YARF_LLM_API_KEY</code>), so that it never appears in the Robot logs. No <code>Authorization</code> header is sent if the variable is unset.</p>
<p>Models that only support the OpenAI Responses API can be used by setting <code>endpoint=/responses</code>. For models that do not accept WEBP images, set <code>image_format</code> to <code>PNG</code> or <code>JPEG</code>.</p>
<p>Set <code>collect_usage=True</code> to record the token usage, inference time and cost of each request, see <a class="name" href="#get-llm-usage" title='"Get Llm Usage" keyword'>Get Llm Usage</a>. It is off by default.</p>

#### Return

```
None
```

#### Raises

- `TypeError`: If unknown parameters are provided.
- `ValueError`: If parameter values are of incorrect type or the provider is unknown.

#### Positional and named arguments

| Name   | Type | Default Value | Kind      | Required | Documentation                                |
| ------ | ---- | ------------- | --------- | -------- | -------------------------------------------- |
| kwargs | Any  |               | VAR_NAMED | No       | Configuration parameters for the LLM client. |

#### Example

```robotframework
Configure Llm Client
...    model=qwen3-vl:2b-instruct
...    server_url=http://localhost:11434/v1
Configure Llm Client    provider=copilot    model=gpt-4.1
Configure Llm Client    provider=openrouter
...    model=qwen/qwen3-vl-8b-instruct
Configure Llm Client    collect_usage=True
```

<hr style="border:1px solid grey">

### Execute Gui Action

<p>Execute a GUI action as specified by the LLM response.</p>

#### Return

```
None
```

#### Raises

- `ValueError`: If the action type is unsupported or if required fields are missing.

#### Positional and named arguments

| Name        | Type       | Default Value | Kind                | Required | Documentation                                          |
| ----------- | ---------- | ------------- | ------------------- | -------- | ------------------------------------------------------ |
| action      | dictionary |               | POSITIONAL_OR_NAMED | Yes      | A dict containing the action_type, text, and point_2d. |
| description | string     |               | POSITIONAL_OR_NAMED | No       | The description provided to the LLM.                   |

#### Example

```robotframework
${action}=    Get Single Gui Action    click the Continue button
Execute Gui Action    ${action}    click the Continue button
```

<hr style="border:1px solid grey">

### Get Llm Usage

<p>Get the accumulated usage of all LLM requests made by this library instance, e.g. during the current test. Requires <code>collect_usage=True</code> in <a class="name" href="#configure-llm-client" title='"Configure Llm Client" keyword'>Configure Llm Client</a>.</p>
<p><code>inference_time</code> is the summed wall-clock time of the requests in seconds, including network latency. <code>cost</code> (OpenRouter credits) and <code>nano_aiu</code> (Copilot billing units) are <code>None</code> if the server does not report them.</p>

#### Return

```
dictionary[string, Any]
```

<p>A dict with the model, number of requests, token counts, inference time, output throughput and cost.</p>

#### Example

```robotframework
Configure Llm Client    collect_usage=True
${usage}=    Get Llm Usage
Log    ${usage}[total_tokens]
```

<hr style="border:1px solid grey">

### Get Object Position

<p>Get the position of an object on the screen in relative coordinates.</p>

#### Return

```
list[float]
```

<p>The object position as normalized relative coordinates <code>[x, y]</code>, where each value is typically in the range <code>0..1</code>.</p>

#### Raises

- `VQADetectionError`: If the LLM indicates that the object was not

#### Positional and named arguments

| Name                 | Type   | Default Value | Kind                | Required | Documentation                                          |
| -------------------- | ------ | ------------- | ------------------- | -------- | ------------------------------------------------------ |
| description          | string |               | POSITIONAL_OR_NAMED | Yes      | Description of the object to locate.                   |
| image                | None   | None          | POSITIONAL_OR_NAMED | No       | Image to inspect. If omitted, a screenshot is grabbed. |
| custom_system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       | Optional system prompt override.                       |

#### Example

```robotframework
${point}=    Get Object Position    the Continue button
```

<hr style="border:1px solid grey">

### Get Single Gui Action

<p>Get a single GUI action from the LLM.</p>

#### Return

```
dictionary[string, Any]
```

<p>The next GUI action as returned by the LLM. For pointer-based actions, <span class="name">point_2d</span> contains the raw coordinates from the LLM's 1000x1000 grid.</p>

#### Positional and named arguments

| Name                 | Type   | Default Value | Kind                | Required | Documentation                                          |
| -------------------- | ------ | ------------- | ------------------- | -------- | ------------------------------------------------------ |
| task                 | string |               | POSITIONAL_OR_NAMED | Yes      | The task description to provide to the LLM.            |
| image                | None   | None          | POSITIONAL_OR_NAMED | No       | Image to inspect. If omitted, a screenshot is grabbed. |
| custom_system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       | Optional system prompt override.                       |

#### Example

```robotframework
${action}=    Get Single Gui Action    click the Continue button
```

<hr style="border:1px solid grey">

### Multiple Step Action

<p>Perform a multiple step action by prompting the LLM iteratively until a "Finish" action is returned.</p>

#### Return

```
None
```

#### Raises

- `RuntimeError`: If the LLM cannot finish within <code>max_steps</code>.

#### Positional and named arguments

| Name                 | Type    | Default Value | Kind                | Required | Documentation                                 |
| -------------------- | ------- | ------------- | ------------------- | -------- | --------------------------------------------- |
| task                 | string  |               | POSITIONAL_OR_NAMED | Yes      | The task description to complete.             |
| custom_system_prompt | None    | None          | POSITIONAL_OR_NAMED | No       | Optional system prompt override.              |
| max_steps            | integer | 50            | POSITIONAL_OR_NAMED | No       | Number of actions to attempt before stopping. |

#### Example

```robotframework
Multiple Step Action    click the Continue button    max_steps=10
```

<hr style="border:1px solid grey">

### Prompt Llm

<p>Send a prompt (text-only or text+image) to the LLM and get the response.</p>

#### Return

```
string
```

<p>The response from the LLM.</p>

#### Positional and named arguments

| Name          | Type   | Default Value | Kind                | Required | Documentation                                                |
| ------------- | ------ | ------------- | ------------------- | -------- | ------------------------------------------------------------ |
| prompt        | string |               | POSITIONAL_OR_NAMED | Yes      | The text prompt to send to the LLM.                          |
| image         | None   | None          | POSITIONAL_OR_NAMED | No       | Optional image (PIL Image or path) to include in the prompt. |
| system_prompt | None   | None          | POSITIONAL_OR_NAMED | No       | Optional system prompt to guide the LLM.                     |

#### Example

```robotframework
${answer}=    Prompt Llm    Describe the screen
${image}=    Grab Screenshot
${answer}=    Prompt Llm    What is shown?    ${image}
```
