"""Dump the script record at offset 220456 and find the object in objects section with that slot."""
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

# Dump the 24-byte script record at offset 220456
off = 220456
pid_word = struct.unpack_from(">I", data, off)[0]
nxt      = struct.unpack_from(">I", data, off+4)[0]
f1       = struct.unpack_from(">i", data, off+8)[0]
f2       = struct.unpack_from(">i", data, off+12)[0]
f3       = struct.unpack_from(">i", data, off+16)[0]
sid      = struct.unpack_from(">i", data, off+20)[0]
print(f"Script record at {off}:")
print(f"  pid_word = {pid_word:#010x}  (type byte = {(pid_word>>24)&0xFF})")
print(f"  next     = {nxt:#010x}")
print(f"  f1       = {f1}")
print(f"  f2       = {f2}")
print(f"  f3       = {f3}")
print(f"  sid      = {sid}  (scripts.lst index)")

# The local script index = pid_word & 0x7FFFFF (or similar mask)
local_idx = pid_word & 0xFFFFFF
print(f"  local_idx= {local_idx}")

# Now find the object in the objects section that references this script slot
# Object's script_id field references the LOCAL script slot index
# Objects section starts at 283048
obj_sec_start = 283048
print(f"\nSearching objects section (start={obj_sec_start}) for script_id={local_idx}...")

# Objects are variable-size; let's scan for the pattern:
# In an object, script_id is at a fixed offset within the object base header.
# F2 object base header (big-endian):
#   0: flags     uint32
#   4: PID       uint32
#   8: CID       int32
#  12: x         int32
#  16: y         int32  (often -1)
#  20: sx        int32
#  24: sy        int32
#  28: frame_idx uint32
#  32: direction uint32
#  36: FrmID     uint32
#  40: anim_code uint32
#  44: script_id int32   <- local script slot index (-1 if none)
# Total base = 48 bytes before type-specific data

# Scan for script_id = local_idx as big-endian int32 in objects section
# Check context: PID at offset-44+4 = offset-40 should be a critter PID
target_sid = struct.pack(">i", local_idx)
pos2 = obj_sec_start
found = []
while pos2 < len(data) - 3:
    idx = data.find(target_sid, pos2)
    if idx == -1:
        break
    # Check if PID at offset idx-40 is a critter
    pid_off = idx - 40
    if pid_off >= obj_sec_start:
        pid_val = struct.unpack_from(">I", data, pid_off)[0]
        if (pid_val >> 24) == 0x01:  # critter type
            proto_id = pid_val & 0xFFFFFF
            found.append((idx, pid_off, proto_id, pid_val))
            print(f"  Potential match at {idx}: PID={pid_val:#010x} proto_id={proto_id}")
    pos2 = idx + 1

if not found:
    print("  No matches found with critter PID 40 bytes before script_id field")

# Also try with script_id at different offsets in object header
# Some objects might have a different layout; try offset 44 from object base
print("\nRaw 4-byte search for sid value in objects section:")
sid_bytes = struct.pack(">i", local_idx)
pos3 = obj_sec_start
count = 0
while pos3 < len(data) - 3:
    idx = data.find(sid_bytes, pos3)
    if idx == -1 or count > 20:
        break
    print(f"  Found at offset {idx} (aligned: {idx%4==0})")
    # Show surrounding context
    ctx_start = max(obj_sec_start, idx-8)
    ctx = data[ctx_start:idx+8]
    print(f"  Context: {ctx.hex()}")
    count += 1
    pos3 = idx + 1
