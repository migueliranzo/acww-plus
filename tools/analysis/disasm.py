"""Disassemble Thumb code from the vanilla EU binaries (read only).
usage: py -3.12 tools/analysis/disasm.py MODULE START LEN   (MODULE = arm9 | ovNNN; START/LEN hex)"""
import re
import sys
import capstone

V = r"E:\claudeGameDecomp\extracted"


def load(mod):
    if mod == "arm9":
        return open(V + r"\arm9\arm9.bin", "rb").read(), 0x02000000
    y = open(V + r"\arm9_overlays\overlays.yaml").read()
    n = int(mod[2:])
    for b in y.split("- id:")[1:]:
        if int(b.split()[0]) == n:
            base = int(re.search(r"base_address:\s*(\d+)", b).group(1))
    return open(V + rf"\arm9_overlays\{mod}.bin", "rb").read(), base


def main():
    mod, start, length = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
    data, base = load(mod)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    o = start - base
    for ins in md.disasm(data[o:o + length], start):
        print(f"{ins.address:08X}: {ins.bytes.hex():10s} {ins.mnemonic} {ins.op_str}")


main()
