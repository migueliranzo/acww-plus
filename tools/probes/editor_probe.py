"""Exploration: from town, open the hub and try to reach the design editor. Steps like a:60 tap:x,y shot:name"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
save = prepare_save(PROJECT / "build" / "probe_editor.sav")
with Emu(ROM_PLUS, str(save), port=19897, tag="ed") as e:
    e.boot_to_town(); e.wait(200)
    for s in sys.argv[1:]:
        k, _, n = s.partition(":")
        if k == "shot": e.shot(n); continue
        if k == "wait": e.wait(int(n)); continue
        if k == "tap":
            x, y = map(int, n.split(",")); e.tap(x, y, hold=4, after=60); continue
        e.press(k, hold=4, after=int(n or 40))
    e.shot("zz_end")
