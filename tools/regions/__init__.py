"""
The game regions AC:WW+ builds for. The sources and tools/patches.py are written with EU (ADMP) addresses; another
region maps them through its address table, tools/regions/<table>.py, which tools/remap_region.py generates.

  eu   Animal Crossing: Wild World (Europe), ADMP, 5 languages
  us   Animal Crossing: Wild World (USA), ADME rev 0, English only
  us1  Animal Crossing: Wild World (USA), ADME rev 1 (a rebuilt binary: every address moved again; 148 overlays,
       numbered like the EU's)

The US vanilla files are extractions of the owner's own dumps (dsd rom extract), outside git, shared by every
checkout: vanilla/ADME/extracted (rev 0) and vanilla/ADME1/extracted (rev 1) in the main checkout. make_vanilla()
creates them from the clean ROMs.
"""
import os
import re
import struct
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import acww_config  # noqa: E402

MAIN_CHECKOUT = acww_config.main_checkout()
DSD_EXE = Path(acww_config.get("DSD_EXE"))

REGIONS = {
    "eu": {
        "code": "ADMP", "title": "Animal Crossing: Wild World (Europe)",
        "vanilla": Path(acww_config.get("VANILLA_EXTRACTED")),
        "clean_rom": Path(acww_config.get("CLEAN_ROM")),
        "clean_crc32": 0xC677970C,
        "save_magic": 0xC5,                   # byte 0 of a save block (func_0209e500)
        "langs": ["ENG", "FRN", "GER", "ITA", "SPN"],
        "ftr_info": "ftr_info/ENG",           # the English furniture info (the test reads it)
        "suffix": "",                         # patch names: acww_plus_<version><suffix>.bps
        "table": None,                        # tools/regions/<table>.py (None: the EU addresses themselves)
    },
    "us": {
        "code": "ADME", "title": "Animal Crossing: Wild World (USA)",
        "vanilla": Path(acww_config.get("US_VANILLA_EXTRACTED") or MAIN_CHECKOUT / "vanilla" / "ADME" / "extracted"),
        "clean_rom": Path(acww_config.get("US_ROM")),
        "rom_key": "US_ROM",
        "clean_crc32": 0xF24508AA,
        "save_magic": 0x8A,                   # the same check, US 0x0209DEFC
        "langs": ["ENG"],
        "ftr_info": "ftr_info",
        "suffix": "_us",
        "table": "adme",
    },
    "us1": {
        "code": "ADME", "title": "Animal Crossing: Wild World (USA) (Rev 1)",
        "vanilla": Path(acww_config.get("US1_VANILLA_EXTRACTED") or MAIN_CHECKOUT / "vanilla" / "ADME1" / "extracted"),
        "clean_rom": Path(acww_config.get("US1_ROM")),
        "rom_key": "US1_ROM",
        "clean_crc32": 0x7E62F586,
        "save_magic": 0x8A,
        "langs": ["ENG"],
        "ftr_info": "ftr_info",
        "suffix": "_us_rev1",
        "table": "adme_rev1",
    },
}


def overlay_map(region):
    """{EU overlay id: this region's id} (None: no counterpart). From content matching (tools/remap_region.py):
    the US has no EU ov018 and ov056 (ov018 is a 0x120-byte stub; ov056 0xE0), so ids shift by 1 after ov017 and
    by 2 after ov056."""
    if region in ("eu", "us1"):      # US rev 1 keeps the EU's overlay ids (checked by content, remap_region.py)
        return {n: n for n in range(148)}
    m = {}
    for n in range(148):
        if n <= 17:
            m[n] = n
        elif n in (18, 56):
            m[n] = None
        elif n <= 55:
            m[n] = n - 1
        else:
            m[n] = n - 2
    return m


def make_vanilla(region):
    """Extracts the clean ROM of the region if its vanilla files are missing."""
    info = REGIONS[region]
    if (info["vanilla"] / "config.yaml").exists():
        return
    if not info["clean_rom"].exists():
        raise FileNotFoundError(f"{info['title']}: no vanilla files at {info['vanilla']} and no clean ROM at "
                                f"{info['clean_rom']} (set ACWW_{info['rom_key']})")
    import zlib
    crc = zlib.crc32(info["clean_rom"].read_bytes())
    if crc != info["clean_crc32"]:
        raise RuntimeError(f"{info['clean_rom']}: CRC32 {crc:08X}, expected {info['clean_crc32']:08X}")
    info["vanilla"].parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(DSD_EXE), "rom", "extract", "--rom", str(info["clean_rom"]), "--output-path",
                    str(info["vanilla"])], check=True)


