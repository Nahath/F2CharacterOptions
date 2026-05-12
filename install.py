"""
install.py — f2Mod installer
────────────────────────────
Packages all mod content into a single f2mod.dat archive, installs it into
the game's mods folder, and registers it in mods_order.txt.

Most files are bundled inside f2mod.dat.  A small number of scripts that the
engine loads via direct file I/O (bypassing DAT lookup) are also written as
loose files to <game>/data/scripts/.

Usage:
    python install.py [path_to_fallout2_directory]
"""

import io
import os
import re
import struct
import sys
import zlib

# ── Inventory art constants ───────────────────────────────────────────────────

DARKEN_FACTOR    = 0.70     # darken 30 % relative to vanilla
OFFSET_INVEN_FID = 52       # uint32 BE in MISC proto: 0x07000000 | inven.lst index

SRC_INVEN_FRM = r"art\inven\DYNAMIT.FRM"   # vanilla inactive dynamite inven sprite
DST_INVEN_FRM = r"art\inven\DYNMK2.FRM"   # Dynamite MKII inven sprite
PAL_INTERNAL  = r"color.pal"               # Fallout 2 768-byte palette
INVEN_LST     = r"art\inven\inven.lst"     # inven art index file

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Script files to include in f2mod.dat.
# internal DAT path -> source path relative to SCRIPT_DIR
DAT_SCRIPTS = {
    r"scripts\gl_powerarmor.int":        r"data\scripts\gl_powerarmor.int",
    r"scripts\gl_goris_armor.int":       r"data\scripts\gl_goris_armor.int",
    r"scripts\hs_inventorymove.int":     r"data\scripts\hs_inventorymove.int",
    r"scripts\hs_steal.int":             r"data\scripts\hs_steal.int",
    r"scripts\dynamitemk2.int":          r"data\scripts\dynamitemk2.int",
    # Stub for a spatial script that the Arroyo map references by name but
    # whose .int is absent from master.dat and all mod archives.  Without it
    # the engine crashes on "Couldn't open … for read" immediately after the
    # Temple-of-Trials cinematic.
    r"scripts\a swarm of mantis infesting some spore plants.int":
        r"data\scripts\a swarm of mantis infesting some spore plants.int",
    # Modified Sajag script: adds APA to personal inventory (stealable, not
    # barterable) and hides personal items from the barter screen.
    r"scripts\kcsajag.int":             r"data\scripts\kcsajag.int",
    # Global script: seeds throwing knife into Buckner House bookcase at runtime.
}

# Proto constants (proto 600 is based on proto 51, inactive dynamite)
SRC_PROTO_ID = 51
DST_PROTO_ID = 600
NEW_COST     = 1000   # barter value in caps
OFFSET_PID       = 0   # uint32 BE
OFFSET_TEXT_ID   = 4   # uint32 BE
OFFSET_SCRIPT_ID = 28  # int32  BE  (-1 = no script)
OFFSET_COST      = 48  # uint32 BE

# pro_item.msg message IDs for proto 600 (convention: proto_id * 100)
MSG_ID_NAME = DST_PROTO_ID * 100      # 60000
MSG_ID_DESC = DST_PROTO_ID * 100 + 1  # 60001

# Scripts that must be loose files because the engine loads them via direct
# file I/O, bypassing DAT archive lookup.
# internal game path (relative to game_root) -> source path relative to SCRIPT_DIR
LOOSE_SCRIPTS = {
    # Spatial script absent from master.dat/rpu.dat; engine loads it by name
    # (not via scripts.lst index) so the DAT copy is not found.
    os.path.join("data", "scripts", "a swarm of mantis infesting some spore plants.int"):
        os.path.join("data", "scripts", "a swarm of mantis infesting some spore plants.int"),
}

# Loose files written by older versions of this installer — remove on install.
LEGACY_FILES = [
    os.path.join("data", "scripts", "gl_powerarmor.int"),
    os.path.join("data", "scripts", "gl_klamath.int"),
    os.path.join("data", "scripts", "gl_goris_armor.int"),
    os.path.join("data", "scripts", "hs_inventorymove.int"),
    os.path.join("data", "scripts", "hs_steal.int"),
    os.path.join("data", "scripts", "dynamitemk2.int"),
    os.path.join("data", "proto", "items", "00000600.pro"),
]

# ── Kisbox map patch constants ────────────────────────────────────────────────

KISBOX_MAP_PATH    = r"maps\kladwtwn.map"
PID_KISBOX         = 0x0000003F  # Container proto 63
KISBOX_TILE        = 15121       # tile number of Sajag's barter Kisbox (Downtown)
PID_DYNMK2         = 0x00000258  # proto 600 (Dynamite MKII)
DYNMK2_QTY         = 3           # number of Dynamite MKII to add
PID_POWER_ARMOR    = 0x0000000E  # Power Armor (T-51b); engine loads 00000014.pro by filename
POWER_ARMOR_FRM_PID = 35         # FrmID from 00000014.pro
PID_GAUSS_RIFLE     = 392        # M72 Gauss Rifle; file 00000392.pro (internal PID=392)
GAUSS_RIFLE_FRM_PID = 36         # FrmID from 00000392.pro

# Golden Gecko bookcase patch constants
PID_POWER_FIST      = 235        # Power Fist; file 00000235.pro (internal PID=235, matches file)
POWER_FIST_FRM_PID  = 47         # FrmID from 00000235.pro
BOOKCASE_PROTO_RANGE = range(60, 71)
GG_TILE_MIN  = 13000
GG_TILE_MAX  = 17000

