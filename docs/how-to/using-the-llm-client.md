# Using the LLM client

The LLM Client library in YARF provides Robot Framework keywords for interacting
with Large Language Model servers that support the OpenAI Chat Completions API
format. This enables you to integrate AI capabilities into your test automation
workflows.

In this guide, we will cover:

1. [Setting up an LLM server](#setting-up-an-llm-server)
1. [Basic text prompting](#basic-text-prompting)
1. [Using images in prompts](#using-images-in-prompts)
1. [Configuring the client](#configuring-the-client)

## Setting up an LLM server

The LLM Client is designed to work with any server that implements the OpenAI
Chat Completions API.

### Option 1: Inference Snap

1. Install an inference snap. For this example, we will use the Qwen VL snap,
which provides a vision-capable model:

    ```{code-block} bash
    ---
    caption: Install the Qwen VL inference snap
    ---
    sudo snap install qwen-vl --channel "2.5/beta"
    ```

1. Inference snaps start their API service automatically. Check the active API URL:

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
   `http://localhost:11434/v1` and `/chat/completions`), so you
   only need to configure the model:

    ```{code-block} robotframework
    ---
    caption: Configure LLM Client for an inference snap endpoint
    ---
    *** Test Cases ***
    Use Inference Snap
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
