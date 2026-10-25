"""
Where AC:WW+ finds the things that are not in this repo (Nintendo's files, third-party tools, the test emulator).

Each entry can be set with an environment variable (ACWW_<KEY>, e.g. ACWW_CLEAN_ROM) or in
tools/acww_config.local.json (gitignored, {"CLEAN_ROM": "...", ...}). The defaults are the original author's machine.
See README.md, "For developers", for what each one is.
"""
import json
import os
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    # Your own dump of the EU ROM (ADMP, CRC32 C677970C)
    "CLEAN_ROM": r"E:\claudeGameDecomp\0389 - Animal Crossing - Wild World (E)(Legacy).nds",
    # US build only: your own dump of the US ROM (ADME rev 0, CRC32 F24508AA). Its unpacked files are made on
    # first use in vanilla/ADME/extracted of the main checkout (git-ignored), unless US_VANILLA_EXTRACTED is set.
    "US_ROM": r"E:\Users\Migue\Downloads\0223 - Animal Crossing - Wild World (U)(SCZ)\0223 - Animal Crossing - Wild World (U)(SCZ).nds",
    "US_VANILLA_EXTRACTED": "",
    # US rev 1 build only: your own dump of US rev 1 (ADME rev 1, CRC32 7E62F586); unpacked into vanilla/ADME1/extracted
    "US1_ROM": r"E:\Users\Migue\Downloads\Welcome to Animal Crossing - Wild World (USA) (Rev 1)\1479 - Welcome to Animal Crossing - Wild World (USA) (Rev 1).nds",
    "US1_VANILLA_EXTRACTED": "",
    # That ROM unpacked with dsd ("dsd rom extract"); the build copies vanilla binaries and files from here
    "VANILLA_EXTRACTED": r"E:\claudeGameDecomp\extracted",
    # dsd (https://github.com/AetiasHax/ds-decomp): rebuilds the ROM
    "DSD_EXE": r"E:\claudeGameDecomp\dsd-windows-x86_64.exe",
    # Metrowerks CodeWarrior for DS, mwccarm.exe (not included; its license.dat is expected two folders up)
    "MWCCARM_EXE": r"C:\NDS_RECOMP\nds-docs\pokemon_dp\sdk\cw\ARM_Tools\Command_Line_Tools\mwccarm.exe",
    # Test harness only: the author's private tools (ndsref emulator client, save editor, scenario files)
    "TEST_TOOLS": r"C:\NDS_RECOMP\prototype\tools",
    "SAVE_TOOLS": r"C:\NDS_RECOMP\animalcrossingwwrecomp\tools",
    "TEST_SAVE": r"C:\NDS_RECOMP\animalcrossingwwrecomp\scenarios\saves\d25.sav",
    "LOAD_SAVE_SCENARIO": r"C:\NDS_RECOMP\animalcrossingwwrecomp\scenarios\acww_load_save.json",
}

_LOCAL = PROJECT / "tools" / "acww_config.local.json"
_local = json.loads(_LOCAL.read_text(encoding="utf-8")) if _LOCAL.exists() else {}


def get(key):
    return os.environ.get("ACWW_" + key) or _local.get(key) or DEFAULTS[key]


def main_checkout():
    """The main checkout of this repo (the same as PROJECT unless this is a git worktree)."""
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=PROJECT, capture_output=True,
                                text=True, check=True).stdout.strip()
        return (PROJECT / common).resolve().parent
    except (OSError, subprocess.CalledProcessError):
        return PROJECT