# Buckner bookcase (Guns&Bullets + Nuka Cola container) patch constants
BUCKNER_BOOK_CONTAINER_TILE = 27299   # tile of the container holding G&B + Nuka Cola
PID_NUKA_COLA               = 106     # Drug, FrmID=116
NUKA_COLA_FRM_PID           = 116
PID_STIMPAK                 = 40      # Drug, FrmID=15
STIMPAK_FRM_PID             = 15
PID_THROWING_KNIFE          = 45      # Weapon, no-ammo, FrmID=28
THROWING_KNIFE_FRM_PID      = 28

# Item subtype → extra bytes in the MAP object record (after the 88-byte header)
_ITEM_SUBTYPE_EXTRA = {0: 0, 1: 0, 2: 4, 3: 8, 4: 4, 5: 4, 6: 4}

# ── Helpers ──────────────────────────────────────────────────────────────────

def abort(msg):
    print(f"\nERROR: {msg}")
    sys.exit(1)


def read_file_from_dat(dat_path, internal_path):
    """Extract a file from a Fallout 2 DAT2 archive.

    DAT2 layout (little-endian integers unless noted):
      [file data]
      [directory tree:
          uint32  file_count
          per file: uint32 name_len, char[] name, uint8 compression,
                    uint32 uncompressed_size, uint32 packed_size, uint32 offset]
      uint32  tree_size
      uint32  dat_size
    compression: 0 = stored, 1 = zlib deflate
    """
    target = internal_path.replace("/", "\\").lower()
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
        pos = 4  # skip file_count
        while pos < len(tree):
            name_len = struct.unpack_from("<I", tree, pos)[0]; pos += 4
            name = tree[pos:pos + name_len].decode("latin-1").lower(); pos += name_len
            compression = tree[pos]; pos += 1
            uncompressed_size, packed_size, offset = struct.unpack_from("<III", tree, pos); pos += 12
            if name == target:
                fh.seek(offset)
                raw = fh.read(packed_size)
                return zlib.decompress(raw) if compression else raw
    return None


def load_palette(pal_bytes):
    """Parse a 768-byte Fallout 2 color.pal into a list of 256 (r,g,b) tuples (0-255)."""
    pal = []
    for i in range(256):
        pal.append((pal_bytes[i*3] * 4, pal_bytes[i*3+1] * 4, pal_bytes[i*3+2] * 4))
    return pal


def nearest_pal_idx(pal, r, g, b):
    best, dist = 0, float("inf")
    for idx, (pr, pg, pb) in enumerate(pal):
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if d < dist:
            dist, best = d, idx
            if d == 0:
                break
    return best


def build_remap_table(pal, factor):
    """256-byte lookup: old_index → darkened_index.  Index 0 (transparent) unchanged."""
    remap = bytearray(256)
    for i in range(1, 256):
        r, g, b = pal[i]
        remap[i] = nearest_pal_idx(pal, int(r * factor), int(g * factor), int(b * factor))
    return bytes(remap)


def darken_frm_inven(frm_bytes, remap):
    """
    Return a darkened copy of a single-direction inven FRM.
    Only the pixel data is remapped; the 62-byte FRM header and per-frame
    record headers (width/height/pixel_count/offsets) are left intact.
    """
    FRM_HEADER  = 62
    FRAME_HDR   = 12   # 2+2+4+2+2 bytes: width, height, pixel_count, x_off, y_off
    data        = bytearray(frm_bytes)
    frames_per_dir = struct.unpack_from(">H", data, 8)[0]
    pos = FRM_HEADER
    for _ in range(frames_per_dir):
        pixel_count = struct.unpack_from(">I", data, pos + 4)[0]
        pix_start   = pos + FRAME_HDR
        for i in range(pix_start, pix_start + pixel_count):
            data[i] = remap[data[i]]
        pos = pix_start + pixel_count
    return bytes(data)


def build_inven_art(game_root):
    """
    Darken DYNAMIT.FRM from master.dat and extend inven.lst with the new entry.
    Returns (frm_bytes, extended_inven_lst_bytes, dynmk2_index).
    """
    master_dat = os.path.join(game_root, "master.dat")

    pal_raw = read_file_from_dat(master_dat, PAL_INTERNAL)
    if pal_raw is None:
        abort("color.pal not found in master.dat.")
    pal = load_palette(pal_raw)
    remap = build_remap_table(pal, DARKEN_FACTOR)

    src_frm = read_file_from_dat(master_dat, SRC_INVEN_FRM)
    if src_frm is None:
        abort(f"{SRC_INVEN_FRM!r} not found in master.dat.")
    dst_frm = darken_frm_inven(src_frm, remap)

    # Try rpu.dat first for inven.lst, then master.dat.
    inven_lst = None
    rpu_dat = os.path.join(game_root, "mods", "rpu.dat")
    if os.path.isfile(rpu_dat):
        inven_lst = read_file_from_dat(rpu_dat, INVEN_LST)
    if inven_lst is None:
        inven_lst = read_file_from_dat(master_dat, INVEN_LST)
    if inven_lst is None:
        abort("inven.lst not found in rpu.dat or master.dat.")

    lines = inven_lst.replace(b"\r\n", b"\n").split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    dynmk2_index = len(lines)

    if not inven_lst.endswith((b"\n", b"\r\n")):
        inven_lst += b"\n"
    inven_lst += b"DYNMK2.FRM\n"

    return dst_frm, inven_lst, dynmk2_index


