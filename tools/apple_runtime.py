"""Run original Apple II initialization and renderer in a controlled 6502 harness."""

from py65.devices.mpu6502 import MPU

POSES = {
    "pose_p1_walk": 0, "pose_p1_step1": 2, "pose_p1_step2": 4, "pose_p1_idle": 6,
    "pose_p2_walk": 8, "pose_p2_step1": 10, "pose_p2_step2": 12, "pose_p2_idle": 14,
    "pose_enemy_idle": 26, "pose_enemy_walk": 20,
    "pose_death_early": 0x1c, "pose_death_late": 0x1d,
    "pose_cash_first": 0x18, "pose_cash_second": 0x19,
}


class AppleMemory(list):
    page = 0x2000

    def __getitem__(self, address):
        if isinstance(address, int) and 0xc000 <= address <= 0xcfff:
            if address in (0xc054, 0xc055):
                self.page = 0x2000 + (address - 0xc054) * 0x2000
            return 0
        return super().__getitem__(address)


def room_start(overlays, room):
    ram = AppleMemory([0] * 65536)

    def load(index):
        address, _, payload = overlays[index]
        ram[address:address+len(payload)] = payload

    for index in (9, 10, 13):
        load(index)
    # Substitute sector I/O and the ROM delay only. The game's init runs.
    ram[0x0625] = ram[0xfca8] = 0x60
    ram[0x1057] = room
    cpu = MPU(memory=ram, pc=0x0824)
    for _ in range(900_000):
        if cpu.pc == 0x0625:
            load(cpu.x)
        if cpu.pc == 0x086a:
            return ram
        if cpu.pc < 0xc000 and ram[cpu.pc] == 0:
            raise ValueError(f"Room {room + 1}: unexpected BRK at ${cpu.pc:04X}")
        cpu.step()
    raise ValueError(f"Room {room + 1}: original init did not reach main loop")


def initial_actors(ram):
    return list(zip(ram[0x1d:0x28], ram[0x3e:0x49], ram[0x49:0x54], ram[0x8b:0x96]))


def exit_zone(ram):
    code = bytes(ram[0x6000:0x7000])
    signature = bytes.fromhex("8d54104c3f08")
    index = code.index(signature)
    window = code[index-80:index]
    # The last two AABB calls test the two players against the same
    # rectangle. Its constants are written to $1064 through $1067.
    first = window.rindex(bytes.fromhex("8d6410")) - 2
    values = {}
    value = None
    p = first
    while p < len(window) and len(values) < 4:
        if window[p] == 0xa9:
            value = window[p+1]
            p += 2
        elif window[p] == 0x8d and window[p+2] == 0x10:
            values[window[p+1]] = value
            p += 3
        else:
            break
    if sorted(values) != [0x64, 0x65, 0x66, 0x67] or code[index-2] != 0xa9:
        raise ValueError("Unexpected Apple exit routine")
    return (values[0x64], values[0x65], values[0x66], values[0x67],
            code[index-1], 0x6000 + index)


def room_mechanisms(index, ram):
    """Room-local tables from the loaded Apple II overlay."""
    if index == 4:
        base, count = 0x658f, 6
        return {"portals": [tuple(ram[base+col*count+i] for col in range(5))
                            for i in range(count)]}
    if index != 5:
        return {}

    layouts = []
    for mask in range(8):
        ptr = int.from_bytes(bytes(ram[0x63de+2*mask:0x63e0+2*mask]), "little")
        entries = ram[ptr:ptr+13]
        if len(entries) != 13 or any(value not in (3, 0x83) for value in entries):
            raise ValueError("Unexpected platform flags at the room 6 dispatch table")
        # $6393 writes in descending terrain-row order, $1f through $13.
        layouts.append([int(value == 3) for value in entries])
    return {
        "portals": [(ram[0x635d+i], ram[0x635f+i], ram[0x6365+i],
                     ram[0x6361+i], ram[0x6363+i]) for i in range(2)],
        "portal_switches": list(zip(ram[0x6367:0x6369], ram[0x6369:0x636b])),
        "pressure_plates": [(x, 0x79) for x in ram[0x615d:0x6160]],
        "platform_layouts": layouts,
    }


def render_pose(initial_ram, pose):
    ram = initial_ram.copy()
    ram[0x2000:0x6000] = [0] * 0x4000
    # Original X=43 maps to HGR X=70. Y is the top of the sprite.
    ram[0x3e], ram[0x49], ram[0x54], ram[0x1063] = 43, 64, pose, 0
    cpu = MPU(memory=ram, pc=0x0ab6)
    cpu.stPushWord(0x02fe)
    for _ in range(20_000):
        if cpu.pc == 0x02ff:
            break
        cpu.step()
    else:
        raise ValueError(f"Pose {pose}: original renderer did not return")

    return bytes(ram[0x2000:0x4000])


