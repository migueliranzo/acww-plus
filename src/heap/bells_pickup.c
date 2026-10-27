/*
 * AC:WW+ code home: Bell bags picked up stack onto a bag already in the pockets.
 *
 * Vanilla pockets every Bell bag (items 0x1492..0x14FD) in a slot of its own, so shaking a few trees fills the
 * pockets with 100-Bell bags. Here a picked-up bag is added to the first bag already in the pockets when the total
 * is itself a bag (the game has bags for 100..900 and 1,000..99,000 in thousands): 100 + 100 -> a 200-Bell bag.
 * Otherwise it is pocketed as before (or, with full pockets, the usual "pockets are full" talk). The money stays a
 * bag; putting it in the wallet is still up to the player.
 *
 * Two places pocket an item taken from the ground:
 * - player_action_19_pick_up_flow (0x0200A900), state 0, once the pick-up animation has ended: pocket_put_item and
 *   state 6 (done) when the pockets have room, else the "pockets are full" talk. Its two callers (the tick of
 *   actions 0x19 and 0x1B) come here first: a bag that stacks skips to state 6, with or without free pocket slots.
 *   The item is already off the ground at that point.
 * - ov003 action 0x60 (shovel put-away after digging something up): its pocket_put_item call comes here.
 */

#include "acww.h"

#define FN_PICK_UP_FLOW         ((void (*)(u32 actor, u8 *state, int pockets_full))(0x0200A900 | 1))
#define FN_ANIM_CLOCK_ENDED     ((int (*)(u32 clock))(0x02056850 | 1))
#define FN_POCKET_PUT_ITEM      ((int (*)(const u16 *item))(0x02099470 | 1))

#define ACTOR_ANIM_CLOCK        0x2CC
#define ACTOR_PICKED_ITEM       0x81C    /* u16 */
#define PICK_UP_DONE            6

#define ITEM_BELL_BAG_FIRST     0x1492   /* 100 Bells; +i: (i+1)*100 for i < 9, else (i-8)*1000 */
#define ITEM_BELL_BAG_LAST      0x14FD   /* 99,000 Bells */

static int bag_value(u16 item) {
    int i;
    if (item < ITEM_BELL_BAG_FIRST || item > ITEM_BELL_BAG_LAST) {
        return 0;
    }
    i = item - ITEM_BELL_BAG_FIRST;
    return i < 9 ? (i + 1) * 100 : (i - 8) * 1000;
}

/* The bag item worth exactly v Bells, or 0 when there is none (no division: the code home has no runtime helpers). */
static u16 bag_of_value(int v) {
    u16 item;
    for (item = ITEM_BELL_BAG_FIRST; item <= ITEM_BELL_BAG_LAST; item++) {
        if (bag_value(item) == v) {
            return item;
        }
    }
    return 0;
}

/* Adds a picked-up bag to the first pocket bag it stacks with. 1 = done, 0 = pocket it as usual. */
static int bag_stack(u16 item) {
    u8 *rec;
    u16 *slots;
    u32 flags;
    int v = bag_value(item), i;
    if (v == 0) {
        return 0;
    }
    rec = FN_PLAYER_RECORD_CURRENT();
    slots = (u16 *)(rec + PREC_POCKET_ITEMS);
    flags = *(u32 *)(rec + PREC_POCKET_FLAGS);
    for (i = 0; i < POCKET_SLOTS; i++) {
        int have = bag_value(slots[i]);
        u16 merged;
        if (have == 0 || ((flags >> (2 * i)) & 3) != 0) {   /* not a bag, or a wrapped / errand slot */
            continue;
        }
        merged = bag_of_value(have + v);
        if (merged != 0) {
            slots[i] = merged;
            return 1;
        }
    }
    return 0;
}

/* Hook: the pick-up flow calls in player_action_19_tick and player_action_1b_tick. */
void hook_pick_up_flow(u32 actor, u8 *state, int pockets_full) {
    if (*state == 0 && FN_ANIM_CLOCK_ENDED(actor + ACTOR_ANIM_CLOCK)
            && bag_stack(*(u16 *)(actor + ACTOR_PICKED_ITEM))) {
        *state = PICK_UP_DONE;
        return;
    }
    FN_PICK_UP_FLOW(actor, state, pockets_full);
}

/* Hook: pocket_put_item in ov003_player_action_60_end (shovel put-away). */
int hook_dig_pocket_put(const u16 *item) {
    if (bag_stack(*item)) {
        return 1;
    }
    return FN_POCKET_PUT_ITEM(item);
}
