"""Reference of Apple $0B36 for room-8 actors (terrain types 0..7)."""
def signed(v):
    return v-256 if v&128 else v

def advance(state, rows, widths, heights):
    x,y,vx,vy,pose,ladder,drop,latch,keys,base=state
    w,h=widths[pose&127],heights[pose&127]
    nx,ny=(x+vx)&255,(y+vy)&255
    hits=[None]*8
    for row in rows:
        kind,left,top,right,bottom=row
        if kind<8 and ((nx+w)&255)>=left and right>=nx and ((ny+h)&255)>=top and bottom>=ny:
            hits[kind]=row
    f=[r is not None for r in hits]
    up,down,left,right,jump=[not keys&bit for bit in (1,2,4,8,16)]
    allow_left=allow_right=allow_jump=False
    gravity=True
    oldvy=vy
    if f[5] and (up or ((not f[3] or f[4]) and down)):ladder=255
    if f[4] and down:drop=255
    if f[0] and signed(vx)<0:nx=hits[0][1];vx=0
    if f[1] and 0<signed(vx):nx=(hits[1][1]-w-1)&255;vx=0
    if not latch:
        kind=4 if f[4] and drop else 5 if ladder and f[5] else None
        if kind is not None:nx=(hits[kind][1]-(w//2))&255;vx=0;w=w//2*2
    kind=2 if f[2] and signed(vy)<0 else None
    if f[7]:
        kind=7;allow_left=allow_right=True
        if not down:gravity=False
    if kind is not None:
        ny=hits[kind][2];vy=0
        if kind==7 and not (left or right):vx=0
    kind=4 if not drop and f[4] and 0<signed(oldvy) else 3 if not drop and f[3] and 0<signed(oldvy) else None
    if kind is not None:
        ny=(hits[kind][2]-h)&255;vy=0
        if f[4] or down:ladder=0
        allow_left=allow_right=allow_jump=True
        if not (left or right):vx=0
    latch=0
    if not f[5]:ladder=0
    if not f[4]:drop=0
    if ladder:
        gravity=False
        if not(up and down):vy=0
    if allow_left and left:vx=254;latch=255
    if allow_right and right:vx=2;latch=255
    if allow_jump and jump:vy=251
    if ladder and up:vy=254
    if ladder and down:vy=2
    if gravity:vy=(signed(vy)+1)&255 if signed(vy)+1<4 else 4
    if signed((1-oldvy)&255)<0 and f[6] and 0<signed(oldvy):
        v=signed((1-oldvy)&255)
        if allow_jump and jump:v=v//2-7
        elif allow_jump and down:v=v//2
        vy=v&255
    return (nx,ny,vx,vy,pose,ladder,drop,latch,keys,base),f

def animate(state,flags):
    x,y,vx,vy,pose,ladder,drop,latch,keys,base=state
    if flags[7]:p=7 if x&2 else 5
    elif ladder:p=5 if y&4 else 4
    elif not vx:p=6
    elif vx&128:p=3 if x&2 else 1
    else:p=2 if x&2 else 0
    return (*state[:4],p+base,*state[5:])
