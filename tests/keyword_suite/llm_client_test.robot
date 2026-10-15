*** Settings ***
Library         yarf/rf_libraries/libraries/llm_client/LlmClient.py
Library         yarf/rf_libraries/libraries/image/utils.py

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::llm_client
...    yarf:test_group_id: com.canonical.yarf::llm_client


*** Test Cases ***
Default Server
    ${out}=                 Prompt Llm              This is my prompt

    # Check that the server echoes with the right parameters
    Should Contain          ${out}                  port 11434
    Should Contain          ${out}                  model qwen3-vl:2b-instruct
    Should Contain          ${out}                  This is my prompt

Switch model
    Configure Llm Client    model=phi4-mini:3.8b
    ${out}=                 Prompt Llm              This is my prompt

    # Check that the server echoes with the right parameters
    Should Contain          ${out}                  port 11434
    Should Contain          ${out}                  model phi4-mini:3.8b
    Should Contain          ${out}                  This is my prompt

Switch Server port
    Configure Llm Client    server_url=http://127.0.0.1:11435/v1
    ${out}=                 Prompt Llm              This is my prompt

    # Check that the server echoes with the right parameters
    Should Contain          ${out}                  port 11435
    Should Contain          ${out}                  model qwen3-vl:2b-instruct
    Should Contain          ${out}                  This is my prompt

Default Server with image
    ${path}=                Set Variable            ${CURDIR}/calculator/01_calculator.png
    ${out}=                 Prompt Llm              This is my prompt       image=${path}

    # Check that the server echoes with the right parameters
    Should Contain          ${out}                  port 11434
    Should Contain          ${out}                  model qwen3-vl:2b-instruct
    Should Contain          ${out}                  This is my prompt
    Should Contain          ${out}                  data:image/webp;base64

Usage Collection Disabled By Default
    Prompt Llm              This is my prompt
    Run Keyword And Expect Error                    *usage collection is disabled*
    ...                     Get Llm Usage

Collect Usage
    Configure Llm Client    collect_usage=True
    Prompt Llm              This is my prompt
    Prompt Llm              This is my second prompt
    ${usage}=               Get Llm Usage

    # The stub server reports the same usage for every request
    Should Be Equal         ${usage}[model]         qwen3-vl:2b-instruct
    Should Be Equal As Integers                     ${usage}[requests]      2
    Should Be Equal As Integers                     ${usage}[prompt_tokens]                         20
    Should Be Equal As Integers                     ${usage}[completion_tokens]                     10
    Should Be Equal As Integers                     ${usage}[reasoning_tokens]                      4
    Should Be Equal As Integers                     ${usage}[total_tokens]                          30
    Should Be Equal As Numbers                      ${usage}[cost]          0.5
    Should Be Equal         ${usage}[nano_aiu]      ${None}
    Should Be True          ${usage}[inference_time] > 0
