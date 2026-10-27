#!/usr/bin/env python3
"""Fruit stacks in the pockets screen: open it with 3 apples in slot 0 and screenshot it (layout, item name).
usage: fruit_eat_probe.py"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from harness import *  # noqa

pokes = {0xC + 0x1B22 + 2 * i: 0xFFF1 for i in range(15)}
pokes[0xC + 0x1B22] = 0x156F          # 3 apples
pokes[0xC + 0x1B22 + 2] = 0x1392
save = prepare_save(BUILD / "probe_fruit_eat.sav", pokes=pokes)
with Emu(ROM_PLUS, str(save), tag="fruit_eat") as e:
    e.boot_to_town()
    e.wait(200)
    e.press("y", hold=6, after=120)
    e.shot("open")
    e.press("a", hold=6, after=60)      # Grab / Drop on Ground / Never Mind
    e.press("a", hold=6, after=60)      # Grab
    e.shot("grabbed")
    for k in range(3):
        e.press("up", hold=6, after=40)
        e.shot(f"up{k}")
    e.press("a", hold=6, after=90)
    e.shot("eat")
    rec = SAVE_RAM_BASE + 0xC
    e.wait(300)
    e.shot("after")
    e.press("b", hold=6, after=60)
    e.press("y", hold=6, after=200)
    e.shot("closed")
    print("  slots after close:", [hex(x) for x in struct.unpack("<15H", e.read(rec + 0x1B22, 30))])
