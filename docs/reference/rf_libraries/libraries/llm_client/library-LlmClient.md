# LlmClient

<p>This class provides the Robot interface for llm interactions with an LLM server.</p>

- **Type**: LIBRARY
- **Scope**: TEST

## Keywords

### Configure Llm Client

<p>Configure the LLM client with the given parameters.</p>
<p>Args: **kwargs: Configuration parameters for the LLM client.</p>
<p>Raises: TypeError: If unknown parameters are provided. ValueError: If parameter values are of incorrect type.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| kwargs | Any |  | VAR_NAMED | No |
<hr style="border:1px solid grey">

### Prompt Llm

<p>Send a prompt (text-only or text+image) to the LLM and get the response.</p>
<p>Args: prompt: The text prompt to send to the LLM. image: Optional image (PIL Image or path) to include in the prompt. system_prompt: Optional system prompt to guide the LLM.</p>
<p>Returns: The response from the LLM.</p>

### Return

{'name': 'str', 'typedoc': 'string', 'nested': [], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| prompt | string |  | POSITIONAL_OR_NAMED | Yes |
| image | None | None | POSITIONAL_OR_NAMED | No |
| system_prompt | None | None | POSITIONAL_OR_NAMED | No |
