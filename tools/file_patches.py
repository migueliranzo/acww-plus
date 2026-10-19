"""
NitroFS file edits for AC:WW+ (applied by tools/build_rom.py on fresh vanilla copies).

New text is English in every language (owner decision 2026-10-19: English first, other languages fall back
to the English text until translated).
"""
from pathlib import Path

import bmg_tool

LANGS = ["ENG", "FRN", "GER", "ITA", "SPN"]


def skin_tone_text(src: Path, dst: Path):
    """Feature 3: 'Skin tone.' in the upstairs phone's Service Center menu (src/skin_tone.c)."""
    out = []
    for lang in LANGS:
        rel = Path("script") / lang / "select" / "select2.bmg"
        b = bmg_tool.Bmg(src / rel)
        assert b.msgs[22][0] == b"", f"{rel}: select2 #22 is not empty"
        b.msgs[22][0] = bmg_tool.encode("Skin tone.")
        b.save(dst / rel)
        out.append(rel)

        rel = Path("script") / lang / "message" / "sp" / "etc" / "sequence1_.bmg"
        b = bmg_tool.Bmg(src / rel)
        assert len(b.msgs) == 0x43, f"{rel}: expected 0x43 messages, found {len(b.msgs)}"
        ask_attr = b.msgs[17][1]                      # a question with inline choices ("how should they talk")
        reply_attr = bytearray(b.msgs[16][1])         # a reply that continues to another message
        reply_attr[4] = 0x43                          # ... back to the skin tone question
        b.msgs.append([bmg_tool.encode(
            "What kind of skin tone\\nwould you like?{2:1:44451f}\\nLighter.\\nDarker.\\nThis is fine."), ask_attr])
        b.msgs.append([bmg_tool.encode("There we go!{1:0:0500}\\nHow does that look?"), bytes(reply_attr)])
        b.msgs.append([bmg_tool.encode("There we go!{1:0:0500}\\nHow does that look?"), bytes(reply_attr)])
        b.save(dst / rel)
        out.append(rel)
    return out


FILE_PATCHES = [skin_tone_text]
