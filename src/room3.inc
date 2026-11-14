ROOM3   equ     ROOM+10
room3_item_table equ TERRAIN+30*5+1+4*176
room3_item_tick
        fcb 5
room3_platform_x
        fcb 111
room3_platform_old
        fcb 188,188
room3_platform_table equ BG+$1000
room3_platform_pose equ room3_platform_table+74
room3_platform_floor equ TERRAIN+21*5
room3_lift_wall equ TERRAIN+19*5
room3_lift_floor equ TERRAIN+20*5
room3_lift_height
        fcb 74
room3_bat_wait
        fcb 96
room3_bat_frame
        fcb 0
room3_bat_path
        fcb 0
room3_platform_tick
        fcb 0
room3_lift_index equ BG+$1200
room3_lift_rows equ room3_lift_index+36*55

reset_room3
        lda     #21
        sta     <crusher_y
        sta     <crusher_y+1
        sta     <crusher_y+2
        clr     <crusher_dir
        clr     <crusher_dir+1
        clr     <crusher_dir+2
        clr     <crusher_timer
        lda     #1
        sta     <crusher_timer+1
        lda     #2
        sta     <crusher_timer+2
        clr     <room3_switch
        lda     #5
        sta     room3_item_tick
        lda     #92
        sta     <crusher_four
        clr     <crusher_four_dir
        lda     <room_bank
        cmpa    #ROOM3
        bne     crusher_reset_done
        lda     #111
        sta     room3_platform_x
        jsr     room3_platform_floor_write
        lda     #96
        sta     room3_bat_wait
        lda     #74
        sta     room3_lift_height
        sta     room3_lift_floor+2
        sta     room3_lift_floor+4
        lda     #$7F
        sta     room3_lift_wall
        clr     room3_platform_tick
        lda     #120
        sta     room3_platform_floor+2
        sta     room3_platform_floor+4
        ldu     #TERRAIN+22*5
        lda     #$7F
        ldb     #4
crusher_reset_wall
        sta     ,u
        sta     5,u
        leau    10,u
        decb
        bne     crusher_reset_wall
crusher_reset_done
        rts

room3_hazards
        lda     <room_bank
        cmpa    #ROOM3
        lbne    crusher_done
        tst     <death
        lbne    crusher_done
        jsr     room3_lift_move
        jsr     room3_platform_move
        jsr     room3_bat_move
        ldy     #crusher_data+12
        ldb     #2
crusher_update
        ldx     #crusher_y
        leax    b,x
        tst     3,x
        bne     crusher_count
        lda     6,x
        suba    #5
        sta     6,x
crusher_count
        dec     6,x
        bpl     crusher_contact
        lda     5,y
        sta     6,x
        tst     3,x
        bne     crusher_rise
        lda     ,x
        adda    #3
        sta     ,x
        cmpa    #$27
        blo     crusher_contact
        inc     3,x
        bra     crusher_contact
crusher_rise
        dec     ,x
        lda     ,x
        cmpa    #$19
        bhs     crusher_contact
        clr     3,x
crusher_contact
        pshs    b
        lda     ,x
        jsr     crusher_walls
        tst     3,x
        bne     crusher_return_contact
        lda     ,x
        ldb     #21
        jsr     crusher_body
crusher_return_contact
        ldb     ,s
        ldx     #crusher_y
        leax    b,x
        lda     #$80
        suba    ,x
        sta     <hazard_box+1
        adda    #4
        sta     <hazard_box+3
        lda     3,y
        ldb     4,y
        sta     <hazard_box
        stb     <hazard_box+2
        ldu     #hazard_box
        jsr     active_box
        bcc     crusher_next
        jsr     mark_death
crusher_next
        puls    b
        leay    -6,y
        decb
        bpl     crusher_update

        lda     <crusher_four
        tst     <crusher_four_dir
        beq     crusher_four_down
        cmpa    #$48
        bls     crusher_four_check
        deca
        bra     crusher_four_check
crusher_four_down
        cmpa    #$58
        bls     crusher_four_increment
        lda     #$58
        bra     crusher_four_check
crusher_four_increment
        beq     crusher_four_check
        inca
crusher_four_check
        sta     <crusher_four
        ldb     #3
        jsr     crusher_walls
        lda     <crusher_four
        tst     <crusher_four_dir
        bne     crusher_four_trigger
        ldy     #crusher_data+18
        ldb     #21
        jsr     crusher_body
crusher_four_trigger
        clr     <crusher_four_dir
        ldu     #crusher_trigger
        jsr     either_box
        bcc     crusher_steam
        inc     <crusher_four_dir
