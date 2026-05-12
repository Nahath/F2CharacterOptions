# Fallout 2 MAP File Format — Object & Inventory Items

Verified empirically from RPU kladwtwn.map.  All integers are **big-endian**.

---

## MAP file layout (high level)

```
[Header]         316 bytes for kladwtwn.map: 236 fixed + 20 global_vars * 4
[Tile data]      60,000 bytes  (3 elevations × 10,000 tiles × 2 bytes each)
[Scripts section] variable
[Objects section] variable — see below
```

The header contains no byte-offset fields pointing into later sections.
Everything is parsed sequentially.

**Header details (kladwtwn.map):**
- Offset 0x00: version = 20
- Offset 0x04: filename = "KLADWTWN.MAP" (16 bytes)
- Offset 0x14: default_player_pos (NOT num_local_vars — install.py reads this at 0x14 for the
  ObjID scan upper bound, which is a coincidental mis-use that still works)
- Offset 0x20: num_local_vars = 0 (map has no local vars at end of file)
- Offset 0x30: num_global_vars = 20
- Fixed header ends at 0xEC = 236; global_vars follow (20×4 = 80 bytes); total = 316
- Tile data: 316 → 60316 (60,000 bytes)

**Objects section:** Does NOT start at a predictable offset — the scripts section between
tile data and objects section is variable length and its end cannot be computed from the
header alone.  Do NOT scan for the (total, e0, e1, e2) header to locate objects.
Instead, scan directly for the proto_pid byte pattern at offset +44 from each candidate
object start, then validate the tile field — same approach as the Kisbox scan.

---

## Objects section layout

```
uint32   objects_total     ← sum of all three elevation counts (top-level only)
uint32   elev0_count
uint32   elev1_count
uint32   elev2_count
[elevation 0 top-level objects, parsed sequentially]
[elevation 1 top-level objects]
[elevation 2 top-level objects]
```

**Inventory items inside containers are NOT counted in any elevation count.**
They are nested inline after their parent object's header and are reached via
the parent's `inv_count` field.

---

## Object header (88 bytes, big-endian uint32 each)

| Offset | Field        | Notes |
|--------|-------------|-------|
| +0     | ObjID        | Unique per-map ID.  Non-zero. |
| +4     | tile         | Map tile index.  0xFFFFFFFF = in inventory. |
| +8     | x            | Pixel x offset within tile. |
| +12    | y            | Pixel y offset. |
| +16    | sx           | Sub-tile screen x. |
| +20    | sy           | Sub-tile screen y. |
| +24    | frame        | Current animation frame. |
| +28    | orientation  | Facing (0–5). |
| +32    | frm_pid      | Ground-art FID.  For items read from proto at offset 8. |
| +36    | flags        | 0x00000008 = in-inventory.  0xA0000008 = in-inventory + extra bits. |
| +40    | elevation    | 0, 1, or 2. |
| +44    | proto_pid    | Proto ID — **file number** (e.g. 14 → `00000014.pro`). NOT the internal PID from offset 0 of the .pro file. See proto-format.md. |
| +48    | critter_idx  | 0xFFFFFFFF for non-critters. |
| +52    | light_rad    | |
| +56    | light_int    | |
| +60    | outline      | |
| +64    | script_pid   | 0xFFFFFFFF = use proto's script. |
| +68    | script_id    | 0xFFFFFFFF = no running instance. |
| +72    | inv_count    | Number of items stored inside this object. |
| +76    | max_slots    | Container capacity (from proto or MAP). |
| +80    | unk10        | |
| +84    | unk11        | |

