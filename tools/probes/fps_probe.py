"""Game frames per 300 vblanks in town (frame counter 0x021F7E10), standing still. usage: fps_probe.py vanilla|plus 0|1 port"""
import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
which, furn, port = sys.argv[1], sys.argv[2] == "1", int(sys.argv[3])
grid = {}
if furn:
    items = [0x3000, 0x300C, 0x3015, 0x301C, 0x3013, 0x303B, 0x3074, 0x3004, 0x3008, 0x3018]
    spots = [(7, 9), (13, 9), (13, 11), (9, 8), (12, 7), (13, 7), (14, 7), (5, 8), (4, 8), (3, 8)]
    for (lx, lz), it in zip(spots, items):
        grid[0xC354 + 9 * 512 + (lz * 16 + lx) * 2] = it
save = prepare_save(PROJECT / "build" / f"probe_fps_{which}{int(furn)}.sav", grid=grid)
with Emu(ROM_VANILLA if which == "vanilla" else ROM_PLUS, str(save), port=port, tag=f"fps_{which}{int(furn)}") as e:
    e.boot_to_town(); e.wait(400)
    out = []
    for k in range(3):
        a = e.u32(0x021F7E10); e.wait(300); b = e.u32(0x021F7E10)
        out.append(b - a)
    print(which, "furniture" if furn else "empty", "game frames per 300 vblanks:", out)
