import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
from PIL import Image
v = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x71
girl = len(sys.argv) > 2
pokes = {0x1DE5: bytes([v])}
if girl: pokes[0x2296] = b"\x01"
save = prepare_save(PROJECT / "build" / "probe_look.sav", pokes=pokes)
with Emu(ROM_PLUS, str(save), port=19894 + (1 if girl else 0), tag="look") as e:
    e.boot_to_town(); e.wait(300)
    p = e.shot(f"town_{v:02x}{'_girl' if girl else ''}")
im = Image.open(p).convert("RGB")
im.crop((115, 260, 165, 320)).resize((250, 300), Image.NEAREST).save(str(p).replace(".png", "_zoom.png"))
print(p)
