        ifne PRELOAD_ALL
        include "room2_motion_data.inc"
; The staging window at $4000 leaves $6000 free for the motion bank.
; The timeline indexes records with four stamp slots and two hit boxes.
MOTION2 equ $3B

motion_next
        fdb BG
motion_current
        fdb 0
motion_old
        fdb 0,0

reset_motion2
        ldd     #BG
        std     motion_next
        clra
        clrb
        std     motion_current
        std     motion_old
        std     motion_old+2
        rts

update_motion2
        lda     #MOTION2
        sta     MMU3
        ldx     motion_next
        ldb     ,x+
        cmpx    #motion_end
        blo     motion_advance
        ldx     #motion_loop
motion_advance
        stx     motion_next
        lda     #24
        mul
        addd    #motion_end
        std     motion_current
        tfr     d,u
        leau    16,u
motion_contact
        lda     ,u
        cmpa    #$FF
        beq     motion_no_contact
        jsr     either_box
        bcs     motion_lethal
        leau    4,u
        lda     ,u
        cmpa    #$FF
        beq     motion_no_contact
        jsr     either_box
        bcc     motion_no_contact
motion_lethal
        jsr     mark_death
motion_no_contact
        jmp     map_terrain

motion_page
        ldx     #motion_old
        lda     <back
        cmpa    #FB0
        beq     motion_page_done
        leax    2,x
motion_page_done
        rts

restore_motion2
        bsr     motion_page
        ldy     ,x
        beq     motion_draw_done
        ldb     #4
motion_restore_next
        lda     #MOTION2
        sta     MMU3
        lda     ,y+
        cmpa    #$FF
        beq     motion_draw_done
        sta     <row_x
        lda     ,y+
        sta     <row_y
        ldu     ,y++
        lda     ,u
        sta     <rows
        pshs    b,y
        jsr     restore_row
        puls    b,y
        decb
        bne     motion_restore_next
        rts

draw_motion2
        bsr     motion_page
        ldy     motion_current
        sty     ,x
        beq     motion_draw_done
        lda     #MOTION2
        sta     MMU3
        ldb     #4
motion_draw_next
        lda     ,y+
        cmpa    #$FF
        beq     motion_draw_done
        sta     <row_x
        lda     ,y+
        sta     <row_y
        ldu     ,y++
        lda     ,u+
        sta     <rows
        pshs    b,y
        jsr     draw_row
        puls    b,y
        decb
        bne     motion_draw_next
motion_draw_done
        rts
        endc