def build_dat2(file_map):
    """Build a Fallout 2 DAT2 archive.

    file_map: dict of {internal_path (backslash-separated): bytes}
    Returns: bytes of the complete .dat file.
    """
    entries = sorted(file_map.items())
    data_buf = io.BytesIO()
    meta = []

    for path, content in entries:
        offset = data_buf.tell()
        compressed = zlib.compress(content, 6)
        if len(compressed) < len(content):
            data_buf.write(compressed)
            meta.append((path, 1, len(content), len(compressed), offset))
        else:
            data_buf.write(content)
            meta.append((path, 0, len(content), len(content), offset))

    tree_buf = io.BytesIO()
    tree_buf.write(struct.pack("<I", len(meta)))
    for path, compression, uncompressed, packed, offset in meta:
        name = path.encode("latin-1")
        tree_buf.write(struct.pack("<I", len(name)))
        tree_buf.write(name)
        tree_buf.write(struct.pack("<B", compression))
        tree_buf.write(struct.pack("<III", uncompressed, packed, offset))

    data_bytes = data_buf.getvalue()
    tree_bytes = tree_buf.getvalue()
    tree_size  = len(tree_bytes)
    dat_size   = len(data_bytes) + tree_size + 8
    return data_bytes + tree_bytes + struct.pack("<II", tree_size, dat_size)


def _kisbox_item_extra(dat_path, pid):
    """Return extra bytes for a MAP object record with the given PID."""
    type_byte = (pid >> 24) & 0xFF
    proto_id  = pid & 0xFFFFFF
    if type_byte == 0x01:
        return 40
    if type_byte == 0x00:
        data = read_file_from_dat(dat_path, f"proto\\items\\{proto_id:08d}.pro")
        if data and len(data) >= 36:
            subtype = struct.unpack_from(">I", data, 32)[0]
            return _ITEM_SUBTYPE_EXTRA.get(subtype, 4)
        return 4
    return 0


def _kisbox_parse_item(data, pos, master_dat):
    """Return total bytes consumed by one item slot (qty + object record).
    Handles nested inventories recursively."""
    start = pos
    pos  += 4  # skip qty
    pid   = struct.unpack_from(">I", data, pos + 44)[0]
    inv_c = struct.unpack_from(">I", data, pos + 72)[0]
    if inv_c > 500:
        inv_c = 0
    extra = _kisbox_item_extra(master_dat, pid)
    pos  += 88 + extra
    for _ in range(inv_c):
        pos += _kisbox_parse_item(data, pos, master_dat)
    return pos - start


def _patch_golden_gecko_bookcase_from_bytes(map_bytes, game_root):
    """Replace the Club in the Golden Gecko bookcase with a Power Fist.

    RPU placed a Club (proto 5, no-ammo weapon: ammo_type=0, ammo_count=0xFFFFFFFF)
    in this scenery container.  That sentinel ammo state crashes the engine when the
    player directly opens the container.  We replace it in-place with a Power Fist
    (proto 235, ammo_type=25 SEC caliber, ammo_count=38), which has valid loaded-weapon
    ammo values that the engine handles correctly.  Both items are Weapon subtype with
    8 extra bytes, so the replacement is the same size and no byte insertion is needed.
    """
    master_dat = os.path.join(game_root, "master.dat")
    data = bytearray(map_bytes)

    bookcase_candidates = []
    seen_abs = set()
    for proto_id in range(60, 71):
        needle = struct.pack(">I", proto_id)
        search_pos = 0
        while True:
            idx = data.find(needle, search_pos)
            if idx < 0:
                break
            obj = idx - 44
            if obj >= 0 and obj + 88 <= len(data) and obj not in seen_abs:
                tile = struct.unpack_from(">I", data, obj + 4)[0]
                if GG_TILE_MIN <= tile <= GG_TILE_MAX:
                    if not (proto_id == 63 and tile == KISBOX_TILE):
                        seen_abs.add(obj)
                        bookcase_candidates.append((obj, proto_id, tile))
            search_pos = idx + 1

    if not bookcase_candidates:
        abort(f"No bookcase container (proto 60-70) found in kladwtwn.map "
              f"tile range {GG_TILE_MIN}-{GG_TILE_MAX}.")

    bookcase_candidates.sort(key=lambda x: abs(x[2] - KISBOX_TILE))
    bookcase_abs, bookcase_proto, bookcase_tile = bookcase_candidates[0]

    if len(bookcase_candidates) > 1:
        others = [(t, p) for _, p, t in bookcase_candidates[1:]]
        print(f"  Multiple bookcase candidates found; others: {others}")

    inv_count = struct.unpack_from(">I", data, bookcase_abs + 72)[0]
    if inv_count == 0:
        abort(f"Bookcase (proto {bookcase_proto}, tile {bookcase_tile}) has no items to replace.")

    # The first item slot starts immediately after the 88-byte bookcase header.
    # Confirm it is the Club (proto 5) we expect to replace.
    slot_abs = bookcase_abs + 88
    first_proto = struct.unpack_from(">I", data, slot_abs + 4 + 44)[0]
    if first_proto != 5:
        abort(f"Bookcase first item is proto {first_proto}, expected 5 (Club). "
              f"Map may have changed; review _patch_golden_gecko_bookcase_from_bytes.")

    # Raise bookcase max_slots from 10 to 100.  Power Fist uses ammo (ammo_count=38);
    # the engine appears to validate ammo_count <= max_slots when opening a container,
    # crashing if ammo_count (38) exceeds max_slots (10).  Same fix as the Kisbox
    # (needed max_slots >= Power Armor Size=15).
    struct.pack_into(">I", data, bookcase_abs + 76, 100)

    # Clear flag bit 0x8000 from the bookcase container's MAP flags.
    # The bookcase has flags=0xa0009000, while other working weapon-containing
    # containers in kladwtwn.map have flags without 0x8000 (e.g. 0xa0001000).
    # This bit is unique to the bookcase among containers that hold weapon items.
    old_flags = struct.unpack_from(">I", data, bookcase_abs + 36)[0]
    struct.pack_into(">I", data, bookcase_abs + 36, old_flags & ~0x8000)

    # Replace in-place: overwrite only the fields that differ between Club and Power Fist.
    # The slot structure (qty=1, tile=0xFFFFFFFF, flags=0x8, etc.) is preserved unchanged.
    # Club and Power Fist are both Weapon subtype (8 extra bytes), so total size is identical.
    struct.pack_into(">I", data, slot_abs + 4 + 32, POWER_FIST_FRM_PID)  # frm_pid
    struct.pack_into(">I", data, slot_abs + 4 + 44, PID_POWER_FIST)       # proto_pid
    struct.pack_into(">I", data, slot_abs + 4 + 88, 0x00000019)            # ammo_type=25 (SEC caliber)
    struct.pack_into(">I", data, slot_abs + 4 + 92, 0xFFFFFFFF)            # ammo_count=0xFFFFFFFF (unloaded sentinel)

    print(f"  Patched kladwtwn.map: replaced Club with Power Fist in bookcase "
          f"(proto {bookcase_proto}, tile {bookcase_tile}) at slot abs={slot_abs}, "
          f"flags 0x{old_flags:08X}->0x{old_flags & ~0x8000:08X}, max_slots 10->100")
    return bytes(data)


