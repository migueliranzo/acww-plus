"""Yard screenshot (10 furniture pieces) for a given ROM. usage: yard_cmp.py rom tag port"""
import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
from PIL import Image
rom, tag, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
items = [0x3000, 0x300C, 0x3015, 0x301C, 0x3013, 0x303B, 0x3074, 0x3004, 0x3008, 0x3018]
spots = [(7, 9), (13, 9), (13, 11), (9, 8), (12, 7), (13, 7), (14, 7), (5, 8), (4, 8), (3, 8)]
grid = {0xC354 + 9 * 512 + (lz * 16 + lx) * 2: it for (lx, lz), it in zip(spots, items)}
save = prepare_save(PROJECT / "build" / f"probe_yard_{tag}.sav", grid=grid)
with Emu(rom, str(save), port=port, tag=f"yard_{tag}") as e:
    e.boot_to_town(); e.wait(400)
    walk_until(e, "down", 2, 58.0, max_frames=200)
    e.wait(60)
    p = e.shot("yard")
im = Image.open(p).convert("RGB")
im.crop((0, 192, 256, 384)).resize((512, 384), Image.NEAREST).save(str(PROJECT / "build" / "screenshots" / f"yardcmp_{tag}.png"))
