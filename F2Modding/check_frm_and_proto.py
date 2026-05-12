import struct, zlib

base = "C:/Games/F2Modding/Fallout 2/"

# 1. Check FRM file validity (all four relevant FRMs)
frm_files = {
    "dynamit.frm  (vanilla, reference)": base + "data/art/inven/dynamit.frm",
    "dynon.frm    (vanilla active, ref)": base + "data/art/inven/dynon.frm",
    "DYNMK2.frm  (super dynamite)":      base + "data/art/inven/DYNMK2.frm",
    "DYNMK2ON.frm (active super dyn)":   base + "data/art/inven/DYNMK2ON.frm",
}

print("=== FRM file headers ===")
for label, path in frm_files.items():
    try:
        with open(path, "rb") as f:
            data = f.read(40)
        version   = struct.unpack(">I", data[0:4])[0]
        fps       = struct.unpack(">H", data[4:6])[0]
        action_fr = struct.unpack(">H", data[6:8])[0]
        frames    = struct.unpack(">H", data[8:10])[0]
        shift_x   = [struct.unpack(">h", data[10+i*2:12+i*2])[0] for i in range(6)]
        shift_y   = [struct.unpack(">h", data[22+i*2:24+i*2])[0] for i in range(6)]
        import os
        size = os.path.getsize(path)
        print(f"\n  {label}")
        print(f"    size={size}, version={version}, fps={fps}, action_frame={action_fr}, frames_per_dir={frames}")
        print(f"    valid FRM: {'YES' if version == 4 else 'UNKNOWN (version=' + str(version) + ')'}")
    except FileNotFoundError:
        print(f"\n  {label}  --> FILE NOT FOUND")
    except Exception as e:
        print(f"\n  {label}  --> ERROR: {e}")

# 2. Compare proto bytes: our 534 vs vanilla 51, our 535 vs vanilla 206
def extract_proto(dat_path, pid):
    with open(dat_path, "rb") as f:
        f.seek(-8, 2)
        tree_size, _ = struct.unpack("<II", f.read(8))
        total = f.seek(0, 2)
        f.seek(total - tree_size - 8)
        n = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            nlen = struct.unpack("<I", f.read(4))[0]
            name = f.read(nlen).decode("latin-1")
            comp, real_size, packed, offset = struct.unpack("<BIII", f.read(13))
            if name.lower().endswith(f"{pid:08d}.pro"):
                pos = f.tell(); f.seek(offset)
                raw = f.read(packed)
                if comp == 1: raw = zlib.decompress(raw)
                f.seek(pos); return raw
    return None

vanilla_51  = extract_proto(base + "master.dat", 51)
vanilla_206 = extract_proto(base + "master.dat", 206)
with open(base + "data/proto/items/00000534.pro", "rb") as f: our_534 = f.read()
with open(base + "data/proto/items/00000535.pro", "rb") as f: our_535 = f.read()

print("\n\n=== Proto byte comparison (zeroing out PID/msg/inv_fid for apples-to-apples) ===")
def normalize(data):
    # Zero out PID (0-3), msg (4-7), inv_fid (52-55) so we can compare structure
    b = bytearray(data)
    b[0:8] = b'\x00'*8
    if len(b) >= 56: b[52:56] = b'\x00'*4
    return bytes(b)

pairs = [
    ("PID 534 vs vanilla 51",  our_534, vanilla_51),
    ("PID 535 vs vanilla 206", our_535, vanilla_206),
]
for label, ours, ref in pairs:
    n_ours = normalize(ours)
    n_ref  = normalize(ref)
    if n_ours == n_ref:
        print(f"\n  {label}: IDENTICAL structure ✓")
    else:
        print(f"\n  {label}: DIFFERENCES found")
        for i, (a, b) in enumerate(zip(n_ours, n_ref)):
            if a != b:
                print(f"    offset {i}: ours=0x{a:02X}, vanilla=0x{b:02X}")
        if len(n_ours) != len(n_ref):
            print(f"    size: ours={len(ours)}, vanilla={len(ref)}")
