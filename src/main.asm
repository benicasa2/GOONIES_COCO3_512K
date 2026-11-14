; CoCo 3 NTSC, 512 KiB. LOADM then EXEC. Reset to return to BASIC.
        org     $2000

INIT0   equ     $FF90
INIT1   equ     $FF91
IRQEN   equ     $FF92
FIRQEN  equ     $FF93
TIMER_H equ     $FF94
TIMER_L equ     $FF95
VMODE   equ     $FF98
VRES    equ     $FF99
VOFF    equ     $FF9D
PAL     equ     $FFB0
MMU2    equ     $FFA2
MMU3    equ     $FFA3
VID     equ     $4000
BG      equ     $6000
FB0     equ     $08
FB1     equ     $0C
ROOM    equ     $10
IRQVEC  equ     $FEF7
FIRQVEC equ     $FEF4

; DP is zero throughout. No BASIC calls after init.
ticks   equ     $80
last    equ     $81
front   equ     $82
back    equ     $83
ready   equ     $84
keys    equ     $85
px      equ     $86
py      equ     $87
p2x     equ     $88
p2y     equ     $89
ex      equ     $8A
ey      equ     $8B
old     equ     $8C             ; two records of three (x,y) pairs
actor   equ     $98
rows    equ     $9A
row_x   equ     $9B
row_y   equ     $9C
bank    equ     $9D
phase   equ     $A0
pitch   equ     $A2
length  equ     $A4
ssc_ptr equ     $A5
vy      equ     $A7
jump_was equ    $A8
active  equ     $A9
enemy_target equ $AA
switch_was equ  $AB
room_bank equ   $AC
room_was equ    $AD
redraw  equ     $AE
grounded equ    $AF
next_y  equ     $B0
feet    equ     $B1
enemy_on equ    $B2
wall_x  equ     $B3
enemy_wait equ  $B6
enemy_patrol equ $B7
STAGE   equ     $4000
passive_vy equ  $B8
idle_step equ   $B9
won     equ     $BA
fire_out equ    $BB
portal_cd equ   $BC             ; one timer per player
plate_timer equ $BE             ; three room-6 switch timers
plate_mask equ  $C1
layout_ptr equ  $C2
lives   equ     $C4
death   equ     $C5
dead_player equ $C6
crusher_y equ   $C7
crusher_dir equ $CA
crusher_timer equ $CD
music_ptr equ   $D0
music_ticks equ $D2
music_note equ  $D3
music_packet equ $D7
pitch2  equ     $E6
phase2  equ     $E8
music_dirty equ $EA
sample_mix equ  $EB
ending_bank equ $EC
ending_ptr equ  $ED
ending_base equ $EF
ending_repeat equ $F0
ending_hold equ $F1
enemy_vy equ    $F2
gate_mask equ   $F3
title_pal_pending equ $F4
room3_switch equ $F5
hazard_box equ   $F6
crusher_four equ $FA
crusher_four_dir equ $FB
room2_open equ   $FC
room2_mask equ   $FD
EXIT    equ     BG+7
TERRAIN equ     BG+12
SPRITE_MAX_X equ 240
SPRITE_MAX_Y equ 170
BODY_X  equ     13
BODY_Y  equ     17

entry
        jmp     start           ; EXEC &H2000
        jmp     preload_banks   ; LZ loader entry alias
        jmp     require_512     ; EXEC &H2006 before loading room data
        jmp     preload_banks   ; LZ loader entry alias
        ifne    PRELOAD_ALL
        jmp     preload_banks   ; EXEC &H200C for LZ banks
        ifne AUDIO_DRIVER_TYPE
        jmp     ssc_install_music ; EXEC &H200F after loading MUSIC
        endc
        endc

start
        orcc    #$50
        lds     #$1EFF
        clra
        tfr     a,dp
        ldx     #ticks
