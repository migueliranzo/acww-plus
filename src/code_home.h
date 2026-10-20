/*
 * AC:WW+ code home: src/heap/*.c, copied by the crt0 at boot (an extra autoload block) to 0x0229F9A0, the start of the SDK's main
 * arena, which the build moves up by the reserved size. See docs/features/code_home.md.
 * Layout: u32 magic 'AWHP', export pointers (HX_* slots, the order of HX_EXPORTS in tools/build_rom.py), code/data.
 */
#ifndef CODE_HOME_H
#define CODE_HOME_H

#include "acww.h"

#define HX_CODE_BASE    0x0229F9A0
#define HX_MAGIC        0x50485741u /* 'AWHP' */

#define HX_CLAIM_VRAM   0
#define HX_CAN_PLACE    1
#define HX_LOAD_MODEL   2
#define HX_NUM_EXPORTS  3

#define g_hx_fn         ((void *const *)(HX_CODE_BASE + 4))
#define hx_ready()      (*(volatile u32 *)HX_CODE_BASE == HX_MAGIC)

#endif
