from pathlib import Path
import argparse, subprocess
parser = argparse.ArgumentParser(description='Build isolated room 6 state and collision tests for XRoar')
parser.add_argument('build', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
from build import make_disk,split_room5_code,room6_segment,room8_segment
from replay_second_room import disk_entries
base=(args.build / 'flat.asm').read_text().replace('        andcc   #$AF\n','        andcc   #$AF\n        bra     title_start\n',1).replace('\ntitle_start\n','\ntitle_start\n        lbra test_run\n',1)
code="""        ifne PRELOAD_ALL
        org $1B00
test_run
        lda #ROOM6
        jsr change_room
        clr particle_rng
        ldd #0
        std <px
        std <p2x
        ldd #$6000
        std test_cursor
        lda #160
        sta test_frames
test_frame
        jsr update_room6
        jsr room_puzzles
        lda #$3D
        sta MMU3
        ldu test_cursor
        ldx #room5_eggs
test_record
        lda 2,x
        sta ,u+
        ldd 3,x
        std ,u++
        lda 7,x
        sta ,u+
        lda 8,x
        sta ,u+
        leax R5_SIZE,x
        cmpx #room5_end
        blo test_record
        ldd <plate_timer
        std ,u++
        lda <plate_timer+2
        sta ,u+
        lda <plate_mask
        sta ,u+
        lda particle_rng
        sta ,u+
        stu test_cursor
        dec test_frames
        bne test_frame
        lda #ROOM6_ART
        sta MMU3
        ldx #room5_eggs
test_hit_loop
        clr 2,x
        lda #1
        sta 8,x
        lda #50
        sta 4,x
        lda #170
        sta 6,x
        lda #0
        sta <death
        ldb 3,x
        addb #2
        clra
        ldu #room5_xmap
        lda d,u
        ldb #52
        std <px
        pshs x
        jsr room6_actor
        puls x
        tst <death
        lbeq test_failed
        lda <dead_player
        cmpa #px
        lbne test_failed
        leax R5_SIZE,x
        cmpx #room5_end
        blo test_hit_loop
        clr <death
        ldd #$00A0
        std <px
        ldd #0
        std <p2x
        jsr room6_pit
        tst <death
        lbne test_failed
        inc <py
        jsr room6_pit
        tst <death
        lbeq test_failed
        clr <death
        ldd #0
        std <px
        ldd #$00A1
        std <p2x
        jsr room6_pit
        tst <death
        lbeq test_failed
        lda <dead_player
        cmpa #p2x
        lbne test_failed
        bra test_passed
test_failed
        bra test_failed
test_passed
        bra test_passed
test_cursor fdb 0
test_frames fcb 0
        endc
"""
p=args.output.with_suffix('');p.with_suffix('.asm').write_text(base.replace('        end entry',code+'        end entry'))
subprocess.run(['lwasm','--6809','--decb','-D','PRELOAD_ALL=1','-D','AUDIO_DRIVER_TYPE=0',f'--map={p}.map',f'--output={p}.bin',f'{p}.asm'],check=True)
raw=p.with_suffix('.bin').read_bytes();e,c=split_room5_code(raw)
p.with_suffix('.DSK').write_bytes(make_disk(disk_entries((args.build / 'GOON-DAC.DSK').read_bytes(),e,b'\0',c,room6_segment(raw),room8_segment(raw))))