state_zero
        clr     ,x+
        cmpx    #room2_mask+1
        blo     state_zero
        sta     $FFD9           ; 1.79 MHz
        lda     #$40           ; 256K DRAMs, task 0, slow timer clock
        sta     INIT1
        clra
        sta     IRQEN
        sta     FIRQEN
        sta     $FF01           ; disable legacy PIA IRQs
        sta     $FF03
        sta     $FF21
        sta     $FF23
        lda     $FF00
        lda     $FF02
        lda     $FF20
        lda     $FF22
        lda     #$6C            ; CoCo3 video, MMU, GIME IRQ, constant FE page, SCS
        sta     INIT0
        jsr     require_512
        ifne PRELOAD_ALL
        jsr     install_room5
        jsr     install_room6
        endc
        ifeq    PRELOAD_ALL
        ifne AUDIO_DRIVER_TYPE
        jsr     ssc_install_music
        endc
        jsr     preload_banks
        endc
        lda     #ROOM
        sta     <room_bank
        ifeq    PRELOAD_ALL
        lda     #FB0
        jsr     copy_background
        lda     #FB1
        jsr     copy_background
        endc
        ifne    PRELOAD_ALL
        ldx     #palette_title
        else
        ldx     #palette_rgb
        endc
        jsr     apply_palette
        clr     $FF9A
        clr     $FF9C
        clr     $FF9F
        lda     #$80
        sta     VMODE
        lda     #$1E            ; 192 rows, 160 bytes/row, 4 bpp
        sta     VRES
        lda     #FB0
        sta     <front
        jsr     show_page
        lda     #FB1
        sta     <back
        lda     #$7E            ; JMP extended in secondary vectors
        sta     IRQVEC
        sta     FIRQVEC
        ldd     #vertical_irq
        std     IRQVEC+1
        ldd     #sample_firq
        std     FIRQVEC+1
        lda     #5
        sta     <lives
        jsr     reset_room
        ldx     #old
old_init
        ldd     <px
        std     ,x++
        ldd     <p2x
        std     ,x++
        ldd     <ex
        std     ,x++
        cmpx    #old+12
        blo     old_init
        jsr     audio_init
        lda     IRQEN
        lda     FIRQEN
        lda     #8
        sta     IRQEN
        andcc   #$AF

        ifne    PRELOAD_ALL
; The disk loader has already drawn the title in FB0. Leave it visible
; while the vertical IRQ plays the theme. Consume Space before gameplay.
title_wait
        lda     <ticks
        cmpa    <last
        beq     title_wait
        sta     <last
        jsr     read_keys
        lda     <keys
        bita    #$40
        beq     title_wait
title_release
        jsr     read_keys
        lda     <keys
        bita    #$40
        bne     title_release
title_start
        lda     #1
        sta     <title_pal_pending
        lda     #2
        sta     <redraw
        endc
main_loop
        lda     <ready
        bne     main_loop
        lda     <ticks
        cmpa    <last
        beq     main_loop
        sta     <last
        ifne    PRELOAD_ALL
        tst     <won
        bne     main_ending
        endc
        tst     <death
        lbne    death_step
        jsr     read_keys
        ifne PRELOAD_ALL
        lda <room_bank
        cmpa #ROOM7
        blo main_other_room
        jsr move_actors
        tst <won
        lbne main_ending
        lbra main_paint
main_other_room
        jsr     update_room6
        endc
        jsr     room_puzzles
        jsr     move_actors
        jsr     settle_idle
        jsr     update_cash
        jsr     update_cooler
        ifne PRELOAD_ALL
        jsr     update_room8
        endc
        jsr     final_room_pit
        jsr     room3_hazards
        jsr     room2_hazards
        ifne    PRELOAD_ALL
        jsr     update_room4
        jsr     update_room5
        endc
        tst     <death
        bne     main_paint
        jsr     check_exit
        ifne    PRELOAD_ALL
        tst     <won
        bne     main_ending
        endc
main_paint
        jsr     paint
        inc     <ready          ; publish only after all writes to back
        bra     main_loop
        ifne    PRELOAD_ALL
main_ending
        jsr     ending_step
        bra     main_loop
        endc

vertical_irq
        lda     IRQEN           ; acknowledge
        bita    #8
        beq     irq_done
        inc     <ticks
        lda     <ready
        beq     irq_audio
        lda     <back
        ldb     <front
        sta     <front
        stb     <back
        jsr     show_page
        ifne    PRELOAD_ALL
        lda     <title_pal_pending
        beq     irq_ready
        ldx     #palette_rgb
        cmpa    #2
        bne     irq_palette
        ldx     #palette_title
irq_palette
        jsr     apply_palette
        clr     <title_pal_pending
irq_ready
        endc
        clr     <ready
irq_audio
        jsr     audio_frame
