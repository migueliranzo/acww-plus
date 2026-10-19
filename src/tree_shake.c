/*
 * AC:WW+ Shake trees while a fishing rod or a net is equipped.
 *
 * The town's "use" dispatcher func_ov003_02208430(player, tool_kind, target) shakes the tree in front only for
 * tool kinds 0 (empty hands) and 10 (umbrella / toy); kind 3 (rod) casts, kind 4 (net) swings. The wrapper
 * below first runs the dispatcher's own kind-0 branch (tree ahead within reach -> field job + action 0x68);
 * only when there is no tree to shake does the rod cast / the net swing as usual.
 * With the net, the swing wins whenever a bug is close by (on the trunk, or bees coming out), so bugs can still
 * be caught on trees.
 */
#include "acww.h"

#define FN_OV003_USE_DISPATCH       ((int (*)(u32 player, int kind, s32 *target))(0x02208430 | 1))
#define TOOL_KIND_ROD               3
#define TOOL_KIND_NET               4

/* ov003 list A: the 8 bug ("thing") slots (GAME-THING.md) */
#define THING_SLOTS                 ((u8 *)0x0225DD4C)
#define THING_SLOT_SIZE             0x25C
#define THING_SLOT_COUNT            8
#define THING_ID                    0x24D    /* s8, -1 empty */
#define THING_POS                   0x204    /* fx32 x, y, z */
#define BUG_NEAR_DIST               0x5000   /* 2.5 units */

static int bug_near_player(u32 player) {
    s32 px = *(s32 *)(player + 0x5C);
    s32 pz = *(s32 *)(player + 0x64);
    int i;
    for (i = 0; i < THING_SLOT_COUNT; i++) {
        u8 *t = THING_SLOTS + i * THING_SLOT_SIZE;
        s32 dx, dz;
        if (*(s8 *)(t + THING_ID) < 0) {
            continue;
        }
        dx = *(s32 *)(t + THING_POS) - px;
        dz = *(s32 *)(t + THING_POS + 8) - pz;
        if (dx < 0) dx = -dx;
        if (dz < 0) dz = -dz;
        if (dx < BUG_NEAR_DIST && dz < BUG_NEAR_DIST) {
            return 1;
        }
    }
    return 0;
}

/* Hook: the 8 calls of func_ov003_02208430 inside func_ov003_022085dc (the A-button "use" handler). */
int hook_ov003_use_dispatch(u32 player, int kind, s32 *target) {
    if (kind == TOOL_KIND_ROD || (kind == TOOL_KIND_NET && !bug_near_player(player))) {
        s32 t[3];
        t[0] = target[0];
        t[1] = target[1];
        t[2] = target[2];
        if (FN_OV003_USE_DISPATCH(player, 0, t)) {
            return 1;
        }
    }
    return FN_OV003_USE_DISPATCH(player, kind, target);
}
