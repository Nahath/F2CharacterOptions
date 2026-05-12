# SSL Compiler (compile.exe) — Usage Reference

## Critical: the -p flag

**Always compile with `-p`.**  Without it the preprocessor does not run and
`#define`, `#include`, and symbolic constants from `DEFINE.H` / `SFALL.H` are
not expanded.  The compiler exits with "Undefined symbol" errors even for
standard symbols like `REPEAT_FRAMES`.

```
compile.exe -q -p script.ssl -o script.int
```

| Flag | Meaning |
|------|---------|
| `-p` | **Run the C-style preprocessor** (handles `#include`, `#define`, `#ifdef`). Required. |
| `-q` | Quiet — suppress progress output. |
| `-O` | Enable optimiser. Does NOT imply `-p`. |
| `-o <file>` | Output file path. Defaults to same name as input with `.int` extension. |

## Include paths

`DEFINE.H` and `SFALL.H` must be on the include path.  Place them in the same
directory as the `.ssl` file, or pass `-I <path>` to add a search directory.

Common additional headers:
- `define_extra.h` — extra sfall constants (e.g. `LIST_CRITTERS`)
- `MAPS.H` — map index constants

## Script types

| Type prefix | Description | Registration |
|-------------|-------------|--------------|
| `gl_`       | Global script — runs every map | Listed in `ddraw.ini` `GlobalScriptPaths` |
| `hs_`       | Hook script — called by sfall hook points | Same as above |
| (plain name) | Item / critter / spatial script | Entry in `scripts.lst`; ScriptID in proto |

## Global script behaviour

- `game_loaded` fires on: new game, save load, **and every map transition**.
- `set_global_script_repeat(0)` means **every frame** (not disabled).  Use `300` for ~5 s interval.
- SSL `and` / `or` are **bitwise** — both sides always evaluate.  Use `if (a) then if (b)` for short-circuit logic.

## Compiling all scripts (build.bat)

```bat
@echo off
set COMPILE=C:\path\to\compile.exe
set SCRIPTS=C:\git\f2Mod\data\scripts
for %%f in (%SCRIPTS%\*.ssl) do (
    echo Compiling %%~nxf ...
    %COMPILE% -q -p "%%f" -o "%%~dpnf.int"
)
echo Done.
```
