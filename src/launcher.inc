        ifne    PRELOAD_ALL
; Overlay 2: $60AB advances a 16-lane launcher after the gate opens or its countdown expires.
; $61D7 advances the bolt one four-unit cell per update.
launcher_y
        fcb 26
launcher_lane
        fcb 0
launcher_hold
        fcb 0
launcher_bolt
        fcb 0
launcher_delay
        fdb $0404
launcher_enabled
        fcb 0
; Initial travel and the first lane change differ from the repeating cycle.
launcher_route_base
        fcb 0
launcher_route
        fdb 0
launcher_old
        fcb 0,$FF,0,0,$FF,0

reset_launcher
        ldd     #$0404
        std     launcher_delay
        clr     launcher_enabled
        lda     #26
        sta     launcher_y
        clr     launcher_lane
        clr     launcher_hold
        clr     launcher_bolt
        clr     launcher_route_base
        clr     launcher_route
        clr     launcher_route+1
        rts

update_launcher
        jsr     map_terrain
        ldd     launcher_delay
        beq     launcher_enable
        dec     launcher_delay+1
        bne     launcher_check_gate
        dec     launcher_delay
launcher_check_gate
        tst     <room2_open
        lbeq    launcher_done
launcher_enable
        lda     #1
        sta     launcher_enabled
        ldb     launcher_lane
        tst     launcher_hold
        beq     launcher_move
        inc     launcher_hold
        lda     launcher_hold
        cmpa    #$60
        blo     launcher_fire
        clr     launcher_hold
        incb
        andb    #15
        stb     launcher_lane
        lda     launcher_route_base
        cmpa    #64
        bhs     launcher_select_route
        adda    #32
        sta     launcher_route_base
        bra     launcher_select_route
launcher_move
        ldx     launcher_route
        bne     launcher_read_route
launcher_select_route
        lda     #MOTION2
        sta     MMU3
        aslb
        addb    launcher_route_base
        ldx     #launcher_travel_table
        ldx     b,x
        bra     launcher_step_route
launcher_read_route
        lda     #MOTION2
        sta     MMU3
launcher_step_route
        lda     ,x+
        cmpa    #$FF
        beq     launcher_route_end
        sta     launcher_y
        stx     launcher_route
        jsr     map_terrain
        bra     launcher_advance
launcher_route_end
        jsr     map_terrain
launcher_arrived
        lda     #2
        sta     launcher_hold
        bra     launcher_advance
launcher_fire
        cmpa    #$28
        bne     launcher_advance
        ldx     #launcher_shot_y
        lda     b,x
        sta     <hazard_box+1
        adda    #12
        sta     <hazard_box+3
        clr     <hazard_box
        lda     #255
        sta     <hazard_box+2
        ldu     #hazard_box
        jsr     either_box
        bcc     launcher_advance
        lda     #5
        sta     launcher_bolt
launcher_advance
        lda     launcher_bolt
        lbeq    launcher_done
        inca
        ldb     launcher_lane
        ldx     #launcher_shot_end
        cmpa    b,x
        bhs     launcher_clear
        sta     launcher_bolt
        ldx     #launcher_shot_y
        lda     b,x
        sta     <hazard_box+1
        sta     <hazard_box+3
        ldx     #launcher_shot_x
        ldb     launcher_bolt
        lda     b,x
        sta     <hazard_box
        incb
        lda     b,x
        sta     <hazard_box+2
        ldu     #hazard_box
        jsr     either_box
        bcs     launcher_hit
launcher_done
        rts
launcher_hit
        jmp     mark_death
launcher_clear
        clr     launcher_bolt
        rts

launcher_page
        ldy     #launcher_old
        lda     <back
        cmpa    #FB0
        beq     launcher_page_done
        leay    3,y
launcher_page_done
        rts

restore_launcher
        lda     <room_bank
        cmpa    #ROOM2
        lbne    launcher_done
        jsr     restore_motion2
        bsr     launcher_page
        ldb     ,y
        beq     restore_bolt
        pshs    y,b
        clra
        jsr     restore
        puls    y,b
        pshs    y
        lda     #15
        jsr     restore
        puls    y
restore_bolt
        ldd     1,y
        cmpa    #$FF
        lbeq    launcher_done
        jmp     restore

draw_launcher
        lda     <room_bank
        cmpa    #ROOM2
        lbne    launcher_done
        bsr     launcher_page
        clr     ,y
        lda     #$FF
        sta     1,y
        tst     launcher_enabled
        lbeq    launcher_done
        ldb     launcher_y
        stb     ,y
        pshs    y
        ldu     #launcher_closed_pose
        lda     launcher_hold
        beq     draw_launcher_moving
        cmpa    #$1C
        bhs     draw_launcher_body
        ldu     #launcher_open_pose
        bra     draw_launcher_body
draw_launcher_moving
        ldu     #launcher_moving_a
        bitb    #2
        beq     draw_launcher_body
        ldu     #launcher_moving_b
draw_launcher_body
        pshs    u
        clra
        jsr     draw_actor
        puls    u
        cmpu    #launcher_open_pose
        beq     draw_launcher_mouth
        cmpu    #launcher_moving_a
        bne     draw_launcher_bolt
        ldu     #launcher_moving_right
        bra     draw_launcher_right
draw_launcher_mouth
        ldu     #launcher_open_right
draw_launcher_right
        lda     #15
        ldb     launcher_y
        jsr     draw_actor
draw_launcher_bolt
        puls    y
        ldb     launcher_bolt
        lbeq    launcher_done
        ldx     #launcher_shot_x
        lda     b,x
        ldx     #launcher_shot_y
        ldb     launcher_lane
        ldb     b,x
        std     1,y
        ldu     #launcher_shot_pose
        pshs    a
        lda     launcher_bolt
        cmpa    #7
        bhs     launcher_bolt_pose
        ldu     #launcher_burst_pose
launcher_bolt_pose
        puls    a
        jmp     draw_actor

launcher_shot_y equ BG+$1910
launcher_shot_end equ launcher_shot_y+16
launcher_shot_x equ launcher_shot_end+16
launcher_closed_pose equ launcher_shot_x+36
launcher_open_pose equ launcher_closed_pose+176
launcher_open_right equ launcher_open_pose+176
launcher_burst_pose equ launcher_open_right+176
launcher_shot_pose equ launcher_burst_pose+176
launcher_moving_a equ launcher_shot_pose+176
launcher_moving_b equ launcher_moving_a+176
launcher_moving_right equ launcher_moving_b+176
        endc

