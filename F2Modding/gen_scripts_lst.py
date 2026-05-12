import os

with open("C:/Games/F2Modding/scripts_lst_base.txt", "rb") as f:
    base = f.read()

# Normalise to \r\n, strip trailing whitespace, then append new entries
lines = base.replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("latin-1").splitlines()
lines = [l for l in lines if l.strip()]  # drop blank lines

lines.append("DYNMK2.int      ; Super Dynamite item script                  # local_vars=0")
lines.append("DYNMK2ON.int    ; Active Super Dynamite item script            # local_vars=0")

content = "\r\n".join(lines) + "\r\n"

os.makedirs("C:/Games/F2Modding/Fallout 2/data/scripts", exist_ok=True)
with open("C:/Games/F2Modding/Fallout 2/data/scripts/scripts.lst", "wb") as f:
    f.write(content.encode("latin-1"))

print(f"Written scripts.lst with {len(lines)} entries")
print(f"Entry 1304: {lines[1303]}")
print(f"Entry 1305: {lines[1304]}")
