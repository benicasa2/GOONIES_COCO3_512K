"""Convert the repeating C64 SID theme to two CoCo 3 tone streams."""
import argparse
from itertools import groupby
import json
from pathlib import Path

SID_CLOCK = 985248
AY_CLOCK = 1789772
TICKS_PER_SAMPLE = 3


def theme_bounds(writes):
    """Locate the repeated opening melody with both pitch and note timing."""
    registers = bytearray(25)
    events = []
    for cycle, register, value in writes:
        registers[register] = value
        if register == 11 and value & 1:
            events.append((cycle, registers[7] | registers[8] << 8))
    opening = events[1:25]  # First gate belongs to the loader.
    for index in range(25, len(events) - len(opening) + 1):
        candidate = events[index:index + len(opening)]
        if all(pitch == original_pitch
               and abs((cycle - candidate[0][0]) - (original_cycle - opening[0][0])) < 1024
               for (cycle, pitch), (original_cycle, original_pitch)
               in zip(candidate, opening)):
            # Include voice 1 writes in the same update, before voice 2.
            return opening[0][0] - 512, candidate[0][0] - 512
    raise ValueError("SID trace does not cover a complete repeat of the theme")


def stream(trace):
    writes = trace["writes"]
    start, end = theme_bounds(writes)
    registers = bytearray(25)
    cursor = 0
    samples = round((end - start) / (SID_CLOCK / 20))
    for frame in range(samples):
        cycle = start + (end - start) * (2 * frame + 1) // (2 * samples)
        while cursor < len(writes) and writes[cursor][0] <= cycle:
            _, register, value = writes[cursor]
            registers[register] = value
            cursor += 1
        yield tuple((registers[base] | registers[base + 1] << 8)
                    if registers[base + 4] & 1 and registers[24] & 15 else 0
                    for base in (0, 7))


def emit(trace):
    frames = list(stream(trace))
    words = sorted({word for frame in frames for word in frame})
    if len(words) > 128:
        raise ValueError("Tone table exceeds the signed 6809 indexed range")
    lines = ["; Generated full SID theme cycle. Duration in 60 Hz ticks.", "music_notes"]
    for frame, run in groupby(frames):
        ticks = TICKS_PER_SAMPLE * len(list(run))
        a, b = (words.index(word) * 2 for word in frame)
        while ticks:
            duration = min(255, ticks)
            lines.append(f"        fcb {duration},{a},{b}")
            ticks -= duration
    lines.extend(("        fcb 0", "music_periods"))
    for word in words:
        hz = word * SID_CLOCK / 2**24
        dac = min(32767, round(hz * 65536 / 8000))
        ay = max(1, min(4095, round(AY_CLOCK / (16 * hz)))) if hz else 0
        if ay & 255 == 254:
            ay -= 1
        lines.extend(("        ifeq AUDIO_DRIVER_TYPE", f"        fdb {dac}",
                      "        else", f"        fdb {ay}", "        endc"))
    return "\n".join(lines + [""])


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("trace", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    args.output.write_text(emit(json.loads(args.trace.read_text())), encoding="ascii")