def _patch_buckner_nuka_cola_from_bytes(map_bytes, game_root):
    """Replace Nuka Cola with Stimpak and add a throwing knife to the Buckner
    House bookcase container.

    The container at tile BUCKNER_BOOK_CONTAINER_TILE (proto 63) holds a Guns &
    Bullets book and a Nuka Cola.  This replaces the Nuka Cola (Drug) with a
    Stimpak (Drug) — same subtype, same record size, simple in-place swap —
    then appends a throwing knife by inserting a new inventory item record and
    incrementing inv_count, mimicking how the vanilla Blades building bookshelf
    stores two throwing knives (ObjID=574) in its static inventory.
    """
    master_dat = os.path.join(game_root, "master.dat")
    data = bytearray(map_bytes)

    # Find the container by scanning for proto 63 at tile BUCKNER_BOOK_CONTAINER_TILE.
    needle = struct.pack(">I", 63)
    container_abs = None
    search_pos = 0
    while True:
        idx = data.find(needle, search_pos)
        if idx < 0:
            break
        obj = idx - 44
        if obj >= 0 and obj + 88 <= len(data):
            tile = struct.unpack_from(">I", data, obj + 4)[0]
            if tile == BUCKNER_BOOK_CONTAINER_TILE:
                container_abs = obj
                break
        search_pos = idx + 1

    if container_abs is None:
        abort(f"Buckner bookcase container (proto 63, tile {BUCKNER_BOOK_CONTAINER_TILE}) "
              f"not found in kladwtwn.map.")

    inv_count_abs = container_abs + 72
    inv_count = struct.unpack_from(">I", data, inv_count_abs)[0]

    # Walk items to find the Nuka Cola slot and the insertion point after all items.
    pos = container_abs + 88
    nuka_slot = None
    for i in range(inv_count):
        ppid = struct.unpack_from(">I", data, pos + 4 + 44)[0]
        pdata = read_file_from_dat(master_dat, f"proto\\items\\{ppid:08d}.pro")
        subtype = struct.unpack_from(">I", pdata, 32)[0] if pdata and len(pdata) >= 36 else 5
        extra = _ITEM_SUBTYPE_EXTRA.get(subtype, 4)
        if ppid == PID_NUKA_COLA:
            nuka_slot = pos
        pos += 4 + 88 + extra
    insert_pos = pos

    if nuka_slot is None:
        abort(f"Nuka Cola (proto {PID_NUKA_COLA}) not found in container at tile "
              f"{BUCKNER_BOOK_CONTAINER_TILE}.")

    # Replace Nuka Cola with Stimpak in-place (both Drug subtype, same size).
    struct.pack_into(">I", data, nuka_slot + 4 + 32, STIMPAK_FRM_PID)  # frm_pid
    struct.pack_into(">I", data, nuka_slot + 4 + 44, PID_STIMPAK)       # proto_pid

    # Compute a unique ObjID for the new knife by scanning existing objects.
    # num_local_vars=0 for kladwtwn.map so local vars do not occupy the file tail.
    scan_start = 0x20000  # objects section starts after ~128 KB tile+scripts data
    max_obj_id = 0
    for i in range(scan_start, len(data) - 8, 4):
        oid  = struct.unpack_from(">I", data, i)[0]
        tile = struct.unpack_from(">I", data, i + 4)[0]
        if oid % 2 == 0 and 2 <= oid <= 8000 and 0 <= tile <= 99999:
            max_obj_id = max(max_obj_id, oid)
    for i in range(scan_start, len(data) - 12, 4):
        qty = struct.unpack_from(">I", data, i)[0]
        if 1 <= qty <= 200:
            oid  = struct.unpack_from(">I", data, i + 4)[0]
            tile = struct.unpack_from(">I", data, i + 8)[0]
            if oid % 2 == 0 and 2 <= oid <= 8000 and tile == 0xFFFFFFFF:
                max_obj_id = max(max_obj_id, oid)
    next_obj_id = max_obj_id + 2

    # Build throwing-knife inventory item record.
    # Weapon subtype: 4 qty + 88 header + 8 weapon-extra = 100 bytes.
    # No-ammo weapon: ammo_type=0, ammo_count=0xFFFFFFFF (engine sentinel).
    rec = bytearray(100)
    struct.pack_into(">I", rec,  0,       1)                     # qty = 1
    struct.pack_into(">I", rec,  4 +  0,  next_obj_id)           # ObjID
    struct.pack_into(">I", rec,  4 +  4,  0xFFFFFFFF)            # tile = in-inventory
    struct.pack_into(">I", rec,  4 + 32,  THROWING_KNIFE_FRM_PID)# frm_pid = 28
    struct.pack_into(">I", rec,  4 + 36,  0x00000008)            # flags = in-inventory
    struct.pack_into(">I", rec,  4 + 44,  PID_THROWING_KNIFE)    # proto_pid = 45
    struct.pack_into(">I", rec,  4 + 48,  0xFFFFFFFF)            # critter_idx = -1
    struct.pack_into(">I", rec,  4 + 64,  0xFFFFFFFF)            # script_pid = -1
    struct.pack_into(">I", rec,  4 + 68,  0xFFFFFFFF)            # script_id = -1
    struct.pack_into(">I", rec,  4 + 88,  0x00000000)            # ammo_type = none
    struct.pack_into(">I", rec,  4 + 92,  0xFFFFFFFF)            # ammo_count = no-ammo sentinel

    patched = bytes(data[:insert_pos]) + bytes(rec) + bytes(data[insert_pos:])
    patched = bytearray(patched)
    struct.pack_into(">I", patched, inv_count_abs, inv_count + 1)

    print(f"  Patched kladwtwn.map: replaced Nuka Cola with Stimpak and added "
          f"throwing knife (ObjID={next_obj_id}) to bookcase container "
          f"(tile {BUCKNER_BOOK_CONTAINER_TILE}, inv_count {inv_count}->{inv_count + 1})")
    return bytes(patched)


