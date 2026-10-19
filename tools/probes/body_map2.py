import sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
from PIL import Image
v = sys.argv[1]
save = prepare_save(PROJECT / "build" / f"probe_body{v}.sav")
with Emu(str(PROJECT / "build" / f"acww_plus_dbg{v}.nds"), str(save), port=19890 + int(v), tag=f"bodymap{v}") as e:
    e.boot_to_town(); e.wait(300)
    p = e.shot("town")
im = Image.open(p).convert("RGB")
im.crop((115, 260, 165, 320)).resize((250, 300), Image.NEAREST).save(str(PROJECT / "build" / "screenshots" / f"bodymap{v}_zoom.png"))
