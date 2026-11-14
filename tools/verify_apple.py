"""Compare recovered room bytes with the original Apple 6502 routine."""
import argparse
from pathlib import Path
from py65.devices.mpu6502 import MPU
from prepare import apple_overlays, hgr_stream


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dsk", type=Path)
    args = p.parse_args()
    _, overlays = apple_overlays(args.dsk.read_bytes())
    for index, (address, _, room) in enumerate(overlays[:8], 1):
        cpu = MPU(pc=0x1bac)
        for address2, _, data in (overlays[9], overlays[10]):
            cpu.memory[address2:address2+len(data)] = data
        cpu.memory[address:address+len(room)] = room
        cpu.stPushWord(0x02fe)
        for step in range(1_000_000):
            if cpu.pc == 0x02ff:
                break
            cpu.step()
        else:
            raise ValueError(f"Room {index} decoder did not return")
        columns, _ = hgr_stream(room)
        for y in range(192):
            page = 0x2000 + ((y & 7) << 10) + ((y & 0x38) << 4) + (y >> 6) * 40
            for x in range(40):
                if cpu.memory[page+x] != columns[x*192+y]:
                    raise ValueError(f"Room {index} mismatch at HGR byte {x},{y}")
        print(f"Room {index}: 7680 HGR bytes match ({step} 6502 instructions)")


if __name__ == "__main__":
    main()
