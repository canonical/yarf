# Discover a test suite with explore mode

Explore mode lets an AI agent discover the tests of an application for you. You give your own agent an application, its documentation and its repository. The agent operates the application on a virtual machine, through YARF, and writes a Robot Framework suite for it. You review the suite, and run it with `yarf`.

In this document, we will walk through how to discover a test suite, using GNOME Calculator as the example:

1. [How explore mode works](#how-explore-mode-works)
1. [What you need](#what-you-need)
1. [Install YARF with the MCP support](#install-yarf-with-the-mcp-support)
1. [Start a virtual machine](#start-a-virtual-machine)
1. [Connect your agent](#connect-your-agent)
1. [Ask the agent to explore](#ask-the-agent-to-explore)
1. [Review the suite](#review-the-suite)
1. [Run the suite locally](#run-the-suite-locally)
1. [Make the suite stable](#make-the-suite-stable)
1. [Troubleshooting](#troubleshooting)
1. [What explore mode does not do yet](#what-explore-mode-does-not-do-yet)

## How explore mode works

Explore mode is made of three parts that work together:

- **YARF** runs a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server, `yarf mcp`. It gives your agent tools to see the screen of the machine, to click and type, and to check what is shown. It records everything the agent does, and exports the steps that worked as a Robot Framework test.
- **Your agent** (GitHub Copilot CLI, VS Code, or another) does the thinking. It reads the documentation and the source, decides what to try, and calls the tools. The `yarf-explore` skill, in `.github/skills/yarf-explore/`, tells it how to do that well.
- **A virtual machine** runs the application. YARF reaches it over VNC.

```{code-block} text
---
caption: What happens in one exploration
---
You ──► start the VM ──► start your agent, with the yarf server and the skill
                         │
 your agent reads the documentation and the source ──► plan.md (scenarios, with evidence)
                         │
 your agent calls tools ──► YARF ──► VNC ──► application in the VM
   screenshot, click_on, type_text, match_text ...
                         │
 your agent calls export_suite ──► .robot files and image templates
                         │
 you review the suite, and run it: yarf --platform Vnc <suite>
```

The result is a normal YARF suite. After the exploration, it runs without the agent.

## What you need

- A Linux machine with KVM and QEMU: `/dev/kvm` is available to you, and `qemu-system-x86_64` is installed. The virtual machine needs about 2.5 GB of free memory, and 4 GB is better.
- An Ubuntu desktop ISO, for example `ubuntu-24.04.3-desktop-amd64.iso`. The live session is enough, nothing is installed in it. Any machine with a VNC server works, see [Using the VNC backend](./using-the-vnc-backend.md).
- [`uv`](https://docs.astral.sh/uv/), and the system packages of YARF: `sudo apt install -y build-essential libxkbcommon-dev tesseract-ocr`.
- An agent that can start a local MCP server and load skills, such as GitHub Copilot CLI, or GitHub Copilot in VS Code. It has to read files and run commands on your machine, as coding agents do.

## Install YARF with the MCP support

From a checkout of YARF that has explore mode:

```{code-block} bash
---
caption: Install YARF and check the MCP server
---
uv sync
uv run yarf mcp --help
```

`uv sync` installs the MCP SDK, which is in the development dependencies. In an installation without them, use the `mcp` extra: `pip install "yarf[mcp]"`. Without the extra, `yarf mcp` stops with a message that says so.

## Start a virtual machine

Start the Ubuntu live session. The VNC server listens on `127.0.0.1` only, so nobody else can reach it:

```{code-block} bash
---
caption: Start the virtual machine, with VNC on port 5901
---
qemu-system-x86_64 -enable-kvm -cpu host -smp 2 -m 4096 \
  -drive file=ubuntu-24.04.3-desktop-amd64.iso,media=cdrom,readonly=on \
  -boot d -vga std -device qemu-xhci -device usb-tablet \
  -display none -vnc 127.0.0.1:1,share=ignore
```

- `-device usb-tablet` makes the pointer land where YARF asks. Without it, clicks drift.
- `-vnc 127.0.0.1:1` is port 5901. YARF names a VNC port by its number after 5900, so this machine is `VNC_PORT=1`.
- `share=ignore` lets you connect a VNC viewer to watch while the agent works.

Wait until the desktop is shown, which takes a minute or two. Then prepare it, so that the agent starts from a known state:

1. Close the **Welcome to Ubuntu** installer window. It has the focus, so press `Alt+F4` in your VNC viewer, or let the agent do it with `press_keys`.
1. Make sure the Activities overview is closed. Press `Escape`.

Check that YARF reaches the machine:

```{code-block} bash
---
caption: Check the connection
---
VNC_PORT=1 uv run python -c "from yarf.rf_libraries.libraries.vnc import Vnc; Vnc().check_connection(); print('connected')"
```

```{note}
The agent can change the state of the machine, for example the settings of the application, and some applications keep it between runs. To start a new exploration from a fresh state, stop QEMU and start it again. A live session loses everything when it stops.
```

## Connect your agent

`yarf mcp` is a server that talks over its standard input and output. Your agent starts it, and stops it when the session ends. There is no port to open.

Add it to the configuration of your agent. Replace `/path/to/yarf` by the folder of your checkout. The `yarf` command is in its virtual environment:

For GitHub Copilot CLI, add it to `~/.copilot/mcp-config.json`:

```{code-block} json
---
caption: `~/.copilot/mcp-config.json`
---
{
  "mcpServers": {
    "yarf": {
      "type": "local",
      "command": "/path/to/yarf/.venv/bin/yarf",
      "args": ["mcp", "--platform", "Vnc", "--outdir", "/tmp/yarf-explore"],
      "env": {"VNC_HOST": "localhost", "VNC_PORT": "1"},
      "tools": ["*"]
    }
  }
}
```

For GitHub Copilot in VS Code, add it to `.vscode/mcp.json`. VS Code names the top-level object `servers`, and the type `stdio`:

```{code-block} json
---
caption: `.vscode/mcp.json`
---
{
  "servers": {
    "yarf": {
      "type": "stdio",
      "command": "/path/to/yarf/.venv/bin/yarf",
      "args": ["mcp", "--platform", "Vnc", "--outdir", "/tmp/yarf-explore"],
      "env": {"VNC_HOST": "localhost", "VNC_PORT": "1"}
    }
  }
}
```

Any other agent that can start a local (stdio) MCP server works the same way: the command, its arguments, and the two environment variables. `--outdir` is where the session is saved, see [Use YARF with an LLM through MCP](./using-the-mcp-server.md).

Then start your agent **in the root of the YARF checkout**, so that it finds the skill, and check both:

- Ask it: "List the tools of the yarf MCP server". It should list 16 tools, such as `screenshot` and `export_suite`.
- In Copilot CLI, `/skills list` shows `yarf-explore`. In VS Code, type `/skills`. For an agent that reads skills from another folder, such as `.claude/skills/`, copy the folder `.github/skills/yarf-explore/` there. Without skills, paste the content of its `SKILL.md` as the first message.

## Ask the agent to explore

Tell the agent which skill to use, what to explore, and where to find it:

```{code-block} text
---
caption: A prompt to explore GNOME Calculator
---
Use the /yarf-explore skill.

Application: GNOME Calculator 46, the version in Ubuntu 24.04
Documentation: https://help.gnome.org/users/gnome-calculator/stable/
Repository: https://gitlab.gnome.org/GNOME/gnome-calculator, tag 46.1
VNC port: 1
Write the suite in suites/gnome-calculator/

The machine is a fresh Ubuntu 24.04 desktop, with the installer closed.
Start with the Basic mode and the keyboard shortcuts of the modes.
```

A smaller first request is better than a big one: one mode, or one panel.

The agent goes through six steps:

| Step | What the agent does                                                                                                                                 | What you do                                          |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 1    | Reads the documentation and the source of the version in the machine, and writes `plan.md`: scenarios, expected results, and the evidence for each. | Read the plan. Remove or add scenarios, and approve. |
| 2    | Runs the scenarios with the tools: it looks at the screen, clicks, types, and checks what is shown.                                                 | Watch with a VNC viewer if you like.                 |
| 3    | Exports the steps that worked with `export_suite`, and copies them into the suite folder.                                                           |                                                      |
| 4    | Edits the exported files: documentation, a setup that opens the application, and exact checks of the values.                                        | Review the result (next section).                    |
| 5    | Runs the suite with `yarf`, three times in a row, and fixes the tests that fail.                                                                    | Restore the machine when it asks, between the runs.  |
| 6    | Writes a report: tests written, tests left out and why, problems found in the application, what the OCR could not read.                             | Read it before you trust the suite.                  |

The agent has no access to the virtual machine itself: it can only use the screen, the keyboard and the pointer. The server refuses any other keyword, see [Use YARF with an LLM through MCP](./using-the-mcp-server.md#understand-the-guardrails).

## Review the suite

You will find a folder like this one. The names depend on your agent:

```{code-block} text
---
caption: The suite folder of the agent
---
suites/gnome-calculator/
├── plan.md                  The scenarios, with their evidence
├── __init__.robot           Suite setup and teardown: open and close the application
├── calculator.resource      Keywords shared by the tests
├── basic_mode.robot         The tests
└── templates/               Image templates of the elements that text can't find
```

A good suite, such as the GNOME Calculator example in `examples/gnome-calculator/` of the YARF repository, has these properties. Check them before you trust the one of the agent:

- **Each expected value has evidence.** The documentation of a test says where its value comes from. Scenarios marked `TO CHECK` were not turned into tests.
- **A check can fail.** `Match Text` accepts similar text, so `Match Text    12` also passes when the screen shows `120`. A check of a value should read the region where it is shown, and compare whole lines. Try it: change an expected value in a test for a close but wrong one, run the test, and see it fail.
- **The text on the screen is unique.** A click on the text `7` can land on the `7` of the clock.
- **The steps wait where they need to.** The export runs the steps back to back, without the time the agent took. Look for a `Sleep` or a check after the clicks that move something.
- **Each test stands alone.** It doesn't depend on what the previous one left on the screen.
- **No absolute paths.** Templates are referenced as `${CURDIR}/templates/name.png`.

### An export can pass and test nothing

The export repeats the steps of the agent without its pauses, and its checks accept approximate text. This is the export of an agent that opened the calculator and added `7+8`:

```{code-block} robotframework
---
caption: The raw export of a short exploration
---
*** Test Cases ***
Add Two Numbers
    Keys Combo    Super_L
    Type String    Calculator
    Keys Combo    Return
    Type String    7+8
    Keys Combo    Return
    Match Text    15    10
```

Run on a fresh machine, this test passes, and the calculator is empty. The digits were typed before the window had opened, and `15` was found in the clock of the top bar, which read `12:15` at that moment. The reviewed version launches the application in a setup, waits for it, and reads the region where the result is shown:

```{code-block} robotframework
---
caption: The reviewed test, with the keywords of the example suite
---
*** Test Cases ***
Add Two Numbers
    Calculate 7+8
    Entry Should Show 15
    Entry Should Not Show 16
```

`Launch Calculator`, `Calculate`, `Entry Should Show` and the other keywords are in `examples/gnome-calculator/calculator.resource`. Replace the expected `15` with `16` and the test fails with `The entry shows ['15'], not '16'`.

## Run the suite locally

The agent already ran the suite. Run it yourself, from a fresh machine, with the command you use for any suite:

```{code-block} bash
---
caption: Run the suite
---
VNC_HOST=localhost VNC_PORT=1 uv run yarf --platform Vnc suites/gnome-calculator
```

Add `--outdir DIR` to choose where the results go, and `--log-video` to keep a video of the run even when it passes. The results are in `/tmp/yarf-outdir` by default: `log.html`, `report.html` and `output.xml`. The exit code is `0` when all the tests passed, see [Exit codes](../reference/exit-codes.md). For more about running a suite, see [Run a robot test suite in YARF](./run-a-robot-test-suite-in-yarf.md).

For the suite to start in the same state as the agent did, stop QEMU and start it again before each run, and prepare the desktop as in [Start a virtual machine](#start-a-virtual-machine).

## Make the suite stable

Run the suite three times in a row, each one from a fresh machine. A suite that passes once can still fail the next time. When a test fails, find out why before you change it:

| What you see                                                                        | What it is                    | What to do                                                           |
| ----------------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------- |
| The screen shows a different value from the documentation.                          | A problem of the application. | Keep the test, and report the problem. Don't change the expectation. |
| The expectation was a guess.                                                        | A wrong expectation.          | Fix it from the evidence, or remove the test.                        |
| The text on the screen is nearly right: `0333` for `0.333333333`, `x` for `×`.      | The OCR misread it.           | Use a value the OCR reads well, or an image template.                |
| The test passes alone, and fails after another one, or the screen is not ready yet. | State or timing.              | Make the test start from a known state, or wait for what it needs.   |

Never loosen a check to make a test pass. A test that stays flaky should leave the suite, and be listed as a gap.

## Troubleshooting

| Problem                                                       | Cause and fix                                                                                                                                                          |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The agent shows no `yarf` tools, or the server fails to start | Run the command of your configuration by hand, for example `/path/to/yarf/.venv/bin/yarf mcp --help`. A wrong path, or `The MCP SDK is not installed`, shows up there. |
| `check_connection` fails                                      | The virtual machine is not started yet, or `VNC_PORT` is wrong. Port 5901 is `VNC_PORT=1`. Check with `ss -ltn \| grep 5901`.                                          |
| A click lands on the wrong element, such as the clock         | The text target is not unique, and is matched approximately anywhere on the screen. Use another text, or save a template of the element.                               |
| Typing after a click goes to the wrong place                  | The application needs a moment. Add a `Sleep` or a check between the two steps.                                                                                        |
| A symbol such as `×`, `=` or `−` is not found                 | The OCR misreads some symbols. Save a template with `save_template`, and click on the template.                                                                        |
| The agent says that a keyword is not allowed                  | The guardrails of the server. The agent has to use the tools it is given, see [Understand the guardrails](./using-the-mcp-server.md#understand-the-guardrails).        |
| The skill is not found                                        | Start the agent in the root of the YARF checkout. In Copilot CLI, run `/skills reload`.                                                                                |

## What explore mode does not do yet

This version is a proof of concept. It has been tried on GNOME Calculator 46 in an Ubuntu 24.04 LTS live session. Other applications and images were not tried.

- There is no `yarf explore` command. Your agent runs the exploration, so the quality of the suite depends on your agent and its model. Always review it.
- YARF does not start, snapshot or restore the virtual machine. You do.
- The checks of exact values are written by hand, following the example. YARF has no keyword for them yet.
- Only the VNC platform was tried. `--platform` also lists Mir, which was not tried.

For the reasons behind the design, see [Explore mode and MCP](../explanation/explore-mode-and-mcp.md).
