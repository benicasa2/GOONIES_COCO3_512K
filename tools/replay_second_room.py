"""Build an XRoar replay disk for the second, third, fourth, fifth or sixth playable room."""
import argparse
from pathlib import Path
import subprocess

from build import DIR_TRACK, GRANULE, SECTOR, STAGE, disk_binary, make_disk, split_room5_code, room6_segment, room8_segment, decode_bank_bytes, encode_bank


REPLAY_INPUT = 0x7F00


def disk_entries(disk, engine, replay, room_code=None, code6=None, code8=None):
    for entry in range(DIR_TRACK + 2 * SECTOR, DIR_TRACK + 2 * SECTOR + 72 * 32, 32):
        name = disk[entry:entry+8].decode("ascii") if disk[entry] != 255 else ""
        if not name:
            break
        ext = disk[entry+8:entry+11].decode("ascii")
        kind, flag, granule = disk[entry+11:entry+14]
        data = bytearray()
        while True:
            next_granule = disk[DIR_TRACK + SECTOR + granule]
            track, half = divmod(granule, 2)
            start = (track + (track >= 17)) * 18 * SECTOR + half * GRANULE
            if next_granule >= 0xC1:
                last = int.from_bytes(disk[entry+14:entry+16], "big")
                length = (next_granule - 0xC1) * SECTOR + last
                data.extend(disk[start:start+length])
                break
            data.extend(disk[start:start+GRANULE])
            granule = next_granule
        name = name.rstrip()
        if name == "ENGINE":
            data = engine
        elif name == "CODE6" and code6 is not None:
            bank = decode_bank_bytes(data[7:-5])
            bank[0xC00:0xC00+len(code6)] = code6
            if code8 is not None:
                bank[0x1000:0x1000+len(code8)] = code8
            data = disk_binary(STAGE, bytes([0x0D, 1]) + encode_bank(bytes(bank)), 0x200C)
        elif name == "NATIVE8" and len(replay) > 0x100:
            bank = decode_bank_bytes(data[7:-5])
            bank[0x1C00:0x1C00+len(replay)] = replay
            data = disk_binary(STAGE, bytes([0x0C,1]) + encode_bank(bytes(bank)), 0x200C)
        elif name == "ROOM5":
            if room_code is not None:
                length = len(data) - 10
                offset = length - len(room_code)
                data = disk_binary(STAGE, data[5:5+offset] + room_code, 0x2000)
            if len(replay) <= 0x100:
                data = data[:-5] + disk_binary(STAGE + 0x1F00, replay, 0x2000)
        yield name, ext.rstrip(), kind, flag, data



REPLAY = f"""
replay_input
        tst     replay_count
        bne     replay_hold
        lda     MMU3
        pshs    a
        lda     #ROOM5_ART
        sta     MMU3
        ldx     replay_cursor
        lda     ,x+
        beq     replay_idle
        sta     replay_count
        lda     ,x+
        sta     <keys
        stx     replay_cursor
        puls    a
        sta     MMU3
replay_hold
        dec     replay_count
        rts
replay_idle
        puls    a
        sta     MMU3
        clr     <keys
        rts
replay_cursor
        fdb     ${REPLAY_INPUT:04X}
replay_count
        fcb     0
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path, help="Directory produced by build.py")
    parser.add_argument("output", type=Path, help="Replay disk path")
    parser.add_argument("--mode", choices=("DAC", "SSC"), default="DAC")
    parser.add_argument("--room", choices=("second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"), default="second")
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1] / "evidence" / f"{args.room}-room-input.txt"
    replay = bytes.fromhex(fixture.read_text(encoding="ascii"))
    assert len(replay) <= (0x400 if args.room in ("eighth", "seventh") else 0x100)
    assert replay[-1] == 0 and all(mask & ~0x6F == 0 for mask in replay[1:-1:2])

    room = {"second": "ROOM3", "third": "ROOM2", "fourth": "ROOM4", "fifth": "ROOM5", "sixth": "ROOM6", "seventh": "ROOM7", "eighth": "ROOM8"}[args.room]
    source = (args.build / "flat.asm").read_text()
    source = source.replace("        lda     #ROOM\n        sta     <room_bank",
                            f"        lda     #{room}\n        sta     <room_bank", 1)
    source = source.replace("        andcc   #$AF\n", "        andcc   #$AF\n        bra     title_start\n", 1)
    before, after = source.split("\nmain_loop\n", 1)
    after = after.replace("        jsr     read_keys", "        jsr     replay_input", 1)
    source = before + "\nmain_loop\n" + after
    replay_code = REPLAY
    if len(replay) > 0x100:
        replay_code = replay_code.replace("#ROOM5_ART", "#NATIVE_BANK").replace("$7F00", "$7C00")
    marker = "        end entry"
    source = source.replace(marker, "        ifne PRELOAD_ALL\n        org     $1B00\n" + replay_code + "        endc\n" + marker, 1)
    if "\nreplay_input\n" not in source:
        raise ValueError("Replay requires the Room 5 staging bank")

    asm = args.output.with_suffix(".asm")
    binary = args.output.with_suffix(".bin")
    listing = args.output.with_suffix(".map")
    asm.write_text(source, encoding="ascii")
    subprocess.run(["lwasm", "--6809", "--decb", "-D", "PRELOAD_ALL=1", "-D",
                    f"AUDIO_DRIVER_TYPE={int(args.mode == 'SSC')}",
                    f"--map={listing}", f"--output={binary}", str(asm)], check=True)
    engine = binary.read_bytes()
    assert 0x2000 + int.from_bytes(engine[1:3], "big") <= STAGE
    code8 = room8_segment(engine)
    code6 = room6_segment(engine)
    engine, code = split_room5_code(engine)
    disk = (args.build / f"GOON-{args.mode}.DSK").read_bytes()
    args.output.write_bytes(make_disk(disk_entries(disk, engine, replay, code, code6, code8)))


if __name__ == "__main__":
    main()

