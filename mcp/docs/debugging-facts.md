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

## data\MAPS\*.SAV — working cache, not cleared between sessions

`data\MAPS\` is a working temp directory, separate from slot save directories
(`data\SAVEGAME\SLOT##\`).  The engine writes a `.SAV` for each visited map on
every map transition — even if the player never manually saves.

**The original Fallout 2 exe does not reliably clear this directory between game
sessions.**  If you start a new game after a prior session visited the same maps,
those stale `.SAV` files are loaded, and your mapper-placed items (picked up,
moved, or otherwise changed in the previous run) will be missing or wrong on the
new run.

**This directory is safe to delete when the game is not running.**  Slot saves
in `data\SAVEGAME\` are unaffected — they are an entirely separate copy written
only on manual save.

**Fix for test runs:** Delete `data\MAPS\*.SAV` before each test run to guarantee
a clean map state.  Failure to do so causes confusing "items missing on fresh new
game" bugs that have nothing to do with scripts or protos.

## obj_pid() on critters includes type bits

`obj_pid(critter_obj)` returns the **full** 32-bit PID including the object type
byte in bits 24–31.  The critter type is `1`, so the full PID is
`0x01000000 | file_number` = `16777216 + file_number`.

Comparing a critter PID against a bare file number (e.g., `obj_pid(goris) == 152`)
will **always fail** — the actual return value is `16777368` for Goris base (file
152).  This mistake makes any critter-identity check a silent no-op.

**Correct constant definition:**
```ssl
#define PID_GORIS_BASE  (16777216 + 152)   /* = 0x01000098 */
```

**Items are unaffected** — item type = 0, so item PIDs equal their file numbers
(e.g., `PID_BRIDGEKEEPERS_ROBES = 524`).

Confirmed from: `fallout2-re` source (`opGetObjectPid` returns `obj->pid` raw),
RPU `critrpid.h` (`PID_GORIS = 16777368`), RPU `party.h`
(`Goris_Ptr = party_member_obj(PID_GORIS)`).

## Strength mechanics and HOOK_ITEMDAMAGE

### Confirmed Strength effects (vanilla Fallout 2)

| Effect | Formula |
|--------|---------|
| Carry Weight | `25 + (ST × 25)` lbs (Small Frame: × 15) |
| Melee Damage (derived stat) | `max(ST − 5, 1)` |
| Starting Unarmed skill | `65 + (AG + ST) / 2` |
| Starting Melee Weapons skill | `55 + (AG + ST) / 2` |
| Starting Hit Points | `15 + ST + (2 × EN)` |
| Weapon min-ST penalty | −20% to hit per missing ST point |

Melee Damage is added to **maximum damage only** (not minimum).  It applies to
**both** unarmed and melee weapon attacks — not unarmed only.  Example: a crowbar
with base 3–10 and Melee Damage 4 becomes 3–14.

Confirmed from: Fallout wiki weapon damage notation, NMA engine calculations,
`tartarus.rpgclassics.com` skill formulas, GOG forum min-ST penalty thread.

### Modifying melee damage with HOOK_ITEMDAMAGE

`HOOK_ITEMDAMAGE` fires whenever the engine retrieves the damage rating of the
player's weapon (including fists).

```
int  arg0 - default min damage (already includes vanilla Melee Damage bonus)
int  arg1 - default max damage (already includes vanilla Melee Damage bonus)
Item arg2 - weapon object (0 if unarmed)
Critter arg3 - the attacker
int  arg4 - attack type
int  arg5 - non-zero if melee weapon

int  ret0 - new min damage (or single fixed value if ret1 not set)
int  ret1 - new max damage
```

**Key detail:** `arg0`/`arg1` already have the vanilla `max(ST − 5, 1)` bonus
baked in.  To replace the formula entirely, subtract the vanilla bonus out first
or just set absolute values directly.

**Pattern for a custom ST-based melee bonus:**
```ssl
procedure hs_itemdamage_proc begin
    variable attacker := get_sfall_arg_at(3);
    if (attacker != dude_obj) then return;
    variable is_melee := get_sfall_arg_at(5);
    if (not is_melee) then return;

    variable st := get_critter_stat(attacker, STAT_st);
    variable cur_min := get_sfall_arg_at(0);
    variable cur_max := get_sfall_arg_at(1);
    /* replace with custom formula */
    set_sfall_return(cur_min);
    set_sfall_return(cur_max + (st - 5));
