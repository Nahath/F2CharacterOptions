# Fallout 2 Item Proto (.pro) File Format

Verified empirically against proto 51 (inactive dynamite) extracted from master.dat.
All integers are **big-endian**.

## Common item header (all item types)

All fields are 4 bytes (uint32/int32). The `PROTO_*` names are the `define_extra.h` constants
used with `set_proto_data` / `get_proto_data` — for these header fields, file byte offset =
in-memory offset. Item-type-specific fields (offset 36+) use **different** in-memory offsets
(e.g. `PROTO_IT_INV_FID = 124` in memory vs byte 52 in file).

| Offset | Size | Type    | Field           | define_extra.h constant | Notes |
|--------|------|---------|-----------------|------------------------|-------|
| 0      | 4    | uint32  | PID             |                        | **Internal PID** — NOT the same as the file number for many items (see section below). |
| 4      | 4    | uint32  | TextID          |                        | Line index into `pro_item.msg`. Convention: `internal_pid * 100`. |
| 8      | 4    | uint32  | FrmID           |                        | Frame set (graphic) ID. |
| 12     | 4    | uint32  | LightDistance   | `PROTO_LDIST`          | |
| 16     | 4    | uint32  | LightIntensity  | `PROTO_LINT`           | |
| 20     | 4    | uint32  | Flags           | `PROTO_FLAG`           | Object flag bits — see table below. Usually `0x0` for items. |
| 24     | 4    | uint32  | ExtendedFlags   | `PROTO_FLAG_EXT`, `PROTO_IT_FLAGS` | More object flag bits **and** item action flags — see table below. |
| 28     | 4    | int32   | **ScriptID**    | `PROTO_SCRIPTID`       | **0-based** line index into scripts.lst. -1 (0xFFFFFFFF) = no script. |
| 32     | 4    | uint32  | ItemType        | `PROTO_IT_TYPE`        | 0=Armor 1=Container 2=Drug 3=Weapon 4=Ammo 5=Misc 6=Key |

> **Previous error in this doc:** LightDistance and LightIntensity were incorrectly listed as
> uint16 (2 bytes) at offsets 12/14. They are uint32 (4 bytes) at offsets 12/16, confirmed by
> `PROTO_LDIST=12` and `PROTO_LINT=16` in define_extra.h and cross-checked against known
> ScriptID at offset 28.

---

## Flags and ExtendedFlags bit definitions

Both `Flags` (offset 20, `PROTO_FLAG`) and `ExtendedFlags` (offset 24, `PROTO_FLAG_EXT`) use
constants from `define_extra.h`. A given proto can have bits from either table in either field.

### Object flags (`FLAG_*` — typically in Flags or ExtendedFlags)

| Constant            | Value        | Meaning |
|---------------------|--------------|---------|
| `FLAG_MOUSE_3D`     | `0x00000001` | 3D mouse interaction |
| `FLAG_WALKTHRU`     | `0x00000004` | Critters can walk through |
| `FLAG_FLAT`         | `0x00000008` | Rendered flat on ground (not upright) |
| `FLAG_NOBLOCK`      | `0x00000010` | Does not block movement |
| `FLAG_LIGHTING`     | `0x00000020` | Emits light |
| `FLAG_TEMP`         | `0x00000400` | Temporary object |
| `FLAG_MULTIHEX`     | `0x00000800` | Occupies multiple hexes |
| `FLAG_NOHIGHLIGHT`  | `0x00001000` | Not highlighted on mouse-over |
| `FLAG_USED`         | `0x00002000` | Marked as used |
| `FLAG_TRANSRED`     | `0x00004000` | Red transparency |
| `FLAG_TRANSNONE`    | `0x00008000` | No transparency |
| `FLAG_TRANSWALL`    | `0x00010000` | Wall transparency |
| `FLAG_TRANSGLASS`   | `0x00020000` | Glass transparency |
| `FLAG_TRANSSTEAM`   | `0x00040000` | Steam transparency |
| `FLAG_TRANSENERGY`  | `0x00080000` | Energy transparency |
| `FLAG_LEFT_HAND`    | `0x01000000` | In left hand slot |
| `FLAG_RIGHT_HAND`   | `0x02000000` | In right hand slot |
| `FLAG_WORN`         | `0x04000000` | Equipped as armor |
| `FLAG_HIDDENITEM`   | `0x08000000` | Hidden from inventory display |
| `FLAG_WALLTRANSEND` | `0x10000000` | End of wall transparency |
| `FLAG_LIGHTTHRU`    | `0x20000000` | Light passes through |
| `FLAG_SEEN`         | `0x40000000` | Has been seen by player |
| `FLAG_SHOOTTHRU`    | `0x80000000` | Projectiles pass through |

