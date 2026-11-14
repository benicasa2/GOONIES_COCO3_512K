"""Execute the fifth room's native enemies and render its trap states."""
from itertools import groupby
from py65.devices.mpu6502 import MPU


def call(ram, address, slot=0, contact=False):
    cpu = MPU(memory=ram, pc=address)
    cpu.x = slot
    cpu.stPushWord(0x02fe)
    hit = False
    for _ in range(30_000):
        if cpu.pc == 0x02ff:
            return hit
        if cpu.pc == 0x0af6 and cpu.y < 2:
            hit = True
            cpu.p = (cpu.p & ~1) | int(contact)
        elif cpu.pc not in (0x142e, 0x833b):
            cpu.step()
            continue
        cpu.pc = (cpu.stPopWord() + 1) & 0xffff
    raise ValueError(f"Room 5 routine at ${address:04X} did not return")


def tracks(initial):
    for path in range(4):
        ram = initial.copy()
        ram[0x1071], ram[0x60b1], ram[0x7de4], ram[0xbe01] = 0, 0, 0, path
        call(ram, 0x1825)
        flying = [(ram[0x40], ram[0x4b], 32)]
        start = None
        for _ in range(400):
            tested = call(ram, 0x173c, 2)
            if not ram[0x1070]:
                break
            born = ram[0x20] == 8 and start is None
            if born:
                start = egg_state(ram)
            pose = ram[0x56] if not ram[0x56] & 128 else 0
            flying.append((ram[0x40], ram[0x4b], pose | (128 if tested else 0) | (64 if born else 0)))
        else:
            raise ValueError("Room 5 flying enemy did not finish its path")
        if start is None:
            raise ValueError("Room 5 flying enemy did not drop an egg")
        yield flying, start


EGG_FIELDS = (0x41, 0x4c, 0x2b, 0x36, 0x57, 0x83, 0x8e)


def egg_state(ram):
    return tuple(ram[address] for address in EGG_FIELDS)


def egg_motion(initial, starts):
    """Native type-8 movement with independent neutral, right and left inputs."""
    ram = initial.copy()
    states = list(dict.fromkeys(starts))
    ids = {state: i for i, state in enumerate(states)}
    records = bytearray()
    for state in states:
        edges = []
        for command, apple in enumerate((31, 23, 27)):
            for address, value in zip(EGG_FIELDS, state):
                ram[address] = value
            ram[0x20], ram[0x6d], ram[0x1074], ram[0x80] = 8, 112, 1, apple
            ram[0x60b1] = 0
            ram[0x615f:0x6161] = [0, 0]
            call(ram, 0x6272, 3, contact=bool(command))
            if not ram[0x20]:
                edges.append(0x4000)
                continue
            new = egg_state(ram)
            # Both egg poses have the same collision dimensions. Keep the
            # native visibility bit while timing the late pose separately.
            if new not in ids:
                ids[new] = len(states)
                states.append(new)
            edges.append(ids[new])
        if state[4] & 128:
            edges[0] |= 0x8000
        records.extend(state[:2])
        for edge in edges:
            records.extend(edge.to_bytes(2, "big"))
        if len(states) > 1024:
            raise ValueError("Room 5 egg motion exceeds four pages")
    pages = [records[offset:offset+2048] for offset in range(0, len(records), 2048)]
    return pages, [ids[start] for start in starts]


def hatch_paths(initial):
    for path in range(4):
        x = int.from_bytes(bytes(initial[0x6530+2*path:0x6532+2*path]), "little")
        y = int.from_bytes(bytes(initial[0x6538+2*path:0x653a+2*path]), "little")
        result = bytearray()
        for i in range(32):
            result.extend((initial[x+i], initial[y+i]))
            if initial[y+i] == 255:
                break
        else:
            raise ValueError("Room 5 hatch path has no terminator")
        yield result


def graphics(initial):
    for side in range(2):
        frames = []
        for active in range(2):
            for phase in range(3):
                ram = initial.copy()
                ram[0x616d] = phase
                call(ram, 0x611c, side, contact=bool(active ^ side))
                frames.append(bytes(ram[0x2000:0x4000]))
        yield frames
    frames = []
    for count in range(5):
        ram = initial.copy()
        ram[0x60b1] = count
        call(ram, 0x608a)
        frames.append(bytes(ram[0x2000:0x4000]))
    yield frames


def shadow(initial):
    ram = initial.copy()
    ram[0x2000:0x6000] = [0] * 0x4000
    ram[0x1070], ram[0x56], ram[0x6c] = 1, 32, 1
    ram[0x40], ram[0x4b] = 43, 64
    call(ram, 0x61e2)
    return bytes(ram[0x2000:0x4000])


def pack_track(frames):
    result = bytearray()
    for frame, group in groupby(frames):
        length = sum(1 for _ in group)
        while length:
            run = min(length, 127)
            result.extend((run, *frame))
            length -= run
    result.append(0)
    return bytes(result)

