/*
 * AC:WW+ code home: fruit stacks up to 9 in one pocket slot.
 *
 * Vanilla fruit is 5 items (0x1518 apple, orange, pear, peach, cherry), one per pocket slot. Like Joan's turnip
 * bundles, a stack is an item of its own: 0x156E + kind * 8 + (count - 2) = "2 apples" .. "9 cherries" (records
 * added by tools/file_patches.py in the blank item_info space; the accessors' "index < 0x56E" clamps are raised).
 *
 * - Picking up a fruit (or a stack) while carrying the same kind adds it to that slot when the total is 9 or less,
 *   with or without free pocket slots (hook in bells_pickup.c). Otherwise it takes a slot of its own as before.
 * - Eating a stack (pockets screen) eats one fruit; the rest stays in the slot.
 * - Burying a stack in a hole plants one fruit tree; the rest stays in the slot.
 * - A stack is worth count x the fruit's value (item_value), so Nook pays the same as for the single fruit.
 * - Dropping, mailing or giving a stack moves the whole stack. Mail, gifts and shops still hand out single fruit.
 */

#include "acww.h"

#define FRUIT_FIRST             0x1518
#define FRUIT_LAST              0x151C
#define FRUIT_STACK_FIRST       0x156E
#define FRUIT_STACK_LAST        0x1595
#define FRUIT_STACK_MAX         9

#define FN_BURY_FIELD_IDS       ((int (*)(s16 *obj, s16 *obj2, u32 item))(0x02043D50 | 1))   /* item_to_field_obj_ids */
#define FN_QUEUE_EAT            ((int (*)(const u16 *item))(0x02094E94 | 1))   /* player_self_queue_action_85 */

/* ov096: pockets screen (ps = the screen; it works on a copy of the pockets, written back when it closes) */
#define PS_HELD_ITEM            0xAC     /* u16: item on the stylus / cursor */
#define PS_HELD_FROM            0xB0     /* u8 */
#define PS_HELD_STATE           0xB1     /* u8: 2 = holding an item */
#define PS_SLOT                 0xB6     /* u8: slot the current action works on */
#define EQUIP_EAT               7        /* func_ov096_0229ab98: fruit / turnips dropped on the player */
#define FN_EQUIP_KIND           ((int (*)(u8 *ps))(0x0229AB98 | 1))
#define FN_EQUIP_RESULT         ((u16 (*)(u8 *ps, int kind, u32 item))(0x0229AA50 | 1))
#define FN_SLOT_ITEM            ((u16 (*)(u8 *ps, int slot))(0x0229B77C | 1))
#define FN_SLOT_CLEAR           ((void (*)(u8 *ps, int slot))(0x0229BC4C | 1))
#define FN_SLOT_WRITE           ((void (*)(u8 *ps, int slot, u32 item, int flags))(0x0229BC80 | 1))

/* item_value's first 4 instructions, then on at 0x0204BFA0 (the entry is patched to jump to hook_item_value) */
static const u32 s_item_value_orig[4] = {
    0xB084B510,     /* push {r4, lr}; sub sp, #0x10 */
    0xA8001C04,     /* adds r4, r0, #0; add r0, sp, #0 */
    0x47184B00,     /* ldr r3, [pc, #0]; bx r3 */
    0x0204BFA1,
};
#define FN_ITEM_VALUE_ORIG      ((int (*)(const u16 *item))((u32)s_item_value_orig | 1))

/* Fruit kind (0..4) and count of an item; count 0 = not fruit. */
static int fruit_count(u16 item, int *kind) {
    if (item >= FRUIT_FIRST && item <= FRUIT_LAST) {
        *kind = item - FRUIT_FIRST;
        return 1;
    }
    if (item >= FRUIT_STACK_FIRST && item <= FRUIT_STACK_LAST) {
        *kind = (item - FRUIT_STACK_FIRST) >> 3;
        return ((item - FRUIT_STACK_FIRST) & 7) + 2;
    }
    return 0;
}

