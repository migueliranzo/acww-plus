"""Prints the autoload list of a ROM's ARM9 binary (decompressing the NitroSDK backward-LZ image first).
usage: py -3.12 tools/analysis/arm9_autoloads.py ROM"""
import struct
import sys


def blz_decompress(data):
    """NitroSDK MIi_UncompressBackward: footer = u32 (buffer top << 0 | header len << 24), u32 extra size."""
    enc_len_hdr, extra = struct.unpack_from("<II", data, len(data) - 8)
    hdr_len = enc_len_hdr >> 24
    enc_len = enc_len_hdr & 0xFFFFFF
    out = bytearray(data) + bytearray(extra)
    src = len(data) - hdr_len
    dst = len(out)
    end = len(data) - enc_len
    while src > end:
        src -= 1
        flags = data[src]
        for _ in range(8):
            if src <= end:
                break
            if flags & 0x80:
                src -= 2
                b = (data[src + 1] << 8) | data[src]
                n = (b >> 12) + 3
                disp = (b & 0xFFF) + 3
                for _ in range(n):
                    dst -= 1
                    out[dst] = out[dst + disp]
            else:
                src -= 1
                dst -= 1
                out[dst] = data[src]
            flags <<= 1
    return bytes(out)


def main():
    rom = open(sys.argv[1], "rb").read()
    off, entry, ram, size = struct.unpack_from("<4I", rom, 0x20)
    arm9 = rom[off:off + size]
    ls, le, ast, bss0, bss1, comp_end = struct.unpack_from("<6I", arm9, 0xB48)
    if comp_end:
        arm9 = arm9[:comp_end - ram] if False else blz_decompress(arm9[:comp_end - ram]) + arm9[comp_end - ram:]
    print(f"list 0x{ls:08X}..0x{le:08X} data from 0x{ast:08X}, compressed end 0x{comp_end:08X}, size 0x{len(arm9):X}")
    src = ast
    for i in range((le - ls) // 12):
        dest, sz, bss = struct.unpack_from("<3I", arm9, ls - ram + 12 * i)
        print(f"  {i}: dest 0x{dest:08X} size 0x{sz:X} bss 0x{bss:X}  src 0x{src:08X}..0x{src + sz:08X}")
        src += sz


if __name__ == "__main__":
    main()
