"""
1. Check if RPU's pro_crit.msg has a Sajag-specific entry.
2. Find the Kisbox (Sajag's inventory box) object in kladwtwn.map.
3. Try LIST_ALL scan approach - dump all object PIDs via scan.
"""
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
rpu_path = game / "mods" / "rpu.dat"

# 1. Check RPU pro_crit.msg for Sajag
print("=== RPU pro_crit.msg Sajag search ===")
msg_rpu = read_dat(rpu_path, r"text\english\game\pro_crit.msg")
if msg_rpu:
    text = msg_rpu.decode("latin-1", errors="replace")
    for line in text.split("\n"):
        if "sajag" in line.lower():
            print(f"  {line.strip()}")
    # Find entries near msg_id 5600 (proto 56)
    print("  Entries 5500-5900:")
    for line in text.split("\n"):
        m = re.match(r'\{(\d+)\}', line.strip())
        if m and 5500 <= int(m.group(1)) <= 5900:
            print(f"    {line.strip()}")
else:
    print("  pro_crit.msg not in rpu.dat")

# 2. Look for Kisbox proto ID in item protos (scrname.msg: Kisbox = scripts.lst[317])
print("\n=== Kisbox barter box search ===")
# scripts.lst[317] = Kisbox.int. Let's find the ITEM proto that uses Kisbox script.
# Item protos are in master.dat at proto\items\000000XX.pro
# The item proto with ScriptID=317 (or thereabouts) would be the barter box.
def read_all_items(dat_path):
    results = {}
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1"); pos += nl
        comp = tree[pos]; pos += 1
        unc, packed, offset = struct.unpack_from("<III", tree, pos); pos += 12
        norm = name.replace("\\", "/").lower()
        if "proto/items/" in norm and norm.endswith(".pro"):
            fname = norm.split("/")[-1]
            try:
                pid = int(fname.replace(".pro", ""))
            except ValueError:
                continue
            with open(dat_path, "rb") as fh:
                fh.seek(offset)
                raw = fh.read(packed)
            results[pid] = zlib.decompress(raw) if comp else raw
    return results

items = read_all_items(game / "master.dat")
print(f"  Item protos in master.dat: {len(items)}")
# Item proto ScriptID is at offset 28 (int32 BE)
for pid, data in sorted(items.items()):
    if len(data) > 31:
        sid = struct.unpack_from(">i", data, 28)[0]
        if sid == 317:
            print(f"  proto {pid}: ScriptID={sid} (Kisbox!)")

# 3. Search kladwtwn.map for the Kisbox item
print("\n=== Searching kladwtwn.map for items with known proto IDs ===")
data = read_dat(rpu_path, "maps\\kladwtwn.map")
# Scan for item PIDs (high byte = 0x00) that match scenery/misc/container types
# Containers/boxes in Fallout 2 are SCENERY type (0x02) or MISC type (0x05)
# Let's look at what proto IDs show up for non-critter objects
from collections import Counter
item_pids = Counter()
for i in range(0, len(data) - 3, 4):
    b = data[i:i+4]
    high = b[0]
    if high in (0x00, 0x02, 0x03, 0x05) and b[1] == 0x00 and b[2] == 0x00:
        proto_id = b[3]
        if 1 <= proto_id <= 200:
            item_pids[(high, proto_id)] += 1

print("  Sample non-critter PIDs (type, proto_id, count):")
for (t, pid), cnt in sorted(item_pids.items())[:30]:
    print(f"    type=0x{t:02x} proto={pid} count={cnt}")
