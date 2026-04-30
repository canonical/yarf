# Using the LLM client

The LLM Client library in YARF provides Robot Framework keywords for interacting
with Large Language Model servers that support the OpenAI Chat Completions API
format. This enables you to integrate AI capabilities into your test automation
workflows.

In this guide, we will cover:

1. [Setting up an LLM server](#setting-up-an-llm-server)
1. [Basic text prompting](#basic-text-prompting)
1. [Using images in prompts](#using-images-in-prompts)
1. [Using LLM GUI keywords](#using-llm-gui-keywords)
1. [Using multi-step GUI navigation](#using-multi-step-gui-navigation)
1. [Configuring the client](#configuring-the-client)

## Setting up an LLM server

The LLM Client is designed to work with any server that implements the OpenAI
Chat Completions API.

### Option 1: Inference Snap

**Inference snaps** are Canonical’s way of packaging AI models as snaps that are
tuned for efficient local inference. Each snap automatically detects your
machine’s available hardware (CPU/GPU/NPU) and selects a compatible runtime and
model optimizations.

They are an easy way to run an OpenAI-compatible LLM endpoint locally, which
makes them a great fit for YARF’s LLM Client. For this guide, you’ll install the
Qwen VL snap, and configure it to be used with YARF.

For more details on available snaps and management commands, see the official
Inference Snaps docs: https://documentation.ubuntu.com/inference-snaps/.

#### Steps

1. Install an inference snap. For this example, we will use the Qwen VL snap,
   which provides a vision-capable model:

   ```{code-block} bash
   ---
   caption: Install the Qwen VL inference snap
   ---
   sudo snap install qwen-vl --channel "2.5/beta"
   ```

1. Inference snaps start their API service automatically. Check the active API
   URL:

   ```{code-block} bash
   ---
   caption: Get the OpenAI-compatible endpoint
   ---
   qwen-vl status
   # engine: cpu-avx512
   # endpoints:
   #     openai: http://localhost:8326/v1
   ```

1. Get the exact model name from the snap:

   ```{code-block} bash
   ---
   caption: List model IDs exposed by the inference snap
   ---
   curl -s http://localhost:8326/v1/models | jq -r '.data[].id'
   # /snap/qwen-vl/components/248/model-qwen2-5-vl-7b-instruct-q4-k-m/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
   ```

1. Configure the LLM Client in your Robot Framework tests to use the snap's
   endpoint and model:

   ```{code-block} robotframework
   ---
   caption: Configure LLM Client for an inference snap endpoint
   ---
   *** Test Cases ***
   Use Inference Snap
       Configure Llm Client
       ...    server_url=http://localhost:8326/v1
       ...    endpoint=/chat/completions
       ...    model=/snap/qwen-vl/components/248/model-qwen2-5-vl-7b-instruct-q4-k-m/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
   ```

   ```{note}
   The inference snap only exposes a single model, so you can also omit the 
   `model` parameter and it will use that one by default.
   ```

### Option 2: Ollama

[Ollama](https://ollama.com/) is a local LLM server that allows you to run
various language models on your machine. It provides an OpenAI-compatible API,
making it easy to integrate with the LLM Client.

#### Steps

1. Install Ollama:

   ```{code-block} bash
   ---
   caption: Install Ollama on Linux
   ---
   curl -fsSL https://ollama.com/install.sh | sh
   ```

1. Run a vision-capable model (example: `qwen3-vl:2b-instruct`):

   ```{code-block} bash
   ---
   caption: Download and run a vision-capable model
   ---
   ollama run qwen3-vl:2b-instruct
   ```

1. By default, Ollama uses the same default values as the LLM Client (
   `http://localhost:11434/v1` and `/chat/completions`), so you only need to
   configure the model:

   ```{code-block} robotframework
   ---
   caption: Configure LLM Client for an Ollama model
   ---
   *** Test Cases ***
   Use Ollama Model
       Configure Llm Client
       ...    model=qwen3-vl:2b-instruct
   ```

## Basic text prompting

To use the LLM Client in your Robot Framework tests, first import the library:

```{code-block} robotframework
---
caption: Import LLM Client library
---
*** Settings ***
Library    yarf.rf_libraries.libraries.llm_client.LlmClient
```

### Simple text prompt

```{code-block} robotframework
---
caption: Basic text prompting example
---
*** Test Cases ***
Ask LLM a Question
    ${response}=    Prompt Llm    What is the capital of France?
    Log             ${response}
    Should Contain  ${response}   Paris
```

### Using system prompts

System prompts help guide the LLM's behavior and responses:

```{code-block} robotframework
---
caption: Using system prompts to guide behavior
---
*** Test Cases ***
Structured Response
    ${response}=    Prompt Llm    
    ...             prompt=Analyze this test result
    ...             system_prompt=You are a test automation expert. Provide concise, actionable feedback.
    Log             ${response}
```

## Using images in prompts

The LLM Client supports multi-modal prompts that include both text and images.
This is particularly useful for visual testing scenarios.

Several image-based keywords can either receive an explicit image or grab a
fresh screenshot automatically. When the `image` argument is omitted, the LLM
Client uses the active `VideoInput` library to capture the current screen.

### Image from file path

```{code-block} robotframework
---
caption: Analyze a screenshot with the LLM
---
*** Test Cases ***
Analyze Interface Screenshot
    # Take a screenshot first (example using YARF's screenshot capabilities)
    ${image} =              Grab Screenshot
    
    # Prompt the LLM to analyze the image
    ${analysis}=    Prompt Llm    
    ...             prompt=Describe what you see in this user interface
    ...             image=${image}
    
    Log             ${analysis}
    # The screenshot shows an image of a simple calculator
    Should Contain  ${analysis}    calculator
```

### Image validation workflows

```{code-block} robotframework
---
caption: Use LLM for visual validation
---
*** Test Cases ***
Validate Installation Screen
    ${image} =          Grab Screenshot
    ${validation}=      Prompt Llm
    ...                 prompt=Does this screen show the ubuntu installation on the "choose your language" step? Answer with YES or NO.
    ...                 image=${image}
    ...                 system_prompt=You are a UI testing assistant. Be very precise in your answers.
    
    Should Start With   ${validation}    YES
```

## Using VQA GUI keywords

The LLM Client includes keywords that leverage the model's vision capabilities
to perform visual validation and assertions on the current screen.

### Checking for visual corruption

`Check For Visual Corruption` asks the model whether an image contains visual
artifacts or corruption. If no image is provided, the keyword grabs a
screenshot from `VideoInput`.

```{code-block} robotframework
---
caption: Check the current screen for visual corruption
---
*** Test Cases ***
Current Screen Is Not Corrupted
    Check For Visual Corruption
```

If the model reports corruption, the keyword raises a `VQAValidationError`.

### Asserting screen state

`Assert State` verifies that the screen matches a natural-language description.
This is useful for checks that are difficult to express with template matching
or OCR alone.

```{code-block} robotframework
---
caption: Assert that the current screen matches an expected state
---
*** Test Cases ***
Desktop Is Visible
    Assert State    desktop is visible and ready for input
```

If the model decides that the state does not match, the keyword raises an
`AssertionError` and includes the model's reasoning in the failure message.

## Using LLM GUI keywords

The LLM Client also provides higher-level keywords for GUI testing. These
keywords ask a vision-capable model to inspect the current screen and return
structured results that can be used in Robot Framework tests.

### Locating an object

`Get Object Position` finds a described object on the screen and returns a
normalized point as `[x, y]`, where each value is relative to the screen size.
For example, `[0.5, 0.5]` is the center of the screen.

```{code-block} robotframework
---
caption: Locate a GUI element with the LLM
---
*** Test Cases ***
Find OK Button
    ${point}=    Get Object Position    the OK button
    Log         ${point}
```

If the object is not found, the keyword raises a `VQAValidationError`.

### Choosing and executing a GUI action

`Get Single Gui Action` asks the model to choose one action for a task. The
returned action can then be passed to `Execute Gui Action`.

Supported action types are:

- `Left Click`
- `Right Click`
- `Double Click`
- `Write`
- `Wait`

```{code-block} robotframework
---
caption: Let the LLM choose and execute one GUI action
---
*** Test Cases ***
Click The OK Button
    ${action}=    Get Single Gui Action    click the OK button
    Execute Gui Action    ${action}
```

Pointer actions returned by `Get Single Gui Action` use the model's 1000x1000
coordinate grid internally. `Execute Gui Action` normalizes that point before
moving the pointer with the active `HID` library.

For typing text directly, the action contains `action_type=Write` and the text
to enter:

```{code-block} robotframework
---
caption: Ask the LLM to type text into the active field
---
*** Test Cases ***
Type A Search Query
    ${action}=    Get Single Gui Action    type "network settings"
    Execute Gui Action    ${action}
```

When `YARF_LOG_LEVEL` is set to `DEBUG`, the GUI action keywords log the
screenshot sent to the model, the point selected by the model, and the
screenshot after an executed action.

## Using multi-step GUI navigation

`Multiple Step Action` lets the model drive a GUI task across several
screenshots. On each step, the keyword:

1. grabs a screenshot from `VideoInput`;
1. asks the model for the next action;
1. executes the action through `HID`;
1. keeps a history of previous actions for the next prompt.

The sequence stops when the model returns a `Finish` action. If the model does
not finish within `max_steps`, the keyword logs a final screenshot and raises a
`RuntimeError`.

This approach may be slower than template-based navigation, but it allows the
model to adapt to unexpected screen states, such as popups or loading screens,
and recover from them.

```{code-block} robotframework
---
caption: Open an application settings panel with multi-step navigation
---
*** Test Cases ***
Open Settings Panel
    Multiple Step Action
    ...    Open the Settings application and show the Network panel
    ...    max_steps=12

    Assert State    the Settings application is open on the Network panel
```

You can use multi-step navigation for workflows where the exact number of
clicks depends on the current UI state.


## Configuring the client

The LLM Client can be configured to work with different servers, models, and
parameters.

### Changing the model

```{code-block} robotframework
---
caption: Switch to a different model
---
*** Test Cases ***
Use Different Model
    Configure Llm Client    model=phi4-mini:3.8b
    ${response}=            Prompt Llm    Hello, what model are you?
    Log                     ${response}
```

### Using a different server

```{code-block} robotframework
---
caption: Connect to a remote LLM server
---
*** Test Cases ***
Remote Server Setup
    Configure Llm Client    
    ...    server_url=http://192.168.1.100:11434/v1
    ...    model=llama3.2-vision:11b
    
    ${response}=    Prompt Llm    Test connection
    Log             ${response}
```

### Adjusting token limits

```{code-block} robotframework
---
caption: Configure maximum tokens for responses
---
*** Test Cases ***
Short Response
    Configure Llm Client    max_tokens=100
    ${response}=            Prompt Llm    Write a brief summary of automated testing
    Log                     ${response}
```

### Complete configuration example

```{code-block} robotframework
---
caption: Full client configuration
---
*** Test Cases ***
Custom Configuration
    Configure Llm Client    
    ...    model=qwen3-vl:7b-instruct
    ...    server_url=http://llm-server:11434/v1
    ...    endpoint=/chat/completions
    ...    max_tokens=2048
```
