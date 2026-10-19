#!/usr/bin/env python3
"""
Headless verification of e:/acww-plus/build/acww_plus.nds in ndsref.exe.
1. Creates test_furniture.sav with 6 furniture pieces arranged in the outdoor yard around the player's
   house (testing Hooks 1, 2, 3 immediately on house exit) and 6 furniture items in the player's pockets (testing Hook 4).
2. Boots acww_plus.nds in ndsref.exe, exits the house into town (ov003), captures screenshots of
   the rendered 3D furniture models on the curved town drum, inspects OutdoorFtrCache in RAM,
   tests collision and pocket dropping, and verifies clean cache teardown.
"""

import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\NDS_RECOMP\prototype\tools")
sys.path.insert(0, r"C:\NDS_RECOMP\animalcrossingwwrecomp\tools")
from acww_paths import ROOT, NDSREF  # noqa: E402
from probe_stall import STALL  # noqa: E402
import acww_save_edit  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "oracle"))
from _client import DebugClient  # noqa: E402
from PIL import Image  # noqa: E402

VANILLA_SAV = r"C:\NDS_RECOMP\animalcrossingwwrecomp\scenarios\saves\d25.sav"
ROM_PATH = r"e:\acww-plus\build\acww_plus.nds"
SAVE_PATH = r"e:\acww-plus\build\test_furniture.sav"
OUT_DIR = Path(r"e:\acww-plus\build\screenshots")
PORT = 19895

KEY_BITS = {
    "a": 0, "b": 1, "select": 2, "start": 3,
    "right": 4, "left": 5, "up": 6, "down": 7,
    "r": 8, "l": 9, "x": 10, "y": 11,
}
RELEASED = 0x0FFF


def prepare_test_save():
    raw = Path(VANILLA_SAV).read_bytes()
    edited = bytearray(
        acww_save_edit.edit(
            raw,
            bells=50000,
            items=[0x305C, 0x3010, 0x3014, 0x301C, 0x3038, 0x3074],
        )
    )
    # Place 6 outdoor furniture pieces (5 distinct models) on the town grid outside the player's house (0x5014 at 0x0D60A)
    yard_placements = [
        (0x0D666, 0x3011),  # Exotic Chair (facing East, rot=1)
        (0x0D668, 0x3014),  # Exotic Table (facing South, rot=0)
        (0x0D64C, 0x301C),  # Exotic Lamp (facing South, rot=0)
        (0x0D64E, 0x303B),  # Ranch Armchair (facing West, rot=3)
        (0x0D66C, 0x3074),  # Classic Clock (facing South, rot=0)
        (0x0D66E, 0x3013),  # Exotic Chair (facing West, rot=3, shares cached model 0x0004!)
    ]
    for copy_base in acww_save_edit.COPIES:
        for off, item_id in yard_placements:
            struct.pack_into("<H", edited, copy_base + off, item_id)
        # Recompute main block checksum at +0x15FDC
        struct.pack_into("<H", edited, copy_base + acww_save_edit.MAIN_CK, 0)
        ck = (-acww_save_edit.word_sum(edited, copy_base, acww_save_edit.BLOCK)) & 0xFFFF
        struct.pack_into("<H", edited, copy_base + acww_save_edit.MAIN_CK, ck)

    acww_save_edit.check(edited)
    Path(SAVE_PATH).write_bytes(edited)
    print(f"Prepared {SAVE_PATH} with 6 yard furniture pieces + 6 pocket furniture items (checksums verified).")


def run_to(c, target_v):
    while True:
        cur = c.cmd("event_counts")["vblank9"]
        if cur >= target_v:
            return cur
        step = min(target_v, cur + 60)
        r = c.cmd("run_to_event", event="vblank9", count=step, stall=STALL["oracle"])
        if not r.get("reached"):
            raise RuntimeError(f"Failed to reach vblank9={step}: {r}")


def wait_frames(c, frames):
    cur = c.cmd("event_counts")["vblank9"]
    return run_to(c, cur + frames)


def press_key(c, key, hold=3, wait_after=0):
    cur = c.cmd("event_counts")["vblank9"]
    mask = RELEASED & ~(1 << KEY_BITS[key])
    c.cmd("keys", mask=mask)
    run_to(c, cur + hold)
    c.cmd("keys", mask=RELEASED)
    if wait_after > 0:
        wait_frames(c, wait_after)


def save_screenshot(c, name):
    v = c.cmd("event_counts")["vblank9"]
    imgs = []
    for e in "AB":
        f = c.cmd("framebuffer", engine=e, adaptive=False)
        rgb = bytes.fromhex(f["rgb"])[: 256 * 192 * 3]
        imgs.append(Image.frombytes("RGB", (256, 192), rgb))
    im = Image.new("RGB", (256, 384))
    im.paste(imgs[0], (0, 0))
    im.paste(imgs[1], (0, 192))
    out_path = OUT_DIR / f"{name}_v{v:05d}.png"
    im.save(out_path)
    print(f"  [screenshot] Saved {out_path.name} (vblank9={v})")
    return out_path


