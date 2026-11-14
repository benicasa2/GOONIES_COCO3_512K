"""Capture a gameplay bitmap from the attached C64 crack with a controlled bus.

Py65 runs the unpacker, trainer, room loader and game. KERNAL GETIN and IEC
reads are substituted with scripted input and the D64 directory streams.
The raster counter and VIC IRQ are approximate, without cycle-exact CIA/VIC.
"""

import argparse
import hashlib
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from apple_runtime import POSES
from extract import d64_files
from prepare import c64_unpack


class C64Bus:
    def __init__(self, memory, roms):
        self.ram = bytearray(memory)
        self.basic = (roms / "basic-901226-01.bin").read_bytes()
        self.kernal = (roms / "kernal-901227-03.bin").read_bytes()
        self.charset = (roms / "chargen-901225-01.bin").read_bytes()
        self.io = bytearray(4096)
        self.ram[0] = 0x2f
        self.io[0xd00] = 3
        self.io[0xc00] = self.io[0xc01] = 255
        self.raster = 0
        self.fire = True
        self.irq = 0
        self.cycles = 0
        self.sid_writes = []

    def __getitem__(self, address):
        bank = self.ram[1] & 7
        if address >= 0xe000 and bank & 2:
            return self.kernal[address-0xe000]
        if 0xa000 <= address < 0xc000 and bank & 3 == 3:
            return self.basic[address-0xa000]
        if 0xd000 <= address < 0xe000 and bank & 3:
            if not bank & 4:
                return self.charset[address-0xd000]
            if address == 0xd012:
                return self.raster & 255
            if address == 0xd011:
                return self.io[0x11] & 127 | (self.raster >> 1) & 128
            if address == 0xd019:
                return self.irq | (128 if self.irq & self.io[0x1a] else 0)
            if address in (0xdc00, 0xdc01):
                return self.io[address-0xd000] & (239 if self.fire else 255)
            if address in (0xdc0d, 0xdd0d):
                return 0
            return self.io[address-0xd000]
        return self.ram[address]

    def __setitem__(self, address, value):
        bank = self.ram[1] & 7
        if 0xd000 <= address < 0xe000 and bank & 4 and bank & 3:
            if address == 0xd019:
                self.irq &= ~value
            else:
                self.io[address-0xd000] = value
            if 0xd400 <= address <= 0xd418:
                self.sid_writes.append((self.cycles, address - 0xd400, value))
        else:
            self.ram[address] = value

    def update_raster(self, cycles):
        line = cycles // 63 % 312
        if line != self.raster:
            self.raster = line
            compare = (self.io[0x11] & 128) << 1 | self.io[0x12]
            if line == compare:
                self.irq |= 1


def decode_frame(bus):
    io = bus.io
    if io[0x11] & 0x20 == 0 or io[0x16] & 0x10 == 0:
        raise ValueError("Expected VIC-II multicolor bitmap")
    if io[0x15] != 0:
        raise ValueError("Hardware sprites need a separate VIC layer")
    bank = (3 - (io[0xd00] & 3)) * 0x4000
    bitmap = bank + (0x2000 if io[0x18] & 8 else 0)
    screen = bank + (io[0x18] >> 4) * 0x400
    pixels = bytearray()
    for y in range(200):
        for col in range(40):
            cell = y // 8 * 40 + col
            attr = bus.ram[screen+cell]
            colors = (io[0x21] & 15, attr >> 4, attr & 15, io[0x800+cell] & 15)
            source = bus.ram[bitmap+cell*8+y%8]
            for shift in (6, 4, 2, 0):
                pixels.extend([colors[(source >> shift) & 3]] * 2)
    return pixels, bitmap, screen


