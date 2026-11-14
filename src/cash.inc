; Apple overlay 1, $62A7/$6321/$635C. Zero Y denotes a free note slot.
cash_y
        fcb 0,0,0,0,0,0,0,0
cash_old
        fcb 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
cash_index
        fcb 0
cash_head
        fcb 26
cash_down
        fcb 0
cash_visible
        fcb 0
cash_low
        fcb 0
cash_limit
        fcb $9A
cash_phase
        fcb 0
cash_grab
        fcb 0
cash_pose_phase
        fcb 0

cash_stamps equ TERRAIN+24*5+1+176

reset_cash
        ldx     #cash_y
cash_clear_slot
        clr     ,x+
        cmpx    #cash_head
        blo     cash_clear_slot
        lda     #26
        sta     cash_head
        clr     cash_down
        clr     cash_visible
        clr     cash_low
        clr     cash_phase
        clr     cash_grab
        clr     cash_pose_phase
        lda     #$9A
        sta     cash_limit
        rts

update_cash
        lda     <room_bank
        cmpa    #ROOM
        bne     cash_done
        ldu     #printer_zone
        jsr     either_box
        bcc     cash_advance
        lda     cash_head
        tst     cash_down
        bne     cash_head_down
        cmpa    #$1C
        blo     cash_head_up
        inc     cash_down
        inc     cash_index
        lda     cash_index
        anda    #7
        sta     cash_index
        ldx     #cash_y
        tst     a,x
        bne     cash_advance
        ldb     #$1A
        stb     a,x
        bra     cash_advance
cash_head_down
        cmpa    #$12
        bhs     cash_lower
        clr     cash_down
cash_head_up
        inc     cash_head
        bra     cash_advance
cash_lower
        dec     cash_head

cash_advance
        clr     cash_low
        ldx     #cash_y+7
cash_next
        lda     ,x
        beq     cash_skip
        adda    #2
        cmpa    cash_limit
        blo     cash_track
        clr     ,x
        dec     cash_visible
        bra     cash_skip
cash_track
        sta     ,x
        cmpa    #$62
        bne     cash_track_low
        inc     cash_visible
cash_track_low
        cmpa    #$74
        blo     cash_skip
        inc     cash_low
cash_skip
        leax    -1,x
        cmpx    #cash_y
        bhs     cash_next
        lda     #$9A
        sta     cash_limit
        rts

cash_tick
        dec     cash_phase
        bpl     cash_done
        lda     #5
        sta     cash_phase
cash_done
        rts

cash_page
        ldx     #cash_old
        lda     <back
        cmpa    #FB0
        beq     cash_done
        leax    8,x
        rts

; B = note Y. These are the three HGR stamp origins in the GIME frame.
cash_rectangle
        stb     <row_y
        lda     #4
        sta     <rows
        ldu     #cash_stamps
        lda     #135
        cmpb    #$20
        blo     cash_column
        leau    32,u
        lda     #142
        bitb    #4
        beq     cash_column
        leau    32,u
        lda     #145
cash_column
        sta     <row_x
        rts

restore_cash
        lda     <room_bank
        cmpa    #ROOM
        bne     cash_done
        bsr     cash_page
        leay    8,x
cash_restore_note
        ldb     ,x+
        beq     cash_restore_next
        pshs    x,y
        bsr     cash_rectangle
        jsr     restore_row
        puls    x,y
cash_restore_next
        pshs    x
        cmpy    ,s++
        bne     cash_restore_note
        rts

draw_cash
        lda     <room_bank
        cmpa    #ROOM
        bne     cash_done
        jsr     map_terrain
        bsr     cash_page
        ldy     #cash_y
cash_draw_note
        ldb     ,y+
        stb     ,x+
        beq     cash_draw_next
        pshs    x,y
        bsr     cash_rectangle
        jsr     draw_row
        puls    x,y
cash_draw_next
        cmpy    #cash_y+8
        bne     cash_draw_note
        rts