### Item action flags (`ITEM_ACTION_*` — in ExtendedFlags)

These control which right-click actions appear for the item. Required by `item_make_explosive`.

| Constant              | Value        | Meaning |
|-----------------------|--------------|---------|
| `ITEM_ACTION_USE`     | `0x00000800` | Can be used from inventory (required by `item_make_explosive`) |
| `ITEM_ACTION_USEON`   | `0x00001000` | Can be used on a target |
| `ITEM_ACTION_PICKUP`  | `0x00008000` | Can be picked up |

### Verified values for key protos

| Proto                          | Flags (offset 20)    | ExtendedFlags (offset 24) | Decoded |
|--------------------------------|----------------------|---------------------------|---------|
| PID 51 — vanilla dynamite      | `0x00000000`         | `0xa0000008`              | ExtFlags: `FLAG_FLAT \| FLAG_LIGHTTHRU \| FLAG_SHOOTTHRU` |
| PID 534 — Super Dynamite inert | `0xa0000008`         | `0x0000a800`              | Flags: `FLAG_FLAT \| FLAG_LIGHTTHRU \| FLAG_SHOOTTHRU`; ExtFlags: `ITEM_ACTION_USE \| 0x2000 \| ITEM_ACTION_PICKUP` |

## Misc item additional fields (ItemType = 5)

File offsets only — in-memory offsets (`PROTO_IT_*`) differ significantly.

| File offset | In-memory offset (`set_proto_data`) | Size | Field    | Notes |
|-------------|-------------------------------------|------|----------|-------|
| 36          | —                                   | 4    | Material | |
| 40          | —                                   | 4    | Size     | |
| 44          | `PROTO_IT_WEIGHT = 116`             | 4    | Weight   | |
| 48          | `PROTO_IT_COST = 120`               | 4    | Cost     | Barter value in caps. |
| 52          | `PROTO_IT_INV_FID = 124`            | 4    | InvFID   | Inventory sprite. Encode as `(art_type << 24) \| index`. Type 7 = INVEN.LST. |

## Verified values for proto 51 (inactive dynamite)

```
PID            = 51
TextID         = 5100
ScriptID       = -1       (no script — vanilla dynamite has no item script)
ItemType       = 5        (Misc)
Cost           = 500
```

## Patching in Python (build_proto_600 pattern)

```python
OFFSET_PID       = 0
OFFSET_SCRIPT_ID = 28  # signed int
OFFSET_COST      = 48

data = bytearray(source_proto_bytes)
struct.pack_into(">I", data, OFFSET_PID,       new_pid)
struct.pack_into(">i", data, OFFSET_SCRIPT_ID, script_id)   # signed
struct.pack_into(">I", data, OFFSET_COST,      new_cost)
```

## Internal PID vs File Number — Critical Distinction

The `PID` field at offset 0 is the **internal PID**, which is NOT the same as the
proto file number for many items.  For some items they happen to match (e.g. Leather
Jacket: file 74, internal PID 74).  For others — particularly early armors and some
weapons — they differ significantly.

**Known items where file number ≠ internal PID (master.dat):**

