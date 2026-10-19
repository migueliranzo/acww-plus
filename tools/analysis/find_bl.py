"""Find Thumb BL/BLX instructions calling TARGET inside [START, END) of a module.
usage: find_bl.py MODULE START END TARGET   (MODULE = arm9 | ovNNN)"""
import struct, sys
V = r"E:\claudeGameDecomp\extracted"
mod, start, end, target = sys.argv[1], *(int(x, 16) for x in sys.argv[2:5])
if mod == "arm9":
    data, base = open(V + r"\arm9\arm9.bin", "rb").read(), 0x02000000
else:
    import re
    y = open(V + r"\arm9_overlays\overlays.yaml").read()
    n = int(mod[2:])
    # find base address of overlay n
    blocks = y.split("- id:")
    for b in blocks[1:]:
        if int(b.split()[0]) == n:
            base = int(re.search(r"base_address:\s*(\d+)", b).group(1))
    data = open(V + rf"\arm9_overlays\{mod}.bin", "rb").read()
for a in range(start, end, 2):
    o = a - base
    hw1, hw2 = struct.unpack_from("<HH", data, o)
    if (hw1 & 0xF800) == 0xF000 and (hw2 & 0xE800) in (0xE800,):
        off = ((hw1 & 0x7FF) << 11) | (hw2 & 0x7FF)
        if off & 0x200000: off -= 0x400000
        dest = a + 4 + (off << 1)
        if (hw2 & 0xF800) == 0xE800: dest &= ~3
        if dest == target or target == 0:
            print(f"0x{a:08X}: {'BLX' if (hw2 & 0xF800) == 0xE800 else 'BL '} -> 0x{dest:08X}  bytes {data[o:o+4].hex()}")
