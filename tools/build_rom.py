#!/usr/bin/env python3
"""
Builds the AC:WW+ ROM (build/acww_plus.nds; the US build: build/us/acww_plus.nds).

usage: py -3.12 tools/build_rom.py [--release] [--region eu|us]

1. Compiles every src/*.c as one unit (build/acww_plus_unity.c) with Metrowerks mwccarm.exe.
2. Links the ELF object at 0x01FFDC00 (unused ITCM tail) and writes build/payload.map.
3. Copies fresh vanilla arm9/overlay binaries from the region's vanilla files (read only), appends the
   payload to itcm.bin, and applies tools/patches.py (each patch checks the vanilla bytes first).
4. Runs dsd rom build.

Regions (tools/regions/): the sources and tools/patches.py are written with EU (ADMP) addresses. --region us
(Animal Crossing: Wild World USA, ADME) builds into build/us/: it compiles copies of the sources with every
address replaced through tools/regions/adme.py (made by tools/remap_region.py), and maps each patch's module,
address and expected bytes the same way. The EU build (the default) is unchanged.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import acww_config  # noqa: E402
import regions  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
REGION = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "eu"
if REGION not in regions.REGIONS:
    sys.exit(f"unknown region {REGION!r} (one of {', '.join(regions.REGIONS)})")
BUILD_DIR = regions.build_dir(ROOT_DIR, REGION)       # build/ (EU), build/us/
UNITY_C = BUILD_DIR / "acww_plus_unity.c"
OBJ_O = BUILD_DIR / "acww_plus.o"
PAYLOAD_BIN = BUILD_DIR / "payload_itcm.bin"
EXTRACTED_DIR = BUILD_DIR / "extracted"
OUT_ROM = BUILD_DIR / "acww_plus.nds"
RELEASE_ROM = BUILD_DIR / "acww_plus_release.nds"
RELEASE = "--release" in sys.argv   # leaves out the hooks of unreleased features (patches.RELEASE_DISABLED)

VANILLA_EXTRACTED = regions.REGIONS[REGION]["vanilla"]
DSD_EXE = regions.DSD_EXE
# Another region: EU address -> its address, EU patch address -> its vanilla bytes there (None, None for the EU)
REGION_ADDR, REGION_EXPECT = regions.address_table(REGION)
OVERLAY_MAP = regions.overlay_map(REGION)
MWCCARM_EXE = Path(acww_config.get("MWCCARM_EXE"))

ITCM_BASE_ADDR = 0x01FF8000
PAYLOAD_OFFSET_IN_ITCM = 0x5C00
PAYLOAD_BASE_ADDR = ITCM_BASE_ADDR + PAYLOAD_OFFSET_IN_ITCM  # 0x01FFDC00
ITCM_END_ADDR = 0x02000000

ARM9_BASE_ADDR = 0x02000000


def encode_thumb_bl(src_addr: int, target_addr: int) -> bytes:
    """Encodes a 4-byte Thumb BL instruction from src_addr to target_addr."""
    rel = (target_addr & ~1) - (src_addr + 4)
    if rel < -0x400000 or rel >= 0x400000 or (rel & 1):
        raise ValueError(f"Thumb BL out of range: 0x{src_addr:08X} -> 0x{target_addr:08X}")
    imm22 = (rel >> 1) & 0x3FFFFF
    hi11 = (imm22 >> 11) & 0x7FF
    lo11 = imm22 & 0x7FF
    hw1 = 0xF000 | hi11
    hw2 = 0xF800 | lo11
    return struct.pack("<HH", hw1, hw2)


def compile_c_source(unity=None, obj=None, include_dir=None):
    unity = unity or UNITY_C
    obj = obj or OBJ_O
    cmd = [
        str(MWCCARM_EXE),
        "-O4,s",
        "-inline", "off",
        "-proc", "arm946e",
        "-thumb",
        "-interworking",
        "-c", str(unity),
        "-o", str(obj),
    ]
    env = os.environ.copy()
    env["MWCIncludes"] = str(include_dir or SRC_DIR)
    env["LM_LICENSE_FILE"] = str(MWCCARM_EXE.parents[2] / "license.dat")
    print(f"[1/4] Compiling {unity.name} with mwccarm.exe...")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)


def link_elf_object(obj_path: Path, base_addr: int, externs=None, relocs_out=None):
    """externs: {name: address} for symbols defined outside the object (heap code -> ITCM payload).
    relocs_out: list that receives the image offsets of ABS32 words pointing inside the image (heap code)."""
    data = obj_path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError("Not a valid ELF file")

    e_shoff, = struct.unpack_from("<I", data, 0x20)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x2E)

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = (
            struct.unpack_from("<10I", data, off)
        )
        sections.append({
            "idx": i,
            "sh_name": sh_name,
            "type": sh_type,
            "flags": sh_flags,
            "offset": sh_offset,
            "size": sh_size,
            "link": sh_link,
            "info": sh_info,
            "align": max(sh_addralign, 4),
            "entsize": sh_entsize,
            "content": bytearray(data[sh_offset : sh_offset + sh_size]) if sh_type != 8 else bytearray(sh_size),
        })

    shstr = bytes(sections[e_shstrndx]["content"])
    for s in sections:
        end = shstr.find(b"\x00", s["sh_name"])
        s["name"] = shstr[s["sh_name"]:end].decode("ascii", errors="replace")

    # Lay out allocatable sections (.text, .rodata, .data, .bss)
    cur_addr = base_addr
    alloc_order = [".text", ".rodata", ".data", ".bss"]
    sec_by_name = {}
    for name in alloc_order:
        for s in sections:
            if s["name"] == name and (s["flags"] & 0x2):  # SHF_ALLOC
                align = max(s["align"], 4)
                cur_addr = (cur_addr + align - 1) & ~(align - 1)
                s["vaddr"] = cur_addr
                cur_addr += s["size"]
                sec_by_name[name] = s

    # Also catch any other SHF_ALLOC sections if present
    for s in sections:
        if (s["flags"] & 0x2) and "vaddr" not in s:
            align = max(s["align"], 4)
            cur_addr = (cur_addr + align - 1) & ~(align - 1)
            s["vaddr"] = cur_addr
            cur_addr += s["size"]

    total_size = (cur_addr - base_addr + 3) & ~3

    # Parse symbol table
    symtab_sec = next(s for s in sections if s["type"] == 2)  # SHT_SYMTAB
    strtab_sec = sections[symtab_sec["link"]]
    strtab = bytes(strtab_sec["content"])
    sym_bytes = bytes(symtab_sec["content"])
    num_syms = len(sym_bytes) // 16

    symbols = []
    sym_addrs = {}
    for i in range(num_syms):
        st_name, st_value, st_size, st_info, st_other, st_shndx = struct.unpack_from("<IIIBBH", sym_bytes, i * 16)
        end = strtab.find(b"\x00", st_name)
        name = strtab[st_name:end].decode("ascii", errors="replace")
        vaddr = st_value
        if 0 < st_shndx < len(sections) and "vaddr" in sections[st_shndx]:
            vaddr += sections[st_shndx]["vaddr"]
        elif st_shndx == 0 and i > 0:
            if externs is None or name not in externs:
                raise ValueError(f"Undefined external symbol in object: {name}")
            vaddr = externs[name]
        symbols.append({"name": name, "vaddr": vaddr, "info": st_info, "shndx": st_shndx, "size": st_size,
                        "external": st_shndx == 0 and i > 0})
        if name:
            sym_addrs[name] = vaddr

    # Apply SHT_RELA (type 4) and SHT_REL (type 9) relocations
    for s in sections:
        if s["type"] not in (4, 9):
            continue
        target_sec = sections[s["info"]]
        if "vaddr" not in target_sec:
            continue
        t_buf = target_sec["content"]
        t_base = target_sec["vaddr"]
        is_rela = (s["type"] == 4)
        ent_sz = 12 if is_rela else 8
        raw = bytes(s["content"])
        for off in range(0, len(raw), ent_sz):
            if is_rela:
                r_offset, r_info, r_addend = struct.unpack_from("<IIi", raw, off)
            else:
                r_offset, r_info = struct.unpack_from("<II", raw, off)
                r_addend = 0
            r_sym = r_info >> 8
            r_type = r_info & 0xFF
            sym = symbols[r_sym]
            S = sym["vaddr"]
            P = t_base + r_offset

            if r_type == 2:  # R_ARM_ABS32
                addend = r_addend if is_rela else struct.unpack_from("<i", t_buf, r_offset)[0]
                val = (S + addend) & 0xFFFFFFFF
                struct.pack_into("<I", t_buf, r_offset, val)
                if relocs_out is not None and not sym["external"] and sym["shndx"] != 0xFFF1:   # SHN_ABS stays
                    relocs_out.append(P - base_addr)
            elif r_type == 10 and relocs_out is not None and sym["external"]:
                raise ValueError(f"heap code: direct call to {sym['name']} outside the image (call it through a pointer)")
            elif r_type == 10:  # R_ARM_THM_CALL
                # Metrowerks RELA uses r_addend = -4 for Thumb BL
                bl_bytes = encode_thumb_bl(P, S)
                t_buf[r_offset : r_offset + 4] = bl_bytes
            else:
                raise ValueError(f"Unsupported relocation type {r_type} at {target_sec['name']}+0x{r_offset:X}")

    # Assemble flat binary image
    image = bytearray(total_size)
    for s in sections:
        if "vaddr" in s and s["type"] != 8:  # Copy non-NOBITS sections
            rel_off = s["vaddr"] - base_addr
            image[rel_off : rel_off + s["size"]] = s["content"]

    return bytes(image), sym_addrs, sections


def module_info():
    """{module: (vanilla path, extracted path, base address)} for arm9 and every overlay."""
    mods = {"arm9": (VANILLA_EXTRACTED / "arm9" / "arm9.bin", EXTRACTED_DIR / "arm9" / "arm9.bin", ARM9_BASE_ADDR)}
    y = (VANILLA_EXTRACTED / "arm9_overlays" / "overlays.yaml").read_text()
    for blk in y.split("- id:")[1:]:
        n = int(blk.split()[0])
        base = int(re.search(r"base_address:\s*(\d+)", blk).group(1))
        name = f"ov{n:03d}"
        mods[name] = (VANILLA_EXTRACTED / "arm9_overlays" / f"{name}.bin",
                      EXTRACTED_DIR / "arm9_overlays" / f"{name}.bin", base)
    return mods


def apply_patches(syms):
    from patches import PATCHES, RELEASE_DISABLED
    mods = module_info()
    data = {}
    skip = [x for x in os.environ.get("ACWW_SKIP", "").split(",") if x]   # experiments: skip patches by value
    for mod, addr, kind, expect, value, note in PATCHES:
        if REGION_ADDR is not None:      # EU module, address and bytes -> this region's
            if addr not in REGION_ADDR or addr not in REGION_EXPECT:
                raise RuntimeError(f"{mod} 0x{addr:08X} is not in the {REGION} address table (tools/remap_region.py)")
            mod = f"ov{OVERLAY_MAP[int(mod[2:])]:03d}" if mod.startswith("ov") else mod
            addr, expect = REGION_ADDR[addr], REGION_EXPECT[addr]
        if RELEASE and value in RELEASE_DISABLED:
            print(f"      OFF   {mod} 0x{addr:08X} {value} (not in the release build)")
            continue
        if "*" in skip or any(x in str(value) for x in skip):
            print(f"      SKIP  {mod} 0x{addr:08X} {value}")
            continue
        if mod not in data:
            data[mod] = bytearray(mods[mod][0].read_bytes())
        buf, base = data[mod], mods[mod][2]
        off = addr - base
        exp = bytes.fromhex(expect)
        if buf[off: off + len(exp)] != exp:
            raise RuntimeError(f"{mod} 0x{addr:08X}: expected {expect}, found {buf[off:off+len(exp)].hex()} ({note})")
        if kind == "bl":
            if value not in syms:
                raise RuntimeError(f"missing payload symbol {value}")
            new = encode_thumb_bl(addr, syms[value])
        elif kind == "ptr":
            new = struct.pack("<I", syms[value] | 1)
        elif kind == "dptr":
            new = struct.pack("<I", syms[value])
        elif kind == "bytes":
            new = bytes.fromhex(value)
        else:
            raise ValueError(kind)
        buf[off: off + len(new)] = new
        print(f"      {mod:5s} 0x{addr:08X} {kind:5s} {value:30s} {note}")
    # Every module starts from vanilla on each build; patched ones are then overwritten
    for mod, (src, dst, _) in mods.items():
        if mod in data:
            dst.write_bytes(data[mod])
        elif not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)


def apply_file_patches():
    """Restores the files edited by the previous build, then applies tools/file_patches.py on fresh copies."""
    import file_patches
    from file_patches import FILE_PATCHES
    file_patches.LANGS = regions.REGIONS[REGION]["langs"]
    src = VANILLA_EXTRACTED / "files"
    dst = EXTRACTED_DIR / "files"
    log = BUILD_DIR / "files_modified.txt"
    if log.exists():
        for rel in log.read_text().split():
            shutil.copyfile(src / rel, dst / rel)
    done = []
    for fn in FILE_PATCHES:
        for rel in fn(src, dst):
            done.append(str(rel).replace(chr(92), "/"))
            print(f"      files/{done[-1]}  ({fn.__name__})")
    log.write_text(chr(10).join(done) + chr(10))


def region_sources():
    """The source tree to compile: src/ itself for the EU. Another region compiles a copy (BUILD_DIR/src) with every
    address replaced through its table; an address in the code that the table lacks stops the build."""
    src = ROOT_DIR / "src"
    if REGION_ADDR is None:
        return src
    out = BUILD_DIR / "src"
    for p in sorted(src.rglob("*")):
        if p.suffix not in (".c", ".h"):
            continue
        rel = p.relative_to(src)
        text = regions.translate_c(p.read_text(encoding="utf-8"), REGION_ADDR, f"src/{rel.as_posix()}")
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        if not (out / rel).exists() or (out / rel).read_text(encoding="utf-8") != text:
            (out / rel).write_text(text, encoding="utf-8")
    return out


SRC_DIR = ROOT_DIR / "src"     # set by main(): region_sources()


def write_unity_source():
    """All src/*.c compiled as one translation unit (one ELF for the tiny linker)."""
    files = sorted(p for p in SRC_DIR.glob("*.c"))
    UNITY_C.write_text("".join(f'#include "{p.as_posix()}"' + chr(10) for p in files))
    return files


HEAP_UNITY_C = BUILD_DIR / "acww_heap_unity.c"
HEAP_OBJ_O = BUILD_DIR / "acww_heap.o"
# Code home: the SDK's main arena (and so the root heap) starts right after the highest overlay (EU: 0x0229F9A0,
# the end of ov098). We move the arena start up by HEAP_CODE_RESERVE and put src/heap/*.c there as an extra autoload
# block, which the crt0 copies in at boot like the ITCM payload (see docs/features/code_home.md).
regions.make_vanilla(REGION)            # the US files are extracted from the owner's dump on first use
_CONSTS = regions.build_constants(REGION)
HEAP_CODE_BASE = _CONSTS["HEAP_CODE_BASE"]              # EU 0x0229F9A0
HEAP_CODE_RESERVE = 0x2000
ARENA_LO_LITERAL = _CONSTS["ARENA_LO_LITERAL"]          # EU 0x02117BD8, unk_autoload_2: SDK main arena lo
                                                        # (OS_InitArena / OS_GetInitArenaLo)
AUTOLOAD2_BASE = _CONSTS["AUTOLOAD2_BASE"]              # EU 0x020E8180
HX_MAGIC = 0x50485741                  # 'AWHP'
# Export table at HEAP_CODE_BASE: magic, then these, in the order of the HX_* slots in src/code_home.h
HX_EXPORTS = ["hx_claim_vram", "hx_can_place", "hx_load_model", "hx_is_seat_model", "hx_sit_request", "hx_sit_start",
              "hx_sit_tick"]


def build_heap_code(itcm_syms):
    """src/heap/*.c -> autoload 4 at HEAP_CODE_BASE; the SDK main arena starts HEAP_CODE_RESERVE later."""
    files = sorted(p for p in (SRC_DIR / "heap").glob("*.c"))
    HEAP_UNITY_C.write_text("".join(f'#include "{p.as_posix()}"' + chr(10) for p in files))
    compile_c_source(HEAP_UNITY_C, HEAP_OBJ_O)
    table = 4 * (1 + len(HX_EXPORTS))
    image, syms, _ = link_elf_object(HEAP_OBJ_O, HEAP_CODE_BASE + table, externs=itcm_syms)
    blob = struct.pack(f"<{1 + len(HX_EXPORTS)}I", HX_MAGIC, *[syms[n] | 1 for n in HX_EXPORTS]) + image
    if len(blob) > HEAP_CODE_RESERVE:
        raise RuntimeError(f"heap code is {len(blob)} bytes, reserve is {HEAP_CODE_RESERVE}")
    # dsd orders autoloads by index, and the crt0 handles them in that order. The main BSS clear (vanilla autoload
    # 3, 0x0213FAA0..0x02203D20) covers where this block's source data sits in the loaded arm9 image, so this block
    # must come first: it takes index 3 and the BSS clear becomes index 4 (the game's autoload callback is a bare
    # bx lr; nothing else looks at the indices). Check: tools/analysis/arm9_autoloads.py build/acww_plus.nds
    arm9_dir = EXTRACTED_DIR / "arm9"
    (arm9_dir / "hx_autoload.bin").write_bytes(blob)
    (arm9_dir / "hx_autoload.yaml").write_text(
        f"base_address: {HEAP_CODE_BASE}{chr(10)}code_size: {len(blob)}{chr(10)}bss_size: 0{chr(10)}kind:{chr(10)}  Unknown: 3{chr(10)}")
    shutil.copyfile(VANILLA_EXTRACTED / "arm9" / "unk_autoload_3.bin", arm9_dir / "bss_autoload.bin")
    bss_yaml = (VANILLA_EXTRACTED / "arm9" / "unk_autoload_3.yaml").read_text()
    assert "Unknown: 3" in bss_yaml
    (arm9_dir / "bss_autoload.yaml").write_text(bss_yaml.replace("Unknown: 3", "Unknown: 4"))
    for old in ("unk_autoload_4.bin", "unk_autoload_4.yaml"):
        (arm9_dir / old).unlink(missing_ok=True)
    cfg_path = EXTRACTED_DIR / "config.yaml"
    cfg = (VANILLA_EXTRACTED / "config.yaml").read_text()
    old_entry = ("  - index: 3" + chr(10) + "    bin: arm9/unk_autoload_3.bin" + chr(10) +
                 "    config: arm9/unk_autoload_3.yaml" + chr(10))
    assert old_entry in cfg
    cfg = cfg.replace(old_entry,
                      "  - index: 3" + chr(10) + "    bin: arm9/hx_autoload.bin" + chr(10) +
                      "    config: arm9/hx_autoload.yaml" + chr(10) +
                      "  - index: 4" + chr(10) + "    bin: arm9/bss_autoload.bin" + chr(10) +
                      "    config: arm9/bss_autoload.yaml" + chr(10))
    cfg_path.write_text(cfg)
    # SDK main arena lo: HEAP_CODE_BASE -> HEAP_CODE_BASE + reserve (checked against vanilla)
    a2 = bytearray((VANILLA_EXTRACTED / "arm9" / "unk_autoload_2.bin").read_bytes())
    off = ARENA_LO_LITERAL - AUTOLOAD2_BASE
    if struct.unpack_from("<I", a2, off)[0] != HEAP_CODE_BASE:
        raise RuntimeError(f"unk_autoload_2: arena lo literal is not 0x{HEAP_CODE_BASE:08X}")
    struct.pack_into("<I", a2, off, HEAP_CODE_BASE + HEAP_CODE_RESERVE)
    (EXTRACTED_DIR / "arm9" / "unk_autoload_2.bin").write_bytes(a2)
    (BUILD_DIR / "heap.map").write_text(chr(10).join(
        f"0x{a:08X} {n}" for n, a in sorted(syms.items(), key=lambda kv: kv[1]) if n and not n.startswith(("@", "."))
        and HEAP_CODE_BASE <= a < HEAP_CODE_BASE + len(blob)) + chr(10))
    print(f"      Heap code: {len(blob)} bytes at 0x{HEAP_CODE_BASE:08X} (autoload 3), "
          f"{HEAP_CODE_RESERVE - len(blob)} of 0x{HEAP_CODE_RESERVE:X} left; arena lo -> "
          f"0x{HEAP_CODE_BASE + HEAP_CODE_RESERVE:08X}")
    return {n: a for n, a in syms.items() if n and HEAP_CODE_BASE <= a < HEAP_CODE_BASE + len(blob)}


def main():
    global OUT_ROM, SRC_DIR
    if RELEASE:
        OUT_ROM = RELEASE_ROM
        print(f"      Release build -> {OUT_ROM.name}")
    if REGION != "eu":
        print(f"      Region: {regions.REGIONS[REGION]['title']} -> {BUILD_DIR.relative_to(ROOT_DIR)}")
    if not (EXTRACTED_DIR / "config.yaml").exists():   # first build here: start from a full vanilla copy
        print(f"      Copying the vanilla files to {EXTRACTED_DIR}...")
        shutil.copytree(VANILLA_EXTRACTED, EXTRACTED_DIR, dirs_exist_ok=True)
    SRC_DIR = region_sources()
    files = write_unity_source()
    print(f"      Sources: {', '.join(p.name for p in files)}")
    compile_c_source()

    print(f"[2/4] Linking {OBJ_O.name} at ITCM 0x{PAYLOAD_BASE_ADDR:08X}...")
    payload, syms, sections = link_elf_object(OBJ_O, PAYLOAD_BASE_ADDR)
    PAYLOAD_BIN.write_bytes(payload)
    map_lines = [f"0x{a:08X} {n}" for n, a in sorted(syms.items(), key=lambda kv: kv[1])
                 if n and not n.startswith(("@", "."))]
    (BUILD_DIR / "payload.map").write_text(chr(10).join(map_lines) + chr(10))

    end_addr = PAYLOAD_BASE_ADDR + len(payload)
    print(f"      Payload size: {len(payload)} bytes (0x{PAYLOAD_BASE_ADDR:08X} .. 0x{end_addr:08X}), "
          f"{ITCM_END_ADDR - end_addr} bytes of ITCM left")
    if end_addr > ITCM_END_ADDR:
        raise RuntimeError(f"Payload overflows ITCM end 0x{ITCM_END_ADDR:08X}!")

    print("[3/4] Patching binaries (fresh vanilla copies + tools/patches.py)...")
    vanilla_itcm = (VANILLA_EXTRACTED / "arm9" / "itcm.bin").read_bytes()
    if len(vanilla_itcm) > PAYLOAD_OFFSET_IN_ITCM:
        raise RuntimeError("Vanilla itcm.bin is larger than expected payload offset 0x5C00")
    padded_itcm = bytearray(vanilla_itcm) + bytearray(PAYLOAD_OFFSET_IN_ITCM - len(vanilla_itcm)) + bytearray(payload)
    if os.environ.get("ACWW_NO_PAYLOAD") == "1":   # experiments: vanilla ITCM image
        padded_itcm = bytearray(vanilla_itcm)
    (EXTRACTED_DIR / "arm9" / "itcm.bin").write_bytes(padded_itcm)
    itcm_yaml_txt = (VANILLA_EXTRACTED / "arm9" / "itcm.yaml").read_text(encoding="utf-8")
    itcm_yaml_txt = re.sub(r"code_size:\s*\d+", f"code_size: {len(padded_itcm)}", itcm_yaml_txt)
    (EXTRACTED_DIR / "arm9" / "itcm.yaml").write_text(itcm_yaml_txt, encoding="utf-8")
    # Keep vanilla's compression flags: an earlier build had arm9 + all overlays "compressed: false", which
    # cost ~12% of the ARM9 in town (tools/probes/headroom_probe.py: idle 47% vs 59%).
    shutil.copyfile(VANILLA_EXTRACTED / "arm9" / "arm9.yaml", EXTRACTED_DIR / "arm9" / "arm9.yaml")
    shutil.copyfile(VANILLA_EXTRACTED / "arm9_overlays" / "overlays.yaml", EXTRACTED_DIR / "arm9_overlays" / "overlays.yaml")
    heap_syms = build_heap_code(syms)
    apply_patches({**heap_syms, **syms})    # hooks can point at ITCM or code-home functions
    if os.environ.get("ACWW_NO_FILES") != "1":
        apply_file_patches()

    print(f"[4/4] Building ROM {OUT_ROM}...")
    build_cmd = [
        str(DSD_EXE),
        "rom", "build",
        "--config", str(EXTRACTED_DIR / "config.yaml"),
        "--rom", str(OUT_ROM),
    ]
    res = subprocess.run(build_cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)
    print(f"Done! Built {OUT_ROM} ({OUT_ROM.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