def ending_frames(overlays):
    """Execute the victory overlay until it hands control back to overlay 1."""
    ram = room_start(overlays, 8)
    cpu = MPU(memory=ram, pc=0x086a)
    for _ in range(5_000_000):
        if cpu.pc == 0x083f:
            if ram[0x1054] != 0:
                raise ValueError("Victory overlay did not return to room 1")
            return
        if cpu.pc == 0x086a:
            yield bytes(ram[ram.page:ram.page + 8192])
        cpu.step()
    raise ValueError("Victory overlay did not finish")


def final_gate_frames(initial):
    """Run the original HGR stamp routine for both positions of each gate."""
    for gate in (2, 1, 0):
        for pointers in (0x63d9, 0x63df):
            ram = initial.copy()
            ram[0x12] = ram[0x6424 + gate]
            ram[0x13] = ram[0x6427 + gate]
            ram[0x15:0x17] = ram[pointers + 2 * gate:pointers + 2 * gate + 2]
            ram[0x1063] = 0
            cpu = MPU(memory=ram, pc=0x8027)
            cpu.stPushWord(0x02fe)
            for _ in range(100_000):
                if cpu.pc == 0x02ff:
                    yield bytes(ram[0x2000:0x4000])
                    break
                cpu.step()
            else:
                raise ValueError("Final gate stamp did not return")

def life_frames(initial):
    def call(ram, address, accumulator=0):
        cpu = MPU(memory=ram, pc=address)
        cpu.a = accumulator
        cpu.stPushWord(0x02fe)
        for _ in range(20_000):
            if cpu.pc == 0x02ff:
                return
            cpu.step()
        raise ValueError("Original life HUD renderer did not return")

    for lives in range(10):
        ram = initial.copy()
        ram[0x1b91] = 0x80 | lives
        call(ram, 0x19b4, 4)
        yield bytes(ram[0x2000:0x4000])
    ram = initial.copy()
    call(ram, 0x1474)
    call(ram, 0x19b4, 3)
    call(ram, 0x19b4, 8)
    yield bytes(ram[0x2000:0x4000])


def crusher_frames(initial):
    for slot in range(4):
        ram = initial.copy()
        ram[0x2000:0x6000] = [0] * 0x4000
        ram[0x12] = ram[0x659e + slot]
        ram[0x13] = 32
        pointer = 0x6ac1 + 2 * slot if slot < 3 else 0x6ac1
        ram[0x15:0x17] = ram[pointer:pointer + 2]
        ram[0x1063] = 0
        cpu = MPU(memory=ram, pc=0x8027)
        cpu.stPushWord(0x02fe)
        for _ in range(30_000):
            if cpu.pc == 0x02ff:
                yield bytes(ram[0x2000:0x4000])
                break
            cpu.step()
        else:
            raise ValueError("Original crusher renderer did not return")


def second_room_frames(initial):
    """Extract trap patches and door patches from their original renderers."""
    switch_points = list(zip(initial[0x65d7:0x65da], initial[0x65da:0x65dd]))
    for entry, states in ((0x64be, [(0, mask) for mask in range(8)]),
                          (0x654d, [(0, 0), (0, 2), *((frame, 0) for frame in range(1, 5))])):
        frames = []
        for gate_frame, mask in states:
            # The opening images are cumulative stamps over the same HGR page.
            if gate_frame <= 1:
                ram = initial.copy()
            ram[0x65d5], ram[0x65d6], ram[0x1073] = mask, gate_frame, 0
            selected = {point for index, point in enumerate(switch_points) if mask & (1 << index)}
            cpu = MPU(memory=ram, pc=entry)
            cpu.stPushWord(0x02fe)
            for _ in range(100_000):
                if cpu.pc == 0x02ff or (entry == 0x64be and cpu.pc == 0x654d):
                    frames.append(bytes(ram[0x2000:0x4000]))
                    break
                if cpu.pc == 0x0af6:
                    hit = (ram[0x1064], ram[0x1065]) in selected
                    cpu.p = (cpu.p & ~1) | hit
                    cpu.pc = (cpu.stPopWord() + 1) & 0xffff
                else:
                    cpu.step()
            else:
                raise ValueError("Original room 2 renderer did not return")
        yield frames


def room2_motion(initial):
    """Trace the native moving hazard until its six state bytes repeat."""
    ram = initial.copy()
    seen = {}
    frames = []
    while True:
        state = tuple(ram[0x661d:0x6623])
        if state in seen:
            return frames, seen[state]
        if len(frames) >= 2048:
            raise ValueError("Room 2 motion did not repeat")
        seen[state] = len(frames)
        draws, hits = [], []
        cpu = MPU(memory=ram, pc=0x6292)
        cpu.stPushWord(0x02fe)
        for _ in range(20_000):
            if cpu.pc == 0x02ff:
                frames.append((tuple(draws), tuple(hits)))
                break
            if cpu.pc == 0x8027:
                draws.append((ram[0x12], ram[0x13], ram[0x15] | ram[0x16] << 8))
            elif cpu.pc == 0x0af6:
                if cpu.y == 0:
                    hits.append(tuple(ram[0x1064:0x1068]))
                cpu.p &= ~1
            else:
                cpu.step()
                continue
            cpu.pc = (cpu.stPopWord() + 1) & 0xffff
        else:
            raise ValueError("Original moving hazard did not return")


