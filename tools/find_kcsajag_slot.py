"""
Find KCSajag (scripts.lst[80]) in kladwtwn.map by scanning all script slots
for value 80 at each possible field position, then find its critter object.
"""
import struct, zlib
from pathlib import Path

def read_dat(dat_path, internal_path):
    target = internal_path.replace("/", "\\").lower()
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1").lower(); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        if name.replace("/", "\\") == target:
            with open(dat_path, "rb") as fh:
                fh.seek(offset)
                raw = fh.read(packed)
            return zlib.decompress(raw) if comp else raw
    return None

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
data = read_dat(game / "mods" / "rpu.dat", "maps\\kladwtwn.map")

num_local_vars  = struct.unpack_from(">i", data, 32)[0]
num_global_vars = struct.unpack_from(">i", data, 48)[0]

# Parse scripts section (3 elevations)
scripts_start = 236 + num_global_vars * 4 + num_local_vars * 4 + 3 * 10000 * 2
obj_start = 283048

print("Scanning scripts section for value 80 in any field position:")
print("  (looking for scripts.lst index = KCSajag = 80)")
pos = scripts_start
for elev in range(3):
    count = struct.unpack_from(">i", data, pos)[0]; pos += 4
    for i in range(count):
        fields = [struct.unpack_from(">i", data, pos + k*4)[0] for k in range(6)]
        for fi, fval in enumerate(fields):
            if fval == 80:
                local_idx = fields[0] & 0xFFFFFF
                print(f"  elev={elev} record={i} offset={pos}: field[{fi}]=80  "
                      f"all_fields={fields}  local_idx={local_idx}")
        pos += 24
    pad = (16 - (count % 16)) % 16
    pos += pad * 24

print()
# Also search entire scripts section bytes for 0x00000050 (=80)
sid_bytes = b'\x00\x00\x00\x50'
p = scripts_start
found = []
while p < obj_start:
    idx = data.find(sid_bytes, p)
    if idx == -1 or idx >= obj_start:
        break
    # Check alignment within a 24-byte record
    offset_in_section = idx - scripts_start
    field_within_record = offset_in_section % 24 // 4
    record_number = offset_in_section // 24
    print(f"  Value 80 at offset {idx} (field {field_within_record} within record ~{record_number})")
    # Show full record
    rec_start = idx - (field_within_record * 4)
    fields = [struct.unpack_from(">i", data, rec_start + k*4)[0] for k in range(6)]
    print(f"    Record: {fields}")
    found.append(idx)
    p = idx + 1