After the 88-byte header: **type-specific extra bytes** (determined by the
item's subtype from its proto):

| Item subtype | Extra bytes | Notes |
|---|---|---|
| 0 Armor     | 0  | |
| 1 Container | 0  | |
| 2 Drug      | 4  | |
| 3 Weapon    | 8  | ammo_type (4 bytes) + ammo_count (4 bytes). For no-ammo weapons: ammo_type=0, ammo_count=0xFFFFFFFF. For loaded ranged weapons: ammo proto PID + round count. ScriptID=-1 required in proto or black screen on load. |
| 4 Ammo      | 4  | |
| 5 Misc      | 4  | |
| 6 Key       | 4  | |

Critter objects have 40 extra bytes.

---

## Inventory item slot (qty prefix)

Items stored inside a container have a **4-byte quantity prefix** before the
88-byte header:

```
uint32   qty       ← stack count
[88-byte object header]
[type-specific extra bytes]
[nested inventory items if inv_count > 0]
```

Top-level map objects do NOT have a qty prefix.

---

## Sajag's barter inventory — Kisbox mechanism

**How it works** (confirmed from BGForge RPU source, kcsajag.ssl):

1. `klam_sajag_box_obj` is an exported variable in `kladwtwn.ssl`.
   The engine populates it from the MAP editor object linkage (MAP global-var
   table), not from any runtime SSL code.
2. At `talk_p_proc` start: `move_obj_inven_to_obj(klam_sajag_box_obj, self_obj)`
   moves ALL Kisbox items to Sajag for barter.
3. At `talk_p_proc` end: moves everything back to the Kisbox.

**Adding items to Sajag's barter inventory:**

- **Armor/non-weapon items:** Use BOTH a static MAP item (day-1 stock) AND a
  kisbox.int restock patch (restocks after being sold).
- **Weapon-type items:** Use ONLY a kisbox.int restock patch.  Adding weapons
  as static MAP items causes a black screen on fresh map load (engine requires
  specific ammo-state values in their 8 extra bytes; see debugging-facts.md).

**PID spaces differ between the two mechanisms:**
- MAP `proto_pid` → **file number** (e.g. `proto_pid=14` → `00000014.pro` = Power Armor)
- kisbox.int `check_restock_item(pid, ...)` → **internal PID** (offset-0 field of the .pro)

See proto-format.md §"Internal PID vs File Number".  Power Armor example:
MAP `proto_pid=14`, kisbox.int PID=3 (internal PID of `00000014.pro`).
Using file number 14 in kisbox.int creates Explosive Rocket (file 8 has internal PID=14).

---

## Kisbox object — verified values in RPU kladwtwn.map

| Field       | Value |
|-------------|-------|
| abs offset  | 158892 |
| tile        | 15121 |
| ObjID       | 318 |
| proto_pid   | 0x0000003F (proto 63, Container) |
| **elevation** | **0** (NOT elevation 1 — earlier doc was wrong) |
| inv_count   | 2  (Money + Booze in vanilla RPU) |
| inv_count field abs | 158964 |
| max_slots   | 10 |
| flags       | 0x20001000 |
| frm_pid     | 10 |
| Items start | 158980 |

## Golden Gecko bookcase — verified values in RPU kladwtwn.map

This is the bookcase closest to the Kisbox in the Golden Gecko bar, confirmed by
direct proto-scan.  Power Fist is inserted into this container.

| Field       | Value |
|-------------|-------|
| abs offset  | 156292 |
| tile        | 15069 |
| ObjID       | 1048 |
| proto_pid   | 70 (Container, bookcase) |
| elevation   | 0 |
| inv_count   | 1 (vanilla: one Misc item) |
| max_slots   | 10 |
| flags       | 0xa0009000 |
| script_pid  | 0xFFFFFFFF (no script) |

**Existing items** (both 96 bytes each: 4 qty + 88 header + 4 Misc/Drug extra):

| i | abs    | proto | subtype | qty | frm_pid | flags      | extra |
|---|--------|-------|---------|-----|---------|------------|-------|
| 0 | 158980 | 41    | Misc    | 56  | 0x03    | 0x00000008 | 0x00  |
| 1 | 159076 | 125   | Drug    | 1   | 0x74    | 0xA0000008 | 0xB8  |

Items end at abs 159172 (insert point for new items).

---

## kisbox.int — restock inventory

The Kisbox has its own script that calls `check_restock_item(pid, min, max, chance)`
on every map enter (subject to a 2-game-day timer) to maintain stock levels.
**This overrides static map data** — items bought by the player are restocked
by this script.

**To edit the restock list, see `inventory-editing.md`.**  The source is at
`data/scripts/kisbox.ssl`; compile it with the `compile_ssl` MCP tool.
Do not patch the compiled bytecode directly.

---

## MAP static inventory patching recipe

This is for adding day-1 items to the Kisbox MAP object (not for restock — use
`kisbox.ssl` for that).  See `kisbox-restock.md` for when to use each mechanism.

```python
# 1. Read kladwtwn.map from rpu.dat (or master.dat fallback)
# 2. Locate Kisbox: scan for PID bytes 0x0000003F at offset +44 of each object,
#    confirm tile==15121
# 3. Walk existing inv_count items to find insertion point (after last item)
# 4. Build item records:
#      rec = bytearray(96)
#      struct.pack_into(">I", rec,  0,      qty)              # qty
#      struct.pack_into(">I", rec,  4+0,    obj_id)           # unique ObjID
#      struct.pack_into(">I", rec,  4+4,    0xFFFFFFFF)       # tile = in-inventory
#      struct.pack_into(">I", rec,  4+32,   frm_pid)          # from proto at offset 8
#      struct.pack_into(">I", rec,  4+36,   0x00000008)       # flags
#      struct.pack_into(">I", rec,  4+44,   proto_pid)        # FILE NUMBER (not internal PID)
#      struct.pack_into(">I", rec,  4+48,   0xFFFFFFFF)       # critter_idx
#      struct.pack_into(">I", rec,  4+64,   0xFFFFFFFF)       # script_pid
#      struct.pack_into(">I", rec,  4+68,   0xFFFFFFFF)       # script_id
#      # bytes 4+80..4+87: unk10/unk11 stay 0
#      # bytes 4+88..95: extra bytes (4 for Misc), leave as 0
# 5. Splice records at insertion point
# 6. Update inv_count at kisbox_abs+72
# 7. Bundle patched map in f2mod.dat as maps\kladwtwn.map
```

---

## Known issue: black screen on fresh Klamath load

**Symptom:** After MAP patching, entering Klamath on a fresh game shows only
the player character and cursor on a black background.  Existing saves (where
the map was already cached from before the patch) load fine.

**Confirmed:** Disabling the MAP patch (not including kladwtwn.map in f2mod.dat)
restores normal rendering.

**Known causes:**

1. **ScriptID ≠ -1** — items whose proto has a non-(-1) ScriptID cause a black screen.
   Fix: only add items with ScriptID=-1 (confirmed working: Power Armor, file 14).

2. **Weapon-type items with wrong ammo state** — a Weapon item whose 8 extra bytes
   contain `ammo_count=0` will crash when the player opens the container.
   **Correct values:** `ammo_type=0x00000000, ammo_count=0xFFFFFFFF` for all no-ammo
   weapons (melee, thrown); for loaded ranged weapons use the ammo proto PID and round
   count.  Confirmed by scanning all weapon items in kladwtwn.map: throwing knives,
   knives, spears, and Power Fist all use `ammo_count=0xFFFFFFFF`.

**Safe item types for MAP patching (confirmed working):**
- Armor (0 extra bytes): ScriptID=-1 required (e.g. Power Armor in Kisbox)
- Misc, Drug: simple 4-byte extra (0 is valid); exist in vanilla Kisbox
- Weapon (no-ammo): 8 extra bytes; set ammo_type=0, ammo_count=0xFFFFFFFF; ScriptID=-1 required.
  Confirmed by vanilla kladwtwn.map (Blades building bookshelf stores throwing knives as
  container static inventory) and f2Mod Buckner House bookcase patch.
