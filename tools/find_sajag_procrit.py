"""Find Sajag proto ID via pro_crit.msg."""
import struct, zlib, re, sys
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

game = Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Fallout 2")

for path in (r"text\english\game\pro_crit.msg",):
    for src, dat in (("master.dat", game / "master.dat"), ("rpu.dat", game / "mods" / "rpu.dat")):
        data = read_dat(dat, path)
        if data:
            text = data.decode("latin-1", errors="replace")
            print(f"Found {path} in {src} ({len(data)} bytes)")
            for line in text.split("\n"):
                if "sajag" in line.lower():
                    print(f"  {line.strip()}")
            # Also dump entries around proto 52-60 (msg IDs 5200*100 to 6000*100)
            # Actually text_id in proto, name_msg_id = text_id * 100
            # For proto 52, text_id=5200 -> msg_id = 520000
            print("  Entries for proto 52-60 (text_ids 5200-6000, msg_ids 520000-600000):")
            for line in text.split("\n"):
                m = re.match(r'\{(\d+)\}', line)
                if m:
                    mid = int(m.group(1))
                    if 520000 <= mid <= 600100:
                        print(f"    {line.strip()}")
            break