| File # | Internal PID | TextID | Item          | Type   |
|--------|-------------|--------|---------------|--------|
| 3      | 1           | 100    | Leather Armor | Armor  |
| 8      | 14          | 1400   | Explosive Rocket | Ammo |
| 14     | 3           | 300    | Power Armor T-51b | Armor (FrmID=35, ScriptID=-1, Weight=85, Cost=12500) |

**Known items where file number = internal PID (safe, no confusion):**

| File # | TextID | Item          | Type   |
|--------|--------|---------------|--------|
| 41     | 4100   | Money (caps)  | Misc   |
| 63     | 6300   | Container     | Container |
| 74     | 7400   | Leather Jacket | Armor (FrmID=30, ScriptID=-1) |
| 125    | 12500  | Booze         | Drug   |
| 392    | 39200  | M72 Gauss Rifle | Weapon (FrmID=36, ScriptID=-1, Weight=9, Cost=8250) |

**Which PID to use, where:**

| Context                             | Uses         |
|-------------------------------------|--------------|
| `proto\items\XXXXXXXX.pro` filename | File number  |
| MAP object `proto_pid` field (+44)  | File number  |
| SSL `PID_X` constants               | Internal PID |
| `obj_pid(obj)` return value         | Internal PID |
| `check_restock_item(pid, ...)`      | Internal PID |
| `create_object_sid(pid, ...)`       | Internal PID |
| `pro_item.msg` entry (TextID)       | `internal_pid × 100` |

**Consequence of confusing them:** Using file number 14 in a script intending Power
Armor causes the engine to find the item whose internal PID is 14 — that is file 8,
an Explosive Rocket ammo.  Empirically confirmed: patching kisbox.int to restock PID
14 produced an Explosive Rocket in Sajag's barter inventory.

**How to identify an item's internal PID:** Use the `inspect_proto` MCP tool on the
file number.  The `PID` field in its output is the internal PID.

---

## ScriptID rules

- The value is the **0-based** line index in scripts.lst.
- Every line counts (blank lines, comment lines starting with `;`).
- To find the right index: count all lines before your appended entry.
- sfall's `DontDeleteProtos=0` (default) causes the engine to delete loose `.pro` files
  at startup unless they are read-only. Set `DontDeleteProtos=1` in ddraw.ini to protect
  writable loose protos, or package them inside a `.dat` archive.

### Critical: ScriptID and item use routing

The engine function `obj_use_radio` runs **before** `obj_use_explosive` in the item-use chain:

```
protinst_use_item → obj_use_radio → (sid != -1: execute script, return 0 → STOP)
                                  → (sid == -1: return -1 → CONTINUE)
                  → obj_use_explosive  ← sfall item_make_explosive hook lives here
```

`obj_use_radio` checks the **object's in-memory `sid` field**, not the proto. If `sid != -1`
it runs `use_p_proc` (even if the script is empty or has no such procedure) and returns 0,
preventing `obj_use_explosive` from ever being reached. This means **`item_make_explosive`
never fires for any object whose `sid != -1`**, regardless of proto flags or script content.

### ScriptID in proto vs. SID in map file

The proto's ScriptID field is the **default** for freshly created objects. For **map-placed
objects**, the SID is written into the map file at placement time (when the mapper calls
`obj_new_sid`, which reads the proto's ScriptID and saves the resulting script instance SID
into the map binary). At load time, `obj_read_obj` reads that saved SID directly from the
map file — the proto's ScriptID is **not re-consulted**.

**Consequence:** Patching a proto's ScriptID to -1 does NOT affect objects already placed on
maps. The map file still holds the old SID. To clear the SID for a map-placed object:

- **Re-place in the mapper** after patching the proto (new placement reads the updated proto).
- **At runtime** via global script: `set_object_data(obj, OBJ_DATA_SID, -1)` where
  `OBJ_DATA_SID = 0x78` (defined in define_extra.h).