irq_done
        rti

apply_palette
        ldy     #PAL
pal_loop
        lda     ,x+
        sta     ,y+
        cmpy    #PAL+16
        blo     pal_loop
        rts

show_page
        lsla                    ; physical (bank * 8192) / 8 = bank * 1024
        lsla
        clrb
        std     VOFF
        rts

; Banks $08/$18 alias on a 128 KiB machine. Restore both test locations.
require_512
        pshs    cc,a,b,x
        orcc    #$50
        lda     MMU2
        pshs    a
        lda     #$08
        sta     MMU2
        ldb     VID
        lda     #$18
        sta     MMU2
        lda     VID
        pshs    a,b
        lda     #$A5
        sta     VID
        lda     #$08
        sta     MMU2
        lda     #$5A
        sta     VID
        lda     #$18
        sta     MMU2
        lda     VID
        tfr     a,b
        clra
        tfr     d,x
        puls    a,b
        sta     VID
        lda     #$08
        sta     MMU2
        stb     VID
        puls    a
        sta     MMU2
        tfr     x,d
        cmpb    #$A5
        beq     ram_ok
        lda     #$6C
        sta     INIT0
        lda     #$80            ; red border error signal on RGB
        sta     VMODE
        lda     #$24
        sta     $FF9A
ram_fail
        bra     ram_fail
ram_ok
        puls    cc,a,b,x,pc

; Load consecutive LZ streams into consecutive physical banks.
preload_banks
        pshs    cc,a,b,x,y,u
        orcc    #$50
        lda     MMU3
        pshs    a
        ldx     #STAGE
        ldd     ,x++
        pshs    a,b
preload_bank
        lda     ,s
        sta     MMU3
        jsr     decode_bank
        inc     ,s
        dec     1,s
        bne     preload_bank
        leas    2,s
        puls    a
        sta     MMU3
        puls    cc,a,b,x,y,u,pc

decode_bank
        ldy     #BG
title_token
        ldb     ,x+
        beq     title_unpacked
        bmi     title_match
title_literal
        lda     ,x+
        sta     ,y+
        decb
        bne     title_literal
        bra     title_token
title_match
        andb    #$7F
        addb    #3
        pshs    b
        ldd     ,x++
        leau    d,y
        puls    b
title_copy
        lda     ,u+
        sta     ,y+
        decb
        bne     title_copy
        bra     title_token
title_unpacked
        rts

; A = first destination bank; never copy into the displayed page in main.
copy_background
        ldb     <room_bank
copy_background_bank
        stb     MMU3
        pshs    a,b
        jsr     room_copy
        puls    a,b
        inca
        incb
        pshs    a
        lda     <room_bank
        adda    #4
        pshs    a
        cmpb    ,s+
        puls    a
        blo     copy_background_bank
        rts
room_copy
        sta     MMU2
        pshs    b
        ldx     #BG
        ldy     #VID
room_copy_word
        ldd     ,x++
        std     ,y++
        cmpy    #VID+$2000
        blo     room_copy_word
        puls    b,pc

; Arrow keys and SPACE use row 3, G uses row 0 and R uses row 2.
read_keys
        clr     $FF03
        lda     #$FF
        sta     $FF02           ; DDRB = outputs
        lda     #KEY_PORT_MODE
        sta     $FF03
        clr     <keys
        ldx     #key_scan
key_loop
        lda     ,x+
        beq     key_done
        sta     $FF02
        lda     $FF00
        bita    ,x+
        bne     key_skip
        lda     <keys
        ora     ,x
        sta     <keys
key_skip
        leax    1,x
        bra     key_loop
key_done
        lda     #$FF
        sta     $FF02
        rts
key_scan
        fcb $F7,8,1,$EF,8,2,$DF,8,4,$BF,8,8,$7F,8,$40,$7F,1,$20,$FB,4,$80,0
map_terrain
        lda     <room_bank
        adda    #4
        sta     MMU3
        rts

