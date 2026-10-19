#!/usr/bin/env python3
"""
BMG (MESGbmg1) read / modify / write for AC:WW (8-bit text, control codes 0x1A len group k(u16) params...).

Files ship as 'LZ77' + an 0xF7 chunked container (chunks of 0x1000 bytes, each LZ10 compressed or stored).
write() produces the same container with LZ10 chunks, so the game's loader sees the format it always sees.

Text helpers: encode("Hello{2:2:434445}\\nYes.") turns {group:k[:hexparams]} back into a control code.
"""
import re
import struct

# ---------------------------------------------------------------- compression

def lz10_decompress(s):
    assert s[0] == 0x10, hex(s[0])
    size = s[1] | s[2] << 8 | s[3] << 16
    out = bytearray(); pos = 4
    while len(out) < size:
        fl = s[pos]; pos += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if fl & (0x80 >> bit) == 0:
                out.append(s[pos]); pos += 1
            else:
                b0, b1 = s[pos], s[pos + 1]; pos += 2
                ln = (b0 >> 4) + 3; disp = ((b0 & 0xF) << 8 | b1) + 1
                st = len(out) - disp
                for i in range(ln):
                    out.append(out[st + i])
    return bytes(out[:size])


def lz10_compress(data):
    """Greedy LZ10 (BIOS LZ77 type 0x10), window 4096, match 3..18. Displacement >= 2 for VRAM safety."""
    out = bytearray([0x10, len(data) & 0xFF, (len(data) >> 8) & 0xFF, (len(data) >> 16) & 0xFF])
    i = 0
    n = len(data)
    while i < n:
        flag_pos = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_disp = 0, 0
            start = max(0, i - 4096)
            maxlen = min(18, n - i)
            if maxlen >= 3:
                # search backwards for the longest match
                j = i - 2
                while j >= start:
                    if data[j] == data[i]:
                        l = 1
                        while l < maxlen and data[j + l] == data[i + l]:
                            l += 1
                        if l > best_len:
                            best_len, best_disp = l, i - j
                            if l == maxlen:
                                break
                    j -= 1
            if best_len >= 3:
                d = best_disp - 1
                out.append(((best_len - 3) << 4) | (d >> 8))
                out.append(d & 0xFF)
                flags |= 0x80 >> bit
                i += best_len
            else:
                out.append(data[i])
                i += 1
        out[flag_pos] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def chunked_decompress(s):
    assert s[0] == 0xF7
    size = s[1] | s[2] << 8 | s[3] << 16
    n = (size + 0xFFF) // 0x1000
    base = 4 + 2 * n
    out = bytearray(); start = base
    for c in range(n):
        end = base + struct.unpack_from('<H', s, 4 + 2 * c)[0]
        b = s[start:end]
        want = min(size - len(out), 0x1000)
        out += b[4:4 + want] if b[0] == 0 else lz10_decompress(b)
        start = end
    return bytes(out)


def chunked_compress(data):
    n = (len(data) + 0xFFF) // 0x1000
    chunks = [lz10_compress(data[i * 0x1000:(i + 1) * 0x1000]) for i in range(n)]
    hdr = bytearray([0xF7, len(data) & 0xFF, (len(data) >> 8) & 0xFF, (len(data) >> 16) & 0xFF])
    ends = []
    pos = 0
    for c in chunks:
        pos += len(c)
        ends.append(pos)
    for e in ends:
        hdr += struct.pack('<H', e)
    return bytes(hdr) + b''.join(chunks)


def unwrap(f):
    if f[:4] == b'LZ77':
        return chunked_decompress(f[4:]) if f[4] == 0xF7 else lz10_decompress(f[4:])
    return f


def wrap(raw):
    return b'LZ77' + chunked_compress(raw)

# ---------------------------------------------------------------- BMG