crusher_steam
        ldu     #steam_zone
        jsr     either_box
        bcc     crusher_switch
        jsr     mark_death
crusher_switch
        tst     <room3_switch
        bne     crusher_done
        dec     room3_item_tick
        bpl     room3_item_contact
        lda     #10
        sta     room3_item_tick
room3_item_contact
        ldu     #crusher_switch_zone
        jsr     active_box
        bcc     crusher_done
        lda     #1
        sta     <room3_switch
crusher_done
        rts

; The original sets two directional wall rows to the moving tip Y.
; B = crusher index; A = Y; X/Y and B survive.
crusher_walls
        pshs    a,b,x
        ldx     #TERRAIN+22*5
        lda     #10
        mul
        leax    d,x
        lda     ,s
        adda    #21
        sta     4,x
        sta     9,x
        lda     #1
        sta     ,x
        clr     5,x
        puls    a,b,x,pc

crusher_body
        sta     <hazard_box+1
        addb    <hazard_box+1
        stb     <hazard_box+3
        lda     1,y
        ldb     2,y
        sta     <hazard_box
        stb     <hazard_box+2
        ldu     #hazard_box
        jsr     either_box
        bcc     crusher_safe
        jsr     mark_death
crusher_safe
        rts

active_box
        ldx     #px
        tst     <active
        beq     active_box_check
        ldx     #p2x
active_box_check
        jmp     box_overlap
either_box
        ldx     #px
        jsr     box_overlap
        bcs     either_box_hit
        ldx     #p2x
        jmp     box_overlap
either_box_hit
        rts

; Original zones from $62E1, $641B and $6509, converted to logical X.
crusher_trigger
        fcb 89,$B4,91,$BF
steam_zone
        fcb 58,$7D,199,$7D
crusher_switch_zone
        fcb 49,$4F,60,$4F

room3_exit
        lda     <room_bank
        cmpa    #ROOM3
        bne     room3_exit_allow
        tst     <room3_switch
        beq     room3_exit_block
room3_exit_allow
        orcc    #1
        rts
room3_exit_block
        andcc   #$FE
        rts

; Each page remembers its last moving stamps so restoring one page
; cannot erase the corresponding stamp on the displayed page.
crusher_page
        ldx     #crusher_old
        lda     <back
        cmpa    #FB0
        beq     crusher_page_done
        leax    4,x
crusher_page_done
        rts
crusher_old
        fcb 0,0,0,0,0,0,0,0

restore_crushers
        lda     <room_bank
        cmpa    #ROOM3
        bne     crusher_restore_done
        jsr     room3_platform_page
        lda     ,x
        ldb     #120
        jsr     restore
        jsr     room3_return_restore
        jsr     crusher_page
        ldy     #crusher_data
        ldb     #4
crusher_restore_loop
        pshs    b,x,y
        lda     ,y
        ldb     ,x+
        stx     1,s
        jsr     restore
        puls    b,x,y
        leay    6,y
        decb
        bne     crusher_restore_loop
crusher_restore_done
        rts

draw_crushers
        lda     <room_bank
        cmpa    #ROOM3
        bne     crusher_draw_done
        jsr     room3_draw_rods
        jsr     map_terrain
        jsr     crusher_page
        ldy     #crusher_data
        ldu     #TERRAIN+30*5+1
        clrb
crusher_draw_loop
        pshs    b,x,y,u
        pshs    y
        ldy     #crusher_y
        lda     b,y
        puls    y
        cmpb    #3
        beq     crusher_draw_four
        adda    #3
        bra     crusher_draw_row
crusher_draw_four
        lda     <crusher_four
crusher_draw_row
        sta     ,x
        lda     ,y
        ldb     ,x
        jsr     draw_actor
        puls    b,x,y,u
        leax    1,x
        leay    6,y
        leau    176,u
        incb
        cmpb    #4
        blo     crusher_draw_loop
        jsr     room3_platform_page
        lda     room3_platform_floor+1
        sta     ,x
        ldb     room3_platform_floor+2
        ldu     #room3_platform_pose
        jsr     draw_actor
        jsr     room3_lift_draw
        jsr     room3_return_draw
        lda     <crusher_four
        anda    #3
        lsla
        ldx     #BG+$1E00
        ldu     a,x
        jsr     video_patch_run
        jsr     map_terrain
        ldx     #room3_item_table
        lda     #4
        tst     <room3_switch
        bne     room3_item_draw
        clra
        ldb     room3_item_tick
        cmpb    #5
        blo     room3_item_draw
        lda     #2
