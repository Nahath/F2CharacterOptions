"""Search all .msg files in master.dat/rpu.dat for 'sajag'."""
import struct, zlib, re
from pathlib import Path

def list_all_dat(dat_path):
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
        results[name.replace("\\", "/").lower()] = (comp, unc, packed, offset)
    return results

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

for dat_name in ("master.dat",):
    dat_path = game / dat_name
    print(f"\nSearching {dat_name}...")
    files = list_all_dat(dat_path)
    msg_files = [f for f in files if f.endswith(".msg")]
    print(f"  {len(msg_files)} .msg files")
    for fname in sorted(msg_files)[:5]:
        print(f"    {fname}")
    print("  ...")
    for fname in sorted(msg_files)[-5:]:
        print(f"    {fname}")

    with open(dat_path, "rb") as fh:
        for fname, (comp, unc, packed, offset) in sorted(files.items()):
            if not fname.endswith(".msg"):
                continue
            fh.seek(offset)
            raw = fh.read(packed)
            try:
                data = zlib.decompress(raw) if comp else raw
                text = data.decode("latin-1")
            except Exception:
                continue
            if "sajag" in text.lower():
                print(f"\n  FOUND in {fname}:")
                for line in text.split("\n"):
                    if "sajag" in line.lower():
                        print(f"    {line.strip()}")