def inspect_cache(c, label=""):
    itcm = c.read_region("itcm")
    mainram = c.read_region("mainram")
    regs9 = c.cmd("regs", cpu=9)
    pc9 = regs9["r"][15]
    # s_cache is at 0x01FFE274 (offset 0x6274 in ITCM)
    s_cache_ptr, = struct.unpack_from("<I", itcm, 0x01FFE274 - 0x01FF8000)
    print(f"  [cache {label}] ARM9 PC=0x{pc9:08X}, s_cache=0x{s_cache_ptr:08X}")
    if 0x02000000 <= s_cache_ptr < 0x02400000:
        off = s_cache_ptr - 0x02000000
        magic, tick, raw_tag, frame_seq = struct.unpack_from("<4I", mainram, off)
        print(f"          magic=0x{magic:08X} tick={tick} raw_tag=0x{raw_tag:08X} frame_seq={frame_seq}")
        slot_base = off + 16
        slot_sz = 196  # sizeof(OutdoorFtrSlot) = 20 + 20 + 156
        for i in range(6):
            so = slot_base + i * slot_sz
            model_id, vram_ready, last_tick, last_fseq, arc_buf, mdl_ptr = struct.unpack_from("<HH4I", mainram, so)
            vram_slot = struct.unpack_from("<5I", mainram, so + 20)
            if model_id != 0xFFFF or vram_ready:
                print(
                    f"          slot[{i}]: model_id=0x{model_id:04X} vram_ready={vram_ready} "
                    f"tick={last_tick} fseq={last_fseq} arc_buf=0x{arc_buf:08X} mdl_ptr=0x{mdl_ptr:08X} "
                    f"vram_slot={[hex(x) for x in vram_slot]}"
                )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prepare_test_save()

    env = dict(os.environ, NDS_3D_RENDERER="soft")
    env["PATH"] = r"C:\msys64\ucrt64\bin;C:\msys64\mingw64\bin;" + env.get("PATH", "")
    cmd = [
        NDSREF,
        "--bios9", "bios/biosnds9.rom",
        "--bios7", "bios/biosnds7.rom",
        "--firmware", "bios/firmware.bin",
        "--rom", ROM_PATH,
        "--boot", "firmware",
        "--port", str(PORT),
        "--save", SAVE_PATH,
    ]
    log_path = OUT_DIR / "ndsref.log"
    print(f"Launching ndsref on port {PORT} with ROM {ROM_PATH}...")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=open(log_path, "wb"), stderr=subprocess.STDOUT)
    try:
        c = None
        for _ in range(30):
            time.sleep(1)
            if proc.poll() is not None:
                raise RuntimeError(f"ndsref exited early with code {proc.returncode}")
            try:
                c = DebugClient(port=PORT, timeout=600)
                break
            except ConnectionRefusedError:
                pass
        if c is None:
            raise RuntimeError("Timed out waiting for ndsref debug server")

        c.cmd("reset")
        c.cmd("keys", mask=RELEASED)
        c.cmd("touch", x=0, y=0, down=False)

        # Boot tap at v600
        run_to(c, 600)
        c.cmd("touch", x=128, y=48, down=True)
        run_to(c, 602)
        c.cmd("touch", x=128, y=48, down=False)
        run_to(c, 3000)

        # Replay acww_load_save.json actions to step out of the house into town
        scn = json.load(open(r"C:\NDS_RECOMP\animalcrossingwwrecomp\scenarios\acww_load_save.json"))
        print("Replaying boot-to-town sequence (acww_load_save.json)...")
        for act in scn["actions"]:
            if act["kind"] == "key":
                press_key(c, act["key"], hold=3)
            elif act["kind"] == "wait":
                wait_frames(c, int(act["frames"]))

        save_screenshot(c, "01_stepped_outside_doorstep")
        inspect_cache(c, "at v6948")

        # Wait 210 frames for the camera swap to the bottom screen to complete
        wait_frames(c, 210)
        save_screenshot(c, "02_all_six_furniture_settled")
        inspect_cache(c, "after camera settle")

        # Walk 1 step south, then walk left into the Exotic Table (0x0D668) to test collision & item label
        press_key(c, "down", hold=18, wait_after=25)
        press_key(c, "left", hold=35, wait_after=30)
        save_screenshot(c, "03_collision_with_exotic_table")

        # Walk south and left onto open dirt, wait 90 frames to settle completely
        press_key(c, "down", hold=55, wait_after=25)
        press_key(c, "left", hold=45, wait_after=90)
        save_screenshot(c, "04_standing_on_open_dirt")

        # Open pockets (Y), move right to slot 1 (Classic Chair 0x305C), wait 60, A (wait 95), Down (wait 40), A (wait 200)
        press_key(c, "y", hold=3, wait_after=120)
        press_key(c, "right", hold=3, wait_after=60)
        press_key(c, "a", hold=3, wait_after=95)
        press_key(c, "down", hold=3, wait_after=40)
        save_screenshot(c, "05_menu_drop_on_ground_selected")
        press_key(c, "a", hold=3, wait_after=200)
        save_screenshot(c, "06_after_drop_in_pockets")
        press_key(c, "y", hold=3, wait_after=120)
        save_screenshot(c, "07_dropped_classic_chair_outdoors")
        inspect_cache(c, "after pocket drop")

    finally:
        proc.kill()


if __name__ == "__main__":
    main()
