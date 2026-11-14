"""Lift the verified first-free-slot loop to a small 6809 ABI."""
import argparse
from pathlib import Path

ENTRY = 0x0951
LOAD = 0x0800
PATTERN = bytes.fromhex("a000b91d00d0021860c8c00b90f43860")


def translate(overlay):
    body = overlay[ENTRY-LOAD:ENTRY-LOAD+len(PATTERN)]
    # This rule matches the loop and every branch target, with a variable
    # table operand and bound. Other flow needs a separate reviewed rule.
    if len(body) != len(PATTERN) or body[:3] != PATTERN[:3] or body[5:11] != PATTERN[5:11] or body[12:] != PATTERN[12:]:
        raise ValueError("Unsupported 6502 loop at $0951")
    bound = body[11]
    if not 1 <= bound <= 127:
        raise ValueError("The 6809 B,X index is signed")
    table = int.from_bytes(body[3:5], "little")
    return f"""; Apple II $0951, table ${table:04X}, {bound} entries
; X = 6809 table base. B = first free index, or {bound} if full.
; Carry clear means free. A holds the entry last read.
find_free_slot
        clrb
scan_free_slot
        lda     b,x
        beq     slot_free
        incb
        cmpb    #{bound}
        blo     scan_free_slot
        orcc    #1
        rts
slot_free
        andcc   #$FE
        rts
"""


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("apple_overlay", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    args.output.write_text(translate(args.apple_overlay.read_bytes()), encoding="ascii")
