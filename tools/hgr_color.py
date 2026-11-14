"""Fit an Apple II HGR composite color model to the supplied gameplay capture."""
from collections import Counter, defaultdict
from statistics import median

HGR_WIDTH = 280
HGR_HEIGHT = 192
FIXED = {0: 0x00, 1: 0x3F, 4: 0x29, 5: 0x12, 8: 0x34, 13: 0x16}


def rgb(code):
    return tuple((((code >> high) & 1) * 2 + ((code >> low) & 1)) * 85
                 for high, low in ((5, 2), (4, 1), (3, 0)))


def signal_keys(row):
    # HGR emits two 14 MHz samples per set bit. Bit 7 delays a byte's
    # contribution by half a pixel. Include nearby samples and color phase.
    wave = [0] * (HGR_WIDTH * 2 + 12)
    for x in range(HGR_WIDTH):
        byte = row[x // 7]
        if byte & (1 << (x % 7)):
            j = 6 + 2*x + (byte >> 7)
            wave[j] = wave[j+1] = 1
    key = sum(value << (11-i) for i, value in enumerate(wave[:12]))
    for x in range(HGR_WIDTH):
        yield key | ((x & 1) << 12)
        key = ((key << 2) & 0xfff) | (wave[2*x+12] << 1) | wave[2*x+13]


def coarse_key(key):
    return ((key >> 2) & 0xff) | ((key >> 4) & 0x100)


def nearest(pixel, palette):
    return min(range(len(palette)), key=lambda i: sum((a-b)**2 for a, b in zip(pixel, palette[i])))


def color_model(columns, capture_path):
    from PIL import Image

    with Image.open(capture_path) as image:
        if image.size != (560, 384):
            raise ValueError("The Apple II calibration capture must be 560x384")
        data = image.convert("RGB").resize((HGR_WIDTH, HGR_HEIGHT), Image.Resampling.BOX).tobytes()
    pixels = list(zip(data[::3], data[1::3], data[2::3]))
    histogram = Counter(pixels)
    colors = [rgb(code) for code in range(64)]
    errors = {pixel: [sum((a-b)**2 for a, b in zip(pixel, c)) for c in colors]
              for pixel in histogram}
    entries = dict(FIXED)
    chosen = set(entries.values())
    residual = {pixel: min(cost[k] for k in chosen) for pixel, cost in errors.items()}
    for i in range(16):
        if i in entries:
            continue
        best = min((code for code in range(64) if code not in chosen),
                   key=lambda code: sum(count * min(residual[pixel], errors[pixel][code])
                                        for pixel, count in histogram.items()))
        entries[i] = best
        chosen.add(best)
        residual = {pixel: min(value, errors[pixel][best]) for pixel, value in residual.items()}
    codes = [entries[i] for i in range(16)]
    palette = [colors[code] for code in codes]
    full, coarse = defaultdict(list), defaultdict(list)
    # Skip the HUD, and use medians so characters in the screenshot do
    # not dominate the calibration against the static room background.
    for y in range(16, HGR_HEIGHT):
        for x, key in enumerate(signal_keys(columns[y::HGR_HEIGHT])):
            pixel = pixels[y*HGR_WIDTH+x]
            full[key].append(pixel)
            coarse[coarse_key(key)].append(pixel)

    def quantize(groups):
        return {key: nearest(tuple(median(channel) for channel in zip(*samples)), palette)
                for key, samples in groups.items() if len(samples) >= 4}

    return codes, quantize(full), quantize(coarse)
