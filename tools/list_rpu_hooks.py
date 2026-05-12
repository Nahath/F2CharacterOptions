"""List all hs_*.int hook scripts in rpu.dat to see which hooks sfall 4.4.8 supports."""
import struct, zlib
from pathlib import Path

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")
for dat_name in ("mods/rpu.dat", "master.dat"):
    dat_path = game / dat_name
    with open(dat_path, "rb") as fh:
        fh.seek(-8, 2)
        tree_size, dat_size = struct.unpack("<II", fh.read(8))
        fh.seek(dat_size - tree_size - 8)
        tree = fh.read(tree_size)
    pos = 4
    hooks = []
    while pos < len(tree):
        nl = struct.unpack_from("<I", tree, pos)[0]; pos += 4
        name = tree[pos:pos+nl].decode("latin-1"); pos += nl
        pos += 1 + 12
        n = name.replace("\\", "/").lower()
        if "/hs_" in n and n.endswith(".int"):
            hooks.append(n.split("/")[-1])
    if hooks:
        print(f"{dat_name}: {sorted(set(hooks))}")
