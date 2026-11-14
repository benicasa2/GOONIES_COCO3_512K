"""Reproduce the Apple II sector loads and unpack the C64 loader offline."""
import argparse
from collections import Counter
import hashlib
import json
from itertools import groupby
from pathlib import Path
from extract import d64_files
from hgr_color import coarse_key, color_model, rgb as gime_rgb, signal_keys
from apple_runtime import POSES, cooler_frames, crusher_frames, ending_frames, exit_zone, final_gate_frames, initial_actors, launcher_frames, launcher_travel, life_frames, render_pose, room2_motion, room2_motion_stamp, room3_item_frames, room_mechanisms, room_start, second_room_frames
from room4 import graphic_groups, motion as room4_motion
from room7 import assets as room7_assets
from room8 import assets as room8_assets
from room5 import egg_motion, hatch_paths, graphics as room5_graphics, pack_track, shadow as room5_shadow, tracks as room5_tracks

DOS_SLOT = (0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15)
# Six Apple II HGR artifact colors represented by the CoCo 3 RGB palette.
TERRAIN_INKS = (4, 5, 6, 8)
STRUCTURE = 1
HGR_COLORS = None
APPLE_PALETTE = (0x00, 0x3f, 0x00, 0x3f, 0x29, 0x12, 0x09, 0x3f,
                 0x34, 0x00, 0x00, 0x00, 0x3f, 0x12, 0x3f, 0x00)


