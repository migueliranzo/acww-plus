"""Lamp switching as a player sees it: exotic lamp two squares south of the door, at 12:00 and at 21:00.
Screenshots before and after A, the lamp's material emission, and how many pixels changed.
usage: py -3.12 tools/probes/lamp_visual.py [day|night|both]"""
import struct
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa
from PIL import Image, ImageChops
import test_furniture as tf


def run(when):
    pokes = {0x15FB4: struct.pack("<i", 9 * 60)} if when == "night" else {}
    save = prepare_save(PROJECT / "build" / f"probe_lamp_{when}.sav", edits=dict(bells=50000),
                        grid={tf.tile_off(9, 11, 9): 0x301C}, pokes=pokes)
    with Emu(ROM_PLUS, str(save), tag=f"lampv_{when}") as e:
        e.boot_to_town()
        e.wait(300)
        tf.walk_until(e, "down", 2, 58.0, max_frames=300)
        e.wait(30)
        before = e.shot("before")
        em0 = tf.model_emis(e).get(7)
        e.press("a", hold=6, after=90)
        after = e.shot("after_a")
        em1 = tf.model_emis(e).get(7)
        diff = ImageChops.difference(Image.open(before), Image.open(after)).convert("L")
        changed = sum(1 for v in diff.getdata() if v > 24)
        print(f"  [{when}] hour={e.u32(0x021DA9A4)} emission {em0:#06x} -> {em1:#06x}, pixels changed: {changed}")


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "both"
    for when in (("day", "night") if w == "both" else (w,)):
        run(when)