def patch_kisbox_map(game_root):
    """Return patched kladwtwn.map bytes with DYNMK2_QTY Dynamite MKII items
    appended to Sajag's Kisbox inventory.

    Reads the map from rpu.dat (preferred) or master.dat.  Locates the Kisbox
    container at tile KISBOX_TILE by scanning for its proto PID, then inserts
    the new item records immediately after the last existing item and increments
    the inv_count field.
    """
    master_dat = os.path.join(game_root, "master.dat")
    rpu_dat    = os.path.join(game_root, "mods", "rpu.dat")

    map_bytes = None
    if os.path.isfile(rpu_dat):
        map_bytes = read_file_from_dat(rpu_dat, KISBOX_MAP_PATH)
    if map_bytes is None:
        map_bytes = read_file_from_dat(master_dat, KISBOX_MAP_PATH)
    if map_bytes is None:
        abort(f"{KISBOX_MAP_PATH!r} not found in rpu.dat or master.dat.")

    # Ground art FID for Dynamite MKII: read from proto 51 (our base proto) at
    # offset 8.  This matches the frm_pid stored in existing Kisbox item records.
    dynmk2_frm_pid = 0
    for _dat in ([rpu_dat] if os.path.isfile(rpu_dat) else []) + [master_dat]:
        _pd = read_file_from_dat(_dat, f"proto\\items\\{SRC_PROTO_ID:08d}.pro")
        if _pd and len(_pd) >= 12:
            dynmk2_frm_pid = struct.unpack_from(">I", _pd, 8)[0]
            break

    data = bytearray(map_bytes)
    needle = struct.pack(">I", PID_KISBOX)

    # Find the Kisbox object (PID at offset +44 within 88-byte header).
    kisbox_abs = None
    search_pos = 0
    while True:
        idx = data.find(needle, search_pos)
        if idx < 0:
            break
        obj = idx - 44
        if obj >= 0 and obj + 88 <= len(data):
            tile = struct.unpack_from(">I", data, obj + 4)[0]
            if tile == KISBOX_TILE:
                kisbox_abs = obj
                break
        search_pos = idx + 1

    if kisbox_abs is None:
        abort(f"Kisbox (proto 63, tile {KISBOX_TILE}) not found in kladwtwn.map.")

    inv_count_abs = kisbox_abs + 72
    inv_count     = struct.unpack_from(">I", data, inv_count_abs)[0]

    # Walk existing items to find the insertion point.
    pos = kisbox_abs + 88
    for _ in range(inv_count):
        pos += _kisbox_parse_item(data, pos, master_dat)
    insert_pos = pos

    # Build each new item record: qty(4) + header(88) + Misc extra(4) = 96 bytes.
    # Items in inventory have tile=0xFFFFFFFF; script fields = 0xFFFFFFFF (use proto).
    # flags=0x00000008 and frm_pid match the format used by existing Kisbox items.
    def _new_item(obj_id):
        rec = bytearray(96)
        struct.pack_into(">I", rec,  4 +  0, obj_id)           # ObjID
        struct.pack_into(">I", rec,  0,      1)                # qty = 1
        struct.pack_into(">I", rec,  4 +  4, 0xFFFFFFFF)       # tile = -1
        struct.pack_into(">I", rec,  4 + 32, dynmk2_frm_pid)   # frm_pid (ground art)
        struct.pack_into(">I", rec,  4 + 36, 0x00000008)       # flags
        struct.pack_into(">I", rec,  4 + 44, PID_DYNMK2)       # proto_pid = 600
        struct.pack_into(">I", rec,  4 + 48, 0xFFFFFFFF)       # critter_idx = -1
        struct.pack_into(">I", rec,  4 + 64, 0xFFFFFFFF)       # script_pid = -1
        struct.pack_into(">I", rec,  4 + 68, 0xFFFFFFFF)       # script_id = -1
        return bytes(rec)

    # Assign unique ObjIDs by finding the max ObjID in the known object headers.
    # Walk all items in the Kisbox to collect their ObjIDs as a lower bound;
    # use 0x8000 as a safe base well above any vanilla map ObjID.
    base_obj_id = 0x8000

    insertion = b"".join(_new_item(base_obj_id + i) for i in range(DYNMK2_QTY))

    # Splice in the new items and update inv_count.
    patched = bytes(data[:insert_pos]) + insertion + bytes(data[insert_pos:])
    patched = bytearray(patched)
    struct.pack_into(">I", patched, inv_count_abs, inv_count + DYNMK2_QTY)

    print(f"  Patched kladwtwn.map: inserted {DYNMK2_QTY} Dynamite MKII at "
          f"Kisbox abs={kisbox_abs} (inv_count {inv_count}->{inv_count+DYNMK2_QTY})")
    return bytes(patched)


