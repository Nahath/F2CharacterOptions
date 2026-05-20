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

## CSV Extraction — COMPLETE

- `tools/extract_data.py` — standalone script, imports read_file_from_dat from install.py
- `tools/items.csv` — 531 items: file_num, internal_pid, name, type
- `tools/npcs.csv` — 857 placements: file_num, internal_pid, name, map (one row per proto per map)
- Scan approach: search every 4-byte aligned offset for a valid critter file_num; validate tile<40000, elevation in {0,1,2}, critter_idx != 0xFFFFFFFF, ObjID non-zero
- Critter internal PIDs are 0x01000000 | file_num (e.g. file_num 15 → internal_pid 16777231)
- Confirmed correct: Power Armor file_num=14/internal_pid=3, Goris/Myron/Sulik on expected maps

## Steal-Only Item System — COMPLETE (first NPC: Doc Andrew)

### Implementation
- `data/scripts/hs_useskill.ssl` — HOOK_USESKILL hook; fires before steal window opens.
  Checks: user==dude_obj, skill==SKILL_STEAL, target PID==16777684 (Doc Andrew, file_num 468),
  player has PERK_thief_perk (105). If all true and fewer than 2 Super Stimpaks (PID 144) in
  Andrew's inventory, injects them via create_object + add_obj_to_inven. Always set_sfall_return(-1).
- `data/scripts/vcandy.ssl` destroy_p_proc — cleanup loop: iterates Andrew's inventory,
  rm_obj_from_inven + destroy_object for any PID 144 items on Andrew's death.
- `install.py` DAT_SCRIPTS — added `scripts\hs_useskill.int`.
- f2mod.dat now 16 files, 66,653 bytes.

### Key facts
- `add_obj_to_inven(critter, item)` is the correct opcode (not move_to_obj_inven).
- `create_object(PID, 0, 0)` creates off-map item; use with add_obj_to_inven (not create_object_sid).
- hs_*.int files are auto-discovered by sfall from DAT archives; no GlobalScriptPaths entry needed.
- GlobalScriptPaths in ddraw.ini only covers gl*.int pattern.
- `PID_SUPER_STIMPAK` is in data/headers/itempid.h but NOT in data/scripts/DEFINE.H;
  must define locally in hook scripts that use data/scripts/DEFINE.H.

### Known gap
Item remains in Andrew's inventory if player opens steal window but doesn't take it.
This is accepted behavior.

## NPC Identification — Stark and Ascorti

### Sgt. Stark (Vault City, NOT Navarro)
- Script: VCStark.int = scripts.lst index **122**
- file_num and internal_pid: not yet confirmed

### Sgt. Dornan (Navarro drill sergeant)
- Script: Ccdrill.int = scripts.lst index **717**
- Comment in scripts.lst: "Drill Seargant in Colusa/Nevarro"
- file_num and internal_pid: not yet confirmed

### Ascorti (Redding Downtown)
- Proto: file_num **456** ("Bureaucrat 2"), internal_pid **16777672** (= 0x010001C8)
- Map: REDDOWN.MAP — 4 instances of Bureaucrat 2, all script-held (tile=0xFFFFFFFF)
- Script: RCAscort.int = scripts.lst index **809**
- To identify Ascorti specifically (vs other Bureaucrat 2 guards): `get_script(target) == 809`
- sfall `get_script(obj)` returns the 0-based scripts.lst line number for the script attached to an object
- The other Bureaucrat 2 instances in REDDOWN use RCAscGrd.int (index 1113)

### Key finding: get_script()
`get_script(obj)` is the clean way to identify named NPCs when multiple critters share the same proto.
Use: `obj_pid(target) == 16777672 and get_script(target) == 809` to gate on Ascorti specifically.

## Steal System Expansion — COMPLETE (pending test)

