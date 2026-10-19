"""Survey VRAM requirements (tex, tex4x4, palette) of every /ftr/*.nsbtx."""
import struct, sys
from pathlib import Path

def lz10(d):
    if d[:4] == b"LZ77":
        d = d[4:]
    if d[0] != 0x10:
        return d
    size = d[1] | d[2] << 8 | d[3] << 16
    out = bytearray(); i = 4
    while len(out) < size:
        flags = d[i]; i += 1
        for b in range(8):
            if len(out) >= size: break
            if flags & (0x80 >> b):
                x = d[i] << 8 | d[i+1]; i += 2
                n = (x >> 12) + 3; disp = (x & 0xFFF) + 1
                for _ in range(n): out.append(out[-disp])
            else:
                out.append(d[i]); i += 1
    return bytes(out)

def tex_sizes(data):
    data = lz10(data)
    assert data[:4] == b'BTX0', data[:4]
    off = struct.unpack_from('<I', data, 0x10)[0]
    t = off
    assert data[t:t+4] == b'TEX0'
    tex = struct.unpack_from('<H', data, t + 0x0C)[0] << 3
    t4 = struct.unpack_from('<H', data, t + 0x1C)[0] << 3
    pl = struct.unpack_from('<H', data, t + 0x30)[0] << 3
    return tex, t4, pl

root = Path(sys.argv[1])
rows = []
for p in sorted(root.glob('[0-6]/*/*.nsbtx')):
    try:
        rows.append((int(p.stem, 16), *tex_sizes(p.read_bytes())))
    except Exception as e:
        errs = globals().setdefault('errs', []); errs.append((p, e))
import statistics
for i, name in ((1, 'tex'), (2, 'tex4x4'), (3, 'pltt')):
    v = sorted(r[i] for r in rows)
    print(name, 'max', hex(v[-1]), 'p50', hex(v[len(v)//2]), 'p90', hex(v[int(len(v)*.9)]), 'p99', hex(v[int(len(v)*.99)]), 'nonzero', sum(1 for x in v if x))
for lim in (0x2000, 0x3000, 0x4000):
    print('fit tex<=%x pltt<=0x80 t4=0:' % lim, sum(1 for r in rows if r[1] <= lim and r[2] == 0 and r[3] <= 0x80), '/', len(rows))
for r in rows:
    if r[0] in (0x17, 0x4, 0x5, 0x7, 0xE, 0x1D):
        print(hex(r[0]), [hex(x) for x in r[1:]])
print('errors', len(globals().get('errs', [])), globals().get('errs', [])[:3])