def room2_motion_stamp(initial, column, pointer):
    ram = initial.copy()
    ram[0x2000:0x6000] = [0] * 0x4000
    ram[0x12], ram[0x13], ram[0x1063] = column, 32, 0
    ram[0x15:0x17] = pointer.to_bytes(2, "little")
    cpu = MPU(memory=ram, pc=0x8027)
    cpu.stPushWord(0x02fe)
    for _ in range(30_000):
        if cpu.pc == 0x02ff:
            return bytes(ram[0x2000:0x4000])
        cpu.step()
    raise ValueError("Original moving hazard stamp did not return")


def launcher_travel(initial):
    """Trace $60AB with no players in the firing lane."""
    def trace(start_lane, arrivals):
        ram = initial.copy()
        ram[0x65d6] = 1
        ram[0x61a3] = start_lane
        ram[0x61a1] = ram[0x61a4+start_lane]
        lane = start_lane
        travel = bytearray()
        paths = []
        for _ in range(4000):
            cpu = MPU(memory=ram, pc=0x60ab)
            cpu.x = 2
            cpu.stPushWord(0x02fe)
            for _ in range(10_000):
                if cpu.pc == 0x02ff:
                    break
                if cpu.pc == 0x0af6:
                    cpu.p &= ~1
                    cpu.pc = (cpu.stPopWord() + 1) & 0xffff
                else:
                    cpu.step()
            else:
                raise ValueError("Original launcher update did not return")
            current_lane = ram[0x61a3] & 15
            if current_lane != lane:
                lane = current_lane
                travel.clear()
            hold, y = ram[0x61a2], ram[0x4b]
            if hold == 0:
                travel.append(y)
            elif hold == 2:
                if not travel or y != travel[-1]:
                    raise ValueError("Unexpected movement during launcher arrival")
                paths.append((lane, bytes(travel)))
                if len(paths) == arrivals:
                    return paths
        raise ValueError("Original launcher did not reach all requested lanes")

    initial_paths = [None] * 16
    second_paths = [None] * 16
    steady_paths = dict(trace(0, 17)[1:])
    for start in range(16):
        first, second, *rest = trace(start, 19)
        initial_paths[first[0]] = first[1]
        second_paths[second[0]] = second[1]
        if any(steady_paths[lane] != path for lane, path in rest):
            raise ValueError("Launcher movement did not settle into its repeating lanes")
    return initial_paths + second_paths + [steady_paths[lane] for lane in range(16)]


def launcher_frames(initial):
    for table, index, column in ((0x6195, 0, 0), (0x6195, 1, 0),
                                 (0x6195, 2, 0), (0x6195, 3, 0),
                                 (0x6256, 0, 12), (0x6256, 2, 12)):
        ram = initial.copy()
        ram[0x2000:0x6000] = [0] * 0x4000
        ram[0x12], ram[0x13], ram[0x1063] = column, 32, 0
        pointer = table + 2*index
        ram[0x15:0x17] = ram[pointer:pointer+2]
        cpu = MPU(memory=ram, pc=0x8027)
        cpu.stPushWord(0x02fe)
        for _ in range(30_000):
            if cpu.pc == 0x02ff:
                yield bytes(ram[0x2000:0x4000])
                break
            cpu.step()
        else:
            raise ValueError("Original launcher renderer did not return")


def cooler_frames(initial):
    """Render the original fireplace first and then the falling cooler."""
    phases = [(state, phase, 0) for state in range(6) for phase in range(4)]
    for state, phase, out in phases + [(5, 0, 1)]:
        ram = initial.copy()
        ram[0x6451] = state
        ram[0x6452] = out
        ram[0x629e] = (phase - 1) & 0xff
        for entry in (0x6259, 0x642d):
            cpu = MPU(memory=ram, pc=entry)
            cpu.stPushWord(0x02fe)
            for _ in range(30_000):
                if cpu.pc == 0x02ff:
                    break
                cpu.step()
            else:
                raise ValueError("Original cooler or fireplace renderer did not return")
        yield bytes(ram[0x2000:0x4000])



def room3_item_frames(initial):
    """Capture the locked passage and both states of the blinking pickup."""
    for picked_up, timer in ((0, 1), (0, 8), (1, 8)):
        ram = initial.copy()
        ram[0x6565], ram[0x65cc] = picked_up, timer
        cpu = MPU(memory=ram, pc=0x64f1)
        cpu.stPushWord(0x02fe)
        for _ in range(30_000):
            if cpu.pc == 0x02ff:
                yield bytes(ram[0x2000:0x4000])
                break
            if cpu.pc == 0x0af6:
                cpu.p &= ~1
                cpu.pc = (cpu.stPopWord() + 1) & 0xffff
            else:
                cpu.step()
        else:
            raise ValueError("Original room 3 item renderer did not return")
