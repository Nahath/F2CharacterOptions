#!/usr/bin/env python3
"""
f2-modding-tools MCP server
----------------------------
Provides Fallout 2 modding documentation search and file inspection tools
for Claude Code.  Registered automatically via .mcp.json.
"""

import json
import os
import struct
import subprocess
import zlib
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

from mcp.server.fastmcp import FastMCP

# ── Paths and config ──────────────────────────────────────────────────────────

SERVER_DIR  = Path(__file__).parent
DOCS_DIR    = SERVER_DIR / "docs"
CONFIG_FILE = SERVER_DIR / "config.json"
MOD_ROOT    = SERVER_DIR.parent  # C:\git\f2Mod


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


_cfg        = _load_config()
GAME_ROOT   = Path(_cfg.get("game_root",   r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2"))
COMPILE_EXE = Path(_cfg.get("compile_exe", r"compile.exe"))

# ── MCP server ────────────────────────────────────────────────────────────────

mcp = FastMCP("f2-modding-tools")

# ── DAT2 helpers ──────────────────────────────────────────────────────────────

def _read_dat(dat_path: Path, internal_path: str) -> bytes | None:
    """Extract a single file from a Fallout 2 DAT2 archive."""
    target = internal_path.replace("/", "\\").lower()
    try:
        with open(dat_path, "rb") as fh:
            fh.seek(-8, 2)
            tree_size, dat_size = struct.unpack("<II", fh.read(8))
            fh.seek(dat_size - tree_size - 8)
            tree = fh.read(tree_size)
        pos = 4
        while pos < len(tree):
            nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
            name = tree[pos:pos + nl].decode("latin-1").lower(); pos += nl
            comp = tree[pos]; pos += 1
            unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
            if name.replace("/", "\\") == target:
                with open(dat_path, "rb") as fh:
                    fh.seek(offset)
                    raw = fh.read(packed)
                return zlib.decompress(raw) if comp else raw
    except OSError:
        pass
    return None


def _list_dat(dat_path: Path) -> list[tuple[str, int, bool]]:
    """List all files in a DAT2 archive as (name, uncompressed_size, compressed)."""
    results = []
    try:
        with open(dat_path, "rb") as fh:
            fh.seek(-8, 2)
            tree_size, dat_size = struct.unpack("<II", fh.read(8))
            fh.seek(dat_size - tree_size - 8)
            tree = fh.read(tree_size)
        pos = 4
        while pos < len(tree):
            nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
            name = tree[pos:pos + nl].decode("latin-1"); pos += nl
            comp = tree[pos]; pos += 1
            unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
            results.append((name, unc, bool(comp)))
    except OSError:
        pass
    return results

# ── Proto parsing ─────────────────────────────────────────────────────────────

ITEM_TYPES = {0: "Armor", 1: "Container", 2: "Drug", 3: "Weapon", 4: "Ammo", 5: "Misc", 6: "Key"}


def _parse_item_proto(data: bytes) -> dict:
    """
    Parse an item proto (.pro) file into named fields.

    Offsets verified empirically against proto 51 (inactive dynamite):
      0   PID               (uint32 BE)
      4   TextID            (uint32 BE) — index into pro_item.msg
      8   FrmID             (uint32 BE)
     12   LightDistance     (uint16 BE)
     14   LightIntensity    (uint16 BE)
     16   Flags             (uint32 BE)
     20   ExtendedFlags     (uint32 BE)
     24   (unknown field)
     28   ScriptID          (int32  BE) — 0-based scripts.lst index; -1 = none
     32   ItemType          (uint32 BE) — 0=Armor 1=Container 2=Drug 3=Weapon 4=Ammo 5=Misc 6=Key
     36   Material          (uint32 BE)
     40   Size              (uint32 BE)
     44   Weight            (uint32 BE)
     48   Cost              (uint32 BE) — barter value in caps
    """
    if len(data) < 52:
        return {"error": f"Too short: {len(data)} bytes (expected ≥52)"}
    item_type_raw = struct.unpack_from(">I", data, 32)[0]
    return {
        "PID":           struct.unpack_from(">I", data,  0)[0],
        "TextID":        struct.unpack_from(">I", data,  4)[0],
        "FrmID":         struct.unpack_from(">I", data,  8)[0],
        "LightDistance": struct.unpack_from(">H", data, 12)[0],
        "LightIntensity":struct.unpack_from(">H", data, 14)[0],
        "Flags":         hex(struct.unpack_from(">I", data, 16)[0]),
        "ExtendedFlags": hex(struct.unpack_from(">I", data, 20)[0]),
        "ScriptID":      struct.unpack_from(">i", data, 28)[0],   # signed; -1 = no script
        "ItemType":      ITEM_TYPES.get(item_type_raw, f"unknown({item_type_raw})"),
        "Material":      struct.unpack_from(">I", data, 36)[0],
        "Size":          struct.unpack_from(">I", data, 40)[0],
        "Weight":        struct.unpack_from(">I", data, 44)[0],
        "Cost":          struct.unpack_from(">I", data, 48)[0],
    }

# ── Documentation search index ────────────────────────────────────────────────

_chunks: list[tuple[str, str]] = []   # (source_filename_stem, chunk_text)
_bm25: object = None                  # BM25Okapi instance or None


def _load_docs() -> None:
    global _chunks, _bm25
    _chunks = []
    if not DOCS_DIR.exists():
        return
    for path in sorted(DOCS_DIR.glob("**/*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        words = text.split()
        chunk_size, step = 120, 90       # words per chunk, stride
        positions = range(0, max(1, len(words) - chunk_size + 1), step)
        for i in positions:
            _chunks.append((path.stem, " ".join(words[i:i + chunk_size])))
        if not words:
            _chunks.append((path.stem, text))

    if HAS_BM25 and _chunks:
        _bm25 = BM25Okapi([c[1].lower().split() for c in _chunks])


_load_docs()

# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_f2_docs(query: str, top_k: int = 5) -> str:
    """
    Search Fallout 2 modding documentation.
    Covers: sfall opcodes, SSL syntax, proto field layout, scripts.lst rules,
    compile.exe flags, and verified facts from prior debugging sessions.
    Returns the most relevant text chunks.
    """
    if not _chunks:
        return (
            "No documentation loaded yet.\n"
            "Run:  py -3 mcp/fetch_docs.py\n"
            "Then restart the MCP server."
        )
    q_tokens = query.lower().split()
    if _bm25 is not None:
        scores = _bm25.get_scores(q_tokens)
    else:
        # Simple keyword-frequency fallback (no rank_bm25)
        scores = [sum(w in chunk[1].lower() for w in q_tokens) for chunk in _chunks]

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    parts = [f"[{_chunks[i][0]}]\n{_chunks[i][1]}" for i in top_indices if scores[i] > 0]
    return "\n\n---\n\n".join(parts) if parts else "No relevant results found."


@mcp.tool()
def inspect_proto(proto_id: int, source: str = "auto") -> str:
    """
    Parse an item proto file and return all named field values.
    proto_id: the numeric proto ID (e.g. 600 for Dynamite MKII, 51 for inactive dynamite)
    source:   'auto' (checks f2mod.dat first, then master.dat),
              'f2mod', or 'master'
    """
    filename = f"{proto_id:08d}.pro"
    internal = f"proto\\items\\{filename}"
    data = None

    f2mod_path  = GAME_ROOT / "mods" / "f2mod.dat"
    master_path = GAME_ROOT / "master.dat"

    if source in ("auto", "f2mod") and f2mod_path.exists():
        data = _read_dat(f2mod_path, internal)
    if data is None and source in ("auto", "master") and master_path.exists():
        data = _read_dat(master_path, internal)

    if data is None:
        searched = []
        if source in ("auto", "f2mod"):  searched.append("f2mod.dat")
        if source in ("auto", "master"): searched.append("master.dat")
        return f"Proto {proto_id} not found in: {', '.join(searched)}"

    fields = _parse_item_proto(data)
    lines = [f"Proto {proto_id} ({filename}) — {len(data)} bytes"]
    for k, v in fields.items():
        lines.append(f"  {k:16s} = {v}")
    return "\n".join(lines)


@mcp.tool()
def read_scripts_lst(source: str = "f2mod", tail: int = 20, search: str = "") -> str:
    """
    Read scripts.lst with 0-based line numbers.
    The 0-based line index is the ScriptID value to use in a proto's ScriptID field.

    source: 'f2mod' (the copy bundled in f2mod.dat — most current),
            'rpu'   (rpu.dat's copy),
            'master' (vanilla copy)
    tail:   show this many lines from the end (default 20); ignored if search is set
    search: if given, show only lines containing this substring
    """
    dat_sources = {
        "f2mod":  GAME_ROOT / "mods" / "f2mod.dat",
        "rpu":    GAME_ROOT / "mods" / "rpu.dat",
        "master": GAME_ROOT / "master.dat",
    }
    dat_path = dat_sources.get(source)
    if dat_path is None:
        return f"Unknown source '{source}'. Use: f2mod, rpu, master"
    if not dat_path.exists():
        return f"{dat_path} not found."

    raw = _read_dat(dat_path, r"scripts\scripts.lst")
    if raw is None:
        return f"scripts.lst not found inside {dat_path.name}"

    all_lines = raw.decode("latin-1").replace("\r\n", "\n").split("\n")
    if all_lines and not all_lines[-1]:
        all_lines = all_lines[:-1]

    total = len(all_lines)
    header = f"scripts.lst from {dat_path.name} — {total} lines (valid ScriptID range: 0–{total - 1})"

    if search:
        matches = [(i, line) for i, line in enumerate(all_lines) if search.lower() in line.lower()]
        if not matches:
            return f"{header}\n\nNo lines matching '{search}'."
        body = "\n".join(f"  {i:5d}  {line}" for i, line in matches)
        return f"{header}\n\nLines matching '{search}':\n{body}"

    show = all_lines[-tail:]
    start_idx = total - len(show)
    body = "\n".join(f"  {start_idx + i:5d}  {line}" for i, line in enumerate(show))
    return f"{header}\n\nLast {len(show)} entries:\n{body}"


@mcp.tool()
def compile_ssl(ssl_path: str) -> str:
    """
    Compile an SSL script to a .int binary using compile.exe.
    ssl_path: path to the .ssl file (absolute, or relative to the mod root C:\\git\\f2Mod)
    compile.exe location must be set as 'compile_exe' in mcp/config.json.
    Returns the compiler output on success or failure.
    """
    ssl = Path(ssl_path)
    if not ssl.is_absolute():
        ssl = MOD_ROOT / ssl_path
    if not ssl.exists():
        return f"File not found: {ssl}"

    if not COMPILE_EXE.exists():
        return (
            f"compile.exe not found at: {COMPILE_EXE}\n"
            "Set the correct path as 'compile_exe' in mcp/config.json and restart the server."
        )

    out = ssl.with_suffix(".int")
    try:
        result = subprocess.run(
            [str(COMPILE_EXE), "-q", "-p", ssl.name, "-o", str(out)],
            capture_output=True, text=True, timeout=30,
            cwd=str(ssl.parent),
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            size = out.stat().st_size if out.exists() else 0
            return f"OK — {out.name} ({size:,} bytes)" + (f"\n{output}" if output else "")
        else:
            return f"FAILED (exit {result.returncode})\n{output}"
    except subprocess.TimeoutExpired:
        return "compile.exe timed out after 30 s"
    except OSError as e:
        return f"Could not run compile.exe: {e}"


@mcp.tool()
def verify_f2mod() -> str:
    """
    Inspect the installed f2mod.dat: list all bundled files, parse proto 600,
    and show the tail of scripts.lst to verify the dynamitemk2 ScriptID entry.
    Use this after running install.py to confirm the build is correct.
    """
    dat_path = GAME_ROOT / "mods" / "f2mod.dat"
    if not dat_path.exists():
        return f"f2mod.dat not found at {dat_path}\nRun install.py first."

    lines = [f"f2mod.dat  ({dat_path.stat().st_size:,} bytes)"]

    # File list
    files = _list_dat(dat_path)
    lines.append(f"\nContents — {len(files)} file(s):")
    for name, size, compressed in sorted(files):
        tag = "[z]" if compressed else "   "
        lines.append(f"  {tag} {name}  ({size:,} bytes uncompressed)")

    # Proto 600
    proto_data = _read_dat(dat_path, r"proto\items\00000600.pro")
    if proto_data:
        fields = _parse_item_proto(proto_data)
        lines.append("\nProto 600:")
        for k, v in fields.items():
            lines.append(f"  {k:16s} = {v}")
    else:
        lines.append("\nProto 600: NOT FOUND")

    # scripts.lst tail
    sl = _read_dat(dat_path, r"scripts\scripts.lst")
    if sl:
        sl_lines = sl.decode("latin-1").replace("\r\n", "\n").split("\n")
        if sl_lines and not sl_lines[-1]:
            sl_lines = sl_lines[:-1]
        total = len(sl_lines)
        lines.append(f"\nscripts.lst — {total} lines (last valid ScriptID = {total - 1}):")
        for i, entry in enumerate(sl_lines[-5:], total - min(5, total)):
            lines.append(f"  {i:5d}  {entry}")
    else:
        lines.append("\nscripts.lst: NOT FOUND")

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
