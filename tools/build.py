"""Assemble the two 6809 builds and create 35-track Disk BASIC images."""
import argparse
from collections import defaultdict, deque
from pathlib import Path
import subprocess
from prepare import asm_bytes

SECTOR = 256
GRANULE = 9 * SECTOR
DIR_TRACK = 17 * 18 * SECTOR
STAGE = 0x4000


def disk_binary(address, data, entry):
    if not data or address + len(data) > 0x10000:
        raise ValueError("Invalid LOADM segment")
    return (b"\x00" + len(data).to_bytes(2, "big") + address.to_bytes(2, "big")
            + data + b"\xff\x00\x00" + entry.to_bytes(2, "big"))


def split_room5_code(engine):
    """Keep room-5/6 runtime overlays out of BASIC workspace until EXEC."""
    kept = bytearray()
    offset = 0
    room_code = None
    while engine[offset] == 0:
        length = int.from_bytes(engine[offset+1:offset+3], "big")
        address = int.from_bytes(engine[offset+3:offset+5], "big")
        end = offset + 5 + length
        if address == 0x0D00:
            if address + length > 0x1280 or room_code is not None:
                raise ValueError("Room 5 code overlaps actor storage")
            room_code = engine[offset+1:offset+3] + engine[offset+5:end]
        elif address not in (0x1400, 0x0400, 0x7500):
            kept.extend(engine[offset:end])
        offset = end
    if room_code is None or len(engine)-offset != 5 or engine[offset] != 255:
        raise ValueError("Unexpected Room 5 engine segments")
    return bytes(kept + engine[offset:]), room_code


def runtime_segment(engine, origin, limit):
    offset = 0
    while engine[offset] == 0:
        length = int.from_bytes(engine[offset+1:offset+3], "big")
        address = int.from_bytes(engine[offset+3:offset+5], "big")
        if address == origin:
            if length > limit:
                raise ValueError("Runtime overlay exceeds its reserved space")
            return engine[offset+1:offset+3] + engine[offset+5:offset+5+length]
        offset += 5 + length
    raise ValueError("Missing runtime overlay")

def room6_segment(engine):
    return runtime_segment(engine, 0x1400, 0x300)

def room8_segment(engine):
    return runtime_segment(engine, 0x0400, 0x900)


def decode_bank_bytes(data):
    out = bytearray()
    cursor = 0
    while data[cursor]:
        token = data[cursor]
        cursor += 1
        if token < 128:
            out.extend(data[cursor:cursor+token])
            cursor += token
        else:
            distance = int.from_bytes(data[cursor:cursor+2], "big", signed=True)
            cursor += 2
            for _ in range((token & 127) + 3):
                out.append(out[len(out)+distance])
    return out


