/*
 * AC:WW+ code home loader.
 *
 * /zplus/code.bin = { u32 magic 'AWHP', u32 image size, u32 export count, u32 reloc count,
 *                     u32 export offsets[], u32 reloc offsets[], image }.
 * The image (src/heap/*.c, .text/.rodata/.data/.bss) is linked at 0. The loader reads the file into one root-heap
 * block (taken from the heap's tail, kept for the whole session), adds the image address to every relocated word,
 * writes the data cache back and invalidates the instruction cache over the image, then fills g_hx_fn.
 * Tried once; if the heap can't spare the block, hx_ready() stays 0 and the features using it fall back to vanilla.
 */

#include "code_home.h"

#define FN_FS_LOAD_ALLOC        ((u8 *(*)(const char *path, u32 heap, int align, u32 *out_sz))(0x02064490 | 1))
#define FN_HEAP_ALLOCATABLE_H   ((u32 (*)(u32 heap, int align))0x020E96A4)
#define FN_DC_FLUSH_RANGE       ((void (*)(const void *p, u32 n))0x021179B0)
#define FN_IC_INVALIDATE_RANGE  ((void (*)(const void *p, u32 n))0x021179EC)
#define HX_ROOT_HEAP_PTR        ((volatile u32 *)0x021F7ECC)
#define HX_MAGIC                0x50485741u /* 'AWHP' */
#define HX_HEAP_MIN_FREE        0x10000     /* largest free block needed before taking the code block */

void *g_hx_fn[HX_NUM_EXPORTS];
static u8 s_hx_state;           /* 0 = not tried, 1 = loaded; failed at: 2 heap check, 3 file load, 4 header */

int hx_ready(void) {
    static const char s_path[16] = "/zplus/code.bin";
    u32 heap = *HX_ROOT_HEAP_PTR;
    u32 sz = 0;
    u32 *f;
    u8 *img;
    u32 i;
    if (s_hx_state != 0) {
        return s_hx_state == 1;
    }
    if (heap == 0) {
        return 0;
    }
    s_hx_state = 2;
    if (FN_HEAP_ALLOCATABLE_H(heap, 4) < HX_HEAP_MIN_FREE) {
        return 0;
    }
    s_hx_state = 3;
    f = (u32 *)FN_FS_LOAD_ALLOC(s_path, heap, -32, &sz);
    if (f == 0) {
        return 0;
    }
    s_hx_state = 4;
    if (f[0] != HX_MAGIC || f[2] != HX_NUM_EXPORTS) {
        return 0;
    }
    img = (u8 *)(f + 4 + f[2] + f[3]);
    for (i = 0; i < f[3]; i++) {
        *(u32 *)(img + f[4 + f[2] + i]) += (u32)img;
    }
    FN_DC_FLUSH_RANGE(img, f[1]);
    FN_IC_INVALIDATE_RANGE(img, f[1]);
    for (i = 0; i < HX_NUM_EXPORTS; i++) {
        g_hx_fn[i] = img + f[4 + i];
    }
    s_hx_state = 1;
    return 1;
}
