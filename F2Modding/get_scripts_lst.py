import struct, zlib

dat_path = "C:/Games/F2Modding/Fallout 2/master.dat"

with open(dat_path, "rb") as f:
    f.seek(-8, 2)
    tree_size, data_size = struct.unpack("<II", f.read(8))
    total_size = f.seek(0, 2)
    tree_offset = total_size - tree_size - 8
    f.seek(tree_offset)
    num_files = struct.unpack("<I", f.read(4))[0]
    for _ in range(num_files):
        name_len = struct.unpack("<I", f.read(4))[0]
        name = f.read(name_len).decode("latin-1")
        comp, real_size, packed_size, offset = struct.unpack("<BIII", f.read(13))
        if "scripts.lst" in name.lower() and "scripts\\" in name.lower():
            pos = f.tell()
            f.seek(offset)
            raw = f.read(packed_size)
            if comp == 1:
                raw = zlib.decompress(raw)
            lines = raw.decode("latin-1").splitlines()
            print(f"scripts.lst: {len(lines)} entries (last script ID = {len(lines)})")
            print("Last 5 entries:")
            for i, line in enumerate(lines[-5:], len(lines)-4):
                print(f"  {i}: {line.strip()}")
            f.seek(pos)
