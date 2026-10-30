# Explore mode and MCP

The goal of the explore mode is to hand an application, its documentation and its repository to an LLM, and get back a suite of Robot Framework scenarios that test it. The LLM explores the application in a virtual machine through VNC, and writes down what worked.

This document explains what the explore mode does, how the LLM talks to YARF, and why. To use it, follow [Discover a test suite with explore mode](../how-to/discover-a-test-suite-with-explore-mode.md). For the tools of the server, see [Use YARF with an LLM through MCP](../how-to/using-the-mcp-server.md).

## What explore mode does

Explore mode is not a command of YARF. It is a way of working in which three parts meet:

- **Your LLM agent**, such as Copilot CLI or VS Code, decides what to try. It reads the documentation and the source of the application, and plans the scenarios.
- **The `yarf mcp` server** gives the agent what it needs to act: the screen as an image, the keyboard, the pointer, text recognition, and every other keyword of the platform. It also records what the agent did.
- **A virtual machine** runs the application, and shows its screen through VNC. You start it.

```{code-block} text
---
caption: What goes in and what comes out
---
 application + documentation + repository + a virtual machine
                          |
                          v
   plan the scenarios, each with the evidence of its expected result
                          |
                          v
   explore: screenshot, act, screenshot, check ...  (YARF tools)
                          |
                          v
   export the steps that worked as Robot Framework tests
                          |
                          v
   harden: wait where needed, check exact values, run three times
                          |
                          v
   a suite that `yarf` runs on its own, without the agent
```

The agent never runs a command on the machine under test, and the suite it writes doesn't need the agent or the MCP server afterwards: it is a normal YARF suite. The skill `yarf-explore`, in `.github/skills/`, gives the agent the procedure.

An export is a start, not a result. It repeats the steps of the agent without its pauses, and its checks accept approximate text, so it can pass and test nothing. See "An export can pass and test nothing" in [Review the suite](../how-to/discover-a-test-suite-with-explore-mode.md#review-the-suite).

## The question

How should an LLM run YARF commands? There are three open questions:

- Is the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) the right way?
- Does it need a server?
- Which parts should be an MCP tool, and which a skill?

## The answer

An LLM client spawns `yarf mcp`, a local MCP server that talks over standard input and output. It exposes the keywords of the platform as MCP tools. The workflows that use these tools, such as the explore mode itself, are skills.

MCP is a protocol, so there is no option of only documenting it: something has to speak it. But a server doesn't have to be a network service. When the LLM client and YARF run on the same machine, the client starts the server as a child process. There is no port, no authentication and no daemon, and the server lives as long as the LLM session.

## Options considered

| Option                                                    | Verdict                                                                                                                                                                                                       |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The LLM runs `yarf suite.robot` with its shell tool       | Good to run a complete suite, so a skill can still do it. Not good to explore: every action is a new process with no state, the output is unstructured, and nothing records what was done.                    |
| The LLM drives the interactive console through a terminal | Fragile. The console is a terminal interface made for people.                                                                                                                                                 |
| A stateful MCP server (`yarf mcp`)                        | Chosen for single keywords.                                                                                                                                                                                   |
| A skill, that is instructions and scripts                 | Chosen for workflows: the exploration procedure, and platform control such as starting a virtual machine or restoring a snapshot. A skill can't hold state or call keywords by itself, so it complements MCP. |
| A native `yarf explore` command with its own agent loop   | Not decided yet. It wouldn't use the subscription and the agent controls of the LLM client that the user already has.                                                                                         |

The process start isn't the main reason to have a persistent server. Starting `yarf` takes roughly a second and the VNC connection is opened for every action anyway. The reasons are:

- **State.** The Robot Framework context, with its variables and imported resources, lives for the whole session, like in the interactive console.
- **Memory.** The server sees every keyword, so it records them in an event cache. The LLM can retrace its steps, and the successful ones become a test.
- **Discovery.** The LLM lists and searches the available keywords, with their documentation, instead of guessing them.
- **Guardrails.** One place decides what the LLM can run.
- **Images.** Screenshots come back as images that a vision model sees directly. The LLM client is the one that thinks, and YARF only provides eyes and hands, so the LLM client of YARF isn't needed.

## How it works

