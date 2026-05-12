"""Look up pro_crit.msg names for a list of proto IDs."""
import struct, zlib, re
from pathlib import Path

PIDS = [42, 225, 6, 188, 250, 128, 78, 63, 284, 65, 180, 151, 70, 65, 178, 61, 62, 149, 150, 277]

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

# Build lookup: msg_id -> name
lookup = {}
for line in text.split("\n"):
    m = re.match(r'\{(\d+)\}\{[^}]*\}\{([^}]*)\}', line.strip())
    if m:
        lookup[int(m.group(1))] = m.group(2)

print(f"{'PID':>5}  {'msg_id':>7}  name")
print("-" * 40)
for pid in sorted(set(PIDS)):
    msg_id = pid * 100
    name = lookup.get(msg_id, "???")
    print(f"{pid:>5}  {msg_id:>7}  {name}")
