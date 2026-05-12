# Verified Debugging Facts — f2Mod Session

Hard-won facts from the f2Mod development session.  These are the things that
caused crashes or wasted hours when wrong.

## Crashes

### `#` comment in pro_item.msg → crash on map load
Appending a line starting with `#` to `pro_item.msg` causes a crash when the
game loads any map that displays an item with that message ID.
**Never write comment lines to pro_item.msg.**

### Incomplete scripts.lst → "Couldn't open scripts\<X>.int" + crash
If f2mod.dat (highest-priority mod) does not bundle `scripts\scripts.lst`, the
engine uses the loose file instead of rpu.dat's more complete version.  The
loose file shipped with RPU is missing entries that rpu.dat itself added, so
any critter or object whose script is listed only in rpu.dat's scripts.lst
triggers this error.
**Always bundle rpu.dat's scripts.lst (modified to add your entries) inside f2mod.dat.**

### Missing spatial script → crash on Arroyo worldmap ("A swarm of mantis infesting some spore plants.int")
**Root cause (pre-existing, not introduced by our changes):**
When the player first enters the Arroyo worldmap region after completing the
Temple of Trials, the engine may trigger a worldmap encounter whose description
in `worldmap.msg` is entry `{4013}{}{ A swarm of mantis infesting some spore
plants.}`.  The engine strips the trailing period and appends `.int`, then
tries to open `scripts\A swarm of mantis infesting some spore plants.int`.
That file was never shipped in master.dat, critter.dat, or rpu.dat — it is
simply absent from the entire installation.

The crash is probabilistic (dependent on encounter RNG), so a player who never
triggered that specific encounter wouldn't notice it.  Our script changes did
not alter any scripts.lst index — we only appended `dynamitemk2` at the end —
so we could not have caused or prevented this crash.

Fixed by writing a no-op stub `.int` as a **loose file** to `<game>/data/scripts/`.
Bundling the stub inside f2mod.dat is NOT sufficient — the engine opens this script
via direct file I/O (bypassing DAT lookup) so a loose copy is required.
**Source: `data/scripts/a swarm of mantis infesting some spore plants.ssl` → written loose via LOOSE_SCRIPTS in install.py.**

### DontDeleteProtos=0 → loose proto files deleted at startup
The default sfall setting (`DontDeleteProtos=0`) causes the engine to delete any
loose `.pro` file that does not have the ReadOnly filesystem attribute.

Two fixes:
1. **Package all protos inside f2mod.dat** (preferred for distribution).
2. **Set `DontDeleteProtos=1` in ddraw.ini** — protects all loose protos regardless
   of ReadOnly attribute. Required when developing/patching protos as loose files.

**Critical interaction:** If you remove the ReadOnly attribute from a loose proto
(e.g. to patch it) and `DontDeleteProtos=0`, the engine will delete the file on the
next launch, causing a "Can't fopen proto!" crash on map load.

### set_global_script_repeat(0) does NOT disable the script
`set_global_script_repeat(0)` means fire every frame.  Use `300` for ~5 s.

## Compiler

### -p flag is required
`compile.exe -O script.ssl` fails with "Undefined symbol REPEAT_FRAMES" because
the optimiser flag does not enable the preprocessor.
**Always use: `compile.exe -q -p script.ssl -o script.int`**

## sfall opcodes

### set_pc_stat_max, get_sfall_arg, set_sfall_return are direct opcodes
These are NOT macros in SFALL.H — they are native sfall VM opcodes.  Do not
add parentheses around their arguments as if calling a macro.

### SSL and/or are bitwise, not short-circuit
Both sides of `and`/`or` are always evaluated.  For short-circuit behaviour:
```ssl
if (condition_a) then begin
    if (condition_b) then begin
        ...
    end
end
```

## Proto 600 (Dynamite MKII)

- Based on proto 51 (inactive dynamite, MISC type).
- ScriptID must be set to the 0-based index of `dynamitemk2` in the bundled scripts.lst.
- TextID uses the convention `proto_id * 100` = 60000 (name) and 60001 (description).
- OFFSET_SCRIPT_ID = 28, OFFSET_COST = 48 (verified against binary of proto 51).

## Weapon-type items in container static inventory — correct ammo state AND max_slots required

The 8 weapon extra bytes (ammo_type + ammo_count) in a MAP-patched weapon item must
be set correctly or the engine crashes when the player opens the container.

**Correct values (confirmed by scanning all weapon items in kladwtwn.map):**

| Weapon class | ammo_type | ammo_count |
|---|---|---|
| No-ammo (melee, thrown) | `0x00000000` | `0xFFFFFFFF` |
| Loaded ranged weapon | ammo proto internal PID | number of rounds loaded |

Setting `ammo_count=0` for a no-ammo weapon causes a crash on container open.
Setting `ammo_count=0xFFFFFFFF` is the correct sentinel for "no ammo loaded."

**Verified examples from kladwtwn.map:** throwing knives (proto 45), knife (proto 4),
spear (proto 7) — `ammo_type=0, ammo_count=0xFFFFFFFF` (true no-ammo weapons).
Power Fist (proto 235) — `ammo_type=25 (Small Energy Cells), ammo_count=38`.
Loaded 10mm pistol (proto 299) — `ammo_type=1, ammo_count=29`.

