"""
Find Sajag's actual critter proto ID.

The scripts section has a slot with pid_word=0x01000038 (local_idx=56).
The objects section has objects referencing script_id=56 at offsets:
295512, 298256, 328620, 409756.

In the Fallout 2 object header:
  +0:  flags     uint32
  +4:  PID       uint32   <-- critter type (0x01) + proto_id
  +8:  CID       int32
  +12: x         int32
  +16: y         int32
  +20: sx        int32
  +24: sy        int32
  +28: frame_idx uint32
  +32: direction uint32
  +36: FrmID     uint32
  +40: anim_code uint32
  +44: script_id int32    <-- local script slot index (we found =56 here)

So PID is 40 bytes before script_id field.
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

# Offsets where script_id=56 (0x00000038) was found in objects section
script_id_offsets = [295512, 298256, 328620, 409756]

print("Checking PID 40 bytes before each script_id=56 occurrence:")
for sid_off in script_id_offsets:
    pid_off = sid_off - 40
    if pid_off < 0:
        continue
    pid_val = struct.unpack_from(">I", data, pid_off)[0]
    obj_type = (pid_val >> 24) & 0xFF
    proto_id = pid_val & 0xFFFFFF
    flags = struct.unpack_from(">I", data, pid_off - 4)[0]
    print(f"  sid_offset={sid_off}: PID_offset={pid_off}  PID={pid_val:#010x}  type={obj_type}  proto_id={proto_id}  flags={flags:#010x}")
    # Dump 48 bytes from object start (pid_off - 4 = flags field)
    obj_start = pid_off - 4
    raw = data[obj_start:obj_start+52]
    print(f"    Raw bytes: {raw.hex()}")

# Also check: maybe script_id is at a different offset in the object header.
# Try checking 4 bytes AFTER the match for additional context.
print("\nAdditional context at each offset:")
for sid_off in script_id_offsets:
    ctx = data[sid_off-16:sid_off+20]
    print(f"  offset {sid_off}: {ctx.hex()}")
    # Try PID at various offsets back from sid_off
    for back in (40, 36, 32, 28):
        pid_off = sid_off - back
        if pid_off >= 0:
            pid_val = struct.unpack_from(">I", data, pid_off)[0]
            if (pid_val >> 24) == 0x01:
                print(f"    PID candidate {back} bytes back: {pid_val:#010x} proto_id={(pid_val & 0xFFFFFF)}")