```{code-block} text
---
caption: Components of `yarf mcp`
---
LLM client (Copilot CLI, VS Code, ...) with skills
        |  JSON-RPC over stdin and stdout, the client starts the server
        v
yarf mcp --platform Vnc
  |- MCP server thread: tools, guardrails
  |- Bridge: a queue of calls
  `- Robot Framework thread: runs the keywords, records events
        |  VNC
        v
Virtual machine under test
```

Robot Framework keywords can only run in the thread that executes the suite, while the MCP server has its own event loop. So the suite has a single test that calls the `Serve Mcp` keyword and blocks. The MCP server runs in another thread, and hands the calls to the Robot Framework thread through a queue. The keywords therefore run in the same execution context as in a normal suite or the interactive console, with the same libraries and resources.

The tools are a mix. A few typed tools cover the actions that almost every exploration needs, which keeps the list of tools short. Generic tools to search and run any keyword cover the rest, including the keywords added by platform plugins. The alternative of a tool per keyword would be larger and grow with every plugin.

## What was measured

The server was run against GNOME Calculator 46 in an Ubuntu 24.04 LTS live session, in a QEMU virtual machine with a 1280×800 screen, over VNC. The agent was a scripted client that sent the same calls as an LLM would, so the numbers show the cost of the server and not the speed of a model.

| Measure                                     | Result                                                                      |
| ------------------------------------------- | --------------------------------------------------------------------------- |
| Start of the server until it is connected   | About 1.5 seconds, once per session                                         |
| A screenshot                                | About 0.6 seconds, with the transfer of the image to the client             |
| Reading all the text of the screen with OCR | About 1.2 seconds                                                           |
| Tools and size of their description         | 16 tools, about 8.6 thousand characters, so roughly 2 thousand tokens       |
| Keywords the LLM can run                    | 53, so a tool per keyword would be more than three times the tools          |
| The reference suite, run with `yarf`        | 15 tests, all passed, in a machine started for the run                      |
| A wrong expected value in a reviewed test   | Failed with `The entry shows ['15'], not '16'`, after five seconds of retry |

What the trials showed about the limits of the approach:

- **Approximate text.** `Match Text` accepts similar text. Of nine deliberately wrong values, four passed, such as `12` for `120`. The reference suite reads the region of the result and compares whole lines.
- **Text that is not unique.** A click on the text `7` landed on the `7` of the clock when it read `17:01`. A check of `15` passed on the clock at `12:15`, with an empty calculator.
- **Timing.** The export has no pauses. An exported test typed `*9` before the application had moved its cursor, and the equation was `×99`.
- **The OCR.** It dropped repeated digits (`0.333333333` was read as `0333`), returned nothing for a region 700 pixels wide while it worked at about 340 pixels, and read `×` as `x`. For symbols the agent saves an image template, and the export includes it.

Two details of the implementation are worth knowing:

- Robot Framework replaces `sys.stdout` while a keyword runs, and the MCP SDK needs the real one to keep everything but the protocol off the standard output. The server restores it, and a test starts `yarf mcp` as a separate process to prove it.
- In the exported files, a space just before a cell separator has to be written as `\x20`. The usual backslash escape is lost there.

## Security

The concern is an LLM tampering with the system to make a test pass. The server limits what the LLM can run to the GUI keywords of the platform, a few harmless BuiltIn keywords, and arguments without code in the variable syntax. See [Understand the guardrails](../how-to/using-the-mcp-server.md#understand-the-guardrails).

The guardrails protect the machine that runs YARF. They don't limit what the LLM does inside the machine under test, and the LLM client may have other tools, such as a shell, that YARF doesn't control. The control of the virtual machine isn't a tool of the MCP server, it belongs in a skill that the user configures and approves.

## Decisions still open

- Whether the explore mode is a native `yarf explore` command or only a skill.
- The skill that starts the virtual machine and restores snapshots from a configuration file. The skill `yarf-explore` has the exploration procedure, and asks the user for a machine in a known state until then.
- Keywords for the exact checks of the example suite (`Get Lines Of`, `Area Should Contain`), which are now in its resource file, and a way to read the text of a region instead of the whole screen.
- A pause between the exported steps, or a check that the screen has settled.
- Packaging in the snap. The snap installs YARF without extras, so it doesn't include the MCP SDK yet, and `yarf mcp` there asks for it. The build and a stdio session in the snap have to be tested.
- The address of the VNC server is read when the server starts, so a virtual machine that comes back on another address needs a restart of the server.
- Running on Mir isn't covered. The exploration is done in a virtual machine over VNC, and a suite may need changes for other platforms.
