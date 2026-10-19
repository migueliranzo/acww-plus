"""Exploration: boot to the wake-up screen and try to reach the phone."""
import json, sys; sys.path.insert(0, r"e:\acww-plus\tools")
from harness import *
save = prepare_save(PROJECT / "build" / "probe_phone.sav")
steps = sys.argv[1:]  # e.g. a:60 right:30 shot:name
with Emu(ROM_PLUS, str(save), port=19897, tag="phone") as e:
    e.run_to(600); e.tap(128, 48); e.run_to(3000)
    scn = json.load(open(LOAD_SAVE_SCN))
    for act in scn["actions"][:12]:
        if act["kind"] == "key": e.press(act["key"], hold=3)
        else: e.wait(int(act["frames"]))
    e.wait(100)
    e.shot("00_wake_screen")
    for s in steps:
        k, _, n = s.partition(":")
        if k == "shot": e.shot(n); continue
        if k == "wait": e.wait(int(n)); continue
        if k.startswith("tap"):
            x, y = map(int, n.split(",")); e.tap(x, y, hold=4, after=40); continue
        e.press(k, hold=4, after=int(n or 40))
    e.shot("99_end")