def patch_kisbox_add_power_armor(game_root):
    """Return patched kladwtwn.map bytes with one Power Armor added to Sajag's Kisbox.

    Power Armor (file 00000014.pro, internal PID=3, ScriptID=-1) is safe to place in
    a container at map-load time — it carries no script and is Armor type (0 extra
    bytes), so the record is 4+88 = 92 bytes.

    Weapon-type items are NOT added as static MAP items because the engine requires
    specific non-trivial values in their 8 extra bytes (ammo state) that depend on
    the weapon.  Weapons are added via kisbox.int restock patches instead, which
    handle the ammo state correctly.
    """
    master_dat = os.path.join(game_root, "master.dat")
    rpu_dat    = os.path.join(game_root, "mods", "rpu.dat")

    map_bytes = None
    if os.path.isfile(rpu_dat):
        map_bytes = read_file_from_dat(rpu_dat, KISBOX_MAP_PATH)
    if map_bytes is None:
        map_bytes = read_file_from_dat(master_dat, KISBOX_MAP_PATH)
    if map_bytes is None:
        abort(f"{KISBOX_MAP_PATH!r} not found in rpu.dat or master.dat.")

    data = bytearray(map_bytes)
    needle = struct.pack(">I", PID_KISBOX)

    kisbox_abs = None
    search_pos = 0
    while True:
        idx = data.find(needle, search_pos)
        if idx < 0:
            break
        obj = idx - 44
        if obj >= 0 and obj + 88 <= len(data):
            tile = struct.unpack_from(">I", data, obj + 4)[0]
            if tile == KISBOX_TILE:
                kisbox_abs = obj
                break
        search_pos = idx + 1

    if kisbox_abs is None:
        abort(f"Kisbox (proto 63, tile {KISBOX_TILE}) not found in kladwtwn.map.")

    inv_count_abs  = kisbox_abs + 72
    max_slots_abs  = kisbox_abs + 76
    inv_count      = struct.unpack_from(">I", data, inv_count_abs)[0]

    # Walk Kisbox items to find the insertion point.
    pos = kisbox_abs + 88
    for _ in range(inv_count):
        pos += _kisbox_parse_item(data, pos, master_dat)
    insert_pos = pos

    # Compute a globally unique ObjID by scanning the entire objects section.
    # The MAP header has num_local_vars at offset 0x14 (int32 BE); local vars occupy
    # the last num_local_vars*4 bytes of the file.
    num_local_vars  = struct.unpack_from(">i", data, 0x14)[0]
    local_vars_start = len(data) - num_local_vars * 4
    scan_start = 0x20000  # objects section starts after ~128KB tile data
    max_map_obj_id = 0
    # Pattern 1: inventory items  [qty 1-200][even ObjID 2-8000][tile=0xFFFFFFFF]
    for i in range(scan_start, local_vars_start - 12, 4):
        qty  = struct.unpack_from(">I", data, i)[0]
        if 1 <= qty <= 200:
            oid  = struct.unpack_from(">I", data, i + 4)[0]
            tile = struct.unpack_from(">I", data, i + 8)[0]
            if oid % 2 == 0 and 2 <= oid <= 8000 and tile == 0xFFFFFFFF:
                max_map_obj_id = max(max_map_obj_id, oid)
    # Pattern 2: top-level objects  [even ObjID 2-8000][tile 0-99999]
    for i in range(scan_start, local_vars_start - 8, 4):
        oid  = struct.unpack_from(">I", data, i)[0]
        tile = struct.unpack_from(">I", data, i + 4)[0]
        if oid % 2 == 0 and 2 <= oid <= 8000 and 0 <= tile <= 99999:
            max_map_obj_id = max(max_map_obj_id, oid)
    next_obj_id = max_map_obj_id + 2

    # Power Armor has Size=15; the vanilla Kisbox max_slots=10 is too small to hold it.
    # Raise max_slots to fit: sum of existing items' sizes + Power Armor's size (15).
    # Use 100 as a round safe ceiling well above anything we'll store.
    struct.pack_into(">I", data, max_slots_abs, 100)

    # Armor subtype → 0 extra bytes: 4 qty + 88 header = 92 bytes total.
    rec = bytearray(92)
    struct.pack_into(">I", rec,  0,      1)                   # qty = 1
    struct.pack_into(">I", rec,  4 +  0, next_obj_id)         # ObjID = last + 2
    struct.pack_into(">I", rec,  4 +  4, 0xFFFFFFFF)          # tile = in-inventory
    struct.pack_into(">I", rec,  4 + 32, POWER_ARMOR_FRM_PID) # frm_pid = 35
    struct.pack_into(">I", rec,  4 + 36, 0x00000008)          # flags
    struct.pack_into(">I", rec,  4 + 44, PID_POWER_ARMOR)     # proto_pid = 14 (file #)
    struct.pack_into(">I", rec,  4 + 48, 0xFFFFFFFF)          # critter_idx = -1
    struct.pack_into(">I", rec,  4 + 64, 0xFFFFFFFF)          # script_pid = -1
    struct.pack_into(">I", rec,  4 + 68, 0xFFFFFFFF)          # script_id = -1

    patched = bytes(data[:insert_pos]) + bytes(rec) + bytes(data[insert_pos:])
    patched = bytearray(patched)
    struct.pack_into(">I", patched, inv_count_abs, inv_count + 1)

    print(f"  Patched kladwtwn.map: inserted Power Armor at "
          f"Kisbox abs={kisbox_abs} (inv_count {inv_count}->{inv_count + 1}, max_slots 10->100)")
    return bytes(patched)


