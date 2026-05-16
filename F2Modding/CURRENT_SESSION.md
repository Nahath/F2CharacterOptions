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

## Additional session work (post-compaction)
- ST cap for Power Armor raised to 14 (from 12); verified via punch damage
- Removed Change 2 (steal equipped weapons): deleted hs_steal.ssl/.int, kcsajag.ssl/.int, removed from install.py
- Removed all Klamath downtown map changes: deleted kisbox.ssl/.int, removed all MAP-patch code from install.py
- Confirmed install.py runs cleanly; f2mod.dat = 9 files, 28,248 bytes
- Documented data\MAPS\ cache behavior in debugging-facts.md

## gl_goris_armor.ssl — COMPLETE (committed 5ee9253)
Goris auto-equips Bridgekeeper's Robes via 30-frame heartbeat using wield_obj_critter.

**Key findings from this session:**
- HOOK_INVENWIELD never fires for companion armor — "Use Best Armor" is the only
  equip mechanism for companions and it bypasses the hook entirely.
- "Use Best Armor" has an upstream engine check that silently skips Goris (vanilla
  behavior). The check is before inven_wield is called; exact condition unknown but
  is NOT body type (Goris is PROTO_CR_BODY_TYPE=0 / Biped in vanilla master.dat).
- wield_obj_critter bypasses the upstream block and works correctly.
- Heartbeat uses party_member_list(0) + inven_count/inven_ptr to find robes (PID 524).
- Verified: AC 28 → 48 (+20) on equip, matching Bridgekeeper's Robes AC bonus.

## Companion Implant System — COMPLETE (all three doctors)

### Doctors modified
- **Dr. Andrew (vcandy.ssl)** — Vault City — done in prior session
- **Doc Johnson (rcdrjohn.ssl)** — Redding — done this session
- **Dr. Fung (fcdrfung.ssl)** — San Francisco — done this session

### How it works
When the player selects "I want implants," the doctor asks who the implants are for. The player
can choose themselves or any companion currently in the party (listed by name via obj_name()).
`target_critter` is set accordingly; all perk checks and grants use that variable.
Combat armor and caps are always taken from dude_obj (unchanged).

### Files changed
- `data/scripts/rcdrjohn.ssl` + `rcdrjohn.int` — generated by `tools/gen_rcdrjohn_ssl.py`
- `data/scripts/fcdrfung.ssl` + `fcdrfung.int` — generated by `tools/gen_fcdrfung_ssl.py`
- `data/headers/rcdrjohn.h` — adapter; added SKILL_CONVERSANT (14), all MVAR/FANNIE defines, If_Party_Has_Injured
- `data/headers/fcdrfung.h` — adapter; added SF_ELRON_ENEMY (bit_19), PID_NAVCOM_PARTS (479), all Shi/spleen/Elron defines
- `install.py` — added rcdrjohn.int, fcdrfung.int to DAT_SCRIPTS; added rcdrjohn.msg (330-333), fcdrfung.msg (241-244) to DIALOG_MSG_PATCHES

### MSG IDs
- vcandy.msg: 360-363
- rcdrjohn.msg: 330-333 (original tops out at 328)
- fcdrfung.msg: 241-244 (original tops out at 240)

### Installer ran clean
f2mod.dat = 65,976 bytes, 15 files. All three MSG files patched.

## Companion Perk Stat Fix — COMPLETE (this session)

### Problem
`critter_add_trait(TRAIT_PERK)` on companions sets the perk flag but the engine's
perk-to-stat logic is player-only. Stat bonuses (FireDR, PlasmaDR, etc.) were never applied.

### Fix
After every `critter_add_trait` for a companion, manually apply `set_critter_extra_stat`.
After every `critter_rm_trait` (upgrade path removes tier-1 first), subtract tier-1 bonus.
Guard: `if (target_critter != dude_obj)` — player still gets bonuses from engine automatically.

### Exact perk stat bonuses (from fallout2-ce stat.cc, verified):
- PERK_dermal_armor_perk (74): +5 STAT_dmg_resist, +5 STAT_dmg_resist_explosion
- PERK_dermal_enhancement_perk (75): +10 STAT_dmg_resist, +10 STAT_dmg_resist_explosion (total; tier-1 removed first)
- PERK_phoenix_armor_perk (76): +5 STAT_dmg_resist_laser, +5 STAT_dmg_resist_fire, +5 STAT_dmg_resist_plasma
- PERK_phoenix_enhancement_perk (77): +10 each (total; tier-1 removed first)
- No AC bonus, no CH penalty — those are engine-only for player (NPC scripts don't apply them)
- Engine uses else-if: if tier-1 perk present, tier-2 bonus silently ignored — MUST remove tier-1 first

### Files updated this session
- `tools/gen_rcdrjohn_ssl.py` — added _add_stat dict + rm_trait reversal loop
- `tools/gen_fcdrfung_ssl.py` — same
- `data/scripts/vcandy.ssl` — direct edits at all 4 implant grant/upgrade points
- All three compiled and installed: f2mod.dat = 66,801 bytes, 15 files

## Next Step
Test in game: give Goris the Phoenix Armor Implants via Dr. Andrew (Vault City).
Expected debug output: FireDR goes from 60 → 65, PlasmaDR from 90 → 95 after grant.

## Open Questions / Decisions
None.

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
