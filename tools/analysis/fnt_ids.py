"""Lists NitroFS file id -> path of a ROM, or compares two ROMs (every id of the first must keep its path).
usage: py -3.12 tools/analysis/fnt_ids.py ROM [ROM2]"""
import struct
import sys


def file_ids(path):
    d = open(path, "rb").read()
    fnt_off, = struct.unpack_from("<I", d, 0x40)
    out = {}

    def walk(dir_id, prefix):
        sub_off, first_id = struct.unpack_from("<IH", d, fnt_off + (dir_id & 0xFFF) * 8)
        p = fnt_off + sub_off
        fid = first_id
        while True:
            t = d[p]
            p += 1
            if t == 0:
                break
            n = t & 0x7F
            name = d[p:p + n].decode("latin-1")
            p += n
            if t & 0x80:
                sub, = struct.unpack_from("<H", d, p)
                p += 2
                walk(sub, prefix + name + "/")
            else:
                out[fid] = prefix + name
                fid += 1

    walk(0xF000, "/")
    return out


if __name__ == "__main__":
    a = file_ids(sys.argv[1])
    if len(sys.argv) == 2:
        for k in sorted(a):
            print(k, a[k])
    else:
        b = file_ids(sys.argv[2])
        bad = [k for k in a if b.get(k) != a[k]]
        print(f"{len(a)} files in the first ROM, {len(b)} in the second, {len(bad)} ids changed")
        for k in sorted(set(b) - set(a)):
            print(f"  new: {k} {b[k]}")
        for k in bad[:10]:
            print(f"  changed: {k} {a[k]} -> {b.get(k)}")
