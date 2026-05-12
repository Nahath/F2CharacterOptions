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

game_root = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
data = None
for dat_name in ["master.dat", "critter.dat"]:
    dat = game_root / dat_name
    if not dat.exists():
        print(f"{dat_name} not found")
        continue
    data = read_dat(dat, "maps\\arvillag.map")
    if data:
        print(f"Found arvillag.map in {dat_name}: {len(data)} bytes")
        break
    else:
        print(f"arvillag.map not in {dat_name}")

if data is None:
    rpu = game_root / "mods" / "rpu.dat"
    if rpu.exists():
        data = read_dat(rpu, "maps\\arvillag.map")
        if data:
            print(f"Found arvillag.map in rpu.dat: {len(data)} bytes")

if data:
    low = data.lower()
    for kw in [b"swarm", b"mantis", b"spore"]:
        idx = low.find(kw)
        if idx >= 0:
            print(f"  Found {kw!r} at offset {idx}: {data[max(0,idx-20):idx+80]!r}")
        else:
            print(f"  {kw!r} not found")

    # Also dump all script-like strings (printable ASCII runs >= 8 chars)
    import re
    strings = re.findall(rb"[ -~]{8,}", data)
    print("\nAll strings >= 8 chars in arvillag.map:")
    for s in strings:
        print(f"  {s.decode('latin-1')!r}")
