"""
NitroFS file edits for AC:WW+ (applied by tools/build_rom.py on fresh vanilla copies).

New text is English in every language (owner decision 2026-10-19: English first, other languages fall back
to the English text until translated).
"""
from pathlib import Path

import bmg_tool

LANGS = ["ENG", "FRN", "GER", "ITA", "SPN"]


def look_menu_text(src: Path, dst: Path):
    """Features 3 + 4: 'Change my look.' in the upstairs phone's Service Center (src/skin_tone.c)."""
    out = []
    for lang in LANGS:
        rel = Path("script") / lang / "select" / "select2.bmg"
        b = bmg_tool.Bmg(src / rel)
        assert b.msgs[22][0] == b"", f"{rel}: select2 #22 is not empty"
        b.msgs[22][0] = bmg_tool.encode("Change my look.")
        b.save(dst / rel)
        out.append(rel)

        rel = Path("script") / lang / "message" / "sp" / "etc" / "sequence1_.bmg"
        b = bmg_tool.Bmg(src / rel)
        assert len(b.msgs) == 0x43, f"{rel}: expected 0x43 messages, found {len(b.msgs)}"
        ask_attr = b.msgs[17][1]                      # a question with inline choices ("how should they talk")

        def reply_to(nxt):                            # a reply that continues to message nxt
            a = bytearray(b.msgs[16][1])
            a[4] = nxt
            return bytes(a)

        new = [
            # 0x43 look menu: 4 choices -> skin question, shoes, socks, "anything else?"
            ("What would you like to\nchange?{2:2:4447481f}\nSkin tone.\nShoes.\nSocks.\nThat's all.", ask_attr),
            # 0x44 skin question: Lighter / Darker -> 0x45 / 0x46, This is fine -> look menu
            ("What kind of skin tone\nwould you like?{2:1:454643}\nLighter.\nDarker.\nThis is fine.", ask_attr),
            # 0x45 / 0x46 skin replies -> back to the skin question
            ("There we go!{1:0:0500}\nHow does that look?", reply_to(0x44)),
            ("There we go!{1:0:0500}\nHow does that look?", reply_to(0x44)),
            # 0x47 / 0x48 shoe / sock replies -> back to the look menu
            ("How about these shoes?", reply_to(0x43)),
            ("How about these socks?", reply_to(0x43)),
        ]
        for text, attr in new:
            b.msgs.append([bmg_tool.encode(text), attr])
        b.save(dst / rel)
        out.append(rel)
    return out


def body_sock_index(src: Path, dst: Path):
    """Player bodies: the sock texels of texture b1 share the white palette entry of the shoe trim (boy 12,
    girl 14), so a sock colour also painted the shoe's white parts. Moves the sock texels (the white band between
    the two mirrored shoe halves, x < 14, mapped in the emulator) to the unused entry 13 / 15, still white."""
    import struct
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "analysis"))
    import nitro_tex
    out = []
    for name, old, new, rows in (("boy", 12, 13, range(6, 18)),
                                 ("grl", 14, 15, list(range(7, 17)) + list(range(20, 24)))):
        rel = Path("PBody") / f"{name}.nsbmd"
        d = bytearray((src / rel).read_bytes())
        texs, _, _, _ = nitro_tex.read_tex0(bytes(d))
        t = [t for t in texs if t["name"] == "b1"][0]
        assert (t["w"], t["h"], t["fmt"]) == (32, 32, 3), rel
        moved = 0
        for y in rows:
            for x in range(14):
                i = y * 32 + x
                o = t["off"] + i // 2
                sh = 4 if i & 1 else 0
                if (d[o] >> sh) & 15 == old:
                    d[o] = (d[o] & ~(15 << sh) & 0xFF) | (new << sh)
                    moved += 1
        assert moved > 20, (rel, moved)
        (dst / rel).write_bytes(d)
        out.append(rel)
    return out


FILE_PATCHES = [look_menu_text, body_sock_index]
