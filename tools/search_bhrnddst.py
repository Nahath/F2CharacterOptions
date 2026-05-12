"""Deep scan of bhrnddst.int for the exact crash string."""
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

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

for dat_name in ["master.dat"]:
    dat_path = game_root / dat_name
    data = read_dat(dat_path, "scripts\\bhrnddst.int")
    if data is None:
        print(f"bhrnddst.int not found in {dat_name}")
        continue

    print(f"\nbhrnddst.int from {dat_name}: {len(data)} bytes")

    # Search for any 'a swarm' substring (case-insensitive)
    low = data.lower()
    idx = 0
    count = 0
    while True:
        found = low.find(b"a swarm", idx)
        if found < 0:
            break
        print(f"  'a swarm' at offset {found}: {data[max(0,found-10):found+80]!r}")
        idx = found + 1
        count += 1
    if count == 0:
        print("  'a swarm' NOT found")

    # Look for ALL strings >= 20 chars (longer strings, more likely to be the crash string)
    long_strings = re.findall(rb"[\x20-\x7E]{20,}", data)
    print(f"\nLong strings (>=20 chars): {len(long_strings)}")
    for s in long_strings:
        dec = s.decode("latin-1")
        if any(kw in dec.lower() for kw in ["swarm", "spore plant", "mantis infest", "of mantis"]):
            print(f"  MATCH: {dec!r}")
        elif not dec.startswith("$") and not "Encounter" in dec and not "Caravan" in dec:
            print(f"  {dec!r}")
