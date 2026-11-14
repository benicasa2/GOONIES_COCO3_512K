        ifne PRELOAD_ALL
        include "room5_data.inc"
        org     $0D00
ROOM5_ART equ $3A
R5_SIZE equ 13

room5_height fcb 0
room5_mask fcb 2
room5_clock fcb 0
room5_phase fcb 0
room5_delay fcb 128
room5_path fcb 0
room5_dropped fcb 0
room5_vars_end equ *
; BASIC work RAM is free once gameplay starts.
room5_eggs equ $1280
room5_fly equ room5_eggs+8*R5_SIZE
room5_end equ room5_fly+R5_SIZE
room5_old equ room5_end

reset_room5
        ldx     #room5_height
room5_clear_vars
        clr     ,x+
        cmpx    #room5_vars_end
        blo     room5_clear_vars
        ldx     #room5_eggs
room5_clear
        clr     ,x+
        cmpx    #room5_old+36
        blo     room5_clear
        lda     #128
        sta     room5_delay
        lda     #2
        sta     room5_mask
        rts

update_room5
        lda     <room_bank
        cmpa    #ROOM5
        lbne    room5_done
        lda     #ROOM5_ART
        sta     MMU3
        dec     room5_clock
        bpl     room5_update_eggs
        lda     #2
        sta     room5_clock
room5_update_eggs
        ldx     #room5_eggs
room5_egg_loop
        jsr     room5_update_egg
        leax    R5_SIZE,x
        cmpx    #room5_fly
        blo     room5_egg_loop
        ldd     ,x
        beq     room5_spawn_fly
        lbsr    room5_advance
        ldd     ,x
        beq     room5_spawn_fly
        lda     7,x
        bita    #$40
        beq     room5_fly_contact
        tst     room5_dropped
        bne     room5_fly_contact
        inc     room5_dropped
        jsr     room5_spawn_egg
room5_fly_contact
        lda     7,x
        lbpl    room5_traps
        ldb     #3
        lda     #13
        jsr     room5_contact
        lbra    room5_traps
room5_spawn_fly
        dec     room5_delay
        lbne    room5_traps
        lda     #64
        sta     room5_delay
        clr     room5_dropped
        ; Shared cursor for the native Apple random table.
        inc     particle_rng
        lda     #ROOM4_GRAPH
        sta     MMU3
        ldu     #particle_random
        clra
        ldb     particle_rng
        lda     d,u
        anda    #3
        cmpa    #3
        bne     room5_choose_path
        ldb     room5_height
        cmpb    #4
        blo     room5_choose_path
        deca
room5_choose_path
        sta     room5_path
        lda     #ROOM5_ART
        sta     MMU3
        ldb     room5_path
        lslb
        lslb
        ldu     #BG
        ldd     b,u
        std     ,x
        clr     2,x
        lbsr    room5_advance
        lbra    room5_traps

; A flying frame is duration, native X, Y and pose/flags.
room5_advance
        ldu     ,x
        beq     room5_advance_done
        tst     2,x
        beq     room5_next_record
        dec     2,x
        bne     room5_advance_done
room5_next_record
        lda     ,u+
        lbeq    room5_clear_actor
        sta     2,x
        lda     ,u+
        sta     3,x
        lda     ,u+
        sta     4,x
        lda     ,u+
        sta     7,x
        stu     ,x
room5_advance_done
        rts
room5_clear_actor
        clr     ,x
        clr     1,x
        clr     7,x
        clr     8,x
        rts

room5_spawn_egg
        pshs    x
        ldx     #room5_eggs
room5_find_slot
        tst     8,x
        beq     room5_egg_slot
        leax    R5_SIZE,x
        cmpx    #room5_fly
        blo     room5_find_slot
        puls    x,pc
room5_egg_slot
        ldb     room5_path
        lslb
        lslb
        ldu     #BG+2
        ldd     b,u
        std     ,x
        lda     #8
        sta     8,x
        lda     #112
        sta     2,x
        lda     #31
        sta     7,x
        jsr     room5_read_egg
        jsr     room5_update_egg
        puls    x,pc

room5_traps
        tst     room5_clock
        bne     room5_trap_switches
        inc     room5_phase
        lda     room5_phase
        cmpa    #3
        blo     room5_trap_switches
        clr     room5_phase
room5_trap_switches
        clr     room5_mask
        ldu     #room5_switches+4
        jsr     either_box
        rol     room5_mask
        leau    -4,u
        jsr     either_box
        rol     room5_mask
        lda     room5_mask
        eora    #2
        sta     room5_mask
        ldu     #room5_tips
        lsra
        bcc     room5_right_tip
        pshs    a
        jsr     either_box
        puls    a
        bcs     room5_player_hit
room5_right_tip
        lsra
        bcc     room5_floor
        leau    4,u
        jsr     either_box
        bcc     room5_floor
