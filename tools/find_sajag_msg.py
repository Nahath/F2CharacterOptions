"""Find Sajag in critter.msg to get the correct proto ID."""
import struct, zlib, re
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

# critter.msg is in master.dat at text\english\game\critter.msg
msg = read_dat(game / "master.dat", r"text\english\game\critter.msg")
if msg is None:
    # try rpu.dat
    msg = read_dat(game / "mods" / "rpu.dat", r"text\english\game\critter.msg")

if msg is None:
    print("critter.msg not found!")
else:
    text = msg.decode("latin-1")
    # Search for "sajag" case-insensitive
    matches = re.findall(r'\{(\d+)\}\{[^}]*\}\{[^}]*sajag[^}]*\}', text, re.IGNORECASE)
    print("critter.msg entries mentioning 'sajag':")
    for m in matches:
        msg_id = int(m)
        # proto_id = msg_id // 100
        proto_id = msg_id // 100
        print(f"  msg_id={msg_id}  proto_id={proto_id}")

    # Also show full lines
    for line in text.split("\n"):
        if "sajag" in line.lower():
            print(f"  line: {line.strip()}")