room3_item_draw
        ldu     a,x
        jmp     video_patch_run
crusher_draw_done
        rts



; Apple $644B moves the platform right by itself and reverses the
; active Goonie's horizontal input on contact with its upper edge.
room3_platform_move
        dec     room3_platform_tick
        bpl     room3_platform_pulse
        lda     #4
        sta     room3_platform_tick
room3_platform_pulse
        tst     room3_platform_tick
        bne     room3_platform_check
        lda     room3_platform_floor+2
        eora    #1
        sta     room3_platform_floor+2
        sta     room3_platform_floor+4
        cmpa    #120
        bne     room3_platform_check
        ldx     #px
        bsr     room3_platform_rise
        ldx     #p2x
        bsr     room3_platform_rise
room3_platform_check
        lda     room3_platform_floor+1
        sta     <hazard_box
        adda    #9
        sta     <hazard_box+2
        ldd     #$757B
        sta     <hazard_box+1
        stb     <hazard_box+3
        ldu     #hazard_box
        jsr     active_box
        bcs     room3_platform_input
        jsr     either_box
        bcs     room3_platform_floor_write
        bra     room3_platform_right
room3_platform_input
        lda     <keys
        bita    #4
        bne     room3_platform_bounce_right
        bita    #8
        beq     room3_platform_floor_write
        lda     room3_platform_x
        cmpa    #39
        bls     room3_platform_floor_write
        dec     room3_platform_x
        lda     ,x
        suba    #4
        bcc     room3_platform_player
        clra
        bra     room3_platform_player
room3_platform_bounce_right
        lda     ,x
        adda    #4
        cmpa    #SPRITE_MAX_X
        bls     room3_platform_bounce_commit
        lda     #SPRITE_MAX_X
room3_platform_bounce_commit
        sta     ,x
        bra     room3_platform_right
room3_platform_player
        sta     ,x
        bra     room3_platform_floor_write
room3_platform_right
        lda     room3_platform_x
        cmpa    #112
        bhs     room3_platform_floor_write
        inc     room3_platform_x
room3_platform_floor_write
        ldx     #room3_platform_table
        lda     room3_platform_x
        suba    #39
        lda     a,x
        sta     room3_platform_floor+1
        adda    #9
        sta     room3_platform_floor+3
        lda     #3
        sta     room3_platform_floor
        rts

; Carry standing players through the one-pixel upward pulse.
room3_platform_rise
        lda     1,x
        cmpa    #121-BODY_Y
        bne     room3_platform_rise_done
        lda     ,x
        cmpa    room3_platform_floor+3
        bhi     room3_platform_rise_done
        adda    #BODY_X
        cmpa    room3_platform_floor+1
        blo     room3_platform_rise_done
        dec     1,x
room3_platform_rise_done
        rts

room3_platform_page
        ldx     #room3_platform_old
        lda     <back
        cmpa    #FB0
        beq     room3_platform_page_done
        leax    1,x
room3_platform_page_done
        rts

; $61FC: the lift drops under either Goonie, and rises when unloaded.
room3_lift_move
        lda     #221
        sta     <hazard_box
        lda     #241
        sta     <hazard_box+2
        lda     room3_lift_height
        sta     <hazard_box+1
        inca
        sta     <hazard_box+3
        ldu     #hazard_box
        jsr     either_box
        lda     room3_lift_height
        bcc     room3_lift_up
        cmpa    #108
        bhs     room3_lift_open
        ldx     #px
        bsr     room3_lift_rider
        ldx     #p2x
        bsr     room3_lift_rider
        lda     room3_lift_height
        inca
        bra     room3_lift_open
room3_lift_up
        cmpa    #74
        blo     room3_lift_open
        deca
        cmpa    #92
        blo     room3_lift_open
        ldb     #1
        bra     room3_lift_commit
room3_lift_open
        ldb     #$7F
room3_lift_commit
        sta     room3_lift_height
        sta     room3_lift_floor+2
        sta     room3_lift_floor+4
        stb     room3_lift_wall
        rts

; Keep the riders' feet on the descending floor after gravity ran.
room3_lift_rider
        lda     1,x
        adda    #BODY_Y
        cmpa    room3_lift_height
        bne     room3_lift_rider_done
        jsr     box_overlap
        bcc     room3_lift_rider_done
        inc     1,x
room3_lift_rider_done
        rts

