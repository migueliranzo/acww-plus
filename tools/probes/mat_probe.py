"""After the yard loads, dump bound material state of each cached furniture model."""
import struct, sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
items = [0x301C, 0x3013, 0x300C]
spots = [(9, 8), (12, 7), (13, 9)]
grid = {0xC354 + 9 * 512 + (lz * 16 + lx) * 2: it for (lx, lz), it in zip(spots, items)}
save = prepare_save(PROJECT / "build" / "probe_mat.sav", grid=grid)
with Emu(ROM_PLUS, str(save), port=19888, tag="mat") as e:
    e.boot_to_town(); e.wait(300)
    sc = e.u32(payload_symbols()["s_cache"])
    for i in range(12):
        b = e.read(sc + 72 + i * 200, 24)
        mid, ar, dist, off, sz, tick, fseq, arc, mdl = struct.unpack("<HBBHHIIII", b)
        if mid == 0xFFFF: continue
        m = mdl
        ofs_mat = e.u32(m + 8); resmat = m + ofs_mat
        dict_ = resmat + 4
        count = e.u8(dict_ + 1)
        info = dict_ + e.u16(dict_ + 6)
        esz = e.u16(info)
        for k in range(count):
            md = resmat + e.u32(info + 4 + k * esz)
            raw = e.read(md, 0x2C)
            tag, size, da, se, pa, pm, tip, tipm, pb, flag, ow, oh, mw, mh = struct.unpack("<HHIIIIIIHHHHii", raw)
            w = 8 << ((tip >> 20) & 7); h = 8 << ((tip >> 23) & 7)
            print(f"model {mid:#x} mat{k}: bound tip={tip:#010x} ({w}x{h}) flag={flag:#06x} orig={ow}x{oh} magW={mw/4096:.3f} magH={mh/4096:.3f}")
