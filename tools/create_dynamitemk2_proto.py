"""
create_dynamitemk2_proto.py
───────────────────────────
Creates the Dynamite MKII item proto (600.pro) by copying the vanilla
inactive-dynamite proto (51.pro / 00000051.pro) and patching the relevant
fields.

Usage:
    python tools/create_dynamitemk2_proto.py <game_data_dir>

    <game_data_dir>  Path to your Fallout 2 "data" directory, e.g.:
                       C:/Games/Fallout2/data
                     The script reads  proto/items/00000051.pro  from there
                     and writes       proto/items/00000600.pro  next to it.

Proto field offsets (big-endian, from define_extra.h — authoritative):
    0x0000  (0) : uint32  Object type (high 16-bit word) + Proto ID (low 16-bit word)
    0x0008  (8) : uint32  FID  — frame/art reference (kept from source)
    0x0078 (120): uint32  Base cost in caps          (PROTO_IT_COST)
    0x0028  (40): uint32  Minimum damage             (PROTO_WP_DMG_MIN)
    0x002C  (44): uint32  Maximum damage             (PROTO_WP_DMG_MAX)

Vanilla inactive dynamite (proto 51) expected values (verify with a hex editor):
    cost      ≈ 150  →  Dynamite MKII cost = 300  (double)
    min_dmg   ≈  30  →  Dynamite MKII min  =  60  (double)
    max_dmg   ≈  60  →  Dynamite MKII max  = 120  (double)
"""

import struct
import sys
import os
import shutil

# ── Configuration ────────────────────────────────────────────────────────────

SRC_PROTO_ID  = 51     # Vanilla inactive dynamite
DST_PROTO_ID  = 600    # Dynamite MKII (new item)

# Object type for items in Fallout 2 (high word of the 4-byte PID field).
ITEM_OBJECT_TYPE = 0

# Values to write into the patched proto.
NEW_COST    = 300
NEW_MIN_DMG =  60
NEW_MAX_DMG = 120

# Byte offsets within the .pro file (big-endian uint32 unless noted).
OFFSET_PID      = 0x0000   # uint32: (object_type << 16) | proto_id
OFFSET_COST     = 120   # uint32: item value in caps      (PROTO_IT_COST)
OFFSET_MIN_DMG  =  40   # uint32: minimum weapon damage  (PROTO_WP_DMG_MIN)
OFFSET_MAX_DMG  =  44   # uint32: maximum weapon damage  (PROTO_WP_DMG_MAX)

# ── Helpers ──────────────────────────────────────────────────────────────────

def read_u32be(data: bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]

def write_u32be(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into(">I", data, offset, value)

def proto_filename(pid: int) -> str:
    return f"{pid:08d}.pro"

# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    game_data_dir = sys.argv[1]
    proto_dir = os.path.join(game_data_dir, "proto", "items")

    src_path = os.path.join(proto_dir, proto_filename(SRC_PROTO_ID))
    dst_path = os.path.join(proto_dir, proto_filename(DST_PROTO_ID))

    if not os.path.isfile(src_path):
        print(f"ERROR: Source proto not found: {src_path}")
        sys.exit(1)

    if os.path.exists(dst_path):
        print(f"WARNING: Destination already exists, overwriting: {dst_path}")

    with open(src_path, "rb") as f:
        data = bytearray(f.read())

    expected_min_size = OFFSET_COST + 4  # OFFSET_COST (120) is the highest offset
    if len(data) < expected_min_size:
        print(f"ERROR: Proto file is only {len(data)} bytes; "
              f"expected at least {expected_min_size}. "
              f"Wrong file or corrupt proto.")
        sys.exit(1)

    # ── Read current values (for verification / user info) ──
    old_pid     = read_u32be(data, OFFSET_PID)
    old_cost    = read_u32be(data, OFFSET_COST)
    old_min_dmg = read_u32be(data, OFFSET_MIN_DMG)
    old_max_dmg = read_u32be(data, OFFSET_MAX_DMG)

    print(f"Source proto  : {src_path}")
    print(f"  PID field   : 0x{old_pid:08X}  (object_type={old_pid >> 16}, id={old_pid & 0xFFFF})")
    print(f"  Cost        : {old_cost} caps")
    print(f"  Damage      : {old_min_dmg}–{old_max_dmg}")
    print()

    # ── Sanity check: source should be an item proto ──
    src_obj_type = old_pid >> 16
    src_proto_id = old_pid & 0xFFFF
    if src_obj_type != ITEM_OBJECT_TYPE:
        print(f"WARNING: Source object type is {src_obj_type}, expected {ITEM_OBJECT_TYPE} (item). "
              f"Continuing anyway.")
    if src_proto_id != SRC_PROTO_ID:
        print(f"WARNING: Source PID field says {src_proto_id}, expected {SRC_PROTO_ID}. "
              f"You may have the wrong file.")

    # ── Patch ──
    new_pid_field = (ITEM_OBJECT_TYPE << 16) | DST_PROTO_ID
    write_u32be(data, OFFSET_PID,     new_pid_field)
    write_u32be(data, OFFSET_COST,    NEW_COST)
    write_u32be(data, OFFSET_MIN_DMG, NEW_MIN_DMG)
    write_u32be(data, OFFSET_MAX_DMG, NEW_MAX_DMG)

    with open(dst_path, "wb") as f:
        f.write(data)

    print(f"Destination   : {dst_path}")
    print(f"  PID field   : 0x{new_pid_field:08X}  (object_type={ITEM_OBJECT_TYPE}, id={DST_PROTO_ID})")
    print(f"  Cost        : {NEW_COST} caps")
    print(f"  Damage      : {NEW_MIN_DMG}–{NEW_MAX_DMG}")
    print()
    print("Done.  Next step: run tools/darken_frm.py to create the darker inventory icon.")


if __name__ == "__main__":
    main()
