"""Minimal Nitro TEX0 reader (BMD0 / BTX0): lists textures + palettes and renders them to PNG.
usage: py -3.12 -I nitro_tex.py FILE.nsbmd OUTDIR [palette_override.bin]"""
import struct, sys
from pathlib import Path
from PIL import Image


def lz10(d):
    if d[:4] == b"LZ77":
        d = d[4:]
    if d[0] != 0x10:
        return d
    size = d[1] | d[2] << 8 | d[3] << 16
    out = bytearray(); i = 4
    while len(out) < size:
        fl = d[i]; i += 1
        for b in range(8):
            if len(out) >= size: break
            if fl & (0x80 >> b):
                x = d[i] << 8 | d[i + 1]; i += 2
                n = (x >> 12) + 3; disp = (x & 0xFFF) + 1
                for _ in range(n): out.append(out[-disp])
            else:
                out.append(d[i]); i += 1
    return bytes(out)


def dict_names(d, off):
    """Nitro dictionary: returns [(name, data_bytes_offset)]"""
    # 0: u8 0, u8 count, u16 dict size; 4: tree block (u16 header size, u16 tree block size, ...)
    count = d[off + 1]
    info = off + struct.unpack_from("<H", d, off + 6)[0]   # tree section size counted from the dict start
    entry_size = struct.unpack_from("<H", d, info)[0]
    entries = info + 4
    names_off = entries + count * entry_size
    out = []
    for i in range(count):
        name = d[names_off + 16 * i: names_off + 16 * (i + 1)].split(b"\0")[0].decode("latin1")
        out.append((name, entries + entry_size * i))
    return out


def find_tex0(d):
    magic = d[:4]
    nblk = struct.unpack_from("<H", d, 0xE)[0]
    for i in range(nblk):
        o = struct.unpack_from("<I", d, 0x10 + 4 * i)[0]
        if d[o:o + 4] == b"TEX0":
            return o
    return None


def read_tex0(d):
    t = find_tex0(d)
    tex_data_size = struct.unpack_from("<H", d, t + 0x0C)[0] << 3
    tex_dict = t + struct.unpack_from("<H", d, t + 0x0E)[0]
    tex_data = t + struct.unpack_from("<I", d, t + 0x14)[0]
    pl_size = struct.unpack_from("<H", d, t + 0x30)[0] << 3
    pl_dict = t + struct.unpack_from("<I", d, t + 0x34)[0]
    pl_data = t + struct.unpack_from("<I", d, t + 0x38)[0]
    texs = []
    for name, p in dict_names(d, tex_dict):
        param = struct.unpack_from("<I", d, p)[0]
        off = (param & 0xFFFF) << 3
        w = 8 << ((param >> 20) & 7)
        h = 8 << ((param >> 23) & 7)
        fmt = (param >> 26) & 7
        col0 = (param >> 29) & 1
        texs.append(dict(name=name, off=tex_data + off, w=w, h=h, fmt=fmt, col0=col0))
    pals = []
    for name, p in dict_names(d, pl_dict):
        off = (struct.unpack_from("<H", d, p)[0]) << 3
        pals.append(dict(name=name, off=pl_data + off))
    return texs, pals, pl_data, pl_size


def rgb555(c):
    return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)


def render(d, tex, pal_bytes, pal_off):
    w, h, fmt = tex["w"], tex["h"], tex["fmt"]
    def col(i):
        c = struct.unpack_from("<H", pal_bytes, pal_off + 2 * i)[0]
        return rgb555(c)
    im = Image.new("RGBA", (w, h))
    px = im.load()
    o = tex["off"]
    for y in range(h):
        for x in range(w):
            n = y * w + x
            a = 255
            if fmt == 3:   # 16 colours
                v = (d[o + n // 2] >> (4 * (n & 1))) & 0xF
                if v == 0 and tex["col0"]: a = 0
                c = col(v)
            elif fmt == 2: # 4 colours
                v = (d[o + n // 4] >> (2 * (n & 3))) & 3
                if v == 0 and tex["col0"]: a = 0
                c = col(v)
            elif fmt == 4: # 256 colours
                v = d[o + n]
                if v == 0 and tex["col0"]: a = 0
                c = col(v)
            elif fmt == 1: # A3I5
                v = d[o + n]; c = col(v & 31); a = ((v >> 5) * 36)
            elif fmt == 6: # A5I3
                v = d[o + n]; c = col(v & 7); a = ((v >> 3) * 8)
            else:
                c = (255, 0, 255)
            px[x, y] = (*c, a)
    return im


if __name__ == "__main__":
    d = lz10(open(sys.argv[1], "rb").read())
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    texs, pals, pl_data, pl_size = read_tex0(d)
    print("textures:", [(t["name"], t["w"], t["h"], t["fmt"]) for t in texs])
    print("palettes:", [(p["name"], hex(p["off"] - pl_data)) for p in pals], "palette bytes", hex(pl_size))
    for p in pals:
        cols = [struct.unpack_from("<H", d, p["off"] + 2 * i)[0] for i in range(16)]
        print(" ", p["name"], [rgb555(c) for c in cols])
    for t in texs:
        for p in pals:
            im = render(d, t, d, p["off"])
            im.resize((t["w"] * 4, t["h"] * 4), Image.NEAREST).save(out / f"{t['name']}__{p['name']}.png")