hs_useskill.ssl extended to 24 NPCs (23 inject-on-steal + President's key copy).
Compiled clean (3,538 bytes). Installed: f2mod.dat = 17 files, 73,613 bytes.

Key implementation notes:
- Helper procedures count_pid(target, pid) and inject(target, pid, want) handle top-up logic
- inject_weapon(target, pid): creates one weapon, reads ammo PID + mag size from proto via
  get_proto_data(pid, PROTO_WP_AMMO_PID) and get_proto_data(pid, PROTO_WP_MAG_SIZE), then
  sets OBJ_DATA_CUR_CHARGES (0x3C) and OBJ_DATA_WEAPON_AMMO_PID (0x40) on the created object
  before adding to inventory. No-op if target already has 1. Used for all ranged weapons.
- Weapons loaded: Alien Blaster, 10mm SMG, Sniper Rifle, Plasma Pistol Ext, Bozar, HK P90c,
  Vindicator, H&K G11E, Pancor Jackhammer, Red Ryder LE BB Gun
- Parametrized user-defined proc calls must use assignment context: r := inject(...) — bare calls cause compile error
- Ascorti uses item_caps_adjust(target, 1500 - item_caps_total(target)) to top up to 1500 caps
- Doc Jubilee painting uses create_object_sid(78, 0, 0, 953) so SIpaint.int is attached — Vault 13 map revealed when player examines stolen painting
- President's key: inject up to 2 total (original stays for looting, copy is stealable)
- All NPCs identified by get_script(target) == SID_xxx; full table in ExtraStealCases.md and debugging-facts.md

## Custom Steal System — COMPLETE (pending test)

Replaced vanilla two-roll steal system with new single-roll formula via HOOK_STEAL (hs_steal.ssl).

### Formula
```
chance = clamp(your_steal - their_steal - (4 × item_size) - session_count, 0, 95)
```
- `your_steal` / `their_steal`: has_skill(critter, SKILL_STEAL). Non-critter targets (containers) use 0.
- `item_size`: get_proto_data(obj_pid(item), PROTO_IT_SIZE) — PROTO_IT_SIZE=112, a separate proto
  field from weight (PROTO_IT_WEIGHT=116). Vanilla coefficient is -4% per size unit (confirmed from
  fallout2-ce skill.cc: `stealModifier -= 4 * itemGetSize(item)`).
- `session_count`: 0 for first item stolen from current target, +1 each subsequent attempt.
  Resets when target changes. Applied before cap so excess skill burns it off first.
- Cap is 95% (hard max).

### Key facts
- Planting is passed through to engine handler (set_sfall_return(-1)).
- Script-level variables persist between hook invocations in sfall (same as global scripts).
- `has_skill(critter, SKILL_STEAL)` is the correct opcode (DEFINE.H: `CRITTER_SKILL_LEVEL = has_skill`).
- `sprintf` in this sfall version only accepts one format argument — use string concatenation for debug.
- Hook return values: 2=success (item transferred), 0=fail, -1=use engine handler.
- Debug lines print: your_skill, their_skill, size_pen, session_pen, final chance%.
- f2mod.dat = 18 files, 74,103 bytes.

## NPC Steal Skill Table + Plastic Explosives — COMPLETE

### hs_useskill.ssl
- Added `#define PID_PLASTIC_EXPLOSIVES (85)`
- Westin and Raul cases expanded to begin/end blocks: inject Bozar/HK P90c (weapon) + 2 plastic explosives each
- Compiled clean: 3,638 bytes

### hs_steal.ssl
- Added `npc_steal_skill(sid)` procedure: 49-entry if-else chain returning user-specified steal skill
- `their_skill` now uses: lookup first, falls back to `has_skill` if not in table
- Compiled clean: 3,728 bytes
- f2mod.dat = 18 files, 74,556 bytes

### Script indices found (all via read_scripts_lst):
| SID | Script | NPC | Steal skill |
|-----|--------|-----|------------|
| 79  | KCMaida.int | Maida Buckner | 15 |
| 41  | DCFlick.int | Flick | 25 |
| 47  | DCTubby.int | Tubby | 25 |
| 51  | dcRebecc.int | Becky | 25 |
| 44  | DCSmitty.int | Smitty | 35 |
| 110 | VCHarry.int | Happy Harry | 50 |
| 118 | VCRandal.int | Randal | 55 |
| 94  | VCDrTroy.int | Dr. Troy | 45 |
| 607 | hcJacob.int | Jacob | 45 |
| 425 | ncEldrid.int | Eldridge | 75 |
| 440 | ncRenesc.int | Renesco | 70 |
| 346 | ncSalMen.int | Salvatore Guards | 60 |
| 807 | RCDrJohn.int | Doc Johnson | 55 |
| 937 | RCCshTnd.int | Cash Tender | 100 |
| 251 | SCBuster.int | Buster | 90 |
| 406 | SCDuppo.int | Duppo | 75 |
| 1182 | SCBGrd.int | NCR Guards (outside Buster's) | 80 |
| 1062 | CcGrdca.int | Navarro Guard (combat armor) | 80 |
| 1063 | CcGrdpa.int | Navarro Guard (power armor) | 80 |
| 824 | FCGunMer.int | Mai Da Chiang | 110 |
| 924 | FCLaoCho.int | Lao Chou | 110 |
| 1103 | FCTnkMer.int | Jenna | 80 |
| 1101 | FCTnkGmr.int | Cal | 80 |
| 747 | FCShiGrd.int | Shi Guards (covers Chinatown + Palace) | 100 |
| 976 | FCMarc.int | Marc | 60 |
| 989 | FCFemPnk.int | Female Tanker Vagrant | 60 |

### Uncertain mappings (noted for testing)
- FCGunMer (824) assumed to be Mai Da Chiang — only SF gun merchant script found
- FCFemPnk (989) assumed to be Female Tanker Vagrant — only SF female punk script
- Chinatown Guards and Shi Palace Guards both mapped to FCShiGrd (747) — no separate Chinatown guard script found

## Next Step
User to test in-game:
1. Steal system: verify debug numbers make sense for various NPCs (especially ones with high override skills like Dornan=110, Cash Tender=100).
2. Verify plastic explosives appear in Westin and Raul inventories when opening steal window.
3. Confirm uncertain mappings: Mai Da Chiang = gun merchant, Female Tanker Vagrant = female punk.

## Open Questions / Decisions
- hcScorp.int (index 1172) is the only Broken Hills scorpion script — assumed correct, user will confirm via testing.
- No separate Chinatown guard script found — FCShiGrd covers both types (both set to 100 steal skill anyway).

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
