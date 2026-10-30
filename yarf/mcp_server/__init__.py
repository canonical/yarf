"""
Model Context Protocol (MCP) server that lets an LLM drive YARF.

An LLM client starts `yarf mcp` as a child process and talks to it over
standard input and output. The LLM sees the screen of a machine, operates it
with the keyboard and the pointer, and can turn what it did into a Robot
Framework suite. Which modules do what:

- `cli`: the `yarf mcp` command. It builds a suite with a single test that
  calls `Serve Mcp`, and runs it.
- `McpHost`: the Robot Framework library behind `Serve Mcp`. It runs the MCP
  server in a thread, while the Robot Framework thread serves the calls.
- `bridge`: the queue that hands the calls from the server thread to the Robot
  Framework thread, the only one that can run keywords.
- `server`: the MCP tools, and the instructions given to the LLM.
- `session`: what the tools do: run an allowed keyword, take a screenshot, save
  a template, search the keywords.
- `policy`: which keywords the LLM may run, and which arguments it may use.
- `events`: the record of everything that was run, and the export of the
  successful steps as a Robot Framework suite.
"""
