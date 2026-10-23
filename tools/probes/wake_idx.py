import json, sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
save = prepare_save(PROJECT / "build" / "probe_wake.sav")
with Emu(ROM_PLUS, str(save), port=19897, tag="wake") as e:
    e.run_to(600); e.tap(128, 48); e.run_to(3000)
    scn = json.load(open(LOAD_SAVE_SCN))
    for act in scn["actions"][:12]:
        if act["kind"] == "key": e.press(act["key"], hold=3)
        else: e.wait(int(act["frames"]))
    e.wait(100)
    s = e.u32(0x020CC0C8)
    print("session", hex(s), "+0x68", hex(e.u32(s + 0x68)), "+0x64", hex(e.u32(s + 0x64)), "+0x6c", hex(e.u32(s+0x6c)))
    print("actors", [hex(e.u32(0x021D3F04 + 4*i)) for i in range(4)])
    print("rec0 ident", e.read(0x021DAA04 + 0x2276, 16).hex())
