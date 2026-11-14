"""Audit room 6 mechanisms by executing the Apple II overlay and optionally compare a 6809 trace."""
import argparse
from pathlib import Path
from prepare import apple_overlays
from apple_runtime import room_start, room_mechanisms
from room5 import call
from verify_room_mechanisms import check_passages, check_platforms

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dsk", type=Path)
    parser.add_argument("--trace", type=Path, help="8000-byte trace from test_sixth_room")
    args = parser.parse_args()
    _, overlays = apple_overlays(args.dsk.read_bytes())
    initial = room_start(overlays, 5)
    data = room_mechanisms(5, initial)
    check_passages(initial, 6, data)
    check_platforms(initial, data)
    for slot in range(2, 11):
        ram = initial.copy()
        assert ram[0x1d + slot] == 12
        index = ram[0x5f + slot]
        plates, poses, contact = set(), set(), False
        for _ in range(350):
            contact |= call(ram, 0x61ca, slot)
            poses.add(ram[0x54 + slot])
            plates.update(i for i in range(3) if ram[0x63d9+i] == 16)
        assert plates == ({index - 3} if 3 <= index < 6 else set())
        assert poses == {43, 44, 45, 46, 47} and contact
        # Inject contact at an actual falling state: native code must kill.
        ram = initial.copy()
        for _ in range(350):
            if call(ram, 0x61ca, slot, contact=True):
                assert ram[0x1d] == 3 and ram[0x106a] != 0
                break
        else:
            raise AssertionError("No falling collision")
        print(f"Apple object {index}: five poses, lethal contact, plates {sorted(plates)}")
    print("Nine falling objects verified; middle three hold plates for 16 updates.")

    if args.trace:
        ram = initial.copy()
        ram[0x7de4] = 0
        expected = bytearray()
        for _ in range(160):
            for slot in range(2, 11):
                call(ram, 0x61ca, slot)
            timers = [max(0, ram[0x63d9+i]-1) for i in range(3)]
            ram[0x63d9:0x63dc] = timers
            mask = sum(4 >> i for i, value in enumerate(timers) if value)
            for slot in range(2, 11):
                expected.extend((ram[0x75+slot], ram[0x3e+slot], ram[0x49+slot],
                                 ram[0x54+slot]-12, ram[0x33+slot]))
            expected.extend((*timers, mask, ram[0x7de4]))
        actual = args.trace.read_bytes()
        if len(actual) != len(expected):
            raise ValueError("Expected 160 records of 50 bytes")
        for index, (native, port) in enumerate(zip(expected, actual)):
            if native != port:
                raise AssertionError(f"Frame {index//50+1}, field {index%50}: {native} != {port}")
        print("PASS: 160 updates x 9 actors; positions, poses, timers, plates and random cursor match")

if __name__ == "__main__":
    main()
