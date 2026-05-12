"""Dump all strings from bhrnddst.int and search for 'mantis' / 'swarm' / 'spore'."""
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

for dat_name in ["master.dat", "mods/rpu.dat"]:
    dat_path = game_root / dat_name
    if not dat_path.exists():
        continue
    data = read_dat(dat_path, "scripts\\bhrnddst.int")
    if data is None:
        print(f"{dat_name}: bhrnddst.int not found")
        continue

    print(f"\n=== bhrnddst.int from {dat_name} ({len(data)} bytes) ===")

    # Extract all null-terminated or length-prefixed strings (look for ASCII runs >= 5 chars)
    strings = re.findall(rb"[\x20-\x7E]{5,}", data)
    print("All ASCII strings (>=5 chars):")
    for s in strings:
        print(f"  {s.decode('latin-1')!r}")

    # Look for 'A swarm' (full phrase, case-insensitive)
    low = data.lower()
    for kw in [b"a swarm", b"mantis infesting", b"spore plants", b"dvmv_mantis", b"arro_spore"]:
        idx = low.find(kw)
        if idx >= 0:
            print(f"\n  FOUND {kw!r} at offset {idx}:")
            print(f"  Context: {data[max(0,idx-40):idx+100]!r}")