reset_room
        jsr     map_terrain
        ldd     BG
        std     <px
        ldd     BG+2
        std     <p2x
        ldd     BG+4
        std     <ex
        lda     BG+6
        sta     <enemy_on
        lda     #193            ; Original home X=$72 in Apple coordinates
        sta     <enemy_target
        lda     #160
        sta     <enemy_wait
        clr     <enemy_patrol
        clr     <grounded
        clr     <vy
        clr     <active
        clr     <passive_vy
        clr     <won
        clr     <fire_out
        clr     <enemy_vy
        clr     <death
        jsr     reset_room1
        jsr     reset_mechanics
        jsr     reset_room3
        clr     <room2_open
        clr     <room2_mask
        ifne    PRELOAD_ALL
        jsr     reset_room4
        jsr     reset_room5
        jsr     reset_room6
        jsr     reset_room8
        jsr     reset_room7
        jsr     reset_motion2
        jsr     reset_launcher
        endc
        clr     $FF9A
        rts

; Demonstration rules. The selected character changes on a new G press.
move_actors
        lda     <keys
        anda    #$80
        cmpa    <room_was
        beq     check_switch
        sta     <room_was
        beq     check_switch
        ifne    PRELOAD_ALL
        lda     <room_bank
        adda    #5
        cmpa    #ROOM+40
        blo     change_room
        lda     #ROOM
change_room
        sta     <room_bank
        jsr     reset_room
        lda     #2
        sta     <redraw
        rts
        endc
check_switch
        lda     <keys
        anda    #$20
        cmpa    <switch_was
        beq     choose_actor
        sta     <switch_was
        beq     choose_actor
        lda     <active
        eora    #1
        sta     <active
        lda     <vy
        ldb     <passive_vy
        sta     <passive_vy
        stb     <vy
        clr     <grounded
        ldx     #speech_actor
        jsr     audio_event
choose_actor
        ifne PRELOAD_ALL
        lda <room_bank
        cmpa #ROOM8
        lbeq room8_native_frame
        cmpa #ROOM7
        lbeq room7_frame
        endc
        jsr     map_terrain
        ldx     #px
        ldb     <active
        beq     actor_cooldown
        leax    2,x
actor_cooldown
        ldy     #portal_cd
        tst     b,y
        lbne    actor_enemy
actor_left
        lda     <keys
        bita    #4
        beq     actor_right
        lda     ,x
        beq     actor_right
        suba    #2
        jsr     wall_left
actor_right
        lda     <keys
        bita    #8
        beq     actor_vertical
        lda     ,x
        cmpa    #SPRITE_MAX_X
        bhs     actor_vertical
        adda    #2
        jsr     wall_right
actor_vertical
        lda     <keys
        anda    #$40
        cmpa    <jump_was
        beq     actor_gravity
        sta     <jump_was
        beq     actor_gravity
        tst     <grounded
        beq     actor_gravity
        lda     #-5
        sta     <vy
        pshs    x
        ldx     #speech_jump
        jsr     audio_event
        puls    x
actor_gravity
        jsr     room_passage
        lbcs    actor_enemy
        jsr     room1_objects
        jsr     fireplace
        lbcs    actor_enemy
        lda     <keys
        bita    #3
        beq     actor_fall
        ldu     #TERRAIN
find_ladder
        lda     ,u
        bmi     actor_fall
        cmpa    #5
        bne     next_ladder
        lda     <room_bank
        cmpa    #ROOM
        bne     ladder_overlap
        cmpu    #TERRAIN+16*5
        bne     ladder_overlap
        lda     1,x
        cmpa    #46
        bhi     next_ladder
ladder_overlap
        lda     ,x
        cmpa    1,u
        bhi     next_ladder
        adda    #BODY_X
        cmpa    1,u
        blo     next_ladder
        lda     1,x
        adda    #BODY_Y
        cmpa    2,u
        blo     next_ladder
        lda     1,x
        cmpa    4,u
        bhi     next_ladder
        clr     <vy
        clr     <grounded
        lda     <keys
        bita    #1
        beq     ladder_down
        lda     1,x
        cmpa    #2
        lblo    actor_enemy
        suba    #2
        sta     1,x
        lbra    actor_enemy
ladder_down
        lda     1,x
        cmpa    #SPRITE_MAX_Y-2
        lbhs    actor_enemy
        inc     1,x
        inc     1,x
        lbra    actor_enemy
next_ladder
        leau    5,u
        bra     find_ladder

actor_fall
        clr     <grounded
        lda     1,x
        adda    <vy
        ; Starting Y is at most 180 and |VY| is at most 5.
        cmpa    #250
        blo     below_sky
        clra