def build_proto_600(game_root, script_id, inven_fid):
    """Return patched proto-600 bytes, derived from proto 51 (inactive dynamite)."""
    src_filename = f"{SRC_PROTO_ID:08d}.pro"

    # Prefer a loose override; fall back to master.dat.
    src_disk = os.path.join(game_root, "data", "proto", "items", src_filename)
    if os.path.isfile(src_disk):
        with open(src_disk, "rb") as fh:
            data = bytearray(fh.read())
        print(f"  Proto source: {src_disk}")
    else:
        dat_path = os.path.join(game_root, "master.dat")
        if not os.path.isfile(dat_path):
            abort("master.dat not found. Make sure the path points to the Fallout 2 game directory.")
        raw = read_file_from_dat(dat_path, "proto\\items\\" + src_filename)
        if raw is None:
            abort(f"{src_filename!r} not found in master.dat.")
        data = bytearray(raw)
        print(f"  Proto source: {src_filename} (from master.dat)")

    struct.pack_into(">I", data, OFFSET_PID,       DST_PROTO_ID)
    struct.pack_into(">I", data, OFFSET_TEXT_ID,   MSG_ID_NAME)
    struct.pack_into(">i", data, OFFSET_SCRIPT_ID, script_id)
    struct.pack_into(">I", data, OFFSET_COST,      NEW_COST)
    struct.pack_into(">I", data, OFFSET_INVEN_FID, inven_fid)
    return bytes(data)

# ── Steps ────────────────────────────────────────────────────────────────────

def step_cleanup_loose(game_root):
    """Remove any loose files written by previous installs."""
    removed = []
    for rel in LEGACY_FILES:
        path = os.path.join(game_root, rel)
        if os.path.exists(path):
            try:
                os.chmod(path, 0o644)  # clear read-only if set
                os.remove(path)
                removed.append(rel)
            except OSError as e:
                print(f"  WARNING: could not remove {rel}: {e}")
    if removed:
        for r in removed:
            print(f"  Removed {r}")
    else:
        print("  Nothing to remove.")


