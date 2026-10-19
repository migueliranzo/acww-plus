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


FILE_PATCHES = [look_menu_text]
