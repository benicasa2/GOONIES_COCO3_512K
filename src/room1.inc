; Overlay 1: chair $61B6, printing machine $62A7 and cash $635C.
chair_x
        fcb 51
chair_old
        fcb 51,51
reset_room1
        lda     #51
        sta     chair_x
        jsr     reset_cash
        clr     cooler_state
        clr     cooler_flame
        lda     #2
        sta     cooler_tick
        lda     <room_bank
        cmpa    #ROOM
        lbne    chair_done
        lda     chair_x
        lbra    chair_floor

room1_objects
        lda     <room_bank
        cmpa    #ROOM
        lbne    chair_done
chair_contact
        lda     1,x
        cmpa    #76
        bhi     chair_done
        adda    #BODY_Y
        cmpa    #76
        blo     chair_done
        lda     <keys
        bita    #8
        bne     chair_right
        bita    #4
        beq     chair_done
        lda     ,x
        cmpa    chair_x
        blo     chair_done
        suba    chair_x
        cmpa    #12
        bhi     chair_done
        lda     chair_x
        cmpa    #43
        bls     chair_done
        suba    #2
        bra     chair_commit
chair_right
        lda     chair_x
        adda    #4
        cmpa    ,x
        blo     chair_done
        lda     ,x
        adda    #BODY_X
        cmpa    chair_x
        blo     chair_done
        lda     chair_x
        cmpa    #202
        bhs     chair_done
        adda    #2
chair_commit
        sta     chair_x
chair_floor
        adda    #5
        sta     TERRAIN+1
        sta     TERRAIN+3
chair_done
        rts

printer_zone
        fcb 201,32,219,32

chair_page
        ldy     #chair_old
        lda     <back
        cmpa    #FB0
        beq     chair_page_done
        leay    1,y
chair_page_done
        rts

restore_chair
        lda     <room_bank
        cmpa    #ROOM
        lbne    chair_done
        bsr     chair_page
        lda     ,y
        ldb     #66
        jmp     restore

draw_chair
        lda     <room_bank
        cmpa    #ROOM
        lbne    chair_done
        bsr     chair_page
        lda     chair_x
        sta     ,y
        jsr     map_terrain
        ldu     #TERRAIN+24*5+1
        lda     chair_x
        ldb     #66
        jmp     draw_actor


; Apple $63D0 advances each fall pose on its third-frame pulse. The
; fireplace stays lit through pose 5 and is disabled on the next update.
cooler_state
        fcb 0
cooler_tick
        fcb 2
cooler_flame
        fcb 0
cooler_table equ pose_cash_second+176

update_cooler
        lda     <room_bank
        cmpa    #ROOM
        bne     cooler_done
        tst     <fire_out
        bne     cooler_done
        inc     cooler_flame
        dec     cooler_tick
        bpl     cooler_advance
        lda     #2
        sta     cooler_tick
cooler_advance
        lda     cooler_state
        beq     cooler_done
        bmi     cooler_impact
        cmpa    #5
        beq     cooler_extinguish
        tst     cooler_tick
        bne     cooler_done
        inc     cooler_state
cooler_done
        rts
cooler_impact
        anda    #$7F
        sta     cooler_state
        rts
cooler_extinguish
        inc     <fire_out
        rts

draw_cooler
        lda     <room_bank
        cmpa    #ROOM
        bne     cooler_done
        jsr     map_terrain
        ldu     cooler_table
        jsr     video_patch_run
        ldx     #cooler_table+2
        lda     #48
        tst     <fire_out
        bne     cooler_stamp
        lda     cooler_state
        lsla
        lsla
        ldb     cooler_flame
        andb    #3
        pshs    b
        adda    ,s+
        lsla
cooler_stamp
        ldu     a,x
        jmp     video_patch_run
