# Current Session

## Task
Make Super Dynamite (PID 534 inert, PID 535 active) work as a 4x-damage dynamite.
- Uses correctly (inert → active in inventory) ✓
- Explodes after 10 seconds with 120–240 damage ✓
- Old inert item removed from inventory on use ✓ (PID mutated in-place — no remove/re-add)

## BEST WORKING STATE — DO NOT LOSE THIS

### What works right now
- Item uses correctly from inventory, icon changes, item stays in slot (PID mutated 534→535 in-place)
- Explosion fires correctly after timer
- Active item destroyed after explosion

### DYNMK2.ssl (fallback — use_p_proc approach, confirmed working):
```
#include "sfall.h"
#include "define_extra.h"

procedure start;
procedure use_p_proc;
procedure timed_event_p_proc;

procedure start
begin
end

procedure use_p_proc
begin
  script_overrides;
  set_object_data(self_obj, OBJ_DATA_PID, 535);
  rm_timer_event(self_obj);
  add_timer_event(self_obj, game_ticks(10), 0);
  inventory_redraw(0);
end

procedure timed_event_p_proc
begin
  variable item_tile;
  variable item_elev;

  item_tile := tile_num(self_obj);
  item_elev := elevation(self_obj);

  if (item_tile <= 0) then begin
    item_tile := tile_num(dude_obj);
    item_elev := elevation(dude_obj);
  end

  explosion(item_tile, item_elev, random(120, 240));
  destroy_object(self_obj);
end
```
(This approach works but gives no timer dialog, fixed 10s, no hand-drop)

## Current Approach (item_make_explosive via gl_superdyn.ssl)
Goal: timer dialog, Traps-based duration, auto hand-drop — identical to vanilla dynamite behavior.

### File state
**DYNMK2.ssl** — empty (no use_p_proc, so engine reaches item_make_explosive handler):
```
procedure start;

procedure start
begin
end
```

**gl_superdyn.ssl** — registers item_make_explosive + patches icon:
```
#include "sfall.h"
#include "define_extra.h"

// dynon.frm = INVEN.LST index 122 (0-based), type 7 = inventory art
#define DYNMK2ON_INVEN_FID  ((ART_TYPE_INVENT * 0x1000000) + 122)

procedure start;

procedure start
begin
  if game_loaded then begin
    item_make_explosive(534, 535, 120, 240);
    set_proto_data(535, PROTO_IT_INV_FID, DYNMK2ON_INVEN_FID);
  end
end
```

**00000534.pro** — 69 bytes, ScriptID patched to FF FF FF FF (bytes 28-31), all other bytes original:
  00 00 02 16 00 00 D0 98 00 00 00 17 00 00 00 00 00 00 00 00 A0 00 00 08
  00 00 A8 00 FF FF FF FF 00 00 00 05 00 00 00 01 00 00 00 01 00 00 00 05
  00 00 01 F4 07 00 00 2E 30 FF FF FF FF 00 00 00 00 00 00 00 00

**00000535.pro** — 69 bytes, ScriptID patched to FF FF FF FF (bytes 28-31), all other bytes original:
  00 00 02 17 00 00 D0 FC 00 00 00 17 00 00 00 00 00 00 00 00 A0 00 00 08
  00 00 A8 00 FF FF FF FF 00 00 00 05 00 00 00 01 00 00 00 01 00 00 00 04
  00 00 02 8A 07 00 00 2F 30 00 00 00 26 00 00 00 03 00 00 00 C8

**ddraw.ini**: DontDeleteProtos=1 (was 0; engine was deleting the loose .pro files at startup)

### Why item_make_explosive requires SID=-1 on the OBJECT
The engine's item-use chain: protinst_use_item → obj_use_radio → obj_use_explosive.
obj_use_radio checks the OBJECT's in-memory sid field. If sid != -1, it runs use_p_proc
(even if the script is empty or has no such procedure) and returns 0, stopping the chain
before obj_use_explosive (and therefore item_make_explosive) is ever reached.

For map-placed objects, the SID is baked into the map file at placement time — it is NOT
re-read from the proto at load time. Patching the proto's ScriptID to -1 alone is not
sufficient for already-placed objects.

Fix used: in gl_superdyn.ssl game_loaded handler, iterate player inventory and call
set_object_data(item, OBJ_DATA_SID, -1) for any PID 534 items. This clears the baked SID
at runtime before the player can use the item. gl_superdyn.ssl final state includes this loop.

### DontDeleteProtos lesson
ddraw.ini had DontDeleteProtos=0. The engine deletes non-read-only loose protos at startup.
Original protos were protected by ReadOnly filesystem attribute. After we removed ReadOnly
to patch them, the engine deleted both files on the next launch → black screen crash.
Fix: DontDeleteProtos=1. Files no longer need to be ReadOnly.

## Key facts learned
- set_object_data(obj, OBJ_DATA_PID, 535) works correctly — stores raw proto number
- item_make_explosive requires SID=-1 on the OBJECT (map-placed items have baked SID independent of proto)
- obj_use_radio is the blocker — it runs before obj_use_explosive and short-circuits on any sid != -1
- game_loaded in global scripts fires on EVERY map transition (not just first load)
- DontDeleteProtos=0 (default): engine deletes non-read-only loose protos at startup
- INVEN.LST index 122 (0-based) = dynon.frm; FID = 0x0700007A
- OBJ_DATA_SID = 0x78 (from define_extra.h)

## Status: COMPLETE
Super Dynamite is fully working:
- Timer dialog appears (Traps-based duration)
- Item auto-drops from hand on activation
- dynon.frm icon shows on active item
- 120–240 damage explosion after timer
MCP docs updated: proto-format.md, debugging-facts.md, sfall-function-notes.md

## Next Step
No pending work.

## scripts.lst (loose override at data\scripts\scripts.lst)
- 0-based index 1303 = line 1304 in file = DYNMK2.int   ; Super Dynamite (inert)
- 0-based index 1304 = line 1305 in file = DYNMK2ON.int ; Super Dynamite (active)
(These entries become unused once ScriptID=-1, harmless to leave)

## Context
- Working dir: C:\Games\F2Modding\Fallout 2\data\scripts
- sfall version: 4.4.9.1
- Compiler: C:\git\f2Mod\tools\compiler\compile.exe (sfall edition 4.4.10)
- Headers in data\scripts\
- Vanilla dynamite: PID 51 (inert), PID 52 (lit) — both ScriptID=-1
- OBJ_DATA_PID = 0x64, stores raw proto number (534/535 confirmed)
