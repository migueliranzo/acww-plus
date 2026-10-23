import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
from PIL import Image
save = prepare_save(PROJECT / "build" / "probe_body.sav")
with Emu(ROM_PLUS, str(save), port=19897, tag="bodymap") as e:
    e.boot_to_town(); e.wait(300)
    p = e.shot("town")
    walk_until(e, "down", 2, 57.5, max_frames=120)
    e.press("left", hold=6, after=30)
    p2 = e.shot("side")
for q in (p, p2):
    im = Image.open(q).convert("RGB")
    im.crop((105, 240, 185, 330)).resize((320, 360), Image.NEAREST).save(str(q).replace(".png", "_zoom.png"))