def coco_x(x):
    return max(0, min(255, (x - 8) * 2 * 256 // 280))


def spawn_data(actors):
    by_type = {kind: (x, y) for kind, x, y, _ in reversed(actors) if kind}
    enemy = by_type.get(5) or by_type.get(14) or by_type.get(14)
    coords = []
    for x, y in (by_type[1], by_type[2], enemy or (8, 0)):
        coords.extend((min(240, coco_x(x) & ~1), min(y, 170)))
    return bytes([*coords, int(enemy is not None)])


def rotate(data):
    return bytes((byte >> 1) | ((byte & 1) << 7) for byte in data)


def apple_overlays(image):
    def sector(track, physical):
        offset = (track * 16 + DOS_SLOT[physical]) * 256
        if not 0 <= offset <= len(image) - 256:
            raise ValueError("Apple sector outside disk")
        return image[offset:offset + 256]

    boot = bytearray(sector(0, 0))
    boot[5:237] = rotate(boot[5:237])
    stage = b"".join(rotate(sector(0, n)) for n in boot[14:20])
    if stage[0x3ef:0x3f1] != b"\xa5\xc2":
        raise ValueError("Apple loader signature at $05EF differs")
    overlays = []
    for i in range(14):
        address = stage[2+i] + 256 * stage[16+i]
        t, s, length = (stage[base+i] for base in (30, 44, 58))
        sectors = [(t + (j + 15 - s) // 16, stage[0x7e + (s - j) % 16]) for j in range(length)]
        overlays.append((address, sectors, b"".join(sector(*ts) for ts in sectors)))
    return stage, overlays


def c64_unpack(image):
    from py65.devices.mpu6502 import MPU

    program = next(data for name, data, _ in d64_files(image) if name == b"THE GOONIES+")
    load = int.from_bytes(program[:2], "little")
    if program[:13] != bytes.fromhex("01080b08d3079e3230353900a0"):
        raise ValueError("Unexpected BASIC SYS/packer signature")
    cpu = MPU(pc=0x080b)
    cpu.memory[1] = 0x37
    cpu.memory[load:load + len(program) - 2] = program[2:]
    for steps in range(4_000_001):
        if cpu.pc == 0x2000:
            return steps, bytes(cpu.memory)
        cpu.step()
    raise ValueError(f"Unpacker did not reach $2000 (PC=${cpu.pc:04X})")


def collision_rows(game, index, address, payload):
    count = game[0x0f9c - 0x0800 + index]
    tables = []
    for pointer_table in (0x0fa6, 0x0fba, 0x0fce, 0x0fe2, 0x0ff6):
        offset = pointer_table - 0x0800 + 2 * index
        pointer = int.from_bytes(game[offset:offset+2], "little")
        first = pointer - address
        if first < 0 or first + count > len(payload):
            raise ValueError(f"Collision pointer outside overlay {index + 1}")
        tables.append(payload[first:first + count])
    return list(zip(*tables))


def coco_collision(rows, room):
    data = bytearray()
    for index, (kind, x0, y0, x1, y1) in enumerate(rows):
        if room == 5 and 19 <= index <= 31:
            kind = 0x40 + index - 19
        elif kind not in (0, 1, 2, 3, 4, 5):
            kind = 0x7f
        data.extend((kind, coco_x(x0), min(191, y0), coco_x(x1), min(191, y1)))
    data.append(0xff)
    return data


def puzzle_tables(mechanisms, rows, last_room):
    def portal_records(portals):
        result = bytearray()
        for x, y, direction, dx, dy in portals:
            destination = (x + dx) & 0xff
            # Keep X even for the packed-pixel blitter.
            offset = (coco_x(destination) & ~1) - (coco_x(x) & ~1)
            if not -128 <= offset <= 127 or direction not in (4, 8):
                raise ValueError("Room passage does not fit the native movement encoding")
            result.extend((coco_x(x), y, direction, offset & 0xff, dy))
        result.append(0xff)
        return result

    room5, room6 = mechanisms[4:6]
    plat_rows = []
    for _, x0, y, x1, _ in rows[19:32]:
        left, right = x0 - 8 + 10, x1 - 8 + 10
        plat_rows.extend((left, y, right-left+1))
    switches = [(coco_x(x), y) for x, y in zip(last_room[0x641c:0x6420],
                                                last_room[0x6420:0x6424])]
    near_gates = [(coco_x(x), y) for x, y in zip(last_room[0x6416:0x6419],
                                                  last_room[0x6419:0x641c])]
    switches = [(coco_x(x), y) for x, y in zip(last_room[0x641c:0x6420],
                                                last_room[0x6420:0x6424])]
    near_gates = [(coco_x(x), y) for x, y in zip(last_room[0x6416:0x6419],
                                                  last_room[0x6419:0x641c])]
    return "".join(asm_bytes(label, data) for label, data in (
        ("portals5", portal_records(room5["portals"])),
        ("portals6", portal_records(room6["portals"])),
        ("portal_switches6", [v for x, y in room6["portal_switches"] for v in (coco_x(x), y)]),
        ("plates6", [v for x, y in room6["pressure_plates"] for v in (coco_x(x), y)]),
        ("layout6", [v for row in room6["platform_layouts"] for v in row]),
        ("platform_rows6", plat_rows),
    )) + "platform_rows6_end\n" + "".join(asm_bytes(label, data) for label, data in (
        ("switches8", [v for point in switches + near_gates for v in point]),
        ("layout8", last_room[0x642c:0x643c]),
        ("fratelli_zone8", [coco_x(0x5c), 0x75, coco_x(0x84), 0x84]),
        ("pit_zone8", [coco_x(0x89), 0xb2, coco_x(0x9f), 0xb2]),
    )) + "".join(asm_bytes(label, data) for label, data in (
        ("switches8", [v for point in switches + near_gates for v in point]),
        ("layout8", last_room[0x642c:0x643c]),
        ("fratelli_zone8", [coco_x(0x5c), 0x75, coco_x(0x84), 0x84]),
        ("pit_zone8", [coco_x(0x89), 0xb2, coco_x(0x9f), 0xb2]),
    ))


def hgr_stream(data):
    columns = bytearray()
    for i in range(0, len(data) - 1, 2):
        count, value = data[i:i+2]
        if count == 0 and len(columns) == 40 * 192:
            return columns, i
        if count == 0 or len(columns) + count > 40 * 192:
            break
        columns.extend([value] * count)
    raise ValueError("Expected exactly 40 x 192 HGR bytes and a zero terminator")


def convert(data):
    columns, source_bytes = hgr_stream(data)
    packed, native_hgr = convert_columns(columns)
    return packed, native_hgr, source_bytes


def convert_columns(columns):
    packed = bytearray()
    native_hgr = bytearray()
    for y in range(192):
        row = [columns[x * 192 + y] for x in range(40)]
        bits = [(row[x // 7] >> (x % 7)) & 1 for x in range(280)]
        colors = []
        keys = signal_keys(row) if HGR_COLORS else (None,) * 280
        for x, key in enumerate(keys):
            if key is not None:
                if key & 0xfff == 0:
                    colors.append(0)
                    continue
                full, coarse = HGR_COLORS
                match = full.get(key, coarse.get(coarse_key(key)))
                if match is not None:
                    colors.append(match)
                    continue
            if not bits[x]:
                colors.append(0)
            elif (x > 0 and bits[x-1]) or (x < 279 and bits[x+1]):
                colors.append(STRUCTURE)
            elif row[x // 7] & 0x80 and HGR_COLORS:
                colors.append((2, 3)[x % 2])
            else:
                colors.append(TERRAIN_INKS[(row[x // 7] >> 7) * 2 + x % 2])
        native_hgr.extend((colors[x] << 4) | colors[x+1] for x in range(0, 280, 2))
        packed.extend(bytes(10))
        packed.extend(native_hgr[-140:])
        packed.extend(bytes(10))
    return bytes(packed), bytes(native_hgr)


def encode(data):
    encoded = bytearray()
    start = 0
    while start < len(data):
        end = start + 1
        while end < min(start + 255, len(data)) and data[end] == data[start]:
            end += 1
        encoded.extend((end - start, data[start]))
        start = end
    return encoded


def asm_bytes(label, data):
    lines = ["; Generated by prepare.py", label]
    for i in range(0, len(data), 16):
        lines.append("        fcb " + ",".join(f"${value:02X}" for value in data[i:i+16]))
    return "\n".join(lines) + "\n"


def hgr_page_pixels(hgr):
    columns = bytes(hgr[((y & 7) << 10) + ((y & 0x38) << 4) + (y >> 6) * 40 + x]
                    for x in range(40) for y in range(192))
    return convert_columns(columns)[0]


def title_bitmap(path):
    from PIL import Image

    with Image.open(path) as source:
        if source.size != (560, 384):
            raise ValueError("Expected the 2x Apple II title capture (560x384)")
        pixels = list(source.convert("RGB").resize((280, 192), Image.Resampling.NEAREST).getdata())

    histogram = Counter(pixels)
    colors = [gime_rgb(code) for code in range(64)]
    errors = {pixel: [sum((a-b)**2 for a, b in zip(pixel, color)) for color in colors]
              for pixel in histogram}
    palette = [0, 63]
    residuals = {pixel: min(cost[0], cost[63]) for pixel, cost in errors.items()}
    while len(palette) < 16:
        best = min((code for code in range(64) if code not in palette),
                   key=lambda code: sum(count * min(residuals[pixel], errors[pixel][code])
                                        for pixel, count in histogram.items()))
        palette.append(best)
        residuals = {pixel: min(error, errors[pixel][best])
                     for pixel, error in residuals.items()}
    indexes = {pixel: min(range(16), key=lambda i: cost[palette[i]])
               for pixel, cost in errors.items()}
    frame = bytearray()
    margin = bytes(10)
    for y in range(192):
        row = pixels[y*280:(y+1)*280]
        frame.extend(margin)
        frame.extend(indexes[a]*16 + indexes[b] for a, b in zip(row[::2], row[1::2]))
        frame.extend(margin)
    return frame, palette


def patch_runs(image, offsets):
    runs = []
    for offset in offsets:
        if (runs and offset - runs[-1][1] <= 3 and offset - runs[-1][0] < 255
                and offset // 8192 == runs[-1][0] // 8192):
            runs[-1][1] = offset
        else:
            runs.append([offset, offset])
    patch = bytearray()
    for start, end in runs:
        patch.extend(start.to_bytes(2, "big"))
        patch.append(end - start + 1)
        patch.extend(image[start:end + 1])
    patch.append(255)
    return patch


def final_gate_assets(initial, geometry_length):
    base = hgr_page_pixels(initial[0x2000:0x4000])
    frames = iter(map(hgr_page_pixels, final_gate_frames(initial)))
    streams = []
    for closed, opened in zip(frames, frames):
        offsets = [i for i, (a, b, c) in enumerate(zip(base, closed, opened))
                   if a != b or b != c]
        streams.extend(patch_runs(frame, offsets) for frame in (closed, opened))
    pointer = 0x6000 + geometry_length + 2 * len(streams)
    table = bytearray()
    for stream in streams:
        table.extend(pointer.to_bytes(2, "big"))
        pointer += len(stream)
    return table + b"".join(streams)


def color_stamp(frame, left, top, height=22):
    return b"".join(frame[y*160+left:y*160+left+8] for y in range(top, top+height))


def cooler_assets(initial, background, geometry_length):
    base = hgr_page_pixels(initial[0x2000:0x4000])
    frames = list(map(hgr_page_pixels, cooler_frames(initial)))
    offsets = [i for i, values in enumerate(zip(base, *frames)) if len(set(values)) > 1]
    streams = [patch_runs(background, offsets)]
    for frame in frames:
        changed = [offset for offset in offsets if frame[offset] != base[offset]]
        composed = bytearray(background)
        for offset in changed:
            composed[offset] = frame[offset]
        streams.append(patch_runs(composed, changed))
    table = bytearray()
    pointer = 0x6000 + geometry_length + 2*len(streams)
    for stream in streams:
        table.extend(pointer.to_bytes(2, "big"))
        pointer += len(stream)
    return table + b"".join(streams)


def first_room_assets(original):
    from py65.devices.mpu6502 import MPU

    ram = original.copy()
    ram[0x2000:0x6000] = [0] * 0x4000
    cpu = MPU(memory=ram, pc=0x61b6)
    cpu.stPushWord(0x02fe)
    for _ in range(30_000):
        if cpu.pc == 0x02ff:
            break
        cpu.step()
    else:
        raise ValueError("Original chair renderer did not return")
    frame = hgr_page_pixels(ram[0x2000:0x4000])
    left = min(i % 160 for i, value in enumerate(frame) if value)
    chair = color_stamp(frame, left, 66)
    notes = bytearray()
    for pointer, column, left in ((0x652d, 0x23, 135), (0x652d, 0x25, 142), (0x6523, 0x26, 145)):
        ram = original.copy()
        ram[0x2000:0x6000] = [0] * 0x4000
        ram[0x12], ram[0x13], ram[0x1063] = column, 32, 0
        ram[0x15:0x17] = pointer.to_bytes(2, "little")
        cpu = MPU(memory=ram, pc=0x8027)
        cpu.stPushWord(0x02fe)
        for _ in range(30_000):
            if cpu.pc == 0x02ff:
                break
            cpu.step()
        else:
            raise ValueError("Original banknote renderer did not return")
        frame = hgr_page_pixels(ram[0x2000:0x4000])
        notes.extend(color_stamp(frame, left, 32, 4))
    return chair + notes


def launcher_assets(original):
    closed, opened, moving_a, moving_b, shot, burst = map(hgr_page_pixels, launcher_frames(original))
    data = (
        ("launcher_targets", original[0x61a4:0x61b4]),
        ("launcher_shot_y", original[0x61b7:0x61c7]),
        ("launcher_shot_end", original[0x61c7:0x61d7]),
        ("launcher_shot_x", [coco_x(i*4) for i in range(36)]),
        ("launcher_closed_pose", color_stamp(closed, 10, 32)),
        ("launcher_open_pose", color_stamp(opened, 10, 32)),
        ("launcher_open_right", color_stamp(opened, 18, 32)),
        ("launcher_burst_pose", color_stamp(burst, 52, 32)),
        ("launcher_shot_pose", color_stamp(shot, 52, 32)),
        ("launcher_moving_a", color_stamp(moving_a, 10, 32)),
        ("launcher_moving_b", color_stamp(moving_b, 10, 32)),
        ("launcher_moving_right", color_stamp(moving_a, 18, 32)),
    )
    return b"".join(bytes(content) for _, content in data)


def room2_motion_assets(initial):
    frames, loop = room2_motion(initial)
    unique = list(dict.fromkeys(frames))
    if len(unique) > 256:
        raise ValueError("Room 2 motion has too many distinct frames")
    ids = {frame: i for i, frame in enumerate(unique)}
    index = bytes(ids[frame] for frame in frames)
    records, stamps = bytearray(), bytearray()
    sprite_data = {}
    graphics = {}
    stamp_base = 0x6000 + len(index) + 24*len(unique)
    for draws, hits in unique:
        if len(hits) > 2:
            raise ValueError("Unexpected room 2 motion collision record")
        sprites = []
        for col, y, pointer in draws:
            key = col, pointer
            if key not in graphics:
                pixels = hgr_page_pixels(room2_motion_stamp(initial, col, pointer))
                used = [i for i, value in enumerate(pixels) if value]
                left = min(i % 160 for i in used)
                right = max(i % 160 for i in used)
                top = min(used)//160
                height = max(used)//160 - top + 1
                stamps_at_x = []
                for x in range(left, right+1, 8):
                    stamp = bytes([height]) + color_stamp(pixels, x, top, height)
                    if stamp not in sprite_data:
                        sprite_data[stamp] = stamp_base + len(stamps)
                        stamps.extend(stamp)
                    stamps_at_x.append((x, top - 32, sprite_data[stamp]))
                graphics[key] = stamps_at_x
            sprites.extend((x, y+offset_y, address) for x, offset_y, address in graphics[key])
        if len(sprites) > 4:
            raise ValueError("Unexpected room 2 motion drawing record")
        for x, y, address in sprites:
            records.extend((x, y))
            records.extend(address.to_bytes(2, "big"))
        records.extend(bytes([255, 0, 0, 0]) * (4-len(sprites)))
        for x0, y0, x1, y1 in hits:
            records.extend((coco_x(x0), y0, coco_x(x1), y1))
        records.extend(bytes([255, 0, 0, 0]) * (2-len(hits)))
    data = index + records + stamps
    travel_address = 0x6000 + len(data)
    paths = launcher_travel(initial)
    addresses = {}
    travel_table, travel_data = bytearray(), bytearray()
    for path in paths:
        if path not in addresses:
            addresses[path] = travel_address + 2*len(paths) + len(travel_data)
            travel_data.extend(path)
            travel_data.append(255)
        travel_table.extend(addresses[path].to_bytes(2, "big"))
    data += travel_table + travel_data
    if len(data) > 0x2000:
        raise ValueError("Room 2 motion exceeds its bank")
    constants = (f"motion_end equ BG+{len(index)}\n"
                 f"motion_loop equ BG+{loop}\n"
                 f"launcher_travel_table equ ${travel_address:04X}\n")
    return data, constants


def crusher_assets(original):
    data = []
    shapes = []
    for index, hgr in enumerate(crusher_frames(original)):
        frame = hgr_page_pixels(hgr)
        left = min(i % 160 for i, value in enumerate(frame) if value)
        logical = next(x for x in range(256) if (x * 140 // 256) + 10 == left)
        hit_x = original[0x65a2 + index] * 4 + 2
        return_x = original[0x6597 + index] * 4 + 2
        data.extend((logical, coco_x(hit_x), coco_x(hit_x + 4),
                     coco_x(return_x), coco_x(return_x + 1), original[0x65cd + index]))
        shapes.append(color_stamp(frame, left, 32))
    return asm_bytes("crusher_data", data), b"".join(shapes)


def room3_platform(initial):
    from py65.devices.mpu6502 import MPU

    ram = initial.copy()
    ram[0x2000:0x6000] = [0] * 0x4000
    cpu = MPU(memory=ram, pc=0x644b)
    cpu.stPushWord(0x02fe)
    for _ in range(30_000):
        if cpu.pc == 0x02ff:
            break
        cpu.step()
    else:
        raise ValueError("Original platform renderer did not return")
    return bytes(coco_x(x) for x in range(39, 113)) + color_stamp(
        hgr_page_pixels(ram[0x2000:0x4000]), 114, 120)


def room3_rods(initial, background):
    from py65.devices.mpu6502 import MPU

    base = hgr_page_pixels(initial[0x2000:0x4000])
    bank = bytearray(14)
    for rod in range(7):
        lower = rod >= 4
        slot = rod - 4 if lower else rod
        start, end = (0x61c8, 0x61f6) if lower else (0x612c, 0x615b)
        first, last = (72, 92) if slot == 3 else (24, 39)
        frames = []
        for height in range(first, last+1):
            ram = initial.copy()
            ram[0x65bb+slot], ram[0x659a+slot], ram[5] = height, 128-height, slot*2
            cpu = MPU(memory=ram, pc=start)
            cpu.x = slot
            for _ in range(20_000):
                if cpu.pc == end:
                    frames.append(hgr_page_pixels(ram[0x2000:0x4000]))
                    break
                cpu.step()
            else:
                raise ValueError("Original rod renderer did not return")
        changed = [i for i, values in enumerate(zip(base, *frames)) if len(set(values)) > 1]
        left, right = min(i % 160 for i in changed), max(i % 160 for i in changed)
        top, bottom = min(changed)//160, max(changed)//160
        width, height = right-left+1, bottom-top+1
        rows = {}
        indices = bytearray()
        for frame in frames:
            for y in range(top, bottom+1):
                offset = y*160 + left
                row = bytes(frame[i] if frame[i] != base[i] else background[i]
                            for i in range(offset, offset+width))
                indices.append(rows.setdefault(row, len(rows)))
        address = 0x6200 + len(bank)
        bank[2*rod:2*rod+2] = address.to_bytes(2, "big")
        bank.extend((left, top, width, height, first))
        bank.extend((address + 7 + len(indices)).to_bytes(2, "big"))
        bank.extend(indices)
        bank.extend(b"".join(rows))
    return bank


def room3_crank(initial, background):
    from py65.devices.mpu6502 import MPU

    base = hgr_page_pixels(initial[0x2000:0x4000])
    frames = []
    for phase in range(4):
        ram = initial.copy()
        ram[0x65be] = 88 + phase
        cpu = MPU(memory=ram, pc=0x6321)
        cpu.stPushWord(0x02fe)
        for _ in range(20_000):
            if cpu.pc == 0x02ff:
                frames.append(hgr_page_pixels(ram[0x2000:0x4000]))
                break
            cpu.step()
        else:
            raise ValueError("Original crank renderer did not return")
    offsets = [i for i, values in enumerate(zip(base, *frames)) if len(set(values)) > 1]
    table = bytearray()
    streams = bytearray()
    for frame in frames:
        image = bytearray(background)
        for offset in offsets:
            image[offset] = frame[offset]
        table.extend((0x7e08 + len(streams)).to_bytes(2, "big"))
        streams.extend(patch_runs(image, offsets))
    return table + streams


def room3_bat(initial, stone):
    from py65.devices.mpu6502 import MPU

    ram = initial.copy()
    ram[0x6564], ram[0x65be] = 0, stone

    def call(entry):
        cpu = MPU(memory=ram, pc=entry)
        cpu.x = 2
        cpu.stPushWord(0x02fe)
        for _ in range(20_000):
            if cpu.pc == 0x02ff:
                return
            if cpu.pc == 0x0af6:
                cpu.p &= ~1
                cpu.pc = (cpu.stPopWord() + 1) & 0xffff
            else:
                cpu.step()
        raise ValueError("Original bat routine did not return")

    call(0x159b)
    path = bytearray()
    for _ in range(150):
        if ram[0x1f] == 0:
            return path + bytes([255, 0])
        path.extend((coco_x(ram[0x40]) & ~1, ram[0x4b]))
        call(0x14bc)
    raise ValueError("Original bat did not finish its path")


def room3_returns(initial):
    from py65.devices.mpu6502 import MPU

    columns = []
    stamps = bytearray()
    for slot in range(3):
        frames = []
        for table in (0x67c5, 0x6a37):
            ram = initial.copy()
            ram[0x2000:0x6000] = [0] * 0x4000
            ram[0x12], ram[0x13], ram[0x1063] = ram[0x6594+slot], 92, 0
            pointer = table + 2*slot
            ram[0x15:0x17] = ram[pointer:pointer+2]
            cpu = MPU(memory=ram, pc=0x8027)
            cpu.stPushWord(0x02fe)
            for _ in range(30_000):
                if cpu.pc == 0x02ff:
                    break
                cpu.step()
            else:
                raise ValueError("Original returning ram renderer did not return")
            frames.append(hgr_page_pixels(ram[0x2000:0x4000]))
        left = min(i % 160 for frame in frames for i, pixel in enumerate(frame) if pixel)
        columns.append(left)
        for frame in frames:
            stamps.extend(color_stamp(frame, left, 92, 14))
    return asm_bytes("room3_return_columns", columns), stamps


def room3_lift(initial, background):
    from py65.devices.mpu6502 import MPU

    base = hgr_page_pixels(initial[0x2000:0x4000])
    rows = {}
    indexes = bytearray()
    for height in range(73, 109):
        ram = initial.copy()
        ram[0x65ca] = height
        cpu = MPU(memory=ram, pc=0x6269)
        for _ in range(30_000):
            if cpu.pc == 0x62a2:
                break
            cpu.step()
        else:
            raise ValueError("Original lift renderer did not return")
        frame = hgr_page_pixels(ram[0x2000:0x4000])
        for y in range(56, 111):
            start = y*160+128
            row = bytes(frame[i] if frame[i] != base[i] else background[i]
                        for i in range(start, start+15))
            indexes.append(rows.setdefault(row, len(rows)))
    return indexes + b"".join(rows)


def room3_items(initial, background, geometry_length):
    base = hgr_page_pixels(initial[0x2000:0x4000])
    frames = list(map(hgr_page_pixels, room3_item_frames(initial)))
    offsets = [i for i, values in enumerate(zip(base, *frames)) if len(set(values)) > 1]
    streams = []
    for frame in frames:
        image = bytearray(background)
        for offset in offsets:
            image[offset] = frame[offset]
        streams.append(patch_runs(image, offsets))
    pointer = 0x6000 + geometry_length + 2*len(streams)
    table = bytearray()
    for stream in streams:
        table.extend(pointer.to_bytes(2, "big"))
        pointer += len(stream)
    return table + b"".join(streams)


def second_room_assets(initial, geometry_length):
    live_background = hgr_page_pixels(initial[0x2000:0x4000])
    streams = []
    for group in second_room_frames(initial):
        frames = list(map(hgr_page_pixels, group))
        offsets = [i for i, values in enumerate(zip(live_background, *frames))
                   if len(set(values)) > 1]
        for frame in frames:
            streams.append(bytes(patch_runs(frame, offsets)))
    address = 0x6000 + geometry_length + 2*len(streams)
    table = bytearray()
    unique = {}
    payload = bytearray()
    for stream in streams:
        if stream not in unique:
            unique[stream] = address + len(payload)
            payload.extend(stream)
        table.extend(unique[stream].to_bytes(2, "big"))
    return table + payload


def room4_assets(initial):
    base = hgr_page_pixels(initial[0x2000:0x4000])
    groups = []
    used = set()
    for group in graphic_groups(initial):
        frames = list(map(hgr_page_pixels, group))
        offsets = {i for i, values in enumerate(zip(base, *frames))
                   if len(set(values)) > 1}
        if used & offsets:
            raise ValueError("Room 4 graphic layers overlap")
        used.update(offsets)
        groups.extend(bytes(patch_runs(frame, sorted(i for i in offsets if frame[i] != base[i])))
                      for frame in frames)
    patches = groups + [bytes(patch_runs(base, sorted(used)))]
    address = 0x64A0 + 2*len(patches)
    table, payload = bytearray(), bytearray()
    addresses = {}
    for patch in patches:
        if patch not in addresses:
            addresses[patch] = address + len(payload)
            payload.extend(patch)
        table.extend(addresses[patch].to_bytes(2, "big"))
    sprite = color_stamp(hgr_page_pixels(render_pose(initial, 30)), 45, 64, 6)
    constants = f"room4_sprite equ ${address + len(payload):04X}\n"
    return table + payload + sprite, constants


def room4_particle_assets(initial):
    data = bytearray(coco_x(x) for x in range(256))
    data.extend(initial[0xBE00:0xBF00])
    for slot in range(5):
        x, y = initial[0x1620+slot], initial[0x1628+slot]
        data.extend((x, y, x, y, initial[0x1630+slot], 0, 0))
    table = 0x7600 + len(data)
    address = table + 7*3
    paths = bytearray()
    for path in range(7):
        x = int.from_bytes(bytes(initial[0x1638+2*path:0x163a+2*path]), "little")
        y = int.from_bytes(bytes(initial[0x164c+2*path:0x164e+2*path]), "little")
        data.extend(address.to_bytes(2, "big"))
        data.append(initial[0x1660+path])
        for i in range(32):
            paths.extend((initial[x+i], initial[y+i]))
            if initial[y+i] == 255:
                break
        else:
            raise ValueError("Missing Apple II particle waypoint terminator")
        address = table + 7*3 + len(paths)
    data.extend(paths)
    for pose in range(16, 20):
        data.extend(color_stamp(hgr_page_pixels(render_pose(initial, pose)), 45, 64, 6))
    symbols = f"particle_paths equ ${table:04X}\nparticle_poses equ ${address:04X}\n"
    return data, symbols


def native8_assets(initial):
    """Unscaled pose bounds, collision rows and every room-8 actor pose."""
    data = bytearray(0x200)
    data[0x78:0xB4] = bytes(initial[0xE1C:0xE58])
    data[0xB4:0xF0] = bytes(initial[0xE58:0xE94])
    ptr = [initial[a] | initial[a+1] << 8 for a in (0x99,0x9B,0x9D,0x9F,0xA1)]
    assert initial[0x98] == 53
    rows = [tuple(initial[p+i] for p in ptr) for i in range(53)]
    assert not any(row[0] == 6 for row in rows)
    data[0xF0:0xF0+265] = bytes(v for row in rows for v in row)
    for pose in (*range(8), *range(20,30), *range(49,58)):
        data[pose*2:pose*2+2] = (0x6000+len(data)).to_bytes(2,'big')
        data.extend(color_stamp(hgr_page_pixels(render_pose(initial,pose)),45,64))
    assert len(data) <= 0x1500
    return data


def room6_assets(initial, terrain):
    """Type-12 state tables and native poses; share the room-5 renderer ABI."""
    if len(terrain) > 0x400:
        raise ValueError("Room 6 terrain overlaps actors")
    data = bytearray(terrain).ljust(0x400, bytes(1))
    for slot in range(2, 11):
        index = initial[0x5f+slot]
        if initial[0x1d+slot] != 12:
            raise ValueError("Expected nine native falling actors")
        data.extend((initial[0x3e+slot], initial[0x49+slot],
                     initial[0x62af+index], initial[0x75+slot], index))
    data = data.ljust(0x480, bytes(1))
    data.extend((coco_x(initial[0x616a]), initial[0x6174],
                 coco_x(initial[0x616f]), initial[0x6174]))
    data = data.ljust(0x57a, bytes(1))
    data.extend(coco_x(x) for x in range(256))
    for pose in range(43, 48):
        frame = hgr_page_pixels(render_pose(initial, pose))
        for x in (45, 53):
            data.extend(color_stamp(frame, x, 64, 14))
    if len(data) > 0xc00:
        raise ValueError("Room 6 graphics overlap its runtime")
    return bytes(data)


def room5_assets(initial):
    flying, starts = zip(*room5_tracks(initial))
    pages, egg_starts = egg_motion(initial, starts)
    data = bytearray(16)
    for path, (frames, start) in enumerate(zip(flying, egg_starts)):
        address = 0x6000 + len(data)
        data[4*path:4*path+4] = address.to_bytes(2, "big") + start.to_bytes(2, "big")
        data.extend(pack_track(frames))
    hatch_table = 0x6000 + len(data)
    data.extend(bytes(8))
    for path, waypoints in enumerate(hatch_paths(initial)):
        address = 0x6000 + len(data)
        offset = hatch_table - 0x6000 + 2*path
        data[offset:offset+2] = address.to_bytes(2, "big")
        data.extend(waypoints)
    xmap = 0x6000 + len(data)
    data.extend(coco_x(x) for x in range(256))
    poses = 0x6000 + len(data)
    for pose in (31, 32, 33, 34, 35, 36, 37, 38, 40, 41, 42):
        frame = hgr_page_pixels(render_pose(initial, pose))
        for x in (45, 53):
            data.extend(color_stamp(frame, x, 64, 14))
    base = hgr_page_pixels(initial[0x2000:0x4000])
    patches, used = [], set()
    for group in room5_graphics(initial):
        frames = list(map(hgr_page_pixels, group))
        offsets = {i for i, values in enumerate(zip(base, *frames))
                   if len(set(values)) > 1}
        if used & offsets:
            raise ValueError("Room 5 graphics layers overlap")
        used.update(offsets)
        patches.extend(bytes(patch_runs(frame, sorted(i for i in offsets if frame[i] != base[i])))
                       for frame in frames)
    patches.append(bytes(patch_runs(base, sorted(used))))
    patch_table = 0x6000 + len(data)
    address = patch_table + 2*len(patches)
    unique, payload = {}, bytearray()
    for patch in patches:
        if patch not in unique:
            unique[patch] = address + len(payload)
            payload.extend(patch)
        data.extend(unique[patch].to_bytes(2, "big"))
    data.extend(payload)
    shadow_address = 0x6000 + len(data)
    data.extend(color_stamp(hgr_page_pixels(room5_shadow(initial)), 51, 77, 7))
    data.append(0)
    if len(data) > 0x2000:
        raise ValueError(f"Room 5 assets exceed staging bank ({len(data)})")
    symbols = (f"room5_xmap equ ${xmap:04X}\n"
               f"room5_poses equ ${poses:04X}\n"
               f"room5_patch_table equ ${patch_table:04X}\n"
               f"room5_track_end equ ${0x6000+len(data)-1:04X}\n"
               f"room5_shadow equ ${shadow_address:04X}\n"
               f"room5_hatch_table equ ${hatch_table:04X}\n"
               f"room5_code equ ${0x6000+len(data):04X}\n")
    return data, symbols, pages


def ending_assets(overlays, output):
    groups = ((hgr_page_pixels(hgr), len(list(run))) for hgr, run in groupby(ending_frames(overlays)))
    previous, initial = next(groups)
    (output / "ending.4bpp").write_bytes(previous)
    banks = [bytearray()]
    frames = initial
    patches = 0
    for image, duration in groups:
        if not 2 <= duration < 255:
            raise ValueError("Ending frame duration cannot use the two-buffer player")
        offsets = (i for i, (new, old) in enumerate(zip(image, previous)) if new != old)
        patch = bytes([duration]) + patch_runs(image, offsets)
        if len(banks[-1]) + len(patch) >= 8192:
            banks[-1].append(255)
            banks.append(bytearray())
        banks[-1].extend(patch)
        previous = image
        frames += duration
        patches += 1
    banks[-1].append(0)
    if initial != 1 or len(banks) != 5 or len(banks[4]) > 0x1f00:
        raise ValueError("Ending does not fit the reserved banks")
    for i, bank in enumerate(banks[:4]):
        (output / f"ending-{i}.bin").write_bytes(bank.ljust(8192, bytes(1)))
    overflow = output / "scene4-collision.bin"
    metadata = overflow.read_bytes()
    if len(metadata) > 0x100:
        raise ValueError("Room 4 metadata overlaps ending animation")
    overflow.write_bytes(metadata.ljust(0x100, bytes(1)) + banks[4])
    return {"overlay": 8, "frames": frames, "patches": patches, "patch_banks": len(banks)}


def main():
    global HGR_COLORS
    cli = argparse.ArgumentParser()
    cli.add_argument("dsk", type=Path)
    cli.add_argument("build", type=Path)
    cli.add_argument("--d64", type=Path)
    args = cli.parse_args()
    args.build.mkdir(parents=True, exist_ok=True)
    stage, overlays = apple_overlays(args.dsk.read_bytes())
    (args.build / "apple-stage.bin").write_bytes(stage)
    (args.build / "apple-game.bin").write_bytes(overlays[9][2])
    reference = Path(__file__).resolve().parents[1] / "assets" / "gameplay-apple2.png"
    room1_hgr, _ = hgr_stream(overlays[0][2])
    codes, full, coarse = color_model(room1_hgr, reference)
    HGR_COLORS = full, coarse
    manifest = {"overlays": [], "decoded_scenes": [], "palette": {
        "reference": reference.name,
        "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "signal_patterns": len(full),
        "gime_codes": codes, "source_geometry": [280, 192], "runtime_geometry": [280, 192],
        "framebuffer_geometry": [320, 192], "left_margin": 20,
    }}
    initial_ram = [room_start(overlays, i) for i in range(8)]
    mechanisms = [room_mechanisms(i, ram) for i, ram in enumerate(initial_ram)]
    address, _, payload = overlays[5]
    room6_rows = collision_rows(overlays[9][2], 5, address, payload)
    (args.build / "puzzles.inc").write_text(puzzle_tables(mechanisms, room6_rows, initial_ram[7]), encoding="ascii")
    (args.build / "room6.bin").write_bytes(room6_assets(initial_ram[5], b""))
    (args.build / "room7.bin").write_bytes(room7_assets(initial_ram[6], hgr_page_pixels,
        lambda ram, pose: color_stamp(hgr_page_pixels(render_pose(ram,pose)),45,64), patch_runs))
    (args.build / "native8.bin").write_bytes(native8_assets(initial_ram[7]))
    (args.build / "room8.bin").write_bytes(room8_assets(initial_ram[7], hgr_page_pixels, patch_runs))
    manifest["sprites"] = {"routine": 0x0ab6, "source": "Apple II", "frames": POSES}
    poses = b"".join(color_stamp(hgr_page_pixels(render_pose(initial_ram[0], pose)), 45, 64)
                     for pose in POSES.values())
    room2 = initial_ram[1]

    switch_data = [v for x, y in zip(room2[0x65d7:0x65da], room2[0x65da:0x65dd])
                   for v in (coco_x(x), y)]
    trap_zones = [v for x, y in zip(room2[0x65f5:0x65f8], room2[0x65f8:0x65fb])
                  for v in (coco_x(x), y, coco_x(x+4), y+4)]
    (args.build / "room2_data.inc").write_text(
        asm_bytes("switches2", switch_data) + asm_bytes("trap_zones2", trap_zones)
        + asm_bytes("trap_flags2", room2[0x65dd:0x65f5]), encoding="ascii")
    crusher_table, crusher_sprites = crusher_assets(initial_ram[2])
    return_columns, return_stamps = room3_returns(initial_ram[2])
    (args.build / "crushers.inc").write_text(crusher_table + return_columns, encoding="ascii")
    frames = iter(map(hgr_page_pixels, life_frames(initial_ram[0])))
    digits = bytearray()
    for _ in range(10):
        frame = next(frames)
        for y in range(8):
            digits.extend(frame[y*160+136:y*160+140])
    game_over = next(frames)
    original = hgr_page_pixels(initial_ram[0][0x2000:0x4000])
    offsets = (i for i, (a, b) in enumerate(zip(game_over, original)) if a != b)
    game_over_patch = patch_runs(game_over, offsets)
    (args.build / "lives.inc").write_text(
        asm_bytes("life_label", patch_runs(original, (i for i in range(8*160)
                                                         if 115 <= i % 160 < 132 and original[i])))
        + "        ifeq PRELOAD_ALL\n" + asm_bytes("life_game_over", game_over_patch) + "        endc\n",
        encoding="ascii")
    for index, (address, sectors, payload) in enumerate(overlays):
        manifest["overlays"].append({"index": index, "load": address, "sectors": sectors})
        if index >= 8:
            continue
        packed, native_hgr, source_bytes = convert(payload)
        name = f"scene{index + 1}"
        (args.build / f"{name}.4bpp").write_bytes(packed)
        (args.build / f"{name}-280x192.4bpp").write_bytes(native_hgr)
        manifest["decoded_scenes"].append({
            "scene": index+1, "hgr_stream_bytes": source_bytes,
            "packed_sha256": hashlib.sha256(packed).hexdigest(),
            "native_280_sha256": hashlib.sha256(native_hgr).hexdigest(),
        })
        rows = collision_rows(overlays[9][2], index, address, payload)
        actors = initial_actors(initial_ram[index])
        x0, y0, x1, y1, next_room, hook = exit_zone(initial_ram[index])
        exit_data = bytes((coco_x(x0), y0, coco_x(x1), y1, next_room))
        terrain = spawn_data(actors) + exit_data + coco_collision(rows, index)
        if index == 0:
            terrain += first_room_assets(initial_ram[0]) + poses
            terrain += cooler_assets(initial_ram[0], packed, len(terrain))
            if len(terrain) > 0x1ea0:
                raise ValueError("Room 1 artwork overlaps the HUD digits")
            terrain = terrain.ljust(0x1ea0, bytes(1)) + digits
        if index == 1:
            if len(rows) != 33:
                raise ValueError("Unexpected collision table size in room 2")
            terrain += second_room_assets(initial_ram[index], len(terrain))
            if len(terrain) > 0x1900:
                raise ValueError("Room 2 graphics overlap launcher data")
            terrain = terrain.ljust(0x1900, bytes(1)) + launcher_assets(room2)
        if index == 2:
            terrain += crusher_sprites
            terrain += room3_items(initial_ram[2], packed, len(terrain))
            if len(terrain) > 0x1000:
                raise ValueError("Room 3 item data overlaps its platform")
            terrain = terrain.ljust(0x1000, bytes(1)) + room3_platform(initial_ram[2])
            terrain = terrain.ljust(0x1200, bytes(1)) + room3_lift(initial_ram[2], packed)
            if len(terrain) + len(game_over_patch) > 0x2000:
                raise ValueError("Game over graphic exceeds room 3 bank")
            terrain = terrain.ljust(0x2000-len(game_over_patch), bytes(1)) + game_over_patch
            (args.build / "game_over.inc").write_text(
                f"life_game_over equ ${0x8000-len(game_over_patch):04X}\n", encoding="ascii")
        if index == 4:
            rods = room3_rods(initial_ram[2], (args.build / "scene3.4bpp").read_bytes())
            if len(terrain) > 0x200 or len(rods) > 0xe00:
                raise ValueError(f"Room 3 rods exceed reserved space: {len(rods)}")
            terrain = terrain.ljust(0x200, bytes(1)) + rods
        if index == 7:
            if len(rows) != 53:
                raise ValueError("Unexpected collision table size in the final room")
            terrain += final_gate_assets(initial_ram[index], len(terrain))
        if mechanisms[index]:
            manifest["decoded_scenes"][-1]["apple_mechanisms"] = mechanisms[index]
        manifest["decoded_scenes"][-1]["apple_exit"] = [x0, y0, x1, y1, next_room, hook]
        (args.build / f"{name}-collision.bin").write_bytes(terrain)
        manifest["decoded_scenes"][-1]["apple_initial_actors"] = actors
        manifest["decoded_scenes"][-1]["apple_collision_rows"] = rows
    if len(manifest["decoded_scenes"]) != 8:
        cli.error("Expected eight validated HGR scenes from this DSK")
    title_source = Path(__file__).resolve().parents[1] / "assets" / "title-apple2.png"
    title, title_palette = title_bitmap(title_source)
    (args.build / "palette.inc").write_text(
        asm_bytes("palette_rgb", codes) + asm_bytes("palette_title", title_palette),
        encoding="ascii")
    (args.build / "title.4bpp").write_bytes(title)
    manifest["title"] = {"source": title_source.name, "source_size": [560, 384],
                         "active_size": [280, 192], "gime_codes": title_palette,
                         "source_sha256": hashlib.sha256(title_source.read_bytes()).hexdigest(),
                         "packed_sha256": hashlib.sha256(title).hexdigest()}
    manifest["ending"] = ending_assets(overlays, args.build)
    overflow = args.build / "scene4-collision.bin"
    metadata = overflow.read_bytes()
    if len(metadata) > 0x1400:
        raise ValueError("Ending animation overlaps room 3 return stamps")
    metadata = metadata.ljust(0x1400, bytes(1)) + return_stamps
    bat_poses = b"".join(color_stamp(hgr_page_pixels(render_pose(initial_ram[2], pose)), 45, 64)
                         for pose in range(16, 20))
    a = room3_bat(initial_ram[2], 72)
    b = room3_bat(initial_ram[2], 88)
    if len(a) > 0x140 or len(b) > 0x140 or a[:72] != b[:72]:
        raise ValueError("Room 3 bat path layout changed")
    metadata = metadata.ljust(0x1800, bytes(1)) + bat_poses + a.ljust(0x140, bytes(1)) + b
    crank = room3_crank(initial_ram[2], (args.build / "scene3.4bpp").read_bytes())
    if len(metadata) > 0x1e00 or len(crank) > 0x200:
        raise ValueError("Room 3 crank exceeds its bank space")
    overflow.write_bytes(metadata.ljust(0x1e00, bytes(1)) + crank)
    motion, motion_constants = room2_motion_assets(initial_ram[1])
    (args.build / "room2-motion.bin").write_bytes(motion)
    (args.build / "room2_motion_data.inc").write_text(motion_constants, encoding="ascii")
    graphics, constants = room4_assets(initial_ram[3])
    motion_pages = room4_motion(initial_ram[3], coco_x)
    for room, offset, payload in (
            (6, 0x100, next(motion_pages)), (7, 0x100, next(motion_pages)),
            (8, 0x4A0, graphics)):
        path = args.build / f"scene{room}-collision.bin"
        metadata = path.read_bytes()
        if len(metadata) > offset or offset + len(payload) > 0x1000:
            raise ValueError(f"Room 4 assets overlap room {room} data")
        path.write_bytes(metadata.ljust(offset, bytes(1)) + payload)
    particles, particle_symbols = room4_particle_assets(initial_ram[3])
    (args.build / "room4-particles.bin").write_bytes(particles)
    (args.build / "room4_data.inc").write_text(constants + particle_symbols, encoding="ascii")
    room5, room5_symbols, egg_pages = room5_assets(initial_ram[4])
    for page, records in enumerate(egg_pages, 5):
        (args.build / f"room5-eggs-{page}.bin").write_bytes(records)
    (args.build / "room5.bin").write_bytes(room5)
    (args.build / "room5_data.inc").write_text(room5_symbols, encoding="ascii")
    if args.d64:
        steps, ram = c64_unpack(args.d64.read_bytes())
        (args.build / "c64-ram.bin").write_bytes(ram)
        (args.build / "c64-entry.bin").write_bytes(ram[0x2000:])
        manifest["c64_unpack"] = {
            "entry": 0x2000, "steps": steps, "cpu_port": ram[1],
            "ram_sha256": hashlib.sha256(ram).hexdigest(),
        }
    (args.build / "assets.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Verified Apple scenes:", [item["scene"] for item in manifest["decoded_scenes"]])


if __name__ == "__main__":
    main()





