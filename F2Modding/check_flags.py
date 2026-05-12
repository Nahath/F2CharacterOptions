import struct, zlib

base = "C:/Games/F2Modding/Fallout 2/"

def extract_item_proto(dat_path, pid):
    target = f"proto\\items\\{pid:08d}.pro"
    with open(dat_path, "rb") as f:
        f.seek(-8, 2)
        ts, _ = struct.unpack("<II", f.read(8))
        tot = f.seek(0, 2)
        f.seek(tot - ts - 8)
        n = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            nl = struct.unpack("<I", f.read(4))[0]
            name = f.read(nl).decode("latin-1")
            comp, rs, ps, off = struct.unpack("<BIII", f.read(13))
            if name.lower().replace("/","\\") == target.lower():
                pos = f.tell(); f.seek(off)
                raw = f.read(ps)
                if comp == 1: raw = zlib.decompress(raw)
                f.seek(pos); return raw, name
    return None, None

for pid, label in [(51, "Vanilla Dynamite"), (206, "Vanilla Active Dynamite")]:
    data, name = extract_item_proto(base + "master.dat", pid)
    if data:
        fid    = struct.unpack(">I", data[8:12])[0]
        flags  = struct.unpack(">I", data[20:24])[0]
        flags2 = struct.unpack(">I", data[24:28])[0]
        sid    = struct.unpack(">i", data[28:32])[0]
        itype  = struct.unpack(">I", data[32:36])[0]
        print(f"PID {pid} ({label}): size={len(data)}")
        print(f"  found as: {name}")
        print(f"  ground FID: 0x{fid:08X}")
        print(f"  flags:      0x{flags:08X}")
        print(f"  flags2:     0x{flags2:08X}")
        print(f"  script_id:  {sid}")
        print(f"  item_type:  {itype}")
        print(f"  raw bytes:  {data.hex()}")

print()
for pid, label, path in [
    (534, "Super Dynamite",        base + "data/proto/items/00000534.pro"),
    (535, "Active Super Dynamite", base + "data/proto/items/00000535.pro"),
]:
    with open(path, "rb") as f: data = f.read()
    fid    = struct.unpack(">I", data[8:12])[0]
    flags  = struct.unpack(">I", data[20:24])[0]
    flags2 = struct.unpack(">I", data[24:28])[0]
    sid    = struct.unpack(">i", data[28:32])[0]
    itype  = struct.unpack(">I", data[32:36])[0]
    print(f"PID {pid} ({label}): size={len(data)}")
    print(f"  ground FID: 0x{fid:08X}")
    print(f"  flags:      0x{flags:08X}")
    print(f"  flags2:     0x{flags2:08X}")
    print(f"  script_id:  {sid}")
    print(f"  item_type:  {itype}")
    print(f"  raw bytes:  {data.hex()}")
