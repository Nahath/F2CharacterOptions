"""
Fix Super Dynamite protos (534, 535) to match vanilla dynamite (51, 52),
correcting Weight, Cost, and tail bytes.
FrmID is left alone (custom icon is handled separately).
"""
import struct, os, shutil

PROTO_DIR = r"C:\Games\F2Modding\Fallout 2\data\proto\items"

def read_be32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]

def write_be32(data, offset, value):
    ba = bytearray(data)
    struct.pack_into('>I', ba, offset, value)
    return bytes(ba)

def patch_proto(filename, patches):
    path = os.path.join(PROTO_DIR, filename)
    with open(path, 'rb') as f:
        data = f.read()

    print(f"\n{filename}:")
    for offset, old_val, new_val, label in patches:
        actual = read_be32(data, offset)
        if actual != old_val:
            print(f"  WARNING: {label} at offset {offset}: expected {old_val:#010x}, found {actual:#010x} — skipping")
            continue
        data = write_be32(data, offset, new_val)
        print(f"  {label}: {old_val} -> {new_val}")

    with open(path, 'wb') as f:
        f.write(data)
    print(f"  Saved.")

# Proto 534 (inert Super Dynamite)
# Vanilla inert (51): Weight=5, Cost=500, tail[0]=0x0700002e
patch_proto("00000534.pro", [
    (44, 10,         5,   "Weight"),
    (48, 1500,       500, "Cost"),
    (52, 0x0700016f, 0x0700002e, "Tail[0] (misc data)"),
])

# Proto 535 (active Super Dynamite)
# Vanilla active (52): Weight=4, Cost=650, tail[0]=0x0700002f
patch_proto("00000535.pro", [
    (44, 10,         4,   "Weight"),
    (48, 1500,       650, "Cost"),
    (52, 0x0700002e, 0x0700002f, "Tail[0] (misc data)"),
])

print("\nDone.")