**Warning:** The Power Fist is NOT a no-ammo weapon despite being melee. It requires
Small Energy Cells. Using `ammo_type=0, ammo_count=0xFFFFFFFF` crashes the engine
when the container is opened. All vanilla map instances use `ammo_type=25, ammo_count=38`.

**Container max_slots must be ≥ ammo_count for loaded weapons.**
The engine appears to validate `ammo_count ≤ max_slots` when opening a container.
If `ammo_count` (e.g. 38 for a Power Fist) exceeds the container's `max_slots` (e.g. 10),
the engine crashes on container open.  Always raise `max_slots` on the container to at
least the weapon's ammo_count before placing a loaded weapon in its static inventory.
(Power Fist: ammo_count=38, so max_slots must be ≥ 38; use 100 as a safe ceiling.)

## PID confusion: file number vs internal PID → wrong item created

Using a file number where an internal PID is expected produces the wrong item with
no error or warning from the engine.

**Example:** Power Armor is stored in `00000014.pro` (file number 14), but its
internal PID field (offset 0) is 3.  Patching kisbox.int to restock PID 14 instead
of PID 74 (leather jacket) caused the game to create the item whose internal PID is
14 — that is file `00000008.pro`, an Explosive Rocket ammo (TextID 1400).

**Rule:**
- MAP object `proto_pid` field → **file number**.
- SSL / kisbox.int `check_restock_item(pid, ...)` → **internal PID** (offset 0 of .pro).
- `obj_pid(obj)` returns internal PID.

For most items the file number and internal PID are equal, masking the distinction.
Items in the low file-number range (approximately 1–14) are the known exceptions.
Use `inspect_proto` to read the `PID` field from the .pro file before using any
proto in a script.  See proto-format.md §"Internal PID vs File Number".

## MAP patch + proto with ScriptID → black screen on fresh map load

Patching `kladwtwn.map` to add items of proto 600 (Dynamite MKII, ScriptID=1558)
to the Sajag Kisbox causes a completely black screen on fresh Klamath entry
(character and cursor visible, no tiles).  Existing saves load fine.

**Root cause confirmed:** A container's static inventory item whose proto has
ScriptID ≠ -1 triggers the black screen.  Adding Power Armor T-51b (file 14,
ScriptID=-1) instead does not.

**Rule:** Items placed in a container via MAP patching must have ScriptID=-1.
Do not add scripted protos to a container's static inventory.

See `map-format.md` for full Kisbox structure and patching recipe.

## Goris body type

All Goris proto variants (152, 319–324) already have PROTO_CR_BODY_TYPE = 0 (Biped)
in vanilla master.dat.  RPU does not override them.  No body-type patching is needed
for `wield_obj_critter` to work.

## MSG_ID conventions

- pro_item.msg ID for a proto = `proto_id * 100` (name), `proto_id * 100 + 1` (description).
- Do NOT use arbitrary IDs — check for collisions with existing entries first.

## GlobalScriptPaths

`ddraw.ini` setting `GlobalScriptPaths=scripts\gl*.int,scripts\sfall\gl*.int`
already covers all `gl_*.int` and `hs_*.int` files by wildcard.  The installer
does not need to modify this setting.

## game_loaded timing

`if game_loaded` in a global script fires on:
1. New game start
2. Save file load
3. **Every map transition**

Use it to set `set_global_script_repeat` and do one-time-per-session
initialisation, but guard stateful operations with checks (e.g. "already
stocked?") because the script will re-run on every map load.

## item_make_explosive silently fails — map-baked SID blocks obj_use_explosive

`item_make_explosive` hooks into `obj_use_explosive`, but the engine calls
`obj_use_radio` first.  The full call chain:

```
protinst_use_item → obj_use_radio → (obj->sid != -1): run use_p_proc, return 0 → STOP
                                  → (obj->sid == -1): return -1 → CONTINUE
                  → obj_use_explosive   ← item_make_explosive hook lives here
```

`obj_use_radio` checks the **object's in-memory `sid` field** — not the proto.
If the object has any sid (even if the script file is empty or has no `use_p_proc`),
`obj_use_radio` runs it and returns 0, and `obj_use_explosive` is never reached.

**Root cause of the silent failure:** Map-placed objects have their SID baked into
the map file at placement time (`obj_new_sid` reads the proto's ScriptID, creates a
script instance, and saves the SID to the map binary).  At load time, `obj_read_obj`
reads the SID directly from the map file — **the proto is not re-consulted**.
Patching the proto's ScriptID to -1 does NOT affect objects already placed on maps.

**Fix (runtime):** In the `game_loaded` handler of a global script, iterate the
player's inventory and clear the SID for any affected items:

```ssl
variable i, item;
for i := 0 to (inven_count(dude_obj) - 1) do begin
  item := inven_nth_item(dude_obj, i);
  if (item != 0 and obj_pid(item) == MY_INERT_PID) then
    set_object_data(item, OBJ_DATA_SID, -1);
end
```

`OBJ_DATA_SID = 0x78` (defined in `define_extra.h`).  Because `game_loaded` fires
on every map transition, this runs before the player can use the item regardless of
which map it was picked up on.

**Alternative fix:** Re-place the item in the mapper after patching the proto's
ScriptID to -1.  The new placement calls `obj_new_sid` against the updated proto,
so the saved SID will be -1 in the map file from then on.
