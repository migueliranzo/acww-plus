"""Town with 10 furniture pieces: game frames and cache counters over 300 vblanks. usage: perf_probe.py [port]"""
import struct, sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
port = int(sys.argv[1]) if len(sys.argv) > 1 else 19884
items = [0x3000, 0x300C, 0x3015, 0x301C, 0x3013, 0x303B, 0x3074, 0x3004, 0x3008, 0x3018]
spots = [(7, 9), (13, 9), (13, 11), (9, 8), (12, 7), (13, 7), (14, 7), (5, 8), (4, 8), (3, 8)]
grid = {0xC354 + 9 * 512 + (lz * 16 + lx) * 2: it for (lx, lz), it in zip(spots, items)}
save = prepare_save(PROJECT / "build" / "probe_perf.sav", grid=grid)
with Emu(ROM_PLUS, str(save), port=port, tag="perf") as e:
    e.boot_to_town(); e.wait(400)
    sym = payload_symbols()["g_ftr_perf"]
    for k in range(3):
        a = e.u32(0x021F7E10); pa = struct.unpack("<4I", e.read(sym, 16))
        e.wait(300)
        b = e.u32(0x021F7E10); pb = struct.unpack("<4I", e.read(sym, 16))
        print(f"  game frames/300vbl={b - a}  loads={pb[0]-pa[0]} evictions={pb[1]-pa[1]}")
    e.shot("perf")