end
```

Registration: `register_hook_proc(HOOK_ITEMDAMAGE, hs_itemdamage_proc)` in
`game_loaded` block of any global script.

---

## NPC Identification — Fast Path

**Goal:** find a named NPC's script index and proto PID so you can gate a hook script on that specific NPC.

### Step 1 — get the scripts.lst index
```
mcp: read_scripts_lst search=<partial name>
```
Returns 0-based line numbers. The 0-based index is what `get_script(obj)` returns at runtime.

Example: `read_scripts_lst search=ascorti` → `809  RCAscort.int`

### Step 2 — get internal_pid (only if needed for obj_pid())
Look up the NPC in `tools/critters.csv` (columns: file_num, internal_pid, name, map).
- internal_pid = `0x01000000 | file_num`
- `obj_pid()` is only needed when `get_script()` alone isn't specific enough (rare).

### Step 3 — runtime gate in hook script
```ssl
if (get_script(target) == 809) then begin   // 809 = RCAscort.int
    // Ascorti-specific logic
end
```

`get_script(obj)` returns the 0-based scripts.lst index for the script attached to an object.
Returns 0 if unscripted, -1 on error. Works on any object, not just the player.

### Why this is faster than MAP binary analysis
MAP binary parsing (reading the scripts section, tracing SID→script index, scanning object fields)
is complex and error-prone. It's only needed for **static MAP patching**. For runtime hook scripts,
`get_script()` does the lookup in one call with no MAP parsing required.

### When multiple critters share a proto
Many named NPCs use a generic proto (e.g., Ascorti uses "Bureaucrat 2" / file_num 456).
`obj_pid()` alone can't distinguish them. `get_script(target) == <index>` uniquely identifies
the named NPC because each NPC has its own script file.

### NPCs confirmed (scripts.lst 0-based index)
| NPC | Script | Index | file_num | internal_pid | Notes |
|-----|--------|-------|----------|--------------|-------|
| Doc Andrew (Vault City) | VCAndy.int | 92 | 468 | 16777684 | — |
| Guards (Ascorti's bar) | RCAscGrd.int | 1113 | 456 | 16777672 | same proto as Ascorti |
| Sgt. Stark (Vault City) | VCStark.int | 122 | — | — | NOT Navarro |
| Sgt. Dornan (Navarro drill sergeant) | Ccdrill.int | 717 | — | — | "Drill Seargant in Colusa/Nevarro" |
| Metzger (The Den, slaver) | dcMetzge.int | 45 | — | — | — |
| Jo (Modoc) | mcJo.int | 101 | — | — | — |
| Mayor Ascorti (Redding) | RCAscort.int | 809 | 456 | 16777672 | — |
| Marge LeBarge (Redding) | RCMarge.int | 693 | — | — | — |
| Dan McGrew (Redding) | RCMcGrew.int | 806 | — | — | — |
| First Citizen Lynette (Vault City) | VCLynett.int | 127 | — | — | — |
| Valerie, Vic's daughter (Vault City) | VCMainWk.int | 971 | — | — | — |
| Festus (Gecko) | GCFestus.int | 130 | — | — | "Festering ghoul" in scripts.lst |
| Rose (Modoc diner) | mcRose.int | 107 | — | — | — |
| Liz (Broken Hills) | hcLiz.int | 596 | — | — | — |
| Intelligent Radscorpion (Broken Hills) | hcScorp.int | 1172 | — | — | only scorpion script in BH |
| Brian, Power Technician (Broken Hills) | hcBrian.int | 1131 | — | — | — |
| Doc Jubilee (NCR) | SCDocJub.int | 462 | — | — | painting = SIpaint.int index 953 |
| Fergus (NCR Congress House receptionist) | SCFergus.int | 520 | — | — | "Welcome to Congress House…" |
| Westin (NCR rancher, NCR3) | SCWestin.int | 470 | — | — | — |
| Raul (Navarro) | CcRaul.int | 1052 | — | — | — |
| Ken Lee (San Francisco) | FCKenLee.int | 855 | — | — | — |
| Big Jesus Mordino (New Reno) | ncBigJes.int | 455 | — | — | — |
| Mr. Salvatore (New Reno boss) | ncSalvat.int | 442 | — | — | — |
| John Bishop (New Reno) | ncBishop.int | 419 | — | — | — |
| Orville Wright (New Reno) | ncOrvill.int | 438 | — | — | — |
| President Richardson (Enclave) | qhPrzRch.int | 802 | — | — | — |

### Doc Jubilee painting — Vault 13 reveal mechanism
- PID 78 (Fuzzy Painting / "Velvet Elvii") has ScriptID=-1 in the proto.
- SIpaint.int (index 953) is attached to the painting OBJECT at runtime by Doc Jubilee's script.
- When the player examines the painting in inventory, SIpaint.int fires and marks Vault 13 on the world map.
- To replicate this for a stolen painting, use `create_object_sid(78, 0, 0, 953)` instead of `create_object(78, 0, 0)`.

### Compiler constraint: parametrized user-defined procedure calls
The F2 SSL compiler (sfall compile.exe) requires parametrized user-defined procedure calls to appear in an **assignment context**. Bare statement calls (`inject(target, pid, want);`) cause "Assignment operator expected." Always assign: `r := inject(target, pid, want);`

---

## Fake Selectable Perks (set_selectable_perk_npc)

### perk_add_mode is a direct opcode, not a metarule
Call as `perk_add_mode(value)` — NOT `sfall_func1("perk_add_mode", value)`.
The metarule form silently fails with `OPCODE ERROR: sfall_func1("perk_add_mode", ...) - metarule function is unknown.` in debug.log, leaving perk_add_mode at its default. The default appears to be `ADD_PERK_MODE_PERK (2)`.

### ADD_PERK_MODE_REMOVE (4) crashes the game on perk selection
Setting `perk_add_mode(ADD_PERK_MODE_PERK + ADD_PERK_MODE_REMOVE)` causes a hard crash when the player selects a fake perk from the level-up dialog. Use `ADD_PERK_MODE_PERK (2)` only. To prevent re-taking a perk, rely on `has_fake_perk_npc` at registration time — if the player already has it, don't call `set_selectable_perk_npc` again on the next game load.

### has_fake_perk_npc is also a direct opcode
`has_fake_perk_npc(critter, name)` returns 1 if taken, 0 if not taken or not registered. It is not defined in SFALL.H — call it directly.

### Registration pattern for player-selectable perks
```ssl
// In game_loaded block:
perk_add_mode(ADD_PERK_MODE_PERK);
if (has_fake_perk_npc(dude_obj, PERK_NAME) == 0) then
   set_selectable_perk_npc(dude_obj, PERK_NAME, 1, IMAGE_INDEX, PERK_DESC);
