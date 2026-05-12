#!/usr/bin/env python3
"""
fetch_docs.py — download sfall scripting documentation for the MCP server.

Run once (and re-run when sfall updates):
    py -3 mcp/fetch_docs.py

Writes files to mcp/docs/.  Does NOT touch the hand-written reference docs
(proto-format.md, ssl-compiler.md, scripts-lst.md, dat2-format.md,
debugging-facts.md) — those already live in mcp/docs/.
"""

import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed.  Run:  pip install requests")
    sys.exit(1)

DOCS_DIR = Path(__file__).parent / "docs"
DOCS_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "f2mod-doc-fetcher/1.0"
TIMEOUT = 20


def fetch(url: str, label: str) -> str | None:
    try:
        r = SESSION.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        print(f"  OK   {label}")
        return r.text
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        return None


def save(filename: str, content: str) -> None:
    path = DOCS_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"       > {path.name} ({len(content):,} chars)")


BASE = "https://raw.githubusercontent.com/phobos2077/sfall/master"

# ── Priority 1: opcode reference and function database ───────────────────────

print("\n=== sfall opcode list ===")
text = fetch(f"{BASE}/artifacts/scripting/sfall%20opcode%20list.md", "sfall opcode list.md")
if text:
    save("sfall-opcode-list.md", text)
else:
    text = fetch(f"{BASE}/artifacts/scripting/sfall%20opcode%20list.txt", "sfall opcode list.txt")
    if text:
        save("sfall-opcode-list.md", text)

print("\n=== functions.yml (full structured function database) ===")
text = fetch(f"{BASE}/artifacts/scripting/functions.yml", "functions.yml")
if text:
    # Save as plain text — the YAML format is already very readable
    # and the BM25 index will handle it fine as a text file
    save("sfall-functions.txt", text)

print("\n=== hooks reference ===")
text = fetch(f"{BASE}/artifacts/scripting/hookscripts.md", "hookscripts.md")
if text:
    save("sfall-hookscripts.md", text)

text = fetch(f"{BASE}/artifacts/scripting/hooks.yml", "hooks.yml")
if text:
    save("sfall-hooks.txt", text)

print("\n=== function notes (extended behaviour docs) ===")
text = fetch(f"{BASE}/artifacts/scripting/sfall%20function%20notes.md", "sfall function notes.md")
if text:
    save("sfall-function-notes.md", text)

print("\n=== arrays documentation ===")
text = fetch(f"{BASE}/artifacts/scripting/arrays.md", "arrays.md")
if text:
    save("sfall-arrays.md", text)

# ── Priority 2: header files (macro and constant definitions) ─────────────────

print("\n=== header files ===")
headers = [
    ("artifacts/scripting/headers/sfall.h",        "sfall-header-sfall.h.txt"),
    ("artifacts/scripting/headers/define_extra.h",  "sfall-header-define_extra.h.txt"),
    ("artifacts/scripting/headers/define_lite.h",   "sfall-header-define_lite.h.txt"),
    ("artifacts/scripting/headers/command_lite.h",  "sfall-header-command_lite.h.txt"),
    ("artifacts/scripting/headers/lib.arrays.h",    "sfall-header-lib.arrays.h.txt"),
    ("artifacts/scripting/headers/lib.inven.h",     "sfall-header-lib.inven.h.txt"),
    ("artifacts/scripting/headers/lib.misc.h",      "sfall-header-lib.misc.h.txt"),
    ("artifacts/scripting/headers/lib.obj.h",       "sfall-header-lib.obj.h.txt"),
]
for path, filename in headers:
    text = fetch(f"{BASE}/{path}", Path(path).name)
    if text:
        save(filename, text)

# ── Priority 3: docs/ Jekyll pages ────────────────────────────────────────────

print("\n=== sfall docs/ pages ===")
doc_pages = [
    ("docs/global-scripts.md", "sfall-docs-global-scripts.md"),
    ("docs/hooks.md",          "sfall-docs-hooks.md"),
    ("docs/arrays.md",         "sfall-docs-arrays.md"),
    ("docs/sslc.md",           "sfall-docs-sslc.md"),
    ("docs/data-types.md",     "sfall-docs-data-types.md"),
    ("docs/best-practices.md", "sfall-docs-best-practices.md"),
    ("docs/index.md",          "sfall-docs-index.md"),
]
for path, filename in doc_pages:
    text = fetch(f"{BASE}/{path}", Path(path).name)
    if text:
        save(filename, text)

# ── Priority 4: README ────────────────────────────────────────────────────────

print("\n=== sfall README ===")
text = fetch(f"{BASE}/README.md", "README.md")
if text:
    # Truncate if huge — READMEs can be very long
    if len(text) > 80_000:
        text = text[:80_000] + "\n\n[... truncated ...]"
    save("sfall-readme.md", text)

# ── Summary ───────────────────────────────────────────────────────────────────

all_docs = sorted(DOCS_DIR.glob("**/*.*"))
total_kb = sum(p.stat().st_size for p in all_docs if p.is_file()) // 1024
print(f"\nDone.  {len(all_docs)} files in {DOCS_DIR}, ~{total_kb} KB total.")
print("Restart the MCP server (or re-open Claude Code) to reload the search index.")