below_sky
        cmpa    #SPRITE_MAX_Y
        bls     choose_floor
        lda     #SPRITE_MAX_Y
        inc     <grounded
choose_floor
        sta     <next_y
        jsr     room_grip
        lbcs    actor_enemy
        lda     1,x
        adda    #BODY_Y
        sta     <feet
        tst     <vy
        bmi     find_ceiling
        ldu     #TERRAIN
find_floor
        lda     ,u
        bmi     commit_y
        cmpa    #3
        beq     floor_x
        cmpa    #4
        beq     floor_x
        suba    #$40
        cmpa    #13
        bhs     next_floor
        tfr     a,b
        ldy     <layout_ptr
        tst     b,y
        beq     next_floor
floor_x
        lda     ,x
        cmpa    3,u
        bhi     next_floor
        adda    #BODY_X
        cmpa    1,u
        blo     next_floor
        lda     2,u
        cmpa    <feet
        blo     next_floor
        suba    #BODY_Y
        cmpa    <next_y
        bhi     next_floor
        sta     <next_y
        inc     <grounded
next_floor
        leau    5,u
        bra     find_floor
find_ceiling
        ldu     #TERRAIN
ceiling_row
        lda     ,u
        bmi     commit_y
        cmpa    #2
        bne     next_ceiling
        lda     ,x
        cmpa    3,u
        bhi     next_ceiling
        adda    #BODY_X
        cmpa    1,u
        blo     next_ceiling
        lda     4,u
        cmpa    1,x
        bhi     next_ceiling
        cmpa    <next_y
        blo     next_ceiling
        sta     <next_y
        clr     <vy
next_ceiling
        leau    5,u
        bra     ceiling_row

commit_y
        lda     <next_y
        sta     1,x
        tst     <grounded
        beq     actor_accelerate
        clr     <vy
        bra     actor_enemy
actor_accelerate
        lda     <vy
        cmpa    #4
        bge     actor_enemy
        inc     <vy
actor_enemy
        tst     <idle_step
        bne     actor_done
        tst     <enemy_on
        beq     actor_done
        lda     <room_bank
        cmpa    #ROOM8
        lbeq    final_room_enemy
        cmpa    #ROOM3
        beq     actor_done
        jmp     first_room_enemy
enemy_contact
        lda     1,x
        suba    <ey
        adda    #BODY_Y
        cmpa    #BODY_Y*2+1
        bhs     actor_done
        lda     ,x
        suba    <ex
        adda    #BODY_X
        cmpa    #BODY_X*2+1
        bhs     actor_done
        jsr     mark_death
actor_done
        rts

; Scene 1, Apple $63EE-$6423 and $6259-$629D.
; The jump toward the cooler opens the floor hatch below the fireplace.
fireplace
        lda     <room_bank
        cmpa    #ROOM
        bne     fire_no_drop
        tst     <fire_out
        bne     fire_try_drop
        tst     cooler_state
        bne     fire_no_drop
        lda     <keys
        bita    #8
        beq     fire_no_drop
        tst     <vy
        bpl     fire_no_drop
        lda     ,x
        cmpa    #31
        bhi     fire_no_drop
        adda    #BODY_X
        cmpa    #27
        blo     fire_no_drop
        lda     1,x
        cmpa    #154
        bhi     fire_no_drop
        adda    #BODY_Y
        cmpa    #131
        blo     fire_no_drop
        lda     #$81            ; First fall pose, skip advance on impact frame.
        sta     cooler_state
        bra     fire_no_drop
fire_try_drop
        lda     <keys
        bita    #2
        beq     fire_no_drop
        lda     ,x
        cmpa    #65
        bhi     fire_no_drop
        adda    #BODY_X
        cmpa    #65
        blo     fire_no_drop
        lda     1,x
        cmpa    #157
        bhi     fire_no_drop
        adda    #BODY_Y
        cmpa    #157
        blo     fire_no_drop
        lda     #158
        sta     1,x
        clr     <vy
        clr     <grounded
        orcc    #1
        rts
fire_no_drop
        andcc   #$FE
        rts

settle_idle
        lda     <vy
        ldb     <grounded
        pshs    a,b
        lda     <passive_vy
        sta     <vy
        ldx     #p2x
        tst     <active
        beq     idle_fall
        ldx     #px