room5_player_hit
        jsr     mark_death
room5_floor
        jsr     map_terrain
        ldx     #room5_levels
        ldb     room5_height
        lda     b,x
        sta     TERRAIN+30*5+2
        sta     TERRAIN+31*5+2
        sta     TERRAIN+31*5+4
room5_done
        rts

room5_switches
        fcb 65,38,71,38,223,38,228,38
room5_tips
        fcb 51,183,51,183,204,183,204,183
room5_levels
        fcb 176,168,160,152,144

room5_update_egg
        lda     8,x
        cmpa    #8
        beq     room5_live_egg
        cmpa    #10
        lbeq    room5_creature
        cmpa    #11
        bne     room5_no_egg
        dec     2,x
        lbeq    room5_clear_actor
room5_no_egg
        rts
room5_live_egg
        lda     2,x
        lbeq    room5_hatch
        cmpa    #8
        lda     #31
        bhs     room5_egg_pose
        lda     #38
room5_egg_pose
        sta     7,x
        tst     room5_clock
        bne     room5_egg_motion
        dec     2,x
room5_egg_motion
        bsr     room5_egg_command
        pshs    b
        bsr     room5_egg_record
        puls    b
        leau    b,u
        ldd     2,u
        bita    #$40
        bne     room5_egg_sensor
        anda    #3
        std     ,x
        bsr     room5_read_egg
        lda     4,x
        cmpa    #176
        lblo    room5_egg_done
        cmpa    #183
        lbhi    room5_egg_done
        bra     room5_egg_traps
room5_egg_sensor
        lda     #ROOM5_ART
        sta     MMU3
        lda     room5_height
        cmpa    #4
        bhs     room5_clear_egg
        inc     room5_height
        jsr     score_room5_egg
room5_clear_egg
        lbra    room5_clear_actor

; The native graph stores current X/Y and the next state for each input.
room5_egg_record
        lda     ,x
        ldb     #5
        mul
        addb    #ROOM+23
        stb     MMU3
        clra
        ldb     1,x
        lslb
        rola
        lslb
        rola
        lslb
        rola
        addd    #$7800
        tfr     d,u
        rts
room5_read_egg
        bsr     room5_egg_record
        ldd     ,u
        std     3,x
        tst     2,u
        bpl     room5_egg_visible
        clr     7,x
room5_egg_visible
        lda     #ROOM5_ART
        sta     MMU3
        rts

room5_egg_command
        lda     <keys
        anda    #12
        beq     room5_egg_neutral
        pshs    x,a
        ldb     3,x
        cmpa    #4
        bne     room5_egg_from_left
        addb    #5
        bra     room5_egg_touch_x
room5_egg_from_left
        decb
room5_egg_touch_x
        clra
        ldu     #room5_xmap
        lda     d,u
        sta     <hazard_box
        sta     <hazard_box+2
        lda     4,x
        sta     <hazard_box+1
        adda    #6
        sta     <hazard_box+3
        ldu     #hazard_box
        jsr     active_box
        puls    a,x
        bcc     room5_egg_neutral
        lsra
        tfr     a,b
        eorb    #6
        rts
room5_egg_neutral
        clrb
        rts

room5_egg_traps
        lda     room5_mask
        lsra
        bcc     room5_egg_right
        ldb     3,x
        cmpb    #30
        blo     room5_egg_right
        cmpb    #40
        bls     room5_egg_break
room5_egg_right
        lsra
        bcc     room5_egg_done
        ldb     3,x
        cmpb    #114
        lblo    room5_egg_done
        cmpb    #124
        bls     room5_egg_break
room5_egg_done
        rts
room5_egg_break
        lda     #11
        sta     8,x
        lda     #3
        sta     2,x
        lda     4,x
        adda    #4
        sta     4,x
        lda     #38
        sta     7,x
        rts

; The creature continues from the egg's actual position and follows
; the native waypoint list for that quadrant.
room5_hatch
        clrb
        lda     4,x
        cmpa    #104
        bhs     room5_hatch_column
        ldb     #4
room5_hatch_column
        lda     3,x
        cmpa    #88
        blo     room5_hatch_path
        addb    #2
room5_hatch_path
        ldu     #room5_hatch_table
        ldu     b,u
        ldd     ,u++
        std     5,x
        stu     9,x
        lda     #10
        sta     8,x
        clr     7,x
        clr     11,x
        clr     12,x
        rts
room5_creature
        tst     12,x
        beq     room5_creature_move
        dec     12,x
        rts
room5_creature_move
        lda     3,x
        anda    #$FE
        sta     3,x
        clrb
        leax    3,x
        jsr     particle_axis
        jsr     particle_axis
        leax    -5,x
        tstb
        bne     room5_creature_pose
        ldu     9,x
        ldd     ,u++
        cmpb    #$FF
        lbeq    room5_clear_actor
        tstb
        bne     room5_creature_target
        ldd     ,u++
        std     3,x
        std     5,x
        stu     9,x
        lda     #4
        sta     12,x
        clr     7,x
        bra     room5_creature_phase
