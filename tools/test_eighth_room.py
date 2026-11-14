from pathlib import Path
import argparse, subprocess
parser = argparse.ArgumentParser(description='Build isolated room 8 mechanism trace for XRoar')
parser.add_argument('build', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
from build import make_disk,split_room5_code,room6_segment,room8_segment
from replay_second_room import disk_entries
base=(args.build / 'flat.asm').read_text().replace('        andcc   #$AF\n','        andcc   #$AF\n        bra     title_start\n',1).replace('\ntitle_start\n','\ntitle_start\n        lbra test_run\n',1)
code="""        ifne PRELOAD_ALL
        org $1B00
test_run
        lda #ROOM8
        jsr change_room
        clr <enemy_on
        lda #8
        sta MMU2
        ldd #$4000
        std test_cursor
        clr test_frame
test_next
        lda #NATIVE_BANK
        sta MMU3
        ldd #0
        std native_actors
        std native_actors+10
        clr native_actors+2
        lda test_frame
        cmpa #70
        bhs test_push
        ldd #$517E
        std native_actors+10
        bra test_update
test_push
        cmpa #90
        bhs test_update
        lda room8_box
        ldb #64
        std native_actors
        lda #1
        sta native_actors+2
test_update
        jsr update_room8
        ldu test_cursor
        ldx #room8_height
        ldb #10
test_copy
        lda ,x+
        sta ,u+
        decb
        bne test_copy
        stu test_cursor
        inc test_frame
        lda test_frame
        cmpa #160
        blo test_next
test_passed
        bra test_passed
test_cursor fdb 0
test_frame fcb 0
        endc
"""
p=args.output.with_suffix('');p.with_suffix('.asm').write_text(base.replace('        end entry',code+'        end entry'))
subprocess.run(['lwasm','--6809','--decb','-D','PRELOAD_ALL=1','-D','AUDIO_DRIVER_TYPE=0',f'--map={p}.map',f'--output={p}.bin',f'{p}.asm'],check=True)
raw=p.with_suffix('.bin').read_bytes();e,c=split_room5_code(raw)
p.with_suffix('.DSK').write_bytes(make_disk(disk_entries((args.build / 'GOON-DAC.DSK').read_bytes(),e,b'\0',c,room6_segment(raw),room8_segment(raw))))
