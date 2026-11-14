"""Check room 8 gates and compare the scripted 6809 mechanism trace with 6502."""
import argparse
from pathlib import Path
from prepare import apple_overlays
from apple_runtime import room_start
from room5 import call
from verify_room_mechanisms import check_final_gates

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dsk', type=Path)
    parser.add_argument('--trace', type=Path)
    args = parser.parse_args()
    _, overlays = apple_overlays(args.dsk.read_bytes())
    initial = room_start(overlays, 7)
    check_final_gates(initial)
    ram = initial.copy()
    expected = bytearray()
    for frame in range(160):
        call(ram, 0x62fa, contact=frame < 70)
        ram[0x1069], ram[0x28] = 0, 1
        call(ram, 0x61ce, contact=70 <= frame < 90)
        call(ram, 0x62bb)
        expected.extend((ram[0x6366], ram[0x6263], ram[0x62f9], ram[0x62f8],
                         ram[0x61cd], 0, *[ram[0x62f4+i] if ram[0x62f0+i] else 0 for i in range(4)]))
    if args.trace:
        actual = args.trace.read_bytes()
        if len(actual) != len(expected):
            raise ValueError('Expected 160 ten-byte records')
        for i, (native, port) in enumerate(zip(expected, actual)):
            if native != port:
                raise AssertionError(f'Frame {i//10+1}, field {i%10}: {native} != {port}')
        print('PASS: 160 updates of platform, pushed object, four falls and enemy diversion')
    else:
        print('Original mechanism sequence executed; provide --trace for comparison')

if __name__ == '__main__':
    main()
