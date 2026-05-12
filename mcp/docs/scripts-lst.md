# scripts.lst — Format and ScriptID Rules

## File format

Plain text, one script entry per line.  Line endings can be LF or CRLF.

```
; This is a comment — the semicolon is NOT the entry
ai_p1                   ; Standard AI  #1
...
dynamitemk2
```

A line's **0-based index** (counting from the very first line, including blank
and comment lines) is the `ScriptID` value written into a proto file's
ScriptID field.

## Where scripts.lst lives

The engine uses the highest-priority copy it can find, following `mods_order.txt`
(last entry = highest priority).

| Source | Priority (typical RPU setup) |
|--------|------------------------------|
| loose `data/scripts/scripts.lst` | Low — overridden by any .dat that contains one |
| `rpu.dat` → `scripts\scripts.lst` | Medium |
| `f2mod.dat` → `scripts\scripts.lst` | **Highest** (last in mods_order.txt) |

**Always bundle a complete scripts.lst inside f2mod.dat.**  If f2mod.dat does
not contain one, the engine falls back to the loose file (1302 lines in vanilla
RPU installs) instead of rpu.dat's complete version (1558 lines), causing
"Couldn't open scripts\<description>.int" errors on map load.

## Adding a new item script

1. Find the last line index in the base scripts.lst (e.g. rpu.dat's copy has
   1558 lines → valid indices 0–1557).
2. Append your entry: `dynamitemk2` (filename without `.int` extension).
3. New entry is at index 1558 — write `ScriptID = 1558` into the proto.
4. Bundle the modified scripts.lst inside f2mod.dat at `scripts\scripts.lst`.

## Counting lines in Python

```python
text_lines = scripts_lst.replace(b"\r\n", b"\n").split(b"\n")
if text_lines and text_lines[-1] == b"":
    text_lines = text_lines[:-1]   # strip trailing empty element
script_id = len(text_lines)        # index of the entry you are about to append
```

## local_vars comment

Some tools write `# local_vars=N` as a trailing comment.  The Fallout 2 engine
ignores it; the compiled `.int` file's header contains the actual local variable
count.  For item scripts with no top-level `variable` declarations, `local_vars=0`.