class Bmg:
    def __init__(self, path):
        self.path = path
        d = unwrap(open(path, 'rb').read())
        assert d[:8] == b'MESGbmg1'
        self.header = bytearray(d[:0x20])
        self.blocks = []        # (magic, payload) for blocks other than INF1/DAT1, in order
        self.order = []
        at = 0x20
        nblk = struct.unpack_from('<I', d, 0xC)[0]
        inf = dat = None
        for _ in range(nblk):
            magic = d[at:at + 4]
            sz = struct.unpack_from('<I', d, at + 4)[0]
            self.order.append(magic)
            if magic == b'INF1':
                inf = d[at:at + sz]
            elif magic == b'DAT1':
                dat = d[at + 8:at + sz]
            else:
                self.blocks.append((magic, d[at:at + sz]))
            at += sz
        cnt, self.esz = struct.unpack_from('<HH', inf, 8)
        self.inf_extra = inf[12:16]
        self.msgs = []          # [text_bytes, attr_bytes]
        for i in range(cnt):
            e = inf[16 + i * self.esz: 16 + (i + 1) * self.esz]
            st = struct.unpack_from('<I', e, 0)[0]
            p = st
            while dat[p] != 0:
                p += max(1, dat[p + 1]) if dat[p] == 0x1A else 1
            self.msgs.append([bytes(dat[st:p]), bytes(e[4:])])

    def save(self, path=None):
        dat = bytearray(b'\0')  # the originals start DAT1 with a NUL; every message (even empty) has its own NUL
        offs = []
        for text, attr in self.msgs:
            offs.append(len(dat))
            dat += text + b'\0'
        inf = bytearray()
        for (text, attr), off in zip(self.msgs, offs):
            inf += struct.pack('<I', off) + attr
        inf_blk = bytearray(b'INF1') + struct.pack('<I', 0) + struct.pack('<HH', len(self.msgs), self.esz) + \
            self.inf_extra + inf
        while len(inf_blk) % 32:
            inf_blk.append(0)
        struct.pack_into('<I', inf_blk, 4, len(inf_blk))
        dat_blk = bytearray(b'DAT1') + struct.pack('<I', 0) + dat
        while len(dat_blk) % 32:
            dat_blk.append(0)
        struct.pack_into('<I', dat_blk, 4, len(dat_blk))
        body = bytearray()
        others = list(self.blocks)
        for magic in self.order:
            if magic == b'INF1':
                body += inf_blk
            elif magic == b'DAT1':
                body += dat_blk
            else:
                body += others.pop(0)[1]
        raw = bytearray(self.header) + body
        struct.pack_into('<I', raw, 8, len(raw))
        open(path or self.path, 'wb').write(wrap(bytes(raw)))

    def text(self, i):
        return render(self.msgs[i][0])


def render(b):
    out = []; i = 0
    while i < len(b):
        if b[i] == 0x1A:
            ln = max(1, b[i + 1]); g = b[i + 2]; k = b[i + 3] | b[i + 4] << 8
            out.append('{%x:%x%s}' % (g, k, (':' + b[i + 5:i + ln].hex()) if ln > 5 else ''))
            i += ln
        else:
            c = b[i]
            out.append('\\n' if c == 10 else chr(c))
            i += 1
    return ''.join(out)


def encode(s):
    """Inverse of render(): '{g:k[:hex]}' -> control code, '\\n' -> newline, other chars latin-1."""
    out = bytearray()
    for part in re.split(r'(\{[0-9a-f]+:[0-9a-f]+(?::[0-9a-f]*)?\})', s.replace('\\n', '\n')):
        m = re.fullmatch(r'\{([0-9a-f]+):([0-9a-f]+)(?::([0-9a-f]*))?\}', part)
        if m:
            g, k = int(m.group(1), 16), int(m.group(2), 16)
            params = bytes.fromhex(m.group(3) or '')
            out += bytes([0x1A, 5 + len(params), g, k & 0xFF, k >> 8]) + params
        else:
            out += part.encode('latin-1')
    return bytes(out)


if __name__ == '__main__':
    import sys
    b = Bmg(sys.argv[1])
    for i, (t, a) in enumerate(b.msgs):
        print('%3d [%s] %s' % (i, a.hex(), render(t)))
