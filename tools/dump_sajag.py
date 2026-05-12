"""
Raw dump of Sajag's 488-byte record in vanilla kladwtwn.map.
Tries to figure out the inventory item format empirically.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"

SAJAG_START   = 169388
SAJAG_SIZE    = 488


def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl   = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1").lower(); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        if name.replace("/", "\\") == target:
            with open(dat_path, "rb") as fh:
                fh.seek(offset); raw = fh.read(packed)
            return zlib.decompress(raw) if comp else raw
    return None


data = read_dat(MASTER, r"maps\kladwtwn.map")
sajag = data[SAJAG_START: SAJAG_START + SAJAG_SIZE]

print("=== Raw Sajag 488-byte record (4-byte words) ===")
print(f"{'rel':>5}  {'abs':>7}  {'unsigned':>10}  {'signed':>12}  note")
for i in range(0, SAJAG_SIZE, 4):
    u  = struct.unpack_from(">I", sajag, i)[0]
    s  = struct.unpack_from(">i", sajag, i)[0]
    ab = SAJAG_START + i
    note = ""
    if i == 0:   note = "flags"
    if i == 4:   note = "PID"
    if i == 12:  note = "tile"
    if i == 44:  note = "script_id"
    if i == 64:  note = "<-- candidate inv_count"
    if i == 68:  note = "<-- candidate inv_count / qty[0]"
    if i == 72:  note = "<-- candidate Kisbox flags"
    if i == 76:  note = "Kisbox PID?"
    if i == 136: note = "Kisbox inv_count?"
    if i == 140: note = "Kisbox sub-item data start?"
    if i == 488-4: note = "last word in record"
    print(f"  {i:5d}  {ab:7d}  {u:#010x}  {s:12d}  {note}")

print()
print("=== Verify: next critter (should start at Sajag+488) ===")
for i in range(488, 504, 4):
    u  = struct.unpack_from(">I", data, SAJAG_START + i)[0]
    print(f"  +{i}  abs={SAJAG_START+i}  {u:#010x}")

# ── Try to determine how many items Sajag actually has ──
print()
print("=== Scan for PID patterns after Sajag header ===")
print("(looking for type_byte 0x00 or 0x01 with plausible proto_id)")
for i in range(64, SAJAG_SIZE, 4):
    u  = struct.unpack_from(">I", sajag, i)[0]
    tb = (u >> 24) & 0xFF
    pid = u & 0xFFFFFF
    if tb in (0x00, 0x01) and 1 <= pid <= 2000:
        print(f"  +{i} (abs={SAJAG_START+i}):  PID={u:#010x}  type={tb}  proto={pid}")
