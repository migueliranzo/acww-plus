/*
 * AC:WW+ shared definitions (EU ADMP). Every src/*.c is compiled as one unit (build/acww_plus_unity.c),
 * so each file includes this header; the include guard keeps it to one copy.
 * Thumb function addresses carry bit 0; ARM ones do not.
 */
#ifndef ACWW_H
#define ACWW_H

typedef unsigned char      u8;
typedef unsigned short     u16;
typedef unsigned int       u32;
typedef signed char        s8;
typedef signed short       s16;
typedef signed int         s32;

/* Items */
#define ITEM_EMPTY                  0xFFF1

/* Player */
#define FN_GET_PLAYER_ACTOR         ((u32 (*)(int idx))(0x02095550 | 1))       /* 4 = the local player */
#define FN_PLAYER_RECORD_CURRENT    ((u8 *(*)(void))(0x02097858 | 1))          /* save record of the local player */
#define PREC_HELD_ITEM              0x220A   /* u16 tool / umbrella in hand */
#define PREC_POCKET_ITEMS           0x1B22   /* u16[15] */
#define PREC_POCKET_FLAGS           0x1B44   /* u32, 2 bits per slot (present / wrapped ...) */
#define POCKET_SLOTS                15

/* Pad (filled once per frame by the pad reader 0x020E8E88), DS key bits */
#define PAD_HELD                    (*(volatile u16 *)0x021F7E80)
#define PAD_PRESSED                 (*(volatile u16 *)0x021F7E82)
#define KEY_A                       0x0001
#define KEY_B                       0x0002
#define KEY_SELECT                  0x0004
#define KEY_START                   0x0008
#define KEY_RIGHT                   0x0010
#define KEY_LEFT                    0x0020
#define KEY_UP                      0x0040
#define KEY_DOWN                    0x0080
#define KEY_R                       0x0100
#define KEY_L                       0x0200
#define KEY_X                       0x0400
#define KEY_Y                       0x0800
#define KEY_DPAD                    0x00F0

/* Field state: 2 while the player has control (pad_to_player 0x0200d720 tests it) */
#define FIELD_CONTROL_STATE         (*(volatile u8 *)0x021C70A0)

#endif