; Each height indexes 55 scanlines, assembled from the actual HGR stamps.
room3_lift_draw
        lda     room3_lift_height
        suba    #73
        ldb     #55
        mul
        addd    #room3_lift_index
        tfr     d,u
        lda     #128
        sta     <row_x
        lda     #56
        sta     <row_y
room3_lift_scan
        jsr     row_address
        ldb     ,u+
        lda     #15
        mul
        addd    #room3_lift_rows
        tfr     d,y
        ldb     #15
room3_lift_byte
        lda     ,y+
        sta     ,x+
        decb
        bne     room3_lift_byte
        inc     <row_y
        lda     <row_y
        cmpa    #111
        blo     room3_lift_scan
        rts

; Returning heads move opposite the upper rams ($611B and $61C0).
room3_return_restore
        jsr     crusher_page
        ldy     #room3_return_columns
room3_return_restore_next
        lda     ,y+
        sta     <row_x
        lda     #131
        suba    ,x+
        sta     <row_y
        lda     #14
        sta     <rows
        pshs    x,y
        jsr     restore_row
        puls    x,y
        cmpy    #room3_return_columns+3
        blo     room3_return_restore_next
        rts

room3_return_draw
        lda     #ROOM+19
        sta     MMU3
        ldu     #BG+$1400
        ldx     #crusher_y
        ldy     #room3_return_columns
room3_return_next
        lda     ,y+
        sta     <row_x
        lda     #128
        suba    ,x+
        sta     <row_y
        pshs    x,y,u
        cmpa    #103
        blo     room3_return_stamp
        leau    112,u
room3_return_stamp
        lda     #14
        sta     <rows
        jsr     draw_row
        puls    x,y,u
        leau    224,u
        cmpy    #room3_return_columns+3
        blo     room3_return_next
        rts

; Spawn cadence and two native paths from $159B / $14BC. The stone's
; height at frame 36 determines whether the bat enters the middle cave.
room3_bat_move
        tst     <enemy_on
        bne     room3_bat_advance
        dec     room3_bat_wait
        bpl     room3_bat_done
        inc     <enemy_on
        clr     room3_bat_frame
        clr     room3_bat_path
        bra     room3_bat_lookup
room3_bat_advance
        inc     room3_bat_frame
        lda     room3_bat_frame
        cmpa    #36
        bne     room3_bat_lookup
        lda     <crusher_four
        cmpa    #80
        blo     room3_bat_lookup
        inc     room3_bat_path
room3_bat_lookup
        lda     #ROOM+19
        sta     MMU3
        ldx     #BG+$1AC0
        tst     room3_bat_path
        beq     room3_bat_read
        leax    $140,x
room3_bat_read
        clra
        ldb     room3_bat_frame
        aslb
        rola
        ldd     d,x
        pshs    a,b
        jsr     map_terrain
        puls    a,b
        cmpa    #255
        beq     room3_bat_stop
        std     <ex
        std     <hazard_box
        adda    #7
        addb    #4
        std     <hazard_box+2
        ldu     #hazard_box
        jsr     either_box
        bcc     room3_bat_done
        jmp     mark_death
room3_bat_stop
        clr     <enemy_on
        lda     #64
        sta     room3_bat_wait
room3_bat_done
        rts

; Draw the seven HGR strips before the heads that overlap their ends.
room3_draw_rods
        lda     #ROOM+24
        sta     MMU3
        ldy     #BG+$200
        ldx     #room3_rod_heights
room3_rod_next
        leax    1,x
        pshs    x,y
        ldx     ,y
        ldd     ,x++
        sta     <row_x
        stb     <row_y
        ldd     ,x++
        sta     <hazard_box
        stb     <rows
        ldy     ,s
        leay    -1,y
        ldb     ,y
        ldy     #0
        clra
        lda     d,y
        suba    ,x+
        bpl     room3_rod_index
        clra
room3_rod_index
        ldb     <rows
        mul
        ldy     ,x++
        sty     <hazard_box+1
        leau    d,x
room3_rod_row
        jsr     row_address
        lda     <hazard_box
        ldb     ,u+
        mul
        addd    <hazard_box+1
        tfr     d,y
        ldb     <hazard_box
room3_rod_byte
        lda     ,y+
        sta     ,x+
        decb
        bne     room3_rod_byte
        inc     <row_y
        dec     <rows
        bne     room3_rod_row
        puls    x,y
        leay    2,y
        cmpx    #room3_rod_heights+7
        blo     room3_rod_next
        rts
room3_rod_heights
        fcb crusher_y,crusher_y+1,crusher_y+2,crusher_four
        fcb crusher_y,crusher_y+1,crusher_y+2