def make_disk(files):
    disk = bytearray(b"\xff" * (35 * 18 * SECTOR))
    next_granule = 0
    for index, (stem, extension, filetype, ascii_flag, data) in enumerate(files):
        granules = (len(data) + GRANULE - 1) // GRANULE
        if not (0 < granules <= 68 - next_granule and index < 72):
            raise ValueError("Disk capacity exceeded or empty file")
        entry = DIR_TRACK + 2 * SECTOR + index * 32
        entry_data = (stem.ljust(8) + extension.ljust(3)).encode("ascii")
        entry_data += bytes([filetype, ascii_flag, next_granule])
        entry_data += ((len(data)-1) % SECTOR + 1).to_bytes(2, "big")
        disk[entry:entry+32] = entry_data.ljust(32, b"\0")
        for offset in range(0, len(data), GRANULE):
            block = data[offset:offset+GRANULE]
            granule = next_granule
            track, half = divmod(granule, 2)
            address = (track + (track >= 17)) * 18 * SECTOR + half * GRANULE
            disk[address:address+len(block)] = block
            fat = DIR_TRACK + SECTOR + granule
            if offset + len(block) == len(data):
                disk[fat] = 0xC0 | ((len(block) + SECTOR - 1) // SECTOR)
            else:
                disk[fat] = granule + 1
            next_granule += 1
    return disk


def encode_bank(block):
    """Bank-local LZ with 127-byte literals and 3-130-byte matches."""
    positions = defaultdict(lambda: deque(maxlen=128))
    literals = bytearray()
    output = bytearray()

    def flush():
        if literals:
            output.append(len(literals))
            output.extend(literals)
            literals.clear()

    offset = 0
    while offset < len(block):
        key = block[offset:offset + 3]
        length = 0
        previous = 0
        limit = min(130, len(block) - offset)
        if limit >= 3:
            for candidate in reversed(positions[key]):
                size = 3
                while size < limit and block[candidate + size] == block[offset + size]:
                    size += 1
                if size > length:
                    length, previous = size, candidate
                    if length == limit:
                        break
        if length >= 4:
            flush()
            output.append(0x80 | (length - 3))
            output.extend((previous - offset).to_bytes(2, "big", signed=True))
        else:
            length = 1
            literals.append(block[offset])
            if len(literals) == 127:
                flush()
        for i in range(offset, offset + length):
            positions[block[i:i + 3]].append(i)
        offset += length
    flush()
    output.append(0)
    return output


def ssc_music_pages(stream):
    pages = [bytearray()]
    cursor = 0
    while cursor < len(stream):
        header = stream[cursor]
        if header == 0:
            if cursor != len(stream)-1:
                raise ValueError("Data after SSC terminator")
            pages[-1].append(0)
            break
        end = cursor + 1 + (header & 7).bit_count()
        if header < 8 or end > len(stream) or any(n > 61 for n in stream[cursor+1:end]):
            raise ValueError("Invalid SSC music event")
        if len(pages[-1]) + end-cursor >= 2048:
            pages[-1].append(1)
            pages.append(bytearray())
        pages[-1].extend(stream[cursor:end])
        cursor = end
    else:
        raise ValueError("Missing SSC terminator")
    if len(pages) > 3:
        raise ValueError("SSC music exceeds three bitmap padding pages")
    return b"".join(p.ljust(2048,b"\0") for p in pages).ljust(6144,b"\0")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("assets", type=Path)
    parser.add_argument("build", type=Path)
    parser.add_argument("--assembler", choices=("lwasm", "asm6809"), default="lwasm")
    args = parser.parse_args()
    assets = args.assets.resolve()
    out = args.build.resolve()
    out.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).resolve().parent.parent / "src"
    source = (src / "main.asm").read_text(encoding="ascii")
    includes = (
        ("audio.inc", src), ("room_mechanics.inc", src), ("room1.inc", src), ("cash.inc", src), ("player_lives.inc", src), ("game_over.inc", assets), ("room3.inc", src), ("room2.inc", src), ("room4.inc", src), ("room4_rewards.inc", src), ("room5.inc", src), ("room6.inc", src), ("room8.inc", src), ("room7.inc", src), ("apple_physics.inc", src), ("room7_physics.inc", src), ("room5_data.inc", assets), ("room4_data.inc", assets), ("room2_motion.inc", src), ("room2_motion_data.inc", assets), ("launcher.inc", src), ("room2_data.inc", assets), ("palette.inc", assets),
        ("lives.inc", assets), ("crushers.inc", assets), ("music.inc", assets), ("puzzles.inc", assets),
    )
    for filename, directory in includes:
        source = source.replace(f'        include "{filename}"',
                                (directory / filename).read_text(encoding="ascii"))

    ssc = ssc_music_pages((src.parent / "assets" / "ssc-theme.bin").read_bytes())
    periods = [0] + [round(111860 / (440 * 2 ** ((n-69)/12))) for n in range(32,93)]
    source = source.replace('        include "ssc_periods.inc"',
                            asm_bytes("ssc_periods", b"".join(n.to_bytes(2,"big") for n in periods)))
    source = source.replace('        include "ssc_data.inc"', asm_bytes("ssc_data", ssc))

    basic = ['10 CLEAR 200,&H16FF', '20 LOADM"ENGINE":EXEC&H2006']
    scenes = []

    def preload_file(name, payload, entry):
        if STAGE + len(payload) > 0x6000:
            parser.error(f"{name} overlaps the preload aperture")
        line = 30 + 10 * len(scenes)
        basic.append(f'{line} LOADM"{name}":EXEC&H{entry:04X}')
        scenes.append((name, "BIN", 2, 0, disk_binary(STAGE, payload, entry)))

    title = (assets / "title.4bpp").read_bytes()
    if len(title) != 320 * 192 // 2:
        parser.error("Invalid title screen size")
    title = title.ljust(0x8000, bytes(1))
    title_banks = [encode_bank(title[i:i + 0x2000]) for i in range(0, len(title), 0x2000)]
    graphics8 = (assets / "room8.bin").read_bytes()
    if len(graphics8) > 0x2000:
        parser.error("Room 8 artwork exceeds its bank")
    graphics8 = graphics8.ljust(0x2000, bytes(1))
    graphics8_parts = [encode_bank(graphics8[i:i+0x1000]) for i in (0, 0x1000)]
    if any(len(part) > 0x800 for part in graphics8_parts):
        parser.error("Room 8 compressed half exceeds scene padding")
    for i in range(1, 9):
        packed = (assets / f"scene{i}.4bpp").read_bytes()
        if len(packed) != 320 * 192 // 2:
            parser.error(f"Scene {i} has invalid length")
        collision = (assets / f"scene{i}-collision.bin").read_bytes()
        if i >= 5:
            if len(collision) > 0x1000:
                parser.error("Room metadata overlaps its title backup")
            collision = collision.ljust(0x1000, bytes(1)) + title_banks[i-5]
        if i == 8:
            if len(collision) > 0x1600:
                parser.error("Room 4 particles overlap the title backup")
            collision = collision.ljust(0x1600, bytes(1)) + (assets / "room4-particles.bin").read_bytes()
        if len(collision) > 0x2000:
            parser.error("Room metadata exceeds one bank")
        room = packed
        if i in (2, 3):
            room += graphics8_parts[i-2]
        if 5 <= i <= 8:
            eggs = (assets / f"room5-eggs-{i}.bin").read_bytes()
            if len(eggs) > 0x800:
                parser.error("Room 5 motion page exceeds screen-bank padding")
            room += eggs
        room = room.ljust(0x8000, bytes(1)) + collision.ljust(0x2000, bytes(1))
        banks = [encode_bank(room[offset:offset+0x2000])
                 for offset in range(0, len(room), 0x2000)]
        if i == 1:
            standalone = bytes([0x10, 5]) + b"".join(banks)
            if STAGE + len(standalone) > 0x6000:
                parser.error("Standalone room overlaps the preload aperture")
            source = source.replace('        include "scene1.inc"', asm_bytes("room_bitmap", standalone))
        bank = 0x10 + 5*(i-1)
        name = f"S{i}"
        if sum(map(len, banks)) + 2 > 0x6000 - STAGE:
            preload_file(name, bytes([bank, 4]) + b"".join(banks[:4]), 0x200C)
            preload_file(name + "G", bytes([bank + 4, 1]) + banks[4], 0x200C)
        else:
            preload_file(name, bytes([bank, 5]) + b"".join(banks), 0x200C)
    background = (assets / "ending.4bpp").read_bytes().ljust(0x8000, bytes(1))
    encoded = b"".join(encode_bank(background[i:i+0x2000]) for i in range(0, 0x8000, 0x2000))
    preload_file("ENDPIC", bytes([0, 4]) + encoded, 0x200C)
    for i in range(4):
        data = (assets / f"ending-{i}.bin").read_bytes()
        if len(data) != 8192:
            parser.error(f"Ending bank {i} must contain 8192 bytes")
        preload_file(f"END{i}", bytes([4+i, 1]) + encode_bank(data), 0x200C)
    motion = (assets / "room2-motion.bin").read_bytes()
    if len(motion) > 0x2000:
        parser.error("Room 2 motion exceeds its bank")
    preload_file("MOTION2", bytes([0x3B, 1]) + encode_bank(motion.ljust(0x2000, bytes(1))), 0x200C)
    # Room 6 shares the strip renderer, with its own bank at identical offsets.
    abi = (assets / "room5_data.inc").read_text().upper()
    if "ROOM5_XMAP EQU $657A" not in abi or "ROOM5_POSES EQU $667A" not in abi:
        parser.error("Room 6 renderer layout must follow the room 5 asset ABI")
    if (assets / "room6.bin").stat().st_size > 0xC00:
        parser.error("Room 6 artwork overlaps runtime code")
    room5 = (assets / "room5.bin").read_bytes()
    if len(room5) > 0x1F00:
        parser.error("Room 5 assets exceed the staging bank")
    room7 = (assets / "room7.bin").read_bytes()
    if len(room7) > 0x1E00:
        parser.error("Room 7 graphics overlap replay space")
    preload_file("NATIVE7", bytes([0x0E,1]) + encode_bank(room7.ljust(0x2000, bytes(1))), 0x200C)
    basic.append('895 LOADM"NATIVE8":EXEC&H200C')
    basic.append('900 LOADM"CODE6":EXEC&H200C')
    basic.append('910 LOADM"ROOM5":EXEC&H2000')
    def make_loader(commands):
        return ("\r".join(f"{10+i*10} " + ":".join(commands[i:i+3])
                          for i in range(0, len(commands), 3)) + "\r").encode("ascii")
    commands = [line.split(" ", 1)[1] for line in basic]
    (out / "flat.asm").write_text(source, encoding="ascii")
    for driver, mode in (("DAC", 0), ("SSC", 1)):
        for preload in (0, 1):
            base = f"GOON-{driver}" + ("-ENGINE" if preload else "")
            defs = (f"AUDIO_DRIVER_TYPE={mode}", f"PRELOAD_ALL={preload}")
            if args.assembler == "lwasm":
                cmd = ["lwasm", "--6809", "--decb", f"--map={base}.map",
                       f"--list={base}.lst", "-D", defs[0], "-D", defs[1]]
            else:
                cmd = ["asm6809", "-9", "-C", "-e", "0x2000", "-s", f"{base}.map",
                       "-l", f"{base}.lst", "-d", defs[0], "-d", defs[1]]
            subprocess.run([*cmd, "-o", f"{base}.BIN", "flat.asm"], cwd=out, check=True)
            engine = (out / f"{base}.BIN").read_bytes()
            if not (engine[:1] == b"\0" and engine[3:5] == b"\x20\x00"
                    and int.from_bytes(engine[1:3], "big") <= STAGE - 0x2000):
                raise ValueError("Engine overlaps its staging buffer")
            if preload:
                code6 = room6_segment(engine)
                bank6 = bytearray((assets / "room6.bin").read_bytes().ljust(0x2000, bytes(1)))
                if 0xC00 + len(code6) > 0x1000:
                    parser.error("Room 6 runtime exceeds its reserved bank region")
                bank6[0xC00:0xC00+len(code6)] = code6
                code8 = room8_segment(engine)
                bank6[0x1000:0x1000+len(code8)] = code8
                code6_file = ("CODE6", "BIN", 2, 0, disk_binary(STAGE, bytes([0x0D, 1]) + encode_bank(bytes(bank6)), 0x200C))
                native8 = bytearray((assets / "native8.bin").read_bytes().ljust(0x2000, bytes(1)))
                native_code = runtime_segment(engine, 0x7500, 0x700)[2:]
                native8[0x1500:0x1500+len(native_code)] = native_code
                native8_file = ("NATIVE8", "BIN", 2, 0, disk_binary(STAGE, bytes([0x0C,1]) + encode_bank(bytes(native8)), 0x200C))
                engine, code = split_room5_code(engine)
                if len(room5) + len(code) > 0x1F00:
                    parser.error("Room 5 code and data overlap replay storage")
                (out / f"{base}.BIN").write_bytes(engine)
                room5_file = ("ROOM5", "BIN", 2, 0, disk_binary(STAGE, room5 + code, 0x2000))
                loader_commands = commands.copy()
                extra = []
                if mode:
                    loader_commands.insert(-1, 'LOADM"MUSIC":EXEC&H200F')
                    # Store the contiguous data without disk padding; zero-filled
                    # bytes after its terminator are irrelevant to playback.
                    extra.append(("MUSIC", "BIN", 2, 0, disk_binary(0x6000, ssc.rstrip(b"\0") + b"\0", 0x200F)))
                files = [("START", "BAS", 0, 255, make_loader(loader_commands)),
                         ("ENGINE", "BIN", 2, 0, engine)]
                (out / f"GOON-{driver}.DSK").write_bytes(make_disk(files + scenes + [code6_file, native8_file, room5_file] + extra))



if __name__ == "__main__":
    main()
