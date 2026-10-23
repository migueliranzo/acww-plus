"""CPU headroom: break on VBlankIntrWait (0x0200052E) in town and record (vblank count, VCOUNT) per call.
The game logic frame is 3 vblanks; the first wait of a frame shows when its work ended.
usage: headroom_probe.py vanilla|plus [stress] port"""
import struct, sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from harness import *
which, stress, port = sys.argv[1], sys.argv[2] == "1", int(sys.argv[3])
wname = __import__("os").path.basename(which).replace(".nds", "")
grid = {}
if stress:
    always = open(PROJECT / "build" / "extracted" / "files" / "ftr_info" / "ENG" / "always.bin", "rb").read()
    models = [m for m in range(0x20, 0x6E9) if always[m * 8 + 5] == 0][:24]
    orig = open(VANILLA_SAV, "rb").read()
    for lz in (8, 9, 10, 11, 12, 13):
        for lx in range(3, 16):
            off = 0xC354 + 9 * 512 + (lz * 16 + lx) * 2
            if len(grid) < 24 and (lx, lz) != (11, 8) and struct.unpack_from("<H", orig, off)[0] == 0xFFF1:
                grid[off] = 0x3000 + models[len(grid)] * 4
save = prepare_save(PROJECT / "build" / f"probe_head_{wname}{int(stress)}.sav", grid=grid)
with Emu(ROM_VANILLA if which == "vanilla" else (ROM_PLUS if which == "plus" else which), str(save), port=port, tag=f"head_{wname}{int(stress)}") as e:
    e.boot_to_town(); e.wait(400)
    walk_until(e, "down", 2, 59.0, max_frames=200)
    e.wait(300)
    c0 = e.c.cmd("event_counts"); cyc_start = c0["cyc9"]; v_start = c0["vblank9"]
    halted = 0; n = 0
    while True:
        r = e.run_to_pc(0x01FFA3C0, timeout_frames=5)
        c1 = e.c.cmd("event_counts")
        if c1["vblank9"] - v_start >= 90 or not r.get("reached", True):
            break
        e.c.cmd("run_to_event", event="insn9", count=c1["insn9"] + 3, stall=2000)
        c2 = e.c.cmd("event_counts")
        halted += c2["cyc9"] - c1["cyc9"]; n += 1
    ce = e.c.cmd("event_counts")
    total = ce["cyc9"] - cyc_start
    print(f"{wname} {'stress' if stress else 'plain'}: {ce['vblank9'] - v_start} vblanks, OS_Halt entries {n}, "
          f"halted {halted} of {total} ARM9 cycles = idle {100.0 * halted / max(1, total):.1f}%")
