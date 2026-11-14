; The six decimal digits follow Apple $1046-$104B.
room4_score zmb 6
room4_high zmb 6

clear_room4_score
        ldx     #room4_score
score_clear
        clr     ,x+
        cmpx    #room4_high
        blo     score_clear
        rts

score_room4_step
        ldx     #room4_score+5
        lda     #5
        bsr     room4_add_digit
        ldx     #room4_score+4
        lda     #3
        bra     room4_score_add
score_room4_exit
        ldx     #room4_score+2
        lda     #1
room4_score_add
        bsr     room4_add_digit
        ldx     #room4_score
        ldu     #room4_high
room4_score_compare
        lda     ,x+
        cmpa    ,u+
        blo     room4_score_done
        bhi     room4_high_copy
        cmpx    #room4_high
        blo     room4_score_compare
room4_score_done
        rts
room4_high_copy
        ldx     #room4_score
        ldu     #room4_high
room4_high_next
        ldd     ,x++
        std     ,u++
        cmpx    #room4_high
        blo     room4_high_next
        rts
room4_add_digit
        adda    ,x
        cmpa    #10
        blo     room4_digit_done
        suba    #10
        sta     ,x
        leax    -1,x
        cmpx    #room4_score
        blo     room4_score_done
        lda     #1
        bra     room4_add_digit
room4_digit_done
        sta     ,x
        rts

draw_room4_score
        ldy     #room4_score
        ldx     #VID+41
        bsr     draw_score_field
        ldx     #VID+76
draw_score_field
        pshs    x
        clra
        pshs    a
        ldb     #6
        pshs    b
draw_score_digit
        lda     ,y+
        bne     draw_score_significant
        ldb     ,s
        cmpb    #2
        bls     draw_score_significant
        tst     1,s
        bne     draw_score_significant
        ldu     #score_blank
        bra     draw_score_rows
draw_score_significant
        inc     1,s
        ldb     #32
        mul
        addd    #BG+$1EA0
        tfr     d,u
draw_score_rows
        ldx     2,s
        ldb     #8
draw_score_row
        pshs    b
        ldd     ,u++
        std     ,x
        ldd     ,u++
        std     2,x
        leax    160,x
        puls    b
        decb
        bne     draw_score_row
        ldx     2,s
        leax    4,x
        stx     2,s
        dec     ,s
        bne     draw_score_digit
        leas    4,s
        rts

score_blank zmb 32

; Apple actor $14BC uses native even coordinates and follows waypoint lists.
particle_xmap equ $7600
particle_random equ $7700
particle_starts equ $7800
particle_spawn fcb 0
particle_rng fcb 0
; BASIC work RAM is free once gameplay starts.
particles equ $1380
particles_end equ particles+5*7
particles_old equ particles_end

reset_room4_particles
        clr     particle_spawn
        ldx     #particles
particle_reset
        clr     ,x+
        cmpx    #particles_old+20
        blo     particle_reset
        rts

update_room4_particles
        lda     #ROOM4_GRAPH
        sta     MMU3
        ldx     #particles
particle_update_next
        tst     1,x
        beq     particle_update_skip
        jsr     particle_step
particle_update_skip
        leax    7,x
        cmpx    #particles_end
        blo     particle_update_next
        lda     room4_flash
        cmpa    #1
        bhi     particle_update_done
        lda     particle_spawn
        beq     particle_update_done
        dec     particle_spawn
        nega
        adda    #5
        ldb     #7
        mul
        ldx     #particles
        ldu     #particle_starts
        leax    d,x
        leau    d,u
        ldb     #7
particle_spawn_copy
        lda     ,u+
        sta     ,x+
        decb
        bne     particle_spawn_copy
particle_update_done
        rts

particle_step
        lda     ,x
        anda    #$FE
        sta     ,x
        clrb
        bsr     particle_axis
        bsr     particle_axis
        leax    -2,x
        tstb
        bne     particle_contact
particle_waypoint
        lda     4,x
        ldb     #3
        mul
        ldu     #particle_paths
        leau    d,u
        ldy     ,u
        inc     5,x
        ldb     5,x
        aslb
        ldd     b,y
        std     2,x
        tstb
        beq     particle_choose
        cmpb    #$FF
        bne     particle_contact
        clr     1,x
        rts
particle_choose
        inc     particle_rng
        ldy     #particle_random
        clra
        ldb     particle_rng
        lda     d,y
        bmi     particle_waypoint
        lda     2,u
        sta     4,x
        lda     #$FF
        sta     5,x
        bra     particle_waypoint

; X points to a record. Update each axis in the same order as $14BC.
particle_axis
        pshs    b
        lda     ,x
        anda    #$FE
        ldb     2,x
        andb    #$FE
        pshs    b
        cmpa    ,s+
        beq     particle_axis_done
        blo     particle_axis_plus
        suba    #4
particle_axis_plus
        adda    #2
        sta     ,x
        puls    b
        incb
        bra     particle_axis_next
particle_axis_done
        puls    b
        tstb
        beq     particle_axis_next
        sta     ,x
particle_axis_next
        leax    1,x
        rts

particle_contact
        inc     6,x
        pshs    x
        ldu     #particle_xmap
        clra
        ldb     ,x
        lda     d,u
        sta     <hazard_box
        ldb     ,x
        addb    #4
        clra
        lda     d,u
        sta     <hazard_box+2
        lda     1,x
        sta     <hazard_box+1
        adda    #4
        sta     <hazard_box+3
        ldu     #hazard_box
        jsr     either_box
        bcc     particle_safe
        jsr     mark_death
particle_safe
        puls    x,pc

particle_page
        ldy     #particles_old
        lda     <back
        cmpa    #FB0
        beq     particle_page_done
        leay    10,y
particle_page_done
        rts

restore_room4_particles
        bsr     particle_page
        ldb     #5
particle_restore
        pshs    b,y
        ldd     ,y
        tstb
        beq     particle_restore_next
        jsr     room4_rect
        jsr     restore_row
particle_restore_next
        puls    b,y
        leay    2,y
        decb
        bne     particle_restore
        rts

draw_room4_particles
        bsr     particle_page
        ldx     #particles
particle_draw
        clr     1,y
        ldb     1,x
        beq     particle_draw_next
        lda     #ROOM4_GRAPH
        sta     MMU3
        pshs    b
        clra
        ldb     ,x
        ldu     #particle_xmap
        lda     d,u
        puls    b
        std     ,y
        pshs    x,y
        jsr     room4_rect
        ldx     ,s
        lda     6,x
        anda    #3
        ldb     #48
        mul
        addd    #particle_poses
        tfr     d,u
        jsr     draw_row
        puls    x,y
particle_draw_next
        leax    7,x
        leay    2,y
        cmpx    #particles_end
        blo     particle_draw
        rts