def _yaml_int(text, key):
    return int(re.search(key + r":\s*(\d+)", text).group(1))


def overlay_table(region):
    """{id: (base, size, bss_size)} from the vanilla overlays.yaml."""
    v = REGIONS[region]["vanilla"]
    out = {}
    for blk in (v / "arm9_overlays" / "overlays.yaml").read_text().split("- id:")[1:]:
        n = int(blk.split()[0])
        out[n] = (_yaml_int(blk, "base_address"), (v / "arm9_overlays" / f"ov{n:03d}.bin").stat().st_size,
                  _yaml_int(blk, "bss_size"))
    return out


def vanilla_modules(region):
    """{name: (base, bytes, bss_size)}: arm9, autoload2, itcm, dtcm, bss (the main BSS, no bytes), ovNNN."""
    v = REGIONS[region]["vanilla"] / "arm9"
    mods = {"arm9": (0x02000000, (v / "arm9.bin").read_bytes(), 0)}
    for name, f in (("autoload2", "unk_autoload_2"), ("itcm", "itcm"), ("dtcm", "dtcm")):
        y = (v / f"{f}.yaml").read_text()
        mods[name] = (_yaml_int(y, "base_address"), (v / f"{f}.bin").read_bytes(), 0)
    y = (v / "unk_autoload_3.yaml").read_text()
    mods["bss"] = (_yaml_int(y, "base_address"), b"", _yaml_int(y, "bss_size"))
    ov = REGIONS[region]["vanilla"] / "arm9_overlays"
    for n, (base, size, bss) in overlay_table(region).items():
        mods[f"ov{n:03d}"] = (base, (ov / f"ov{n:03d}.bin").read_bytes(), bss)
    return mods


def build_constants(region):
    """The addresses tools/build_rom.py needs, read from the region's own tables."""
    v = REGIONS[region]["vanilla"] / "arm9"
    ovs = overlay_table(region)
    heap_code_base = max(b + s + z for b, s, z in ovs.values())          # vanilla SDK main arena lo
    y = (v / "unk_autoload_2.yaml").read_text()
    a2_base = _yaml_int(y, "base_address")
    a2 = (v / "unk_autoload_2.bin").read_bytes()
    hits = [a2_base + i for i in range(0, len(a2) - 3, 4) if struct.unpack_from("<I", a2, i)[0] == heap_code_base]
    if len(hits) != 1:
        raise RuntimeError(f"{region}: arena lo literal 0x{heap_code_base:08X} found {len(hits)} times in autoload 2")
    return {
        "HEAP_CODE_BASE": heap_code_base,
        "ARENA_LO_LITERAL": hits[0],
        "AUTOLOAD2_BASE": a2_base,
        "OV003_BASE_ADDR": ovs[overlay_map(region)[3]][0],
    }


def build_dir(root, region):
    """Where a region's build goes: build/ for the EU (as before regions), build/<region>/ otherwise."""
    return Path(root) / "build" if region == "eu" else Path(root) / "build" / region


ADDR_RE = re.compile(r"0x0[12][0-9A-Fa-f]{6}\b")


def strip_c_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def translate_c(text, table, name):
    """C source with every EU address literal in table replaced by the region's (comments too, so they stay
    true). Raises if the code (comments aside) has a literal the table lacks."""
    missing = sorted({m.group(0) for m in ADDR_RE.finditer(strip_c_comments(text)) if int(m.group(0), 16) not in table})
    if missing:
        raise RuntimeError(f"{name}: no address for {', '.join(missing)} in the region table: rerun "
                           f"tools/remap_region.py")
    return ADDR_RE.sub(lambda m: f"0x{table[int(m.group(0), 16)]:08X}" if int(m.group(0), 16) in table
                       else m.group(0), text)


def address_table(region):
    """(ADDR, PATCH_EXPECT) of the region: EU address -> the region's address. The EU's maps to itself."""
    if region == "eu":
        return None, None
    import importlib
    mod = importlib.import_module(f"regions.{REGIONS[region]['table']}")
    return mod.ADDR, mod.PATCH_EXPECT
