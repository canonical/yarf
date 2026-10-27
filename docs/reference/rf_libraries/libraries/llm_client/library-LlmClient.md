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
<p>Supported parameters are <code>model</code>, <code>server_url</code>, <code>endpoint</code>, <code>max_tokens</code>, <code>api_key_env</code>, <code>image_format</code>, <code>collect_usage</code>, <code>tracing</code>, <code>experiment</code> and <code>provider</code>.</p>
<p><code>provider</code> applies a preset for a hosted service, which explicit parameters override:</p>
<ul>
<li><code>openrouter</code>: OpenRouter, key read from <code>OPENROUTER_API_KEY</code>.</li>
<li><code>copilot</code>: GitHub Copilot, key read from <code>GITHUB_TOKEN</code> (e.g. <code>export GITHUB_TOKEN=$(gh auth token)</code>).</li>
<li><code>gemini</code>: Google Gemini API, key read from <code>GEMINI_API_KEY</code>.</li>
</ul>
<p>The API key is sent as a bearer token and read from the environment variable named by <code>api_key_env</code> (default <code>YARF_LLM_API_KEY</code>), so that it never appears in the Robot logs. No <code>Authorization</code> header is sent if the variable is unset.</p>
<p>Models that only support the OpenAI Responses API can be used by setting <code>endpoint=/responses</code>. For models that do not accept WEBP images, set <code>image_format</code> to <code>PNG</code> or <code>JPEG</code>.</p>
<p>Set <code>collect_usage=True</code> to record the token usage, inference time and cost of each request, see <a class="name" href="#get-llm-usage" title='"Get Llm Usage" keyword'>Get Llm Usage</a>. It is off by default.</p>
<p>Set <code>tracing=True</code> to record each LLM keyword as an MLflow trace, in the experiment named by <code>experiment</code> (default <code>yarf</code>). A trace shows the prompts and screenshots sent to the model, its answers, token usage, latency, response parsing and the GUI actions taken. Traces are tagged with the Robot suite and test, grouped in one session per test, and get automatic feedback such as <code>keyword_passed</code> and <code>valid_json_first_try</code>. Attach your own with <a class="name" href="#log-llm-feedback" title='"Log Llm Feedback" keyword'>Log Llm Feedback</a> and <a class="name" href="#log-llm-expectation" title='"Log Llm Expectation" keyword'>Log Llm Expectation</a>, and judge them with <a class="name" href="#evaluate-llm-traces" title='"Evaluate Llm Traces" keyword'>Evaluate Llm Traces</a>. Tracing requires <code>pip install yarf[mlflow]</code>. Traces are sent to <code>MLFLOW_TRACKING_URI</code> if set, otherwise to <code>mlflow.db</code> in the Robot output directory, viewed with <code>mlflow ui --backend-store-uri <a href="sqlite:///&lt;outdir&gt;/mlflow.db&lt;/code&gt;">sqlite:///&lt;outdir&gt;/mlflow.db</a></code>.</p>

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
Configure Llm Client    provider=gemini    model=gemini-2.5-flash
Configure Llm Client    collect_usage=True
Configure Llm Client    tracing=True    experiment=installer
```

<hr style="border:1px solid grey">

### Evaluate Llm Traces

<p>Evaluate the LLM traces against guidelines with an LLM judge, and against their expected tool calls. Requires <code>tracing=True</code> in <a class="name" href="#configure-llm-client" title='"Configure Llm Client" keyword'>Configure Llm Client</a>.</p>
<p>The judge reads the keyword inputs and outputs of each trace, the GUI actions it took in order, and looks at the screenshots sent to the model, then decides whether they follow all the guidelines. Its verdict and rationale are attached to the traces as a <code>guidelines</code> feedback, and the evaluation is logged as an MLflow run. Traces without an LLM request, such as those of <a class="name" href="#execute-gui-action" title='"Execute Gui Action" keyword'>Execute Gui Action</a>, are not judged. An answer other than yes or no is recorded as an error, and left out of the metrics.</p>
<p>The trajectory of the traces with an <code>expected_tool_calls</code> expectation, see <a class="name" href="#log-llm-expectation" title='"Log Llm Expectation" keyword'>Log Llm Expectation</a>, is checked without an LLM: the HID keywords called by the GUI actions must match the expected ones, in order. An expected call is a keyword name, e.g. <code>Click Pointer Button</code>, or a dict with a <code>name</code> and the <code>arguments</code> to compare, e.g. <code>{"name": "Type String", "arguments": {"string": "42"}}</code>. The result is a <code>tool_calls</code> feedback, with the mismatches as rationale. Guidelines are optional when such expectations are logged.</p>
<p>Seeing the screenshots requires a vision model as the judge. Set <code>screenshots=False</code> for a text-only judge, or to save tokens on traces with many screenshots, e.g. from <a class="name" href="#multiple-step-action" title='"Multiple Step Action" keyword'>Multiple Step Action</a>.</p>
<p>By default the judge is the configured model on the configured server. Any MLflow model URI can be used instead, e.g. <code>openai:/gpt-4.1-mini</code>, with the provider credentials in the environment, e.g. <code>OPENAI_API_KEY</code> and <code>OPENAI_BASE_URL</code>. Judges are called one at a time, unless <code>MLFLOW_GENAI_EVAL_MAX_WORKERS</code> and <code>MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS</code> are set.</p>

#### Return

```
dictionary[string, Any]
```

<p>The evaluation metrics, e.g. <code>guidelines/mean</code> for the share of traces that follow the guidelines, <code>tool_calls/mean</code> for the share of traces with the expected tool calls.</p>

#### Positional and named arguments

| Name        | Type    | Default Value | Kind           | Required | Documentation                                                                                                     |
| ----------- | ------- | ------------- | -------------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| guidelines  | string  |               | VAR_POSITIONAL | No       | The rules that the keyword outputs must follow.                                                                   |
| judge_model | None    | None          | NAMED_ONLY     | No       | Optional MLflow model URI of the judge.                                                                           |
| scope       | string  | suite         | NAMED_ONLY     | No       | The traces to judge: those of the current <code>test</code>, <code>suite</code> or of the whole <code>run</code>. |
| screenshots | boolean | True          | NAMED_ONLY     | No       | Whether the judge sees the screenshots sent to the model.                                                         |

#### Example

```robotframework
${metrics}=    Evaluate Llm Traces
...    The reasoning must describe the visible window.
...    A missing object must not be reported as found.
Should Be True    ${metrics}[guidelines/mean] >= 0.8
Evaluate Llm Traces    The answer is polite.    screenshots=False
Multiple Step Action    compute 6 times 7
Log Llm Expectation    expected_tool_calls
...    ${{["Move Pointer To Proportional", "Click Pointer Button"] * 4}}
${metrics}=    Evaluate Llm Traces    scope=test
Should Be Equal As Numbers    ${metrics}[tool_calls/mean]    1
```

<hr style="border:1px solid grey">

### Execute Gui Action

<p>Execute a GUI action as specified by the LLM response.</p>
<p>When tracing, each HID keyword the action calls is recorded as a tool call with its arguments, e.g. <code>Move Pointer To Proportional</code> then <code>Click Pointer Button</code> for a <code>Left Click</code>.</p>

#### Return

```
None
```

#### Raises

- `ValueError`: If the action type is unsupported or if required fields are missing.

#### Positional and named arguments

| Name        | Type       | Default Value | Kind                | Required | Documentation                                                                                                                                                |
| ----------- | ---------- | ------------- | ------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| action      | dictionary |               | POSITIONAL_OR_NAMED | Yes      | A dict containing the action_type, text and point, the proportional <code>[x, y]</code> position on the screen, e.g. <code>[0.5, 0.5]</code> for its center. |
| description | string     |               | POSITIONAL_OR_NAMED | No       | The description provided to the LLM.                                                                                                                         |

#### Example

```robotframework
${action}=    Get Single Gui Action    click the Continue button
Execute Gui Action    ${action}    click the Continue button
${action}=    Create Dictionary    action_type=Left Click
...    text=${None}    point=${{[0.5, 0.5]}}
Execute Gui Action    ${action}
```

<hr style="border:1px solid grey">

### Get Llm Usage

<p>Get the accumulated usage of all LLM requests made by this library instance, e.g. during the current test. Requires <code>collect_usage=True</code> in <a class="name" href="#configure-llm-client" title='"Configure Llm Client" keyword'>Configure Llm Client</a>.</p>
<p><code>inference_time</code> is the summed wall-clock time of the requests in seconds, including network latency. Retries of transient server errors are counted separately in <code>retries</code>; only the final attempt of each request counts in <code>requests</code> and <code>inference_time</code>. <code>cost</code> (OpenRouter credits) and <code>nano_aiu</code> (Copilot billing units) are <code>None</code> if the server does not report them.</p>

#### Return

```
dictionary[string, Any]
```

<p>A dict with the model, number of requests and retries, token counts, inference time, output throughput and cost.</p>

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

<p>The next GUI action, a dict with <code>action_type</code>, <code>text</code> and <code>point</code>. For pointer-based actions, <code>point</code> is the proportional <code>[x, y]</code> position on the screenshot, e.g. <code>[0.5, 0.5]</code> for its center; otherwise it is None.</p>

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

### Log Llm Expectation

<p>Attach an expectation, the ground truth, to the last LLM trace of the current test. Requires <code>tracing=True</code> in <a class="name" href="#configure-llm-client" title='"Configure Llm Client" keyword'>Configure Llm Client</a>.</p>
<p>Expectations turn traces into an evaluation dataset, e.g. for judges that compare the output with the expected facts.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name  | Type   | Default Value | Kind                | Required | Documentation         |
| ----- | ------ | ------------- | ------------------- | -------- | --------------------- |
| name  | string |               | POSITIONAL_OR_NAMED | Yes      | The expectation name. |
| value | Any    |               | POSITIONAL_OR_NAMED | Yes      | The expected value.   |

#### Example

```robotframework
${action}=    Get Single Gui Action    click the OK button
Log Llm Expectation    expected_action    Left Click
```

<hr style="border:1px solid grey">

### Log Llm Feedback

<p>Attach a feedback, a judgement of the result, to the last LLM trace of the current test. Requires <code>tracing=True</code> in <a class="name" href="#configure-llm-client" title='"Configure Llm Client" keyword'>Configure Llm Client</a>.</p>
<p>MLflow aggregates feedback per name, e.g. to compare the accuracy of prompts or models across runs.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name      | Type   | Default Value | Kind                | Required | Documentation                                  |
| --------- | ------ | ------------- | ------------------- | -------- | ---------------------------------------------- |
| name      | string |               | POSITIONAL_OR_NAMED | Yes      | The feedback name.                             |
| value     | Any    |               | POSITIONAL_OR_NAMED | Yes      | The feedback value, e.g. a boolean or a score. |
| rationale | None   | None          | POSITIONAL_OR_NAMED | No       | Optional explanation of the value.             |

#### Example

```robotframework
${point}=    Get Object Position    the OK button
${ok}=    Evaluate    0.4 < ${point}[0] < 0.6
Log Llm Feedback    found_ok_button    ${ok}
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