idle_fall
        inc     <idle_step
        jsr     actor_fall
        clr     <idle_step
        lda     <vy
        sta     <passive_vy
        puls    a,b
        sta     <vy
        stb     <grounded
        rts

; The shared exit test uses the original rectangle and next-room index.
; Individual puzzle gate scripts are separate from this geometric check.
check_exit
        ifne    PRELOAD_ALL
        tst     <won
        bne     exit_done
        ldx     #px
        jsr     exit_overlap
        bcc     exit_done
        ldx     #p2x
        jsr     exit_overlap
        bcc     exit_done
        lda     <room_bank
        cmpa    #ROOM
        bne     exit_other
        tst     <fire_out
        beq     exit_done
exit_other
        jsr     room2_exit
        bcc     exit_done
        jsr     room3_exit
        bcc     exit_done
        lda     <room_bank
        cmpa    #ROOM+15
        bne     exit_room5_score
        lda     <lives
        adda    #3
        cmpa    #9
        bls     exit_bonus
        lda     #9
exit_bonus
        sta     <lives
        bra     exit_score
exit_room5_score
        cmpa    #ROOM8
        beq     exit_score
        cmpa    #ROOM5
        bne     exit_destination
exit_score
        jsr     score_room4_exit
exit_destination
        lda     EXIT+4
        cmpa    #8
        bhs     exit_win
        ldb     #5
        mul
        tfr     b,a
        adda    #ROOM
        lbra    change_room
exit_win
        inc     <won
        clr     <room_bank
        clr     <ending_base
        clr     <ending_repeat
        clr     <ending_hold
        lda     #4
        sta     <ending_bank
        ldd     #BG
        std     <ending_ptr
exit_done
        endc
        rts

exit_overlap
        ldu     #EXIT
box_overlap
        lda     ,x
        cmpa    2,u
        bhi     exit_outside
        adda    #BODY_X
        cmpa    ,u
        blo     exit_outside
        lda     1,x
        cmpa    3,u
        bhi     exit_outside
        adda    #BODY_Y
        cmpa    1,u
        blo     exit_outside
        orcc    #1
        rts
exit_outside
        andcc   #$FE
        rts

; The original wall type depends on direction. Compare the swept leading edge.
wall_left
        sta     <wall_x
        ldu     #TERRAIN
wall_left_loop
        lda     ,u
        bmi     wall_commit
        bne     wall_left_next
        lda     3,u
        cmpa    ,x
        bhi     wall_left_next
        cmpa    <wall_x
        bhs     wall_y
wall_left_next
        leau    5,u
        bra     wall_left_loop
wall_right
        sta     <wall_x
        ldu     #TERRAIN
wall_right_loop
        lda     ,u
        bmi     wall_commit
        cmpa    #1
        bne     wall_right_next
        lda     ,x
        adda    #BODY_X
        cmpa    1,u
        bhi     wall_right_next
        lda     <wall_x
        adda    #BODY_X
        cmpa    1,u
        bhs     wall_y
wall_right_next
        leau    5,u
        bra     wall_right_loop
wall_y
        lda     1,x
        cmpa    4,u
        bhi     wall_continue
        adda    #BODY_Y-1
        cmpa    2,u
        blo     wall_continue
        rts
wall_continue
        tst     ,u
        beq     wall_left_next
        bra     wall_right_next
wall_commit
        lda     <wall_x
        sta     ,x
        rts

; Restore the dirty rectangles of the page being reused, then draw actors.
; A/B = even x/top y. Sprite envelopes are 16x22 and inside the viewport.
paint
        ifne PRELOAD_ALL
        lda <room_bank
        cmpa #ROOM7
        lbeq room7_paint
        endc
        tst     <redraw
        beq     paint_dirty
        dec     <redraw
        lda     <back
        jsr     copy_background
        bra     paint_positions
paint_dirty
        ldx     #old
        lda     <back
        cmpa    #FB0
        beq     paint_old
        leax    6,x
paint_old
        stx     <actor
        ldd     ,x
        jsr     restore
        ldx     <actor
        ldd     2,x
        jsr     restore
        ldx     <actor
        ldd     4,x
        jsr     restore
        jsr     restore_crushers
        jsr     restore_chair
        jsr     restore_cash
        ifne    PRELOAD_ALL
        jsr     restore_room4
        jsr     restore_room5
        jsr     restore_room6
        jsr     restore_launcher
        endc