static u16 fruit_item(int kind, int count) {
    return count == 1 ? FRUIT_FIRST + kind : FRUIT_STACK_FIRST + kind * 8 + count - 2;
}

/* The stack with one fruit less, or 0 when the item is not a stack. */
static u16 stack_less_one(u16 item) {
    int kind, n = fruit_count(item, &kind);
    return n >= 2 ? fruit_item(kind, n - 1) : 0;
}

/* Adds a picked-up fruit (or stack) to a pocket slot of the same kind. 1 = done, 0 = pocket it as usual. */
int fruit_stack(u16 item) {
    u8 *rec;
    u16 *slots;
    u32 flags;
    int kind, have_kind, n = fruit_count(item, &kind), i;
    if (n == 0) {
        return 0;
    }
    rec = FN_PLAYER_RECORD_CURRENT();
    slots = (u16 *)(rec + PREC_POCKET_ITEMS);
    flags = *(u32 *)(rec + PREC_POCKET_FLAGS);
    for (i = 0; i < POCKET_SLOTS; i++) {
        int have = fruit_count(slots[i], &have_kind);
        if (have == 0 || have_kind != kind || ((flags >> (2 * i)) & 3) != 0 || have + n > FRUIT_STACK_MAX) {
            continue;
        }
        slots[i] = fruit_item(kind, have + n);
        return 1;
    }
    return 0;
}

/* Hook: item_value's entry. A stack is worth count x one fruit (town fruit and foreign fruit alike). */
int hook_item_value(const u16 *item) {
    int kind, n = fruit_count(*item, &kind);
    if (n >= 2) {
        u16 one = fruit_item(kind, 1);
        return n * FN_ITEM_VALUE_ORIG(&one);
    }
    return FN_ITEM_VALUE_ORIG(item);
}

/* Hook: the pockets screen's "what does dropping the held item on the player do" (3 calls). Stacks are eaten. */
int hook_equip_kind(u8 *ps) {
    if (ps[PS_HELD_STATE] == 2 && ps[PS_HELD_FROM] == 0 && stack_less_one(*(u16 *)(ps + PS_HELD_ITEM))) {
        return EQUIP_EAT;
    }
    return FN_EQUIP_KIND(ps);
}

/* Hook: the two calls that start eating (player_self_queue_action_85): the player eats one fruit. */
int hook_queue_eat(const u16 *item) {
    int kind;
    u16 one;
    if (fruit_count(*item, &kind) >= 2) {
        one = fruit_item(kind, 1);
        return FN_QUEUE_EAT(&one);
    }
    return FN_QUEUE_EAT(item);
}

/* Hook: what the stylus holds after a held item was dropped on the player. After eating from a stack, the rest. */
u16 hook_equip_result(u8 *ps, int kind, u32 item) {
    u16 rest = stack_less_one((u16)item);
    u16 held = FN_EQUIP_RESULT(ps, kind, item);
    return (kind == EQUIP_EAT && rest) ? rest : held;
}

/* Hook: emptying the slot after eating from it (ov096), or after burying its item in a hole ("Bury", or "Drop on
 * Ground" facing a hole; ov098). A stack keeps the rest. */
void hook_eat_slot_clear(u8 *ps, int slot) {
    u16 rest = stack_less_one(FN_SLOT_ITEM(ps, slot));
    if (rest) {
        FN_SLOT_WRITE(ps, slot, rest, 0);
        return;
    }
    FN_SLOT_CLEAR(ps, slot);
}

/* Hook: item_to_field_obj_ids in func_02043d0c (an item put in a hole). A stack plants as one fruit. */
int hook_bury_field_ids(s16 *obj, s16 *obj2, u32 item) {
    int kind;
    if (fruit_count((u16)item, &kind) >= 2) {
        item = fruit_item(kind, 1);
    }
    return FN_BURY_FIELD_IDS(obj, obj2, item);
}
