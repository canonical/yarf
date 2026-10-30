# Use YARF with an LLM through MCP

YARF can be driven by a large language model (LLM) through the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP). The LLM sees the screen of a machine, operates it with the keyboard and the pointer, and can turn what worked into a Robot Framework test.

This document is the reference of the MCP server, `yarf mcp`. To discover the tests of an application with your own agent, step by step, see [Discover a test suite with explore mode](./discover-a-test-suite-with-explore-mode.md).

In this document, we will walk through how to use it:

1. [Install the MCP support](#install-the-mcp-support)
1. [Connect an LLM client](#connect-an-llm-client)
1. [What the LLM can do](#what-the-llm-can-do)
1. [What an export looks like](#what-an-export-looks-like)
1. [Understand the guardrails](#understand-the-guardrails)
1. [Find the results of a session](#find-the-results-of-a-session)

For the reasons behind this design, see [Explore mode and MCP](../explanation/explore-mode-and-mcp.md).

## Install the MCP support

The MCP support is an optional extra, so that YARF doesn't pull its dependencies unless you need them:

```{code-block} bash
---
caption: Install YARF with the MCP support
---
pip install "yarf[mcp]"
```

In a checkout of YARF, `uv sync` is enough: the development dependencies include the MCP SDK.

If the extra isn't installed, `yarf mcp` fails with a message telling you so.

## Connect an LLM client

`yarf mcp` is an MCP server that talks over its standard input and output. You don't start it yourself, the LLM client starts it as a child process, and stops it when the session ends. There is no network port to open, and nothing keeps running afterwards.

You need a machine to control, reachable through VNC. See [Using the VNC backend](./using-the-vnc-backend.md) to start one. The address of the VNC server is given in the environment variables `VNC_HOST` and `VNC_PORT`, which are read when the server starts.

Add the server to the configuration of your LLM client, as a local server that runs the command `yarf` with the arguments `mcp --platform Vnc`, and the two environment variables. The complete configurations for GitHub Copilot CLI and for VS Code are in [Connect your agent](./discover-a-test-suite-with-explore-mode.md#connect-your-agent).

Use one entry per machine you want to control, with a different name and `VNC_PORT` in each.

The options of `yarf mcp` are:

| Option               | Description                                                                                                       |
| -------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `--platform`         | Platform to control, `Vnc` by default.                                                                            |
| `--outdir`           | Directory where the session is saved.                                                                             |
| `--debug`, `--quiet` | Be more or less verbose. The logs go to the standard error, because the standard output is only for the protocol. |

## What the LLM can do

The LLM gets a few tools for the most common actions, and generic ones to find and run any other keyword.

| Tool                | What it does                                                   |
| ------------------- | -------------------------------------------------------------- |
| `screenshot`        | Returns the screen as an image.                                |
| `click_on`          | Clicks on a text shown on the screen, or on an image template. |
| `click_at`          | Clicks on some coordinates.                                    |
| `type_text`         | Types text.                                                    |
| `press_keys`        | Presses keys at the same time, for example `Alt_L` and `F4`.   |
| `match_text`        | Waits until a text is shown, it fails otherwise.               |
| `match_template`    | Waits until an image template is shown, it fails otherwise.    |
| `read_text`         | Reads the text shown on the screen with OCR.                   |
| `wait_still_screen` | Waits until the screen stops changing.                         |
| `save_template`     | Saves part of the screen as an image template.                 |
| `search_keywords`   | Finds the keywords it can run.                                 |
| `get_keyword_doc`   | Shows the arguments and documentation of a keyword.            |
| `run_keyword`       | Runs any allowed keyword.                                      |
| `get_history`       | Lists what it already did, with the result.                    |
| `export_suite`      | Exports the successful steps as a Robot Framework test.        |
| `check_connection`  | Checks that the machine can be reached.                        |

The arguments of `run_keyword` follow the Robot Framework syntax, so a backslash, `${`, `@{` or `&{` have to be escaped with a backslash. The tools with a text argument, such as `type_text`, do it for you.

`yarf mcp` starts even if the machine isn't reachable yet, so it can be started, or restored from a snapshot, afterwards. Use `check_connection` to know when it is ready.

## What an export looks like

`export_suite` writes the successful steps of the session as a Robot Framework suite, in `exports/<name>/` of the output directory. This is a real export, after an LLM opened GNOME Calculator from the Activities overview, switched it to the Advanced mode, and checked two results:

```{code-block} robotframework
---
caption: A suite exported by the LLM
---
*** Settings ***
Resource            kvm.resource


*** Test Cases ***
GNOME Calculator explored
    Keys Combo    Super_L
    Match Text    regex:search    10
    Sleep    1s
    Type String    calculator
    Sleep    2s
    Keys Combo    Return
    Match Text    Undo    30
    Click LEFT Button On Basic
    Sleep    1s
    Click LEFT Button On Advanced
    Sleep    1s
    Type String    sin 30
    Keys Combo    Return
    Match Text    0.5    10
    Type String    5/0
    Keys Combo    Return
    Match Text    Division by zero is undefined    10
```

The templates it uses are copied to the `templates` directory next to the suite. Run it as any other suite:

```{code-block} bash
---
caption: Run an exported suite
---
VNC_HOST=localhost VNC_PORT=1 yarf --platform Vnc /tmp/yarf-explore/exports/GNOME_Calculator_explored
```

Only the successful actions are exported, in order, together with the checks. Observations such as screenshots, and the steps that failed, are left out. The LLM can pass the ids shown by `get_history` to `export_suite` to choose exactly which steps to export.

An export has three limits that you have to know:

- **It has no pauses.** The steps are replayed back to back, without the time the LLM took between them. Some applications need that time: GNOME Calculator moves its text cursor a moment after a click on a button, so typing right after the click lands at the start of the entry. If a step needs time to settle, the LLM adds a `Sleep` with `run_keyword`, or a `match_text`, and both are exported. The `Sleep` steps above are such pauses.
- **Text targets are approximate.** The text of `click_on` is matched approximately, anywhere on the screen. A `7` matches the clock when it shows `17:01`. Use text that appears once, or an image template.
- **Checks accept similar text.** `Match Text    12` also passes when the screen shows `120`. To check a value exactly, the suite has to read a region and compare whole lines, as `examples/gnome-calculator/calculator.resource` does.

A test also starts from whatever state the machine is in. The export holds the steps, not the state they started from: add a setup that opens the application from a known state.

## Understand the guardrails

An LLM that can run anything could tamper with the machine that runs YARF to make a test pass. To prevent it, `yarf mcp` only runs:

- The keywords of the platform libraries, and of the YARF resources such as `kvm.resource`.
- A few harmless BuiltIn keywords: `Log`, `Sleep`, `Should Be Equal`, `Should Be Equal As Strings`, `Should Contain` and `Should Not Contain`.

Everything else is refused, for example `Evaluate`, `Run Process` or `Import Library`. The arguments can't use the variable syntax of Robot Framework to run code or read the environment either: `${{ ... }}`, `${object.method()}`, `${1 + 1}` and `%{VAR}` are refused, while plain variables such as `${NAME}` work.

```{note}
The LLM can do in the machine anything a person can do with its screen, keyboard and pointer. The guardrails protect the host running YARF, not the machine under test. Use a disposable virtual machine, and restore it from a snapshot when needed.
```

## Find the results of a session

Everything is saved in the directory given by `--outdir`, `/tmp/yarf-outdir` by default. When a session starts, it deletes the `output.xml`, `log.html` and `report.html` of the previous one, and replaces its `events.jsonl`. The templates and exports are kept.

| Path                                    | Content                                                                       |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| `events.jsonl`                          | Every keyword that was run, one JSON object per line, written as they happen. |
| `templates/`                            | The image templates saved by the LLM.                                         |
| `exports/<name>/`                       | The suites exported by the LLM, with their templates.                         |
| `log.html`, `report.html`, `output.xml` | The Robot Framework log of the session, generated when it ends.               |

```{note}
LLM clients give the server only a short time to stop after the session ends. If they don't wait for the Robot Framework log, it can be missing, but `events.jsonl`, the templates and the exports are written as they happen, so nothing else is lost.
```
