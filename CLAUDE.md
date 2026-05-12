# Working Directory

All mod work is done in `C:\Games\F2Modding`. This includes mod tools and the Fallout 2 install being modified. Do NOT touch the GOG install at `C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2`.

# Instructions

- Take the user's words literally. Do not add, infer, or expand beyond what is explicitly stated. When something is unspecified, ask rather than assume.
- Before flagging something as unspecified, re-read the full document to confirm it is not already addressed.
- Do not flag two statements as contradictory unless they describe the same situation with mutually exclusive outcomes.
- Do not flag something as missing or unspecified if it can be solved with standard programming logic or algorithms.

# MCP Server

An MCP server with Fallout 2 modding tools is available. Use it proactively:

- `search_f2_docs` — search Fallout 2 and sfall documentation. Use this BEFORE spawning a web search agent for any F2 engine behavior, proto format, scripting, or sfall question.
- `compile_ssl` — compile SSL scripts to .int.
- `inspect_proto` — parse and display proto file fields.
- `read_scripts_lst` — read scripts.lst with 0-based line numbers.
- `verify_f2mod` — verify mod state. Use this before declaring anything working or broken.

# Session Notes

Maintain `C:\Games\F2Modding\CURRENT_SESSION.md` throughout every session. Update it regularly — not just at the end — capturing:
- What was tried and what the result was
- What works and what doesn't, with best judgment as to why
- Any new understanding of how the engine or sfall behaves
- The current state of each file being worked on
- The next step and any open questions

This file is the primary record for resuming work across sessions. Keep it accurate and current so future sessions don't repeat failed approaches.
