/*
 * AC:WW+ code home: a code file (/zplus/code.bin, built from src/heap/*.c) loaded once into a root-heap block,
 * for code that doesn't fit the ITCM payload. See src/code_home.c.
 */
#ifndef CODE_HOME_H
#define CODE_HOME_H

#include "acww.h"

/* Export slots, in the order of HX_EXPORTS in tools/build_rom.py */
#define HX_CLAIM_VRAM   0
#define HX_CAN_PLACE    1
#define HX_LOAD_MODEL   2
#define HX_NUM_EXPORTS  3

extern void *g_hx_fn[HX_NUM_EXPORTS];
int hx_ready(void);

#endif
