#!/usr/bin/env python3
"""Skin tone on the upstairs phone (ndsref). Boots to the wake-up screen, calls the Service Center, picks
Skin tone -> Darker x2 -> Lighter x1 -> This is fine, and checks the tan + the saved base."""
import json
import sys
sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *  # noqa

REC0 = 0x021DAA04
BASE_WORD = 0x021EF9C2


def tan(e):
    return (e.u8(REC0 + 0x223D) >> 3) & 7


def main():
    save = prepare_save(PROJECT / "build" / "test_skin.sav")
    res = []
    with Emu(ROM_PLUS, str(save), tag="skin") as e:
        e.run_to(600); e.tap(128, 48); e.run_to(3000)
        scn = json.load(open(LOAD_SAVE_SCN))
        for act in scn["actions"][:12]:
            if act["kind"] == "key":
                e.press(act["key"], hold=3)
            else:
                e.wait(int(act["frames"]))
        e.wait(100)
        for after in (60, 60, 60, 80):     # tutorial text (timings from the phone probe)
            e.press("a", hold=4, after=after)
        e.press("up", hold=4, after=40)    # cursor to the phone
        e.press("a", hold=4, after=150)    # call
        e.press("a", hold=4, after=120)    # "This is the Service Center..."
        e.press("a", hold=4, after=120)    # "What can we do for you today?" -> menu
        e.shot("01_menu")
        t0 = tan(e); w0 = e.u16(BASE_WORD)
        print(f"  start: tan={t0} base word={w0:#06x}")
        e.press("down", hold=4, after=20)
        e.press("down", hold=4, after=20)
        e.press("a", hold=4, after=120)    # Skin tone. -> question
        e.shot("02_question")
        seq = []
        for name, downs in (("darker", 1), ("darker", 1), ("darker", 1), ("lighter", 0)):
            e.press("a", hold=4, after=100)  # question text -> choices
            for _ in range(downs):
                e.press("down", hold=4, after=30)
            e.press("a", hold=4, after=120)  # choice -> "There we go! How does that look?"
            e.shot(f"03_{name}_{len(seq)}")
            seq.append(tan(e))
            e.press("a", hold=4, after=150)  # -> back to the question
        print(f"  tan after darker x3, lighter: {seq}  base word={e.u16(BASE_WORD):#06x}")
        res.append(("darker x3 / lighter steps the tan", seq == [t0 + 1, t0 + 2, t0 + 3, t0 + 2]))
        res.append(("base saved in the pad word (player 0 nibble = tone + 1)", (e.u16(BASE_WORD) & 0xF) == seq[-1] + 1))
        e.press("a", hold=4, after=100)
        e.press("down", hold=4, after=30)
        e.press("down", hold=4, after=30)
        e.press("a", hold=4, after=150)    # This is fine. -> "Is there anything else?"
        e.shot("04_anything_else")
    print()
    for n, ok in res:
        print(f"  RESULT {n}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
