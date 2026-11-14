"""Recover the fourth overlay's moving piece and controls from 6502 code."""
from py65.devices.mpu6502 import MPU


def call(ram, address, *, draw=False):
    cpu = MPU(memory=ram, pc=address)
    cpu.x = 2
    cpu.stPushWord(0x02fe)
    for _ in range(30_000):
        if cpu.pc == 0x02ff:
            return
        if cpu.pc in (0x142e, 0x15d0, 0x833b) or (cpu.pc == 0x8027 and not draw):
            cpu.pc = (cpu.stPopWord() + 1) & 0xffff
        else:
            cpu.step()
    raise ValueError(f"Room 4 routine at ${address:04X} did not return")


def motion(initial, convert_x):
    # Actor slot 2 position, pose, velocity, terrain contacts and direction.
    fields = (0x2a, 0x35, 0x40, 0x4b, 0x56, 0x6c, 0x77, 0x82, 0x8d)

    def state(ram):
        return tuple(ram[address] for address in fields)

    states = [state(initial)]
    ids = {states[0]: 0}
    edges = []
    for current in states:
        row = []
        for mask in range(16):
            ram = initial.copy()
            for address, value in zip(fields, current):
                ram[address] = value
            for i in range(9):
                ix = initial[0x62a9+i]
                source = 0x62b2 if mask & (1 << (i//3)) else 0x62bb
                ram[0x645a+ix] = initial[source+i]
            ram[0x627f] = mask >> 3
            call(ram, 0x62c4)
            new = state(ram)
            if new not in ids:
                ids[new] = len(states)
                states.append(new)
            event = int(ram[0x61dc] != initial[0x61dc])
            event |= 2 * int(ram[0x621d] != initial[0x621d])
            row.append((ids[new], event))
        edges.append(row)
        if len(states) * 5 >= 0x2000:
            raise ValueError("Room 4 motion graph exceeds its bank")

    split = 720
    branches_at = 0xF10

    def pointer(edge):
        destination, event = edge
        page, index = divmod(destination, split)
        return (0x100 + 5*index | event << 13 | page << 15).to_bytes(2, "big")

    for start in (0, split):
        records, branches = bytearray(), bytearray()
        for current, row in zip(states[start:start+split], edges[start:start+split]):
            records.extend((convert_x(current[2]), current[3]))
            records.extend(pointer(row[0]))
            if len(set(row)) == 1:
                records.append(0)
                continue
            for bit in (1, 2, 4, 8):
                if all(edge == row[mask & bit] for mask, edge in enumerate(row)):
                    break
            else:
                raise ValueError("Room 4 branch depends on multiple contacts")
            records.append(len(branches)//3 + 1)
            branches.append(bit)
            branches.extend(pointer(row[bit]))
        if len(records) > branches_at - 0x100 or branches_at + len(branches) > 0x1000:
            raise ValueError("Room 4 motion records exceed their bank")
        yield records.ljust(branches_at - 0x100, bytes(1)) + branches


def graphic_groups(initial):
    """Render switches, lower bumper, removable ledges and counter."""
    for group, count in ((0, 8), (1, 2), (2, 4), (3, 13)):
        frames = []
        for i in range(count):
            ram = initial.copy()
            if group == 0:
                call(ram, 0x6290)
                for bit, routine in enumerate((0x60fe, 0x6102, 0x6106)):
                    if i & (1 << bit):
                        call(ram, routine)
                call(ram, 0x611f, draw=True)
            elif group == 1:
                # Start immediately after the original player-contact test.
                call(ram, 0x623d if i else 0x6241, draw=True)
            elif group == 2:
                ram[0x621d] = i
                call(ram, 0x61ed, draw=True)
            else:
                ram[0x61dc] = i if i < 7 else 0
                ram[0x61cd] = i-6 if i >= 7 else 0
                call(ram, 0x618e, draw=True)
            frames.append(bytes(ram[0x2000:0x4000]))
        yield frames
