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
    r"scripts\dynamitemk2.int":          r"data\scripts\dynamitemk2.int",
    r"scripts\vcandy.int":               r"data\scripts\vcandy.int",
    r"scripts\rcdrjohn.int":             r"data\scripts\rcdrjohn.int",
    r"scripts\fcdrfung.int":             r"data\scripts\fcdrfung.int",
    # Stub for a spatial script that the Arroyo map references by name but
    # whose .int is absent from master.dat and all mod archives.  Without it
    # the engine crashes on "Couldn't open … for read" immediately after the
    # Temple-of-Trials cinematic.
    r"scripts\a swarm of mantis infesting some spore plants.int":
        r"data\scripts\a swarm of mantis infesting some spore plants.int",
}

# Dialog MSG files to patch: internal DAT path -> list of (msg_id, text) to append.
# Each file is extracted from master.dat (or rpu.dat), entries appended, then
# included in f2mod.dat so the engine uses our patched version.
DIALOG_MSG_PATCHES = {
    r"text\english\dialog\vcandy.msg": [
        (360, "Who do you want this for?"),
        (361, "On myself."),
        (362, "Actually, I changed my mind."),
        (363, "They already have as many implants as I can give them."),
    ],
    r"text\english\dialog\rcdrjohn.msg": [
        (330, "Who do you want this for?"),
        (331, "On myself."),
        (332, "Actually, I changed my mind."),
        (333, "They already have as many implants as I can give them."),
    ],
    r"text\english\dialog\fcdrfung.msg": [
        (241, "Who do you want this for?"),
        (242, "On myself."),
        (243, "Actually, I changed my mind."),
        (244, "They already have as many implants as I can give them."),
    ],
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
    os.path.join("data", "scripts", "dynamitemk2.int"),
    os.path.join("data", "proto", "items", "00000600.pro"),
]

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

    master_dat = os.path.join(game_root, "master.dat")
    rpu_dat    = os.path.join(game_root, "mods", "rpu.dat")
    for dat_msg_path, new_entries in DIALOG_MSG_PATCHES.items():
        raw = None
        if os.path.isfile(rpu_dat):
            raw = read_file_from_dat(rpu_dat, dat_msg_path)
        if raw is None:
            raw = read_file_from_dat(master_dat, dat_msg_path)
        if raw is None:
            abort(f"{dat_msg_path!r} not found in rpu.dat or master.dat.")
        text = raw.decode("latin-1")
        if not text.endswith("\n"):
            text += "\n"
        for msg_id, msg_text in new_entries:
            marker = "{" + str(msg_id) + "}"
            if marker not in text:
                text += f"{{{msg_id}}}{{}}{{{msg_text}}}\n"
        file_map[dat_msg_path] = text.encode("latin-1")
        print(f"  Patched {os.path.basename(dat_msg_path)} (+{len(new_entries)} entries)")

    proto_key = f"proto\\items\\{DST_PROTO_ID:08d}.pro"
    file_map[proto_key] = build_proto_600(game_root, script_id, inven_fid)

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
