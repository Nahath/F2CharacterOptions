import struct, zlib

dat_path = "C:/Games/F2Modding/Fallout 2/master.dat"

# Find items.lst and all item protos
targets = []
with open(dat_path, "rb") as f:
    f.seek(-8, 2)
    tree_size, data_size = struct.unpack("<II", f.read(8))
    total_size = f.seek(0, 2)
    tree_offset = total_size - tree_size - 8

    f.seek(tree_offset)
    num_files = struct.unpack("<I", f.read(4))[0]

    index = {}
    for _ in range(num_files):
        name_len = struct.unpack("<I", f.read(4))[0]
        name = f.read(name_len).decode("latin-1")
        comp, real_size, packed_size, offset = struct.unpack("<BIII", f.read(13))
        if "proto\\items\\items.lst" in name.lower() or "proto/items/items.lst" in name.lower():
            index[name] = (comp, real_size, packed_size, offset)
        if "proto\\items\\" in name.lower() or "proto/items/" in name.lower():
            index[name] = (comp, real_size, packed_size, offset)

    # Extract items.lst
    for name, (comp, real_size, packed_size, offset) in index.items():
        if "items.lst" in name.lower():
            f.seek(offset)
            data = f.read(packed_size)
            if comp == 1:
                data = zlib.decompress(data)
            lines = data.decode("latin-1").splitlines()
            print(f"items.lst has {len(lines)} entries")
            # Find dynamite - search around known FID area
            for i, line in enumerate(lines):
                if "dyn" in line.lower():
                    print(f"  Line {i}: {line.strip()}")
            break
