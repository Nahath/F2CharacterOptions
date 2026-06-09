# Current Session

## Task
Key card door system — Sargeant NPC carries a key card; a custom door can only be opened with it.

## Progress
- Created `data/scripts/scenDoor.ssl` — door script with `map_enter_p_proc` (lock on enter),
  `use_p_proc` (show "locked" message), `use_obj_on_p_proc` (unlock if PID 601 key card used).
- Updated `data/scripts/npcSargt.ssl` — gives key card (PID 601) on first map enter via
  `create_object_sid` + `add_mult_objs_to_inven`, guarded by `LVAR_gave_keycard`.
- Created custom item proto 601 in install.py (`build_proto_601`) based on Access Card (proto 140).
  PID patched to 601, TextID to 60100 ("Sargeant's Key Card" / "A security key card.").
- Added pro_item.msg entries 60100/60101 to DIALOG_MSG_PATCHES.
- Added scenDoor.int to DAT_SCRIPTS; appended `scenDoor` to scripts.lst at index 1306.
- Copied scenDoor.int and npcSargt.int to loose game scripts folder (for mapper).
- Appended `scenDoor.int` to loose scripts.lst (index 1306, no trailing newline).
- Rebuilt f2mod.dat — 26 files, scenDoor at index 1306 confirmed by verify_f2mod.

## Next Step
**Assign the door script in BIS mapper:**
1. Open the map containing the door in BIS mapper.
2. Select the door object (right-click → Properties or use the object picker).
3. In the Script field, pick `scenDoor` (index 1306).
4. Save the map.
5. Run install.py to rebuild f2mod.dat with the updated map.

## Open Questions / Decisions
- The door currently uses the stock "door is locked" text. If you want a custom message
  (e.g. "Security access required"), edit the `display_msg` string in scenDoor.ssl and recompile.
- The key card stays in the player's inventory after use (not consumed). Let me know if it
  should be removed on first use.

## Context
Key card PID: 601
Door script index: 1306
Sargeant script index: 1305

Proto 601 based on Access Card (140):
- Same inventory art (card graphic, FrmID 41)
- Same misc item type, weight 1, size 1

`create_object` (vanilla) = not a built-in in sfall compiler 4.4.10 — must use
`create_object_sid(pid, 0, 0, -1)` instead (from define.h: `create_object(X,Y,Z) = create_object_sid(X,Y,Z,-1)`).
