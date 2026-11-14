"""Extract room 7 collision, original sprites, wave tracks and bat waypoints."""
from room5 import call


def word(ram, address):
    return ram[address] | ram[address+1] << 8


def collision(ram, pointers, count):
    columns = [word(ram, a) for a in range(pointers, pointers+10, 2)]
    return bytes(ram[p+i] for i in range(count) for p in columns)


def assets(ram, convert, pose, patch):
    data = bytearray(0x212)
    data.extend(ram[0xBE00:0xBF00])
    stored = {}
    data[0x78:0xF0] = bytes(ram[0xE1C:0xE94])
    data[0xF0:0x1C2] = collision(ram, 0x99, 37) + collision(ram, 0x64A2, 5)
    def store(table, index, payload):
        at = table+2*index
        if payload not in stored:
            stored[payload] = 0x6000+len(data)
            data.extend(payload)
        data[at:at+2] = stored[payload].to_bytes(2, 'big')
    for i in (*range(8,20),48):
        store(0, i, pose(ram, i))
    for i in range(10):
        x, y = word(ram, 0x1638+2*i), word(ram, 0x164C+2*i)
        for end in range(1,65):
            if ram[y+end-1] == 255:
                break
        else:
            raise ValueError(f"Missing bat terminator for path {i}")
        store(0x1C2, i, bytes(v for j in range(end) for v in (ram[x+j],ram[y+j])))
    data[0x1D6:0x1E0] = bytes(ram[0x1660:0x166A])
    def stamp(table, index, address, column, height):
        mem = ram.copy()
        mem[0x2000:0x4000] = [0] * 8192
        mem[0x12:0x17] = [column, 64, 0, address & 255, address >> 8]
        call(mem, 0x8027)
        image = convert(mem[0x2000:0x4000])
        start = 10 + column*7//2
        width = (7*ram[address] + 2)//2
        pixels = bytes(image[y*160+x] for y in range(64,64+height)
                       for x in range(start,start+width))
        store(table,index,bytes((start,width,height))+pixels)
    for i in range(4):
        for j, table in enumerate((0x62E2,0x62EA)):
            a = word(ram,table+2*i)
            stamp(0x1E0,4*j+i,a,32 if j==0 else ram[0x62F2+i],ram[a+1])
    for i in range(4):
        y,x = word(ram,0x61AF+2*i),word(ram,0x61BB+2*i)
        end = next(j for j in range(32) if ram[x+j]==0)
        store(0x1F0,i,bytes(v for j in range(end) for v in (ram[x+j],ram[y+j]))+bytes((0,0)))
    # Wave stamp variants are selected by the Apple x-coordinate remainder.
    for i, x in enumerate((8,9,10,11,12,13,14)):
        v = ram[0x13A2+x-8]
        stamp(0x1F8,i,word(ram,0x61C7+2*v),ram[0x1316+x-8],1)
    base = convert(ram[0x2000:0x4000])
    lever_pixels = set()
    for i, (addr, x, y) in enumerate(((0x65D7,8,112),(0x65C2,7,111),
            (0x65FA,12,111),(0x65EC,7,105),(0x6608,12,105))):
        mem = ram.copy()
        mem[0x12:0x17] = [x,y,0,addr&255,addr>>8]
        call(mem, 0x8027)
        image=convert(mem[0x2000:0x4000])
        data[0x206+2*i:0x208+2*i]=(0x6000+len(data)).to_bytes(2,'big')
        changed = [n for n,(a,b) in enumerate(zip(image,base)) if a!=b]
        lever_pixels.update(changed)
        data.extend(patch(image,changed))
    data[0x210:0x212] = (0x6000+len(data)).to_bytes(2,"big")
    data.extend(patch(base,sorted(lever_pixels)))
    return bytes(data)