def sprite_masks(bus):
    masks = bytearray()
    for pose in POSES.values():
        ram = list(bus.ram)
        ram[0x2000:0x3f40] = [0] * 8000
        ram[0x4000:0x5f40] = [0] * 8000
        ram[0x3e], ram[0x49], ram[0x54] = 40, 64, pose
        cpu = MPU(memory=ram, pc=0x0c8a)
        cpu.stPushWord(0x02fe)
        for _ in range(20_000):
            if cpu.pc == 0x02ff:
                break
            cpu.step()
        else:
            raise ValueError(f"C64 sprite frame {pose} did not return")
        frame = bytearray()
        for y in range(72, 94):
            row = 0
            for x in range(16):
                start = 80 + x * 280 // 256
                stop = min(96, 80 + (x + 1) * 280 // 256)
                for sample in range(start, stop):
                    offset = (y // 8 * 40 + sample // 8) * 8 + y % 8
                    b = ram[0x2000+offset] | ram[0x4000+offset]
                    if b >> (6 - sample % 8 // 2 * 2) & 3:
                        row |= 1 << (15-x)
            frame.extend(row.to_bytes(2, "big"))
        if not any(frame):
            raise ValueError(f"C64 sprite frame {pose} is empty")
        masks.extend(frame)
    return masks


def capture(memory, files, roms, selector, frame_target=12):
    bus = C64Bus(memory, roms)
    cpu = MPU(memory=bus, pc=0x2000)
    bus.ram[0x314:0x316] = b"\x31\xea"
    bus.ram[0x288], bus.ram[0x286] = 4, 14
    stream = iter(())
    loaded = False
    frames = 0
    for _ in range(max(7_000_000, 2_000_000 + frame_target * 80_000)):
        pc = cpu.pc
        if pc == 0x09a1 and loaded:
            frames += 1
            if frames >= frame_target and bus.io[0x18] == 0x80 and bus.io[0xd00] & 3 == 2:
                pixels, bitmap, screen = decode_frame(bus)
                return bus, pixels, {
                    "selector": selector, "room_index": bus.ram[0x12b9],
                    "bitmap": bitmap, "screen": screen, "frame": frames,
                    "cycles": cpu.processorCycles,
                    "vic_d015": bus.io[0x15], "file_name_hex": name.hex(),
                    "sha256": hashlib.sha256(pixels).hexdigest(),
                }
        if pc == 0x4550:
            pointer = bus.ram[0xbb] | bus.ram[0xbc] << 8
            name = bytes(bus.ram[pointer:pointer+bus.ram[0xb7]]).rstrip(b"\xa0")
            stream = iter(files[name])
            loaded = True
            cpu.pc = 0x45c0
            continue
        if pc in (0xee13, 0xffe4, 0xf642):
            ret = cpu.stPopWord()
            if pc == 0xee13:
                value = next(stream, None)
                if value is None:
                    bus.ram[0x90] = 0x40
                    value = 0
                cpu.a = value
                cpu.FlagsNZ(cpu.a)
            elif pc == 0xffe4:
                if ret == 0x0854:
                    cpu.a = 3
                elif ret == 0x26df:
                    cpu.a = bus.ram[2]
                elif ret == 0x25ed:
                    cpu.a = 48 + selector
                else:
                    cpu.a = 13
                cpu.FlagsNZ(cpu.a)
            else:
                cpu.p &= ~1
            cpu.pc = (ret + 1) & 65535
            continue
        bus.cycles = cpu.processorCycles
        cpu.step()
        bus.update_raster(cpu.processorCycles)
        if bus.irq & bus.io[0x1a]:
            cpu.irq()
        if pc == 0x2685:
            bus.fire = False
    raise ValueError(f"C64 selector {selector} did not reach capture at $09A1")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("d64", type=Path)
    cli.add_argument("rom_dir", type=Path)
    cli.add_argument("output", type=Path)
    cli.add_argument("--room", type=int, choices=range(1,9), required=True)
    cli.add_argument("--frames", type=int, default=12)
    cli.add_argument("--sid-out", type=Path, help="Write [cycle, register, value] trace")
    args = cli.parse_args()
    if not 1 <= args.frames <= 1200:
        cli.error("--frames must be between 1 and 1200")
    disk = args.d64.read_bytes()
    _, memory = c64_unpack(disk)
    files = {name: data for name, data, _ in d64_files(disk)}
    bus, pixels, meta = capture(memory, files, args.rom_dir, args.room, args.frames)
    args.output.mkdir(parents=True, exist_ok=True)
    stem = args.output / f"c64-scene{meta['room_index'] + 1}"
    stem.with_suffix(".indices").write_bytes(pixels)
    if meta["room_index"] == 0:
        masks = sprite_masks(bus)
        (args.output / "c64-poses.bin").write_bytes(masks)
        meta["sprite_source"] = {"routine": 0x0c8a, "frames": POSES,
                                 "sha256": hashlib.sha256(masks).hexdigest()}
    stem.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="ascii")
    if args.sid_out:
        trace = {"clock": "approximate PAL CPU cycles", "writes": bus.sid_writes}
        args.sid_out.write_text(json.dumps(trace, separators=(",", ":")) + "\n", encoding="ascii")
    print(meta)


if __name__ == "__main__":
    main()


