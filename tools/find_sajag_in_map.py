"""Parse kladwtwn.map to find which critter has KCSajag (script index 80),
and print that critter's proto PID."""
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

# Load kladwtwn.map — prefer rpu.dat version
data = read_dat(game / "mods" / "rpu.dat", "maps\\kladwtwn.map")
src = "rpu.dat"
if data is None:
    data = read_dat(game / "master.dat", "maps\\kladwtwn.map")
    src = "master.dat"
print(f"kladwtwn.map from {src}: {len(data)} bytes")

# Parse header
version       = struct.unpack_from(">i", data, 0)[0]
map_name      = data[4:20].rstrip(b"\x00").decode("latin-1")
num_local_vars = struct.unpack_from(">i", data, 32)[0]
map_script_id  = struct.unpack_from(">i", data, 36)[0]
num_global_vars = struct.unpack_from(">i", data, 48)[0]
print(f"name={map_name!r}  map_script_id={map_script_id}  local_vars={num_local_vars}  global_vars={num_global_vars}")

# Skip header (236 bytes), global vars, local vars
pos = 236 + num_global_vars * 4 + num_local_vars * 4
# Skip tiles
pos += 3 * 10000 * 2

# Parse scripts section — read all script types and collect (type, script_id) pairs
print(f"\nScripts section at offset {pos}")

KCSAJAG_SCRIPT_IDX = 80
found_pids = []

for elev in range(3):
    if pos + 4 > len(data):
        break
    count = struct.unpack_from(">i", data, pos)[0]; pos += 4
    for i in range(count):
        if pos + 24 > len(data):
            break
        pid_word = struct.unpack_from(">i", data, pos)[0]; pos += 4
        nxt      = struct.unpack_from(">i", data, pos)[0]; pos += 4
        f1       = struct.unpack_from(">i", data, pos)[0]; pos += 4
        f2       = struct.unpack_from(">i", data, pos)[0]; pos += 4
        f3       = struct.unpack_from(">i", data, pos)[0]; pos += 4
        sid      = struct.unpack_from(">i", data, pos)[0]; pos += 4

        script_type = (pid_word >> 24) & 0xFF
        # pid_word low 3 bytes = local script index; the critter's proto PID
        # is stored in the OBJECT section, not here.
        # But script_id (sid) is the scripts.lst index.
        if sid == KCSAJAG_SCRIPT_IDX:
            print(f"  elev={elev} script#{i}: pid_word={pid_word:#010x} type={script_type} sid={sid}")
            found_pids.append((elev, i, pid_word, script_type))

    # Padding to multiple of 16
    pad = (16 - (count % 16)) % 16
    pos += pad * 24

# Now search the objects section for critters at those script indices
# The objects section comes after scripts
# Each object has a different format but includes PID, script references
# Let's search for the proto PID by scanning for the script local index
print(f"\nObject section search (looking for critters referencing script entries)...")
# In the objects section, critter objects have PID at a known offset
# Let's look for objects with type=1 (critter) that have script_id=KCSAJAG in the map
# Use a simpler scan: look for 0x01 (critter type) in PID high byte followed by proto id

# Actually, let's scan for PID values where type=1 (critter) and look near
# the script slot that matched
for elev, idx, pid_word, stype in found_pids:
    print(f"  Script slot: elev={elev} idx={idx} type={stype}")

# Simpler: scan entire binary for critter PIDs 0x01000000-0x010000FF
# that appear near offset patterns typical of Sajag
import re
print("\nAll critter proto PIDs referenced in script section:")
all_script_pids = set()
pos2 = 236 + num_global_vars * 4 + num_local_vars * 4 + 3 * 10000 * 2
for elev in range(3):
    if pos2 + 4 > len(data):
        break
    count = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
    for i in range(count):
        if pos2 + 24 > len(data):
            break
        pid_word = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
        nxt = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
        f1  = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
        f2  = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
        f3  = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
        sid = struct.unpack_from(">i", data, pos2)[0]; pos2 += 4
        script_type = (pid_word >> 24) & 0xFF
        if script_type == 4:  # critter type
            all_script_pids.add((sid, pid_word & 0xFFFFFF))
    pad = (16 - (count % 16)) % 16
    pos2 += pad * 24

print("  (script_lst_idx, local_script_idx) for critter-type scripts:")
for sid, local in sorted(all_script_pids):
    print(f"  sid={sid}, local_idx={local}")
