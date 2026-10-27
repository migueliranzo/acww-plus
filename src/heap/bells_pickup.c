/*
 * AC:WW+ code home: Bell bags picked up go straight into the wallet.
 *
 * Vanilla pockets a Bell bag (items 0x1492..0x14FD) like any other item, so the player has to open the pockets and
 * drag it onto the wallet. Here, when the whole amount fits in the wallet (99,999 cap), it is added to the wallet
 * instead; otherwise the bag is pocketed as usual (or, with full pockets, the usual "pockets are full" talk).
 *
 * Two places pocket an item taken from the ground:
 * - player_action_19_pick_up_flow (0x0200A900), state 0, once the pick-up animation has ended: pocket_put_item and
 *   state 6 (done) when the pockets have room, else the "pockets are full" talk. Its two callers (the tick of
 *   actions 0x19 and 0x1B) come here first: a bag that fits goes to the wallet and the flow skips to state 6 with
 *   or without free pocket slots. The item is already off the ground at that point.
 * - ov003 action 0x60 (shovel put-away after digging something up): its pocket_put_item call comes here.
 */

#include "acww.h"

#define FN_PICK_UP_FLOW         ((void (*)(u32 actor, u8 *state, int pockets_full))(0x0200A900 | 1))
#define FN_ANIM_CLOCK_ENDED     ((int (*)(u32 clock))(0x02056850 | 1))
#define FN_POCKET_PUT_ITEM      ((int (*)(const u16 *item))(0x02099470 | 1))
#define FN_PLAYER_POCKET        ((u8 *(*)(u8 *rec))(0x02098A9C | 1))
#define FN_WALLET_ROOM          ((int (*)(u8 *pocket, int with_bags, int extra))(0x02098030 | 1))
#define FN_WALLET_ADD           ((void (*)(u8 *pocket, int delta, int use_bags))(0x02097D94 | 1))

#define ACTOR_ANIM_CLOCK        0x2CC
#define ACTOR_PICKED_ITEM       0x81C    /* u16 */
#define PICK_UP_DONE            6

#define ITEM_BELL_BAG_FIRST     0x1492   /* 100 Bells */
#define ITEM_BELL_BAG_LAST      0x14FD   /* 99,000 Bells */

/* Adds a Bell bag's face value to the local player's wallet when it fits whole. 1 = done, 0 = pocket it. */
static int bells_to_wallet(u16 item) {
    u8 *pocket;
    int i, value;
    if (item < ITEM_BELL_BAG_FIRST || item > ITEM_BELL_BAG_LAST) {
        return 0;
    }
    i = item - ITEM_BELL_BAG_FIRST;
    value = i < 9 ? (i + 1) * 100 : (i - 8) * 1000;
    pocket = FN_PLAYER_POCKET(FN_PLAYER_RECORD_CURRENT());
    if (FN_WALLET_ROOM(pocket, 0, 0) < value) {
        return 0;
    }
    FN_WALLET_ADD(pocket, value, 0);
    return 1;
}

/* Hook: the pick-up flow calls in player_action_19_tick and player_action_1b_tick. */
void hook_pick_up_flow(u32 actor, u8 *state, int pockets_full) {
    if (*state == 0 && FN_ANIM_CLOCK_ENDED(actor + ACTOR_ANIM_CLOCK)
            && bells_to_wallet(*(u16 *)(actor + ACTOR_PICKED_ITEM))) {
        *state = PICK_UP_DONE;
        return;
    }
    FN_PICK_UP_FLOW(actor, state, pockets_full);
}

/* Hook: pocket_put_item in ov003_player_action_60_end (shovel put-away). */
int hook_dig_pocket_put(const u16 *item) {
    if (bells_to_wallet(*item)) {
        return 1;
    }
    return FN_POCKET_PUT_ITEM(item);
}