room5_creature_target
        std     5,x
        stu     9,x
room5_creature_pose
        lda     11,x
        inca
        cmpa    #3
        blo     room5_creature_frame
        clra
room5_creature_frame
        sta     11,x
        adda    #40
        sta     7,x
        clrb
        lda     #4
        jmp     room5_contact
room5_creature_phase
        inc     11,x
        lda     11,x
        cmpa    #3
        lblo    room5_egg_done
        clr     11,x
        rts

; Expand the native attack box after projecting horizontal coordinates.
room5_contact
        pshs    x,a
        addb    3,x
        clra
        ldu     #room5_xmap
        lda     d,u
        sta     <hazard_box
        ldb     3,x
        addb    ,s
        clra
        lda     d,u
        sta     <hazard_box+2
        lda     4,x
        sta     <hazard_box+1
        ldb     #8
        cmpx    #room5_fly
        bne     room5_contact_bottom
        ldb     #11
room5_contact_bottom
        addb    <hazard_box+1
        stb     <hazard_box+3
        ldu     #hazard_box
        jsr     either_box
        bcc     room5_contact_done
        jsr     mark_death
room5_contact_done
        puls    a,x,pc

score_room5_egg
        pshs    x
        ldx     #room4_score+4
        lda     #5
        jsr     room4_score_add
        puls    x,pc

room5_page
        ldy     #room5_old
        lda     <back
        cmpa    #FB0
        beq     room5_page_done
        leay    18,y
room5_page_done
        rts

restore_room5
        lda     <room_bank
        cmpa    #ROOM5
        lbne    room5_done
        bsr     room5_page
room5_restore_next
        pshs    y
        ldd     ,y
        tstb
        beq     room5_restore_skip
        lbsr    room5_rect
        bsr     room5_restore_rows
        pshs    d
        jsr     restore_row
        puls    d
        adda    #8
        lbsr    room5_strip
        bsr     room5_restore_rows
        jsr     restore_row
room5_restore_skip
        puls    y
        leay    2,y
        cmpy    #room5_old+18
        beq     room5_restore_done
        cmpy    #room5_old+36
        blo     room5_restore_next
room5_restore_done
        rts

room5_restore_rows
        pshs    a
        lda     #192
        suba    <row_y
        cmpa    #20
        bls     room5_restore_clip
        lda     #20
room5_restore_clip
        sta     <rows
        puls    a,pc

draw_room5
        lda     <room_bank
        cmpa    #ROOM5
        lbne    room5_done
        lda     #ROOM5_ART
        sta     MMU3
        ldb     #17
        lbsr    room5_patch
        lda     room5_mask
        anda    #1
        ldb     #3
        mul
        addb    room5_phase
        lbsr    room5_patch
        lda     room5_mask
        lsra
        ldb     #3
        mul
        addb    room5_phase
        addb    #6
        lbsr    room5_patch
        ldb     room5_height
        addb    #12
        lbsr    room5_patch
        lbsr    room5_page
        ldx     #room5_eggs
room5_draw_actor
        clr     1,y
        lda     7,x
        anda    #$3F
        beq     room5_draw_next
        suba    #31
        cmpa    #8
        blo     room5_pose_index
        deca
room5_pose_index
        ldb     #224
        mul
        addd    #room5_poses
        pshs    x,y,d
        ldu     #room5_xmap
        clra
        ldb     3,x
        lda     d,u
        ldb     4,x
        std     ,y
        lbsr    room5_rect
        ldu     ,s
        pshs    d
        jsr     draw_row
        puls    d
        adda    #8
        lbsr    room5_strip
        ldu     ,s
        leau    112,u
        jsr     draw_row
        puls    d,x,y
room5_draw_next
        leax    R5_SIZE,x
        leay    2,y
        cmpx    #room5_end
        blo     room5_draw_actor
        tst     room5_dropped
        bne     room5_shadow_done
        ldd     -2,y
        tstb
        beq     room5_shadow_done
        addb    #13
        pshs    b
        jsr     logical_to_row_x
        adda    #6
        sta     <row_x
        puls    b
        stb     <row_y
        lda     #7
        sta     <rows
        ldu     #room5_shadow
        jmp     draw_row
room5_shadow_done
        rts
room5_patch
        lslb
        ldx     #room5_patch_table
        ldu     b,x
        jmp     video_patch_run
room5_rect
        pshs    b
        jsr     logical_to_row_x
        puls    b
room5_strip
        sta     <row_x
        stb     <row_y
        lda     #192
        suba    <row_y
        cmpa    #14
        bls     room5_rows
        lda     #14
room5_rows
        sta     <rows
        lda     <row_x
        rts
        endc


