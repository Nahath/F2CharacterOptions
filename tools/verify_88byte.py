"""
Verify the 88-byte object header hypothesis.

If the base header is 88 bytes (not 68), then:
- Proto PID is at offset +44 (0x2C) per wiki
- Inventory Count is at offset +72 (0x48)
- If Sajag's PID (0x01000038) is at abs 169392, Sajag starts at 169392-44 = 169348.

Also try the alternative: PID at +4 (as I've been assuming), so Sajag starts at 169388.

For each hypothesis, check if the inventory count and first-item qty are sensible.
"""
import struct, zlib
from pathlib import Path

GAME   = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
MASTER = GAME / "master.dat"

PID_SAJAG  = 0x01000038  # confirmed at abs 169392

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

# ── Hypothesis A: PID at +4, Sajag starts at 169388 ──────────────────────────
print("=== Hypothesis A: 88-byte header, PID at +4 ===")
# In this case: PID at +4, Critter Index at +8, ... Inventory Count at +72
# if header is 88 bytes with PID at offset 4, layout shifted by 4 vs wiki
sajag_a = 169388
pid_a    = struct.unpack_from(">I", data, sajag_a + 4)[0]
inv_a    = struct.unpack_from(">I", data, sajag_a + 72)[0]  # inv count at +72 (88-byte layout)
max_a    = struct.unpack_from(">I", data, sajag_a + 76)[0]
print(f"  PID at +4  = {pid_a:#010x} (expected 0x01000038: {'OK' if pid_a==PID_SAJAG else 'FAIL'})")
print(f"  inv_count at +72 = {inv_a} (signed: {struct.unpack_from('>i',data,sajag_a+72)[0]})")
print(f"  max_slots at +76 = {max_a}")
# Critter extra = 40 bytes after 88-byte header → items start at 88+40=128
items_start_a = sajag_a + 128
qty0_a = struct.unpack_from(">I", data, items_start_a)[0]
print(f"  Items start at +128, qty[0] = {qty0_a}")
if qty0_a <= 100:
    # Check item 0's PID (at item_start + 4 + 4 for first field, then +4 for PID)
    item0_pid_a = struct.unpack_from(">I", data, items_start_a + 4 + 4)[0]
    print(f"  Item[0] at item_start+4: field0={struct.unpack_from('>I',data,items_start_a+4)[0]:#010x}, PID={item0_pid_a:#010x}")

print()

# ── Hypothesis B: PID at +44, Sajag starts at 169348 ─────────────────────────
print("=== Hypothesis B: 88-byte header, PID at +44 (wiki layout) ===")
sajag_b = 169392 - 44  # = 169348
pid_b    = struct.unpack_from(">I", data, sajag_b + 44)[0]
inv_b    = struct.unpack_from(">I", data, sajag_b + 72)[0]
max_b    = struct.unpack_from(">I", data, sajag_b + 76)[0]
print(f"  PID at +44  = {pid_b:#010x} (expected 0x01000038: {'OK' if pid_b==PID_SAJAG else 'FAIL'})")
print(f"  inv_count at +72 = {inv_b}")
print(f"  max_slots at +76 = {max_b}")
# Critter extra = 40 bytes → items start at 88+40=128
items_start_b = sajag_b + 128
qty0_b = struct.unpack_from(">I", data, items_start_b)[0]
print(f"  Items start at +128, qty[0] = {qty0_b}")
if qty0_b <= 100:
    item0_start = items_start_b + 4  # after qty
    field0_b    = struct.unpack_from(">I", data, item0_start)[0]
    pid_item0_b = struct.unpack_from(">I", data, item0_start + 44)[0]
    print(f"  Item[0] field0={field0_b:#010x}, PID at item+44={pid_item0_b:#010x}")

print()

# ── Dump 48 bytes before and after abs 169392 for context ────────────────────
print("=== Context around PID (abs 169392) ===")
for rel in range(-48, 52, 4):
    abs_p = 169392 + rel
    v = struct.unpack_from(">I", data, abs_p)[0]
    note = ""
    if rel == 0: note = "<-- PID=0x01000038"
    if rel == -44: note = "<-- start if PID@+44 (wiki)"
    if rel == -4:  note = "<-- start if PID@+4"
    print(f"  {rel:+5d}  abs={abs_p}  {v:#010x}  {note}")

print()
print("=== Critter extra candidates (40 bytes after header) ===")
# Try B: header ends at 169348+88=169436, critter extra at 169436..169475
print("Hypothesis B critter extra (169436..169475):")
for i in range(10):
    abs_p = 169436 + i*4
    rel_from_sajag_b = abs_p - sajag_b
    v = struct.unpack_from(">I", data, abs_p)[0]
    field_names = ["reaction","current_mp","combat_results","damage_last_turn",
                   "ai_packet","group_id","who_hit_me","current_hp","current_rad","current_poison"]
    print(f"  [{i}] +{rel_from_sajag_b:3d}  abs={abs_p}  {v:#010x} = {struct.unpack_from('>i',data,abs_p)[0]:10d}  ({field_names[i]})")
