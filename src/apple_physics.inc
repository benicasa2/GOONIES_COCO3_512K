; Apple $0B36/$0A62, native coordinates and previous-velocity integration.
; Bank $3E must remain mapped during calls. X: ten-byte actor record.
        ifne PRELOAD_ALL
NATIVE_BANK equ $3E
native_actors equ $1320
np_hits equ $1340             ; eight last-overlap row pointers
np_nx equ $1350
np_ny equ $1351
np_w equ $1352
np_h equ $1353
np_keys equ $1354             ; active HIGH, Apple bit order
np_oldvy equ $1355
np_allow equ $1356            ; horizontal=1, jump=2
np_gravity equ $1357
np_first equ $1358
np_limit equ $135A
np_rows equ $60F0
room7_rows equ $40F0
ROOM7_ART equ $3F
np_widths equ $6078
np_heights equ $60B4
        org $7500
native_physics
        ldu #np_rows
        ldd #np_rows+53*5
        std np_limit
        bra native_set_rows
native_physics7
        ldu #room7_rows
        ldd #room7_rows+37*5
        bra native_box_rows
native_box_physics
        ldu #room7_rows+37*5
        ldd #room7_rows+42*5
native_box_rows
        std np_limit
native_set_rows
        stu np_first
        lda 4,x
        anda #127
        ldu #np_widths
        ldb a,u
        stb np_w
        ldu #np_heights
        ldb a,u
        stb np_h
        lda ,x
        adda 2,x
        sta np_nx
        lda 1,x
        adda 3,x
        sta np_ny
        lda 3,x
        sta np_oldvy
        lda 8,x
        coma
        sta np_keys
        clr np_allow
        lda #1
        sta np_gravity
        ldu #np_hits
np_clear
        clr ,u+
        cmpu #np_nx
        blo np_clear
        ldu np_first
np_scan
        ldb ,u
        cmpb #8
        bhs np_scan_next
        lda np_nx
        cmpa 3,u
        bhi np_scan_next
        adda np_w
        cmpa 1,u
        blo np_scan_next
        lda np_ny
        cmpa 4,u
        bhi np_scan_next
        adda np_h
        cmpa 2,u
        blo np_scan_next
        lslb
        ldy #np_hits
        stu b,y
np_scan_next
        leau 5,u
        cmpu np_limit
        blo np_scan
        ldd np_hits+10
        beq np_drop
        lda np_keys
        bita #1
        bne np_ladder_on
        bita #2
        beq np_drop
        ldd np_hits+6
        beq np_ladder_on
        ldd np_hits+8
        beq np_drop
np_ladder_on
        lda #255
        sta 5,x
np_drop
        ldd np_hits+8
        beq np_wall0
        lda np_keys
        bita #2
        beq np_wall0
        lda #255
        sta 6,x
np_wall0
        ldu np_hits
        beq np_wall1
        tst 2,x
        bpl np_wall1
        lda 1,u
        sta np_nx
        clr 2,x
np_wall1
        ldu np_hits+2
        beq np_center
        tst 2,x
        ble np_center
        lda 1,u
        suba np_w
        deca
        sta np_nx
        clr 2,x
np_center
        tst 7,x
        bne np_ceiling
        ldu np_hits+8
        beq np_center_ladder
        tst 6,x
        bne np_center_do
np_center_ladder
        tst 5,x
        beq np_ceiling
        ldu np_hits+10
        beq np_ceiling
np_center_do
        lda np_w
        lsra
        sta np_w
        lda 1,u
        suba np_w
        sta np_nx
        lsl np_w
        clr 2,x
np_ceiling
        ldu np_hits+14
        beq np_ceiling2
        lda #1
        sta np_allow
        lda np_keys
        bita #2
        bne np_grip_stop
        clr np_gravity
np_grip_stop
        bita #12
        bne np_stop_y
        clr 2,x
        bra np_stop_y
