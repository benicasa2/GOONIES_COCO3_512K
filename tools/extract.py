"""Extract read-only analysis inputs. Requires Python 3.10+."""
import argparse
import hashlib
import json
from pathlib import Path


def d64_files(image):
    sectors = [21] * 17 + [19] * 7 + [18] * 6 + [17] * 5

    def sector(track, number):
        if not (1 <= track <= 35 and 0 <= number < sectors[track - 1]):
            raise ValueError(f"Invalid D64 address {track}/{number}")
        offset = 256 * (sum(sectors[:track - 1]) + number)
        return image[offset:offset + 256]

    def chain(track, number):
        seen = set()
        while track:
            if (track, number) in seen:
                raise ValueError("D64 sector chain cycle")
            seen.add((track, number))
            block = sector(track, number)
            yield track, number, block
            track, number = block[:2]

    for _, _, directory in chain(18, 1):
        for offset in range(0, 256, 32):
            if directory[offset + 2] & 7 != 2:
                continue
            name = directory[offset + 5:offset + 21].rstrip(b"\xa0")
            start = directory[offset + 3:offset + 5]
            blocks = list(chain(*start))
            data = b"".join(b[2:] if b[0] else b[2:b[1] + 1] for _, _, b in blocks)
            yield name, data, [(t, s) for t, s, _ in blocks]


def main():
    cli = argparse.ArgumentParser()
    for argument in ("d64", "dsk", "output"):
        cli.add_argument(argument, type=Path)
    args = cli.parse_args()
    d64, dsk = args.d64.read_bytes(), args.dsk.read_bytes()
    if len(d64) not in (174848, 175531) or len(dsk) != 143360:
        cli.error("Expected a 35-track D64 and a 35x16x256 Apple II DSK")
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "d64_sha256": hashlib.sha256(d64).hexdigest(),
        "dsk_sha256": hashlib.sha256(dsk).hexdigest(),
        "c64": [],
        "apple2_boot": {"offset": 0, "length": 256, "load": 0x0800, "entry": 0x0801},
    }
    (out / "apple2-boot.bin").write_bytes(dsk[:256])
    for name, data, chain in d64_files(d64):
        stem = {b"THE GOONIES+": "c64-game", b"THE GOONIES PIC": "c64-picture"}.get(name)
        if stem is None:
            continue
        load = int.from_bytes(data[:2], "little")
        (out / (stem + ".prg")).write_bytes(data)
        (out / (stem + ".bin")).write_bytes(data[2:])
        manifest["c64"].append({
            "file": stem + ".bin", "name": name.decode("ascii"), "load": load,
            "length": len(data) - 2, "sectors": chain,
        })
    if len(manifest["c64"]) != 2:
        cli.error("The two expected Goonies PRGs were not found")
    (out / "disks.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for item in manifest["c64"]:
        print(f"{item['name']}: ${item['load']:04X}, {item['length']} payload bytes")


if __name__ == "__main__":
    main()
