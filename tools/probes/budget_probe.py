"""Town budget probe: VRAM bank control, frame-VRAM texture manager state, 3D polygon / vertex counts per frame,
and game frame pacing. usage: budget_probe.py vanilla|plus [furniture]"""
import struct, sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
which = sys.argv[1]
furn = len(sys.argv) > 2
rom = ROM_VANILLA if which == "vanilla" else ROM_PLUS
grid = {}
if furn:
    items = [0x3000, 0x300C, 0x3015, 0x301C, 0x3013, 0x303B, 0x3074, 0x3004, 0x3008, 0x3018]
    spots = [(7, 9), (13, 9), (13, 11), (9, 8), (12, 7), (13, 7), (14, 7), (5, 8), (4, 8), (3, 8)]
    for (lx, lz), it in zip(spots, items):
        grid[0xC354 + 9 * 512 + (lz * 16 + lx) * 2] = it
save = prepare_save(PROJECT / "build" / f"probe_budget_{which}.sav", grid=grid)
names = "ABCDEFG?HI"
with Emu(rom, str(save), port=19897 if which == "plus" else 19896, tag=f"budget_{which}{'_f' if furn else ''}") as e:
    e.boot_to_town(); e.wait(300)
    vc = []
    for i, n in enumerate(names):
        if n == "?": continue
        v = e.c.cmd("read_io", cpu=9, addr=0x04000240 + i, width=8)["value"]
        vc.append(f"{n}:{v:#04x}(mst{v & 7},ofs{(v >> 3) & 3},{'on' if v & 0x80 else 'off'})")
    print("VRAMCNT", " ".join(vc))
    print("DISPCNT A", hex(e.c.cmd("read_io", cpu=9, addr=0x04000000, width=32)["value"]),
          "B", hex(e.c.cmd("read_io", cpu=9, addr=0x04001000, width=32)["value"]))
    print("frame tex mgr words 0x021F2CA0..", [hex(e.u32(0x021F2CA0 + 4 * i)) for i in range(16)])
    polys, verts = [], []
    fc = []
    for i in range(40):
        e.wait(1)
        r = e.c.cmd("read_io", cpu=9, addr=0x04000604, width=32)["value"]
        polys.append(r & 0xFFF); verts.append((r >> 16) & 0x1FFF)
        fc.append(e.u32(0x021F7E10))
    print("RAM_COUNT polys min/max", min(polys), max(polys), "verts min/max", min(verts), max(verts))
    print("game frame counter over 40 vblanks:", fc[-1] - fc[0])
    # walk a bit to stress (more acres in view)
    walk_until(e, "down", 2, 62.0, max_frames=300)
    p2 = []
    for i in range(30):
        e.wait(1)
        r = e.c.cmd("read_io", cpu=9, addr=0x04000604, width=32)["value"]
        p2.append((r & 0xFFF, (r >> 16) & 0x1FFF))
    print("after walking south: polys max", max(p[0] for p in p2), "verts max", max(p[1] for p in p2))
    e.shot("budget")