np_ceiling2
        ldu np_hits+4
        beq np_floor
        tst 3,x
        bpl np_floor
np_stop_y
        lda 2,u
        sta np_ny
        clr 3,x
np_floor
        tst 6,x
        bne np_release
        tst np_oldvy
        ble np_release
        ldu np_hits+8
        bne np_floor_do
        ldu np_hits+6
        beq np_release
np_floor_do
        lda 2,u
        suba np_h
        sta np_ny
        clr 3,x
        ldd np_hits+8
        bne np_floor_ladder
        lda np_keys
        bita #2
        beq np_floor_allow
np_floor_ladder
        clr 5,x
np_floor_allow
        lda #3
        sta np_allow
        lda np_keys
        bita #12
        bne np_release
        clr 2,x
np_release
        clr 7,x
        ldd np_hits+10
        bne np_release_drop
        clr 5,x
np_release_drop
        ldd np_hits+8
        bne np_ladder_y
        clr 6,x
np_ladder_y
        tst 5,x
        beq np_input
        clr np_gravity
        lda np_keys
        anda #3
        cmpa #3
        beq np_input
        clr 3,x
np_input
        lda np_allow
        bita #1
        beq np_jump
        lda np_keys
        bita #4
        beq np_right
        ldb #-2
        stb 2,x
        ldb #255
        stb 7,x
np_right
        bita #8
        beq np_jump
        ldb #2
        stb 2,x
        ldb #255
        stb 7,x
np_jump
        lda np_allow
        bita #2
        beq np_climb
        lda np_keys
        bita #16
        beq np_climb
        lda #-5
        sta 3,x
np_climb
        tst 5,x
        beq np_gravity_do
        lda np_keys
        bita #1
        beq np_down
        ldb #-2
        stb 3,x
np_down
        bita #2
        beq np_gravity_do
        ldb #2
        stb 3,x
np_gravity_do
        tst np_gravity
        beq np_commit
        lda 3,x
        inca
        cmpa #4
        blt np_store_vy
        lda #4
np_store_vy
        sta 3,x
np_commit
        ; Type 6 retains the Apple trampoline velocity and input modifiers.
        ldd np_hits+12
        beq np_position
        lda np_oldvy
        cmpa #1
        ble np_position
        nega
        inca
        ldb np_allow
        bitb #2
        beq np_bounce_store
        ldb np_keys
        bitb #16
        beq np_bounce_down
        asra
        suba #7
        bra np_bounce_store
np_bounce_down
        bitb #2
        beq np_bounce_store
        asra
np_bounce_store
        sta 3,x
np_position
        ldd np_nx
        std ,x
        rts
native_animate
        ldd np_hits+14
        bne np_anim_grip
        tst 5,x
        bne np_anim_ladder
        lda 2,x
        beq np_anim_idle
        ldb #0
        tsta
        bpl np_anim_walk
        incb
np_anim_walk
        lda ,x
        bita #2
        beq np_anim_save
        addb #2
        bra np_anim_save
np_anim_ladder
        ldb #4
        lda 1,x
        bita #4
        beq np_anim_save
        incb
        bra np_anim_save
np_anim_idle
        ldb #6
        bra np_anim_save
np_anim_grip
        ldb #5
        lda ,x
        bita #2
        beq np_anim_save
        addb #2
np_anim_save
        addb 9,x
        stb 4,x
        rts

; Pose-sized native contact, X actor, U = left,top,right,bottom.
native_overlap
        lda ,x
        cmpa 2,u
        bhi np_outside
        ldb 4,x
        andb #127
        ldy #np_widths
        adda b,y
        cmpa ,u
        blo np_outside
        lda 1,x
        cmpa 3,u
        bhi np_outside
        ldy #np_heights
        adda b,y
        cmpa 1,u
        blo np_outside
        orcc #1
        rts
np_outside
        andcc #254
        rts
        include "room7_physics.inc"
native_code_end
        endc
