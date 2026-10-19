import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
from PIL import Image
save = prepare_save(PROJECT / "build" / "probe_girl.sav", pokes={0x2296: b"\x01"})
with Emu(str(PROJECT / "build" / "acww_plus_dbg3.nds"), str(save), port=19893, tag="girl") as e:
    e.boot_to_town(); e.wait(300)
    p = e.shot("town")
im = Image.open(p).convert("RGB")
im.crop((115, 260, 165, 320)).resize((250, 300), Image.NEAREST).save(str(PROJECT / "build" / "screenshots" / "girl_zoom.png"))