paint_positions
        ifne PRELOAD_ALL
        jsr     clear_room8_art
        endc
        jsr     draw_platforms
        jsr     draw_final_gates
        jsr     draw_crushers
        jsr     draw_chair
        jsr     draw_cash
        jsr     draw_cooler
        jsr     draw_room2
        ifne    PRELOAD_ALL
        jsr     draw_room4
        jsr     draw_room5
        jsr     draw_room6
        jsr     draw_room8
        jsr     draw_launcher
        endc
        jsr     draw_lives
        ifne PRELOAD_ALL
        jsr     draw_room4_score
        endc
        ldx     #old
        lda     <back
        cmpa    #FB0
        beq     paint_save
        leax    6,x
paint_save
        ldd     <px
        std     ,x
        ldd     <p2x
        std     2,x
        ldd     <ex
        std     4,x
        ifne PRELOAD_ALL
        lda <room_bank
        cmpa #ROOM8
        lbeq room8_native_draw
        endc
        lda     #ROOM+4
        sta     MMU3
        ldu     #pose_p1_idle
        tst     <active
        bne     paint_p1
        jsr     actor_walking
        beq     paint_p1
        ldu     #pose_p1_walk
        jsr     walking_frame
paint_p1
        lda     #px
        jsr     death_pose
        ldd     <px
        jsr     draw_actor
        ldu     #pose_p2_idle
        tst     <active
        beq     paint_p2
        jsr     actor_walking
        beq     paint_p2
        ldu     #pose_p2_walk
        jsr     walking_frame
paint_p2
        lda     #p2x
        jsr     death_pose
        ldd     <p2x
        jsr     draw_actor
        tst     <enemy_on
        beq     paint_done
        ldu     #pose_enemy_idle
        lda     <room_bank
        cmpa    #ROOM3
        bne     paint_enemy_room1
        lda     #ROOM+19
        sta     MMU3
        lda     room3_bat_frame
        anda    #3
        ldb     #176
        mul
        addd    #BG+$1800
        tfr     d,u
        bra     paint_enemy
paint_enemy_room1
        cmpa    #ROOM
        bne     paint_enemy_walk
        tst     cash_grab
        beq     paint_enemy_walk
        ldu     #pose_cash_first
        tst     cash_pose_phase
        beq     paint_enemy
        ldu     #pose_cash_second
        bra     paint_enemy
paint_enemy_walk
        lda     <ticks
        bita    #8
        beq     paint_enemy
        ldu     #pose_enemy_walk
paint_enemy
        ifne PRELOAD_ALL
        jsr room8_enemy_pose
        endc
        ldd     <ex
        jmp     draw_actor
paint_done
        rts
actor_walking
        lda     <keys
        anda    #15
        rts

walking_frame
        lda     <ticks
        lsra
        lsra
        anda    #3
        ldb     #176
        mul
        leau    d,u
        rts

restore
        jsr     rect_start
restore_row
        jsr     row_address
        lda     <bank
        adda    <room_bank
        sta     MMU3
        leay    $2000,x
        cmpx    #BG-8
        bhi     restore_split
        ldd     ,y
        std     ,x
        ldd     2,y
        std     2,x
        ldd     4,y
        std     4,x
        ldd     6,y
        std     6,x
        bra     restore_next
restore_split
        ldb     #8
restore_byte
        lda     ,y+
        sta     ,x+
        cmpx    #BG
        bne     restore_count
        jsr     next_video_bank
        lda     <bank
        adda    <room_bank
        sta     MMU3
        ldy     #BG
restore_count
        decb
        bne     restore_byte
restore_next
        inc     <row_y
        dec     <rows
        bne     restore_row
        rts

draw_actor
        jsr     rect_start
draw_row
        jsr     row_address
        lda     #8
        pshs    a
draw_byte
        ldb     ,u+
        beq     draw_skip
        lda     #$FF
        bitb    #$F0
        beq     draw_keep_high
        anda    #$0F
draw_keep_high
        bitb    #$0F
        beq     draw_merge
        anda    #$F0
draw_merge
        anda    ,x
        pshs    b
        ora     ,s+
        sta     ,x
draw_skip
        leax    1,x
        cmpx    #BG
        bne     draw_count
        jsr     next_video_bank
