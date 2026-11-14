; The Apple death slot starts at 1, changes pose at 8 and costs a life
; at 16. Zero lives are playable until the next death.
mark_death
        tst     <death
        bne     death_marked
        tfr     x,d
        stb     <dead_player
        inc     <death
death_marked
        rts

death_step
        inc     <death
        lda     <death
        bmi     game_over_frame
        cmpa    #17
        bhs     death_spend
        jsr     update_cash
        jsr     update_cooler
        lbra    main_paint
death_spend
        dec     <lives
        bmi     game_over_begin
        lda     <fire_out
        tst     cooler_state
        beq     death_save_fire
        lda     #1
death_save_fire
        ldb     <room3_switch
        pshs    a,b
        lda     <room2_open
        pshs    a
        ifne    PRELOAD_ALL
        lda     launcher_lane
        pshs    a
        ldd     room4_steps
        pshs    a,b
        lda     room5_height
        pshs    a
        endc
        lda     cash_index
        pshs    a
        jsr     reset_room
        puls    a
        sta     cash_index
        ifne    PRELOAD_ALL
        puls    a
        sta     room5_height
        puls    a,b
        std     room4_steps
        puls    a
        sta     launcher_lane
        endc
        puls    a
        sta     <room2_open
        puls    a,b
        sta     <fire_out
        stb     <room3_switch
        lda     #2
        sta     <redraw
        lbra    main_paint
game_over_begin
        clr     <lives
        lda     #$80
        sta     <death
game_over_frame
        cmpa    #$A0
        bhs     game_over_restart
        jsr     paint
        ifne    PRELOAD_ALL
        lda     #ROOM+14
        sta     MMU3
        include "game_over.inc"
        endc
        ldu     #life_game_over
        jsr     video_patch_run
        inc     <ready
        lbra    main_loop

game_over_restart
        ifne PRELOAD_ALL
        jsr     clear_room4_score
        endc
        lda     #5
        sta     <lives
        lda     #ROOM
        sta     <room_bank
        jsr     reset_room
        ifne    PRELOAD_ALL
        jsr     restore_title
        lda     #2
        sta     <title_pal_pending
        inc     <ready
game_over_flip
        tst     <ready
        bne     game_over_flip
        lbra    title_wait
        else
        lda     #2
        sta     <redraw
        lbra    main_paint
        endc

        ifne    PRELOAD_ALL
; The LZ streams are backed up at offset $1000 of the last four
; geometry banks. Expand into the hidden page before publishing it.
restore_title
        ldd     #((ROOM+24)*256)
        ldb     <back
        pshs    a,b
restore_title_bank
        ldd     ,s
        sta     MMU2
        stb     MMU3
        ldx     #VID+$1000
        jsr     decode_bank
        inc     1,s
        lda     ,s
        adda    #5
        sta     ,s
        cmpa    #ROOM+44
        blo     restore_title_bank
        leas    2,s
        rts
        endc

; A is the player's direct-page address. U is the selected walking pose.
death_pose
        cmpa    <dead_player
        bne     death_pose_done
        lda     <death
        beq     death_pose_done
        ldu     #pose_death_early
        cmpa    #9
        blo     death_pose_done
        ldu     #pose_death_late
death_pose_done
        rts

draw_lives
        ldu     #life_label
        jsr     video_patch_run
        lda     <back
        sta     MMU2
        lda     #ROOM+4
        sta     MMU3
        lda     <lives
        ldb     #32
        mul
        addd    #BG+$1EA0
        tfr     d,u
        ldx     #VID+136
draw_life_row
        ldd     ,u++
        std     ,x
        ldd     ,u++
        std     2,x
        leax    160,x
        cmpx    #VID+136+8*160
        blo     draw_life_row
        rts