def step_build_and_install_dat(game_root):
    """Build f2mod.dat from scripts + proto and copy it to <game>/mods/."""
    file_map = {}

    for dat_path, src_rel in DAT_SCRIPTS.items():
        src = os.path.join(SCRIPT_DIR, src_rel)
        if not os.path.isfile(src):
            abort(f"Source file not found: {src}")
        with open(src, "rb") as fh:
            file_map[dat_path] = fh.read()

    # Get scripts.lst to bundle (prevents f2mod.dat from shadowing rpu.dat's copy)
    # and to determine the correct ScriptID for the dynamitemk2 item script.
    scripts_lst = None
    rpu_dat = os.path.join(game_root, "mods", "rpu.dat")
    if os.path.isfile(rpu_dat):
        scripts_lst = read_file_from_dat(rpu_dat, r"scripts\scripts.lst")
        if scripts_lst is not None:
            print("  Bundled scripts.lst from rpu.dat")
    if scripts_lst is None:
        master_dat = os.path.join(game_root, "master.dat")
        if os.path.isfile(master_dat):
            scripts_lst = read_file_from_dat(master_dat, r"scripts\scripts.lst")
            if scripts_lst is not None:
                print("  Bundled scripts.lst from master.dat (rpu.dat not found)")
    if scripts_lst is None:
        abort("Could not find scripts.lst in rpu.dat or master.dat.")

    # Count existing lines to determine the 0-based index for dynamitemk2.
    # Every line (including blank and comment lines) counts as a script slot.
    text_lines = scripts_lst.replace(b"\r\n", b"\n").split(b"\n")
    if text_lines and text_lines[-1] == b"":
        text_lines = text_lines[:-1]
    script_id = len(text_lines)

    # Append the dynamitemk2 entry.
    if not scripts_lst.endswith((b"\n", b"\r\n")):
        scripts_lst += b"\n"
    scripts_lst += b"dynamitemk2\n"
    file_map[r"scripts\scripts.lst"] = scripts_lst
    print(f"  Appended dynamitemk2 to scripts.lst at index {script_id}")

    dynmk2_frm, ext_inven_lst, dynmk2_idx = build_inven_art(game_root)
    file_map[DST_INVEN_FRM] = dynmk2_frm
    file_map[INVEN_LST]     = ext_inven_lst
    inven_fid = 0x07000000 | dynmk2_idx
    print(f"  Built DYNMK2.FRM (inven index {dynmk2_idx}, FID=0x{inven_fid:08X})")

    proto_key = f"proto\\items\\{DST_PROTO_ID:08d}.pro"
    file_map[proto_key] = build_proto_600(game_root, script_id, inven_fid)

    map_bytes = patch_kisbox_add_power_armor(game_root)
    map_bytes = _patch_golden_gecko_bookcase_from_bytes(map_bytes, game_root)
    map_bytes = _patch_buckner_nuka_cola_from_bytes(map_bytes, game_root)
    file_map[KISBOX_MAP_PATH] = map_bytes

    kisbox_int_path = os.path.join(SCRIPT_DIR, r"data\scripts\kisbox.int")
    with open(kisbox_int_path, "rb") as fh:
        file_map[r"scripts\kisbox.int"] = fh.read()
    print(f"  Bundled kisbox.int from source-compiled data/scripts/kisbox.int")

    dat_bytes = build_dat2(file_map)

    mods_dir = os.path.join(game_root, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    out_path = os.path.join(mods_dir, "f2mod.dat")
    with open(out_path, "wb") as fh:
        fh.write(dat_bytes)
    print(f"  Built f2mod.dat ({len(dat_bytes):,} bytes, {len(file_map)} files)")


def step_update_mods_order(game_root):
    """Add f2mod.dat to mods_order.txt (if not already present)."""
    path = os.path.join(game_root, "mods", "mods_order.txt")

    if not os.path.isfile(path):
        with open(path, "w", encoding="latin-1") as fh:
            fh.write("f2mod.dat\n")
        print("  Created mods_order.txt with f2mod.dat")
        return

    with open(path, "r", encoding="latin-1") as fh:
        content = fh.read()

    # Already active (not commented out)?
    if re.search(r"^f2mod\.dat\s*$", content, re.MULTILINE | re.IGNORECASE):
        print("  f2mod.dat already in mods_order.txt — skipped.")
        return

    # Remove any commented-out entry from a previous install.
    content = re.sub(r"^;+\s*f2mod\.dat.*\n?", "", content, flags=re.MULTILINE | re.IGNORECASE)

    if not content.endswith("\n"):
        content += "\n"
    content += "f2mod.dat\n"

    with open(path, "w", encoding="latin-1") as fh:
        fh.write(content)
    print("  Added f2mod.dat to mods_order.txt")


def step_update_msg(game_root):
    """Append Dynamite MKII name/description to pro_item.msg."""
    path = os.path.join(
        game_root, "data", "text", "english", "game", "pro_item.msg"
    )
    if not os.path.isfile(path):
        # Extract from master.dat on a fresh install.
        dat_path = os.path.join(game_root, "master.dat")
        raw = read_file_from_dat(dat_path, r"text\english\game\pro_item.msg")
        if raw is None:
            abort("pro_item.msg not found as loose file or in master.dat.")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(raw)
        print("  Extracted pro_item.msg from master.dat")

    with open(path, "r", encoding="latin-1") as fh:
        content = fh.read()

    marker = "{" + str(MSG_ID_NAME) + "}"
    if marker in content:
        print(f"  pro_item.msg already has entry {marker} — skipped.")
        return

    entries = (
        f"\n{{{MSG_ID_NAME}}}" + "{}{Dynamite MKII}\n"
        f"{{{MSG_ID_DESC}}}" + "{}{A military-grade demolition charge packing twice the explosive "
        "force of standard dynamite. The casing is reinforced and the blasting "
        "compound has been enhanced for maximum yield. Handle with extreme care.}\n"
    )
    with open(path, "a", encoding="latin-1") as fh:
        fh.write(entries)
    print(f"  Appended Dynamite MKII entries ({MSG_ID_NAME}, {MSG_ID_DESC}) to pro_item.msg")

def step_install_loose_scripts(game_root):
    """Write scripts that require loose-file access to <game>/data/scripts/."""
    scripts_dir = os.path.join(game_root, "data", "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    for rel_dest, rel_src in LOOSE_SCRIPTS.items():
        src = os.path.join(SCRIPT_DIR, rel_src)
        if not os.path.isfile(src):
            abort(f"Source file not found: {src}")
        dst = os.path.join(game_root, rel_dest)
        with open(src, "rb") as fh:
            data = fh.read()
        with open(dst, "wb") as fh:
            fh.write(data)
        print(f"  Wrote loose {os.path.basename(dst)} ({len(data):,} bytes)")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) >= 2:
        game_root = sys.argv[1]
    else:
        print("f2Mod Installer\n---------------")
        game_root = input("Enter the path to your Fallout 2 directory: ").strip().strip('"')

    game_root = os.path.normpath(game_root)

    if not os.path.isdir(game_root):
        abort(f"Directory not found: {game_root}")

    if os.path.basename(game_root).lower() == "data":
        game_root = os.path.dirname(game_root)

    if not os.path.isdir(os.path.join(game_root, "data")):
        abort(
            f"'data' subdirectory not found in {game_root!r}.\n"
            "Make sure you are pointing at the Fallout 2 game folder."
        )

    print(f"\nInstalling into: {game_root}\n")

    print("1. Removing loose files from previous installs ...")
    step_cleanup_loose(game_root)

    print("\n2. Building and installing f2mod.dat ...")
    step_build_and_install_dat(game_root)

    print("\n3. Updating mods_order.txt ...")
    step_update_mods_order(game_root)

    print("\n4. Installing loose script stubs ...")
    step_install_loose_scripts(game_root)

    print("\n5. Updating item message file ...")
    step_update_msg(game_root)

    print("\nInstallation complete.")


if __name__ == "__main__":
    main()
