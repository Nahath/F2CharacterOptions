# Fallout 2 DAT2 Archive Format

Used for `master.dat`, `critter.dat`, and all mod `.dat` files.
All integers are **little-endian**.

## Layout

```
[file data — packed or raw, back to back]
[directory tree]
uint32  tree_size
uint32  dat_size
```

### Directory tree structure

```
uint32  file_count
for each file:
    uint32  name_len
    char[]  name          (latin-1, backslash-separated, NOT null-terminated)
    uint8   compression   (0 = stored, 1 = zlib deflate)
    uint32  uncompressed_size
    uint32  packed_size
    uint32  offset        (byte offset from start of file to this entry's data)
```

### Reading a file

```python
fh.seek(-8, 2)
tree_size, dat_size = struct.unpack("<II", fh.read(8))
fh.seek(dat_size - tree_size - 8)   # jump to start of tree
tree = fh.read(tree_size)
```

## Mod priority

Mods are loaded in `mods_order.txt` order; **the last entry wins** for any
file that appears in multiple archives.  f2mod.dat is last → highest priority.

## Building a DAT2 in Python

See `install.py → build_dat2()` for a reference implementation.  Key points:
- Sort entries before writing to produce a deterministic archive.
- Try zlib compression; only use it if the compressed size is smaller.
- `dat_size` includes the data, the tree, and the 8-byte footer.

## Internal path conventions

- Separator: backslash `\`
- Case: the engine compares case-insensitively on Windows.
- Common top-level folders: `scripts\`, `proto\items\`, `proto\critters\`,
  `art\`, `text\english\game\`
