"""Dump pro_crit.msg content and find Sajag range."""
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
data = read_dat(game / "master.dat", r"text\english\game\pro_crit.msg")
text = data.decode("latin-1", errors="replace")

lines = [l.strip() for l in text.split("\n") if l.strip() and l.strip().startswith("{")]
print(f"Total entries: {len(lines)}")
print("First 10:")
for l in lines[:10]:
    print(f"  {l}")
print("Last 10:")
for l in lines[-10:]:
    print(f"  {l}")
print()

# Find Sajag
for l in lines:
    if "sajag" in l.lower():
        print(f"Sajag line: {l}")
        m = re.match(r'\{(\d+)\}', l)
        if m:
            mid = int(m.group(1))
            print(f"  msg_id={mid}  proto_id if text_id=mid//100: {mid//100}  proto_id if text_id=mid: {mid}")
