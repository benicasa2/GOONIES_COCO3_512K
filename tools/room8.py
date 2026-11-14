"""Extract the moving platform, pushed object and falling stamps from overlay 8."""
from room5 import call

def frames(initial):
    for height in range(46, 91):
        ram = initial.copy()
        ram[0x6366] = height
        call(ram, 0x62fa)
        yield bytes(ram[0x2000:0x4000])
    for position in range(128, 142):
        ram = initial.copy()
        ram[0x6263] = position
        call(ram, 0x61ce)
        yield bytes(ram[0x2000:0x4000])
    for height in range(61, 177, 5):
        ram = initial.copy()
        ram[0x62f0] = 1
        ram[0x62f4] = height-5
        call(ram, 0x62bb)
        yield bytes(ram[0x2000:0x4000])

def assets(initial, convert, patch_runs):
    base = convert(initial[0x2000:0x4000])
    images = list(map(convert, frames(initial)))
    assert len(images) == 83
    changed = {i for i, values in enumerate(zip(base, *images)) if len(set(values)) > 1}
    patches = [bytes(patch_runs(im, sorted(i for i in changed if im[i] != base[i]))) for im in images]
    patches.append(bytes(patch_runs(base, sorted(changed))))
    data = bytearray()
    address = 0x6000+len(patches)*2
    payload = bytearray()
    unique = {}
    for patch in patches:
        if patch not in unique:
            unique[patch] = address+len(payload)
            payload.extend(patch)
        data.extend(unique[patch].to_bytes(2, 'big'))
    data.extend(payload)
    if len(data) > 0x2000:
        raise ValueError(f'Room 8 graphics require {len(data)} bytes')
    return data
