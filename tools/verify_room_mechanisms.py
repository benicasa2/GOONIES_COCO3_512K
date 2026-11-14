"""Check the extracted passages and platform flags against original 6502 code."""
import argparse
from itertools import product
from pathlib import Path

from py65.devices.mpu6502 import MPU
from apple_runtime import room_mechanisms, room_start
from prepare import apple_overlays


def call(ram, address):
    cpu = MPU(memory=ram, pc=address)
    cpu.stPushWord(0x02fe)
    for _ in range(100_000):
        if cpu.pc == 0x02ff:
            return
        cpu.step()
    raise ValueError(f"Apple II routine ${address:04X} did not return")


def check_passages(original, room, data):
    address, timer = (0x617a, 0x61e0) if room == 5 else (0x62b8, 0x635b)
    for x, y, direction, dx, dy in data["portals"]:
        for pressed in (False, True):
            ram = original.copy()
            ram[0x3e], ram[0x49] = x, y
            ram[0x80] = 0xff ^ (direction if pressed else 0)
            ram[0x54] = 6
            ram[0x1069] = 0
            if room == 6:
                ram[0x3f], ram[0x4a] = data["portal_switches"][0]
            call(ram, address)
            expected = ((x+dx)&255, (y+dy)&255, 3) if pressed else (x,y,0)
            if (ram[0x3e], ram[0x49], ram[timer]) != expected:
                raise ValueError(f"Room {room}: passage from {x},{y} mismatches original")
    print(f"Apple II room {room}: {len(data['portals'])} passages match both input states")


def check_platforms(original, data):
    for mask, layout in enumerate(data["platform_layouts"]):
        ram = original.copy()
        for index in range(3):
            ram[0x63d9+index] = 2 if mask & (4 >> index) else 0
        call(ram, 0x636b)
        pointer = ram[0x99] | ram[0x9a] << 8
        actual = [int(ram[pointer+i] == 3) for i in range(19,32)]
        if actual != layout:
            raise ValueError(f"Room 6: platform mask {mask} mismatches original")
    print("Apple II room 6: 8 states x 13 platform flags match")


def check_final_gates(original):
    switches = list(zip(original[0x641c:0x6420], original[0x6420:0x6424]))
    clearance = list(zip(original[0x6416:0x6419], original[0x6419:0x641c]))
    table = original[0x642c:0x643c]
    rows = original[0x99] | original[0x9a] << 8
    for switch_mask, clearance_mask in product(range(16), range(8)):
        selected = {point for i, point in enumerate(switches) if switch_mask & (8 >> i)}
        selected.update(point for i, point in enumerate(clearance) if clearance_mask & (4 >> i))
        ram = original.copy()
        cpu = MPU(memory=ram, pc=0x6367)
        cpu.stPushWord(0x02fe)
        for _ in range(100_000):
            if cpu.pc == 0x02ff:
                break
            if cpu.pc == 0x0af6:
                # Inject the contact outcome, then let the gate code update
                # the display stamps and collision table as it normally does.
                hit = (ram[0x1064], ram[0x1065]) in selected
                cpu.p = (cpu.p & ~1) | hit
                cpu.pc = (cpu.stPopWord() + 1) & 0xffff
            else:
                cpu.step()
        else:
            raise ValueError("Original final gate routine did not return")
        mask = table[switch_mask] | clearance_mask
        floor = original[0x6460:0x6463]
        ceiling = original[0x6463:0x6466]
        for i, (floor_row, ceiling_row) in enumerate(zip(floor, ceiling)):
            expected = (4, 0x80) if mask & (4 >> i) else (3, 2)
            if (ram[rows + floor_row], ram[rows + ceiling_row]) != expected:
                raise ValueError(f"Final gate {i} differs for masks {switch_mask}, {clearance_mask}")
    print("Apple II room 8: 128 switch and clearance combinations match")

def check_lives(original):
    for timer, lives, destination, result, pose in (
        (1, 5, 0x02ff, 5, 0x1c),
        (7, 5, 0x02ff, 5, 0x1c),
        (8, 5, 0x02ff, 5, 0x1d),
        (15, 5, 0x02ff, 5, 0x1d),
        (16, 1, 0x0847, 0, None),
        (16, 0, 0x05ff, 255, None),
    ):
        ram = original.copy()
        ram[0x106a], ram[0x1052] = timer, lives
        cpu = MPU(memory=ram, pc=0x09ea)
        cpu.stPushWord(0x02fe)
        for _ in range(100_000):
            if cpu.pc in (0x02ff, 0x0847, 0x05ff):
                break
            cpu.step()
        if (cpu.pc, ram[0x1052]) != (destination, result):
            raise ValueError("Original life transition differs from expected state")
        if pose is not None and (ram[0x54], ram[0x106a]) != (pose, timer + 1):
            raise ValueError(f"Original death pose or counter differs: {timer}, {ram[0x54]}, {ram[0x106a]}, {cpu.x}")
    print("Apple II death handler: timing, both poses, zero lives and game-over branch match")


def check_crushers(original):
    ram = original.copy()
    heights, timers, returning = [21]*3, [0, 1, 2], [False]*3
    for _ in range(120):
        cpu = MPU(memory=ram, pc=0x60c4)
        for _ in range(20_000):
            if cpu.pc == 0x6119:
                break
            if cpu.pc == 0x833b:
                cpu.pc = (cpu.stPopWord() + 1) & 0xffff
            else:
                cpu.step()
        else:
            raise ValueError(f"Original crusher loop did not finish at {cpu.pc:04X}")
        for index in range(3):
            timers[index] -= 1 if returning[index] else 6
            if timers[index] < 0:
                timers[index] = index
                heights[index] += -1 if returning[index] else 3
                if heights[index] >= 39:
                    returning[index] = True
                if heights[index] < 25:
                    returning[index] = False
        if (ram[0x65bb:0x65be], ram[0x65c5:0x65c8],
                [bool(value) for value in ram[0x65c0:0x65c3]]) != (heights, timers, returning):
            raise ValueError("Original crusher timers differ from expected state")
    print("Apple II room 3: all three timed crusher paths match for 120 frames")

def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("dsk", type=Path)
    args = cli.parse_args()
    _, overlays = apple_overlays(args.dsk.read_bytes())
    for index in (4,5):
        original = room_start(overlays, index)
        data = room_mechanisms(index, original)
        check_passages(original, index+1, data)
        if index == 5:
            check_platforms(original, data)
    check_final_gates(room_start(overlays, 7))
    check_lives(room_start(overlays, 0))
    check_crushers(room_start(overlays, 2))


if __name__ == "__main__":
    main()


