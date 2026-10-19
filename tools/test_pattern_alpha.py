#!/usr/bin/env python3
"""Pattern transparency (ndsref): player 0's designs get index-0 pixels and are laid on the ground south of the
door; vanilla draws index 0 black, AC:WW+ shows the ground through."""
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa
from PIL import Image

GRID = 0xC354
def tile(acre, lx, lz):
    return GRID + acre * 512 + (lz * 16 + lx) * 2

# left 16 columns transparent (index 0), right 16 columns colour 3, plus a colour-5 frame row
row = bytes([0x00] * 8 + [0x33] * 8)
pix = bytearray(row * 32)
for x in range(16):
    pix[x] = 0x55          # top row colour 5
pokes = {}
for k in range(8):
    pokes[0xC + 0x228 * k] = bytes(pix)
grid = {tile(9, 10 + i % 3, 9 + i // 3): 0xA7 + i for i in range(6)}


def run(rom, tag, port):
    save = prepare_save(PROJECT / "build" / f"test_alpha_{tag}.sav", pokes=pokes, grid=grid)
    with Emu(rom, str(save), port=port, tag=f"alpha_{tag}") as e:
        e.boot_to_town()
        e.wait(300)
        p = e.shot("designs")
    im = Image.open(p).convert("RGB")
    im.crop((60, 250, 230, 384)).resize((340, 268), Image.NEAREST).save(str(p).replace(".png", "_zoom.png"))
    return p


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "plus"
    print(run(ROM_VANILLA if which == "vanilla" else ROM_PLUS, which, 19896 if which == "vanilla" else 19895))