```
`set_selectable_perk_npc` uses `obj_dude->id` as the owner, bypassing the IsNpcControlled() check, which is what makes it work for the player character.

---

## HOOK_CALCAPCOST facts

### arg4 (weapon) can be non-zero garbage in non-combat contexts
The hook fires during interface redraws (not just combat). In those calls, arg4 is not 0 but is also not a valid object pointer (observed value: 5). Passing it to `obj_pid()` crashes. **Always get the weapon via `critter_inven_obj`** — never trust arg4:
```ssl
if (atktype < 2) then
   wpn := critter_inven_obj(critter, INVEN_TYPE_LEFT_HAND);
else
   wpn := critter_inven_obj(critter, INVEN_TYPE_RIGHT_HAND);
```

### The hook fires multiple times per attack action — arg3 (ap_cost) compounds
HOOK_CALCAPCOST fires for display updates, computing, sequencing, and running phases. Each subsequent firing receives the already-modified cost from the previous firing as arg3. A naive `-2` applied three times gives `5→3→1→1` instead of `5→3`. To compute the reduction idempotently, **read the vanilla AP cost from the proto** instead of from arg3:
```ssl
if (atktype bwand 1) then
   new_cost := get_proto_data(obj_pid(wpn), PROTO_WP_APCOST_2) - 2;
else
   new_cost := get_proto_data(obj_pid(wpn), PROTO_WP_APCOST_1) - 2;
```
`atktype bwand 1 == 0` = primary attack (LWEP1/RWEP1); `== 1` = secondary (LWEP2/RWEP2).

### Detecting throw attacks: use PROTO_FLAG_EXT, not PROTO_WP_ANIM
`PROTO_WP_ANIM` (offset 36) stores the **weapon animation class** (WPN_ANIM_KNIFE=1, WPN_ANIM_PISTOL=5, etc.) — NOT the attack mode.

Attack modes (Swing/Thrust/Throw/Single/Burst/Flame) are packed in **`PROTO_FLAG_EXT` (offset 24)**:
- **Lower nibble** (bits 0–3): primary attack mode
- **Upper nibble** (bits 4–7): secondary attack mode

Confirmed from `fallout2-ce` source (`weaponGetAttackTypeForHitMode` reads `extendedFlags & 0xF` for primary, `(extendedFlags & 0xF0) >> 4` for secondary).

```ssl
variable ext := get_proto_data(obj_pid(wpn), PROTO_FLAG_EXT);
if (atktype bwand 1) then
   is_throw := ((ext bwand 0xF0) == (ATTACK_MODE_THROW * 16));  // secondary
else
   is_throw := ((ext bwand 0xF) == ATTACK_MODE_THROW);           // primary
```
Both `PROTO_FLAG_EXT` and `ATTACK_MODE_THROW` are already defined in `define_extra.h`.