draw_count
        dec     ,s
        bne     draw_byte
        leas    1,s
        inc     <row_y
        dec     <rows
        bne     draw_row
        rts


rect_start
        stb     <row_y
        jsr     logical_to_row_x
        lda     #22
        sta     <rows
        rts

; Convert logical X into the packed byte column of the centered HGR area.
logical_to_row_x
        ldb     #140
        mul
        adda    #10
        sta     <row_x
        rts

row_address
        lda     <row_y
        ldb     #160
        mul
        addb    <row_x
        adca    #0
        pshs    a
        anda    #$1F
        ora     #$40
        tfr     d,x
        puls    a
        lsra
        lsra
        lsra
        lsra
        lsra
        sta     <bank
        bra     select_video_bank

next_video_bank
        ldx     #VID
        inc     <bank
        lda     <bank
select_video_bank
        adda    <back
        sta     MMU2
        rts

        ifne    PRELOAD_ALL
; Replay the original HGR ending as per-frame changes. Apply every patch
; once to each framebuffer before using a subsequent patch.
ending_step
        lda     <ending_base
        cmpa    #2
        bhs     ending_play
        lda     <back
        jsr     copy_background
        inc     <ending_base
        lda     <ending_base
        cmpa    #1
        beq     ending_publish
ending_play
        tst     <ending_repeat
        bne     ending_read
        tst     <ending_hold
        beq     ending_read
        dec     <ending_hold
        rts
ending_read
        lda     <ending_bank
        sta     MMU3
        ldu     <ending_ptr
        lda     ,u+
        beq     ending_finished
        cmpa    #$FF
        bne     ending_patch
        inc     <ending_bank
        lda     <ending_bank
        cmpa    #8
        bne     ending_next_bank
        lda     #ROOM+19
        sta     <ending_bank
        ldd     #BG+$100
        bra     ending_bank_pointer
ending_next_bank
        ldd     #BG
ending_bank_pointer
        std     <ending_ptr
        bra     ending_read
ending_patch
        suba    #2
        sta     <ending_hold
        jsr     video_patch_run
ending_patched
        lda     <ending_repeat
        eora    #1
        sta     <ending_repeat
        bne     ending_publish
        stu     <ending_ptr
ending_publish
        inc     <ready
        rts
ending_finished
        lda     #ROOM
        jsr     change_room
        jsr     paint
        bra     ending_publish
        endc

video_patch_run
        lda     ,u+
        bmi     video_patch_done
        ldb     ,u+
        pshs    a
        anda    #$1F
        ora     #$40
        tfr     d,x
        puls    a
        lsra
        lsra
        lsra
        lsra
        lsra
        adda    <back
        sta     MMU2
        ldb     ,u+
video_patch_byte
        lda     ,u+
        sta     ,x+
        decb
        bne     video_patch_byte
        bra     video_patch_run
video_patch_done
        rts

        include "player_lives.inc"
        include "room3.inc"
        include "room2.inc"
        include "room2_motion.inc"
        include "launcher.inc"
        include "room2_data.inc"
        include "crushers.inc"
        include "lives.inc"
pose_p1_walk equ cash_stamps+96
pose_p1_idle equ pose_p1_walk+3*176
pose_p2_walk equ pose_p1_idle+176
pose_p2_idle equ pose_p2_walk+3*176
pose_enemy_idle equ pose_p2_idle+176
pose_enemy_walk equ pose_enemy_idle+176
pose_death_early equ pose_enemy_walk+176
pose_death_late equ pose_death_early+176
pose_cash_first equ pose_death_late+176
pose_cash_second equ pose_cash_first+176
        include "room_mechanics.inc"
        include "room1.inc"
        include "cash.inc"
        include "puzzles.inc"
        include "audio.inc"
        ifeq AUDIO_DRIVER_TYPE
        include "music.inc"
        else
        include "ssc_periods.inc"
        endc
        org $1DE0
        include "palette.inc"
        ifeq PRELOAD_ALL
        org STAGE
        include "scene1.inc"
        ifne AUDIO_DRIVER_TYPE
        org $6000
        include "ssc_data.inc"
        endc
        endc
        include "room4.inc"
        include "room5.inc"
        include "room6.inc"
        include "room8.inc"
        include "apple_physics.inc"
        end entry




