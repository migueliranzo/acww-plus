#!/usr/bin/env python3
"""
Reusable headless test harness for AC:WW+ on ndsref (melonDS oracle).

    from harness import Emu, prepare_save
    with Emu(rom, save) as e:
        e.boot_to_town()            # replays acww_load_save.json (player steps out of the house)
        e.press("down", hold=10)
        e.shot("name")
        e.u32(0x021F2CB0)

Only ndsref is used. It has no write_mem and no savestates, so every test boots from cold (~7000 frames).
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

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
import regions  # noqa: E402

# ACWW_REGION=us: test the US build (tools/build_rom.py --region us). Tests keep EU addresses and read memory at
# A(eu_address), which maps them through the region's table.
REGION = os.environ.get("ACWW_REGION", "eu")
BUILD = regions.build_dir(PROJECT, REGION)             # build/ (EU), build/us/
_ADDR, _ = regions.address_table(REGION)


def A(eu_addr):
    """The running region's address for an EU address (the EU's own address on the EU build)."""
    if _ADDR is None:
        return eu_addr
    if eu_addr not in _ADDR:
        raise KeyError(f"0x{eu_addr:08X} is not in the {REGION} address table (tools/remap_region.py)")
    return _ADDR[eu_addr]


ROM_PLUS = os.environ.get("ACWW_ROM") or str(BUILD / "acww_plus.nds")   # ACWW_ROM: e.g. the release ROM
ROM_VANILLA = str(regions.REGIONS[REGION]["clean_rom"])
EU_SAV = r"C:\NDS_RECOMP\animalcrossingwwrecomp\scenarios\saves\d25.sav"
# The save layout is the same in every region but byte 0 (the game's save magic). Another region tests with the
# d25 save converted: build/<region>/d25_<region>.sav (region_save()).
acww_save_edit.MAGIC = regions.REGIONS[REGION]["save_magic"]
VANILLA_SAV = EU_SAV if REGION == "eu" else str(BUILD / f"d25_{REGION}.sav")
LOAD_SAVE_SCN = r"C:\NDS_RECOMP\animalcrossingwwrecomp\scenarios\acww_load_save.json"
SHOT_DIR = BUILD / "screenshots"
MAP_PATH = BUILD / "payload.map"

KEY_BITS = {
    "a": 0, "b": 1, "select": 2, "start": 3,
    "right": 4, "left": 5, "up": 6, "down": 7,
    "r": 8, "l": 9, "x": 10, "y": 11,
}
RELEASED = 0x0FFF

SAVE_RAM_BASE = A(0x021DA9F8)  # RAM address of save block offset 0


def payload_symbols():
    syms = {}
    if MAP_PATH.exists():
        for line in MAP_PATH.read_text().splitlines():
            addr, name = line.split()
            syms[name] = int(addr, 16)
    return syms


def region_save(src=EU_SAV, out=None):
    """An EU save converted for the running region: save magic in byte 0 of both copies, main checksums fixed.
    Every other byte is the same (the layout is shared). Returns the path (src itself on the EU)."""
    if REGION == "eu":
        return src
    out = Path(out or VANILLA_SAV)
    data = bytearray(Path(src).read_bytes())
    for copy_base in acww_save_edit.COPIES:
        data[copy_base] = acww_save_edit.MAGIC
        struct.pack_into("<H", data, copy_base + acww_save_edit.MAIN_CK, 0)
        ck = (-acww_save_edit.word_sum(data, copy_base, acww_save_edit.BLOCK)) & 0xFFFF
        struct.pack_into("<H", data, copy_base + acww_save_edit.MAIN_CK, ck)
    acww_save_edit.check(data)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return str(out)


if REGION != "eu":
    region_save()


def prepare_save(out_path, edits=None, grid=None, pokes=None, base=VANILLA_SAV):
    """Builds a test save.
    edits: kwargs for acww_save_edit.edit (bells=, items=[...], ...)
    grid / pokes: {save_block_offset: u16} written to both copies (u16 values) before checksumming.
    """
    raw = Path(base).read_bytes()
    data = bytearray(acww_save_edit.edit(raw, **(edits or {}))) if edits else bytearray(raw)
    writes = dict(grid or {})
    writes.update(pokes or {})
    if writes:
        for copy_base in acww_save_edit.COPIES:
            for off, val in writes.items():
                if isinstance(val, (bytes, bytearray)):
                    data[copy_base + off: copy_base + off + len(val)] = val
                else:
                    struct.pack_into("<H", data, copy_base + off, val)
            struct.pack_into("<H", data, copy_base + acww_save_edit.MAIN_CK, 0)
            ck = (-acww_save_edit.word_sum(data, copy_base, acww_save_edit.BLOCK)) & 0xFFFF
            struct.pack_into("<H", data, copy_base + acww_save_edit.MAIN_CK, ck)
    acww_save_edit.check(data)
    Path(out_path).write_bytes(data)
    return out_path


class Emu:
    def __init__(self, rom=ROM_PLUS, save=None, port=19895, tag="run"):
        # ACWW_PORT_OFFSET: run beside another checkout's tests (each run needs its own debug ports)
        port += int(os.environ.get("ACWW_PORT_OFFSET", "0"))
        self.rom, self.save, self.port, self.tag = rom, save, port, tag
        self.proc = None
        self.c = None

    def __enter__(self):
        import socket
        with socket.socket() as s:      # a leftover emulator on the port would answer instead of ours
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", self.port)) == 0:
                raise RuntimeError(f"port {self.port} is taken (a leftover ndsref?); stop it or set ACWW_PORT_OFFSET")
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, NDS_3D_RENDERER="soft")
        env["PATH"] = r"C:\msys64\ucrt64\bin;C:\msys64\mingw64\bin;" + env.get("PATH", "")
        cmd = [NDSREF, "--bios9", "bios/biosnds9.rom", "--bios7", "bios/biosnds7.rom",
               "--firmware", "bios/firmware.bin", "--rom", self.rom, "--boot", "firmware",
               "--port", str(self.port)]
        if self.save:
            cmd += ["--save", self.save]
        log = open(SHOT_DIR / f"ndsref_{self.tag}.log", "wb")
        self.proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(30):
            time.sleep(1)
            if self.proc.poll() is not None:
                raise RuntimeError(f"ndsref exited early ({self.proc.returncode})")
            try:
                self.c = DebugClient(port=self.port, timeout=600)
                break
            except ConnectionRefusedError:
                pass
        if self.c is None:
            raise RuntimeError("ndsref debug server did not come up")
        self.c.cmd("reset")
        self.c.cmd("keys", mask=RELEASED)
        self.c.cmd("touch", x=0, y=0, down=False)
        return self

    def __exit__(self, *a):
        if self.proc:
            self.proc.kill()

    # --- time ---
    def v(self):
        return self.c.cmd("event_counts")["vblank9"]

    def run_to(self, target):
        while True:
            cur = self.v()
            if cur >= target:
                return cur
            step = min(target, cur + 60)
            r = self.c.cmd("run_to_event", event="vblank9", count=step, stall=STALL["oracle"])
            if not r.get("reached"):
                raise RuntimeError(f"failed to reach vblank9={step}: {r}")

    def wait(self, frames):
        return self.run_to(self.v() + frames)

    def run_to_pc(self, pc, timeout_frames=600):
        return self.c.cmd("run_to_pc", pc=pc, cpu=9, timeout=timeout_frames)

    # --- input ---
    def press(self, key, hold=3, after=0):
        keys = key if isinstance(key, (list, tuple)) else [key]
        mask = RELEASED
        for k in keys:
            mask &= ~(1 << KEY_BITS[k])
        self.c.cmd("keys", mask=mask)
        self.wait(hold)
        self.c.cmd("keys", mask=RELEASED)
        if after:
            self.wait(after)

    def tap(self, x, y, hold=2, after=0):
        self.c.cmd("touch", x=x, y=y, down=True)
        self.wait(hold)
        self.c.cmd("touch", x=x, y=y, down=False)
        if after:
            self.wait(after)

    # --- memory ---
    def read(self, addr, n):
        return bytes.fromhex(self.c.cmd("read_mem", cpu=9, addr=addr, len=n)["hex"])

    def u8(self, a):
        return self.read(a, 1)[0]

    def u16(self, a):
        return struct.unpack("<H", self.read(a, 2))[0]

    def u32(self, a):
        return struct.unpack("<I", self.read(a, 4))[0]

    def regs(self):
        return self.c.cmd("regs", cpu=9)

    # --- video ---
    def shot(self, name):
        v = self.v()
        imgs = []
        for eng in "AB":
            f = self.c.cmd("framebuffer", engine=eng, adaptive=False)
            imgs.append(Image.frombytes("RGB", (256, 192), bytes.fromhex(f["rgb"])[: 256 * 192 * 3]))
        im = Image.new("RGB", (256, 384))
        im.paste(imgs[0], (0, 0))
        im.paste(imgs[1], (0, 192))
        p = SHOT_DIR / f"{self.tag}_{name}_v{v:05d}.png"
        im.save(p)
        print(f"  [shot] {p.name}")
        return p

    # --- scripted boot ---
    def boot_to_town(self):
        """Cold boot with the d25-based save; ends with the player standing outside the house (~v6950)."""
        self.run_to(600)
        self.tap(128, 48)
        self.run_to(3000)
        scn = json.load(open(LOAD_SAVE_SCN))
        for act in scn["actions"]:
            if act["kind"] == "key":
                self.press(act["key"], hold=3)
            elif act["kind"] == "wait":
                self.wait(int(act["frames"]))
        return self.v()


def player_actor(e):
    idx = e.u32(e.u32(A(0x020CC0C8)) + 0x68)
    return e.u32(A(0x021D3F04) + 4 * idx) if idx < 4 else 0


def player_pos(e):
    """(x, y, z, angle) of the local player; x/z in fx32 world units (one town unit = 0x2000)."""
    a = player_actor(e)
    x, y, z = struct.unpack("<3i", e.read(a + 0x5C, 12))
    ang = e.u16(a + 0x8E)
    return x, y, z, ang


def player_unit(e):
    x, _, z, _ = player_pos(e)
    return x >> 13, z >> 13


def walk_until(e, key, axis, target, max_frames=600, step=4):
    """Holds key until the player's x (axis 0) or z (axis 2) in units crosses target, or stops moving.
    Returns the final (x, z) in units."""
    keys = key if isinstance(key, (list, tuple)) else [key]
    mask = RELEASED
    for k in keys:
        mask &= ~(1 << KEY_BITS[k])
    start = player_pos(e)
    sign = 1 if target > start[axis] / 8192 else -1
    last = None
    still = 0
    e.c.cmd("keys", mask=mask)
    try:
        for _ in range(0, max_frames, step):
            e.wait(step)
            p = player_pos(e)
            v = p[axis] / 8192
            if (v - target) * sign >= 0:
                break
            if last is not None and abs(v - last) < 0.005:
                still += 1
                if still >= 8:   # blocked
                    break
            else:
                still = 0
            last = v
    finally:
        e.c.cmd("keys", mask=RELEASED)
    e.wait(10)
    p = player_pos(e)
    return p[0] / 8192, p[2] / 8192
