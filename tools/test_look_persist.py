#!/usr/bin/env python3
"""Saved look persists (ndsref): a save with a chosen base tone 3 (PostOffice pad nibble = 4), a faded tan 0 and
red shoes boots into town with tan 3 restored by the player_tan_level floor; compared with vanilla skin."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[0]))
from harness import *  # noqa
from PIL import Image

REC0 = 0x021DAA04


def face_rgb(p):
    im = Image.open(p).convert("RGB")
    # skin-coloured pixels of the face (r > g > b, bright red channel) over the whole face area
    px = [c for c in (im.getpixel((x, y)) for x in range(112, 148) for y in range(268, 296))
          if c[0] > 120 and c[0] > c[1] > c[2]]
    return tuple(sum(c[i] for c in px) // max(1, len(px)) for i in range(3))


def main():
    res = []
    shots = {}
    for tag, pokes in (("base", {}), ("tone3", {0x14FCA: b"\x04\x00", 0x1DE5: b"\x01"})):
        save = prepare_save(PROJECT / "build" / f"test_persist_{tag}.sav", pokes=pokes)
        with Emu(ROM_PLUS, str(save), tag=f"persist_{tag}") as e:
            e.boot_to_town()
            e.wait(300)
            shots[tag] = e.shot("town")
            tan = (e.u8(REC0 + 0x223D) >> 3) & 7
            print(f"  [{tag}] tan in town = {tan}, face rgb = {face_rgb(shots[tag])}")
            if tag == "tone3":
                res.append(("faded tan restored to the chosen base tone", tan == 3))
    a, b = face_rgb(shots["base"]), face_rgb(shots["tone3"])
    res.append(("skin visibly darker in town", sum(b) < sum(a) - 30))
    for n, ok in res:
        print(f"  RESULT {n}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
