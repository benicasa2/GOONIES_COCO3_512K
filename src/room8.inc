        ifne PRELOAD_ALL
        org $0400
ROOM8_ART equ $3D
room8_height fcb 90
room8_box fcb 128
room8_left fcb 4
room8_delay fcb 0
room8_forced fcb 0
room8_dying fcb 0
room8_drops zmb 4
room8_previous fcb 90
reset_room8
        lda #90
        sta room8_height
        sta room8_previous
        lda #128
        sta room8_box
        lda #4
        sta room8_left
        ldx #room8_delay
room8_clear
        clr ,x+
        cmpx #room8_previous
        blo room8_clear
        jmp room8_native_reset
update_room8
        lda <room_bank
        cmpa #ROOM8
        lbne room8_done
        lda room8_height
        sta room8_previous
        ; Apple $62FA selects the second appearance (base $31), even after G.
        ldx #native_actors+10
        ldu #native_control_box
        jsr native_overlap
        bcc room8_lower
        lda room8_height
        cmpa #47
        blo room8_platform
        dec room8_height
        bra room8_platform
room8_lower
        lda room8_height
        cmpa #90
        bhs room8_platform
        inc room8_height
room8_platform
        lda room8_height
        sta np_rows+45*5+2
        sta np_rows+45*5+4
        adda #3
        sta np_rows+46*5+2
        adda #3
        sta np_rows+46*5+4
        jsr room8_active
        lda room8_box
        sta <hazard_box
        sta <hazard_box+2
        lda #64
        sta <hazard_box+1
        sta <hazard_box+3
        ldu #hazard_box
        jsr native_overlap
        bcc room8_box_floor
        lda 2,x
        ble room8_box_floor
        adda room8_box
        cmpa #142
        bhs room8_box_floor
        sta room8_box
room8_box_floor
        lda #$80
        ldb room8_box
        cmpb #134
        blo room8_store_floor
        lda #4
room8_store_floor
        sta np_rows+52*5
        cmpb #134
        blo room8_falling
        tst room8_left
        beq room8_falling
        tst room8_delay
        beq room8_emit
        dec room8_delay
        bra room8_falling
room8_emit
        lda #3
        sta room8_delay
        ldx #room8_drops+3
room8_slot
        tst ,x
        beq room8_spawn
        leax -1,x
        cmpx #room8_drops
        bhs room8_slot
        bra room8_falling
room8_spawn
        lda #56
        sta ,x
        dec room8_left
        lda room8_left
        cmpa #2
        bne room8_falling
        sta room8_forced
room8_falling
        ldx #room8_drops+3
room8_drop_next
        lda ,x
        beq room8_drop_skip
        adda #5
        cmpa #180
        blo room8_drop_store
        clra
room8_drop_store
        sta ,x
room8_drop_skip
        leax -1,x
        cmpx #room8_drops
        bhs room8_drop_next

room8_done
        rts
room8_control_box fcb 133,126,133,126

clear_room8_art
        lda <room_bank
        cmpa #ROOM8
        bne room8_done
        ldb #83
        bra room8_patch
draw_room8
        lda <room_bank
        cmpa #ROOM8
        bne room8_done
        ldb room8_height
        subb #46
        bsr room8_patch
        ldb room8_box
        subb #83               ; 128 -> frame 45
        bsr room8_patch
        ldy #room8_drops
room8_draw_drop
        ldb ,y+
        beq room8_draw_next
        subb #61
        clra
room8_divide
        cmpb #5
        blo room8_drop_frame
        subb #5
        inca
        bra room8_divide
room8_drop_frame
        adda #59
        tfr a,b
        pshs y
        bsr room8_patch
        puls y
room8_draw_next
        cmpy #room8_drops+4
        blo room8_draw_drop
        rts
room8_patch
        lda #ROOM8_ART
        sta MMU3
        clra
        lslb
        rola
        ldx #BG
        leax d,x
        ldu ,x
        jmp video_patch_run

room8_enemy_hit
        tst room8_dying
        bne room8_done
        lda #8
        sta room8_dying
        rts
room8_enemy_pose
        lda <room_bank
        cmpa #ROOM8
        bne room8_done
        lda room8_dying
        beq room8_done
        ldu #pose_death_early
        cmpa #4
        bhs room8_done
        ldu #pose_death_late
        rts
room8_grip
        ldu #room8_bars
room8_grip_loop
        lda ,x
        cmpa 2,u
        bhi room8_grip_next
        adda #BODY_X
        cmpa ,u
        blo room8_grip_next
        lda <next_y
        cmpa 3,u
        bhi room8_grip_next
        adda #BODY_Y
        cmpa 1,u
        blo room8_grip_next
        lda 1,u
        sta 1,x
        clr <vy
        clr <grounded
        orcc #1
        rts
room8_grip_next
        leau 4,u
        cmpu #room8_bars_end
        blo room8_grip_loop
        andcc #$FE
        rts
room8_bars
        fcb 232,74,232,107
        fcb 62,71,62,71
        fcb 98,111,98,111
        fcb 98,152,98,152
        fcb 151,17,235,17
room8_bars_end
room8_enemy
        rts

; Native actor state: x,y,dx,dy,pose,ladder,drop,latch,input,pose-base.
room8_clock fcb 0
room8_phase fcb 102
room8_initial
        fcb 10,153,0,0,0,0,0,0,0,0
        fcb 10,153,0,0,0,0,0,0,0,49
        fcb 87,117,0,0,20,0,0,0,31,20
room8_native_reset
        lda <room_bank
        cmpa #ROOM8
        lbne room8_done
        lda #NATIVE_BANK
        sta MMU3
        ldx #room8_initial
        ldu #native_actors
room8_initial_copy
        lda ,x+
        sta ,u+
        cmpu #native_actors+30
        blo room8_initial_copy
        clr room8_clock
        lda #102
        sta room8_phase
        lda #90
        sta np_rows+45*5+2
        sta np_rows+45*5+4
        lda #93
        sta np_rows+46*5+2
        lda #96
        sta np_rows+46*5+4
        lda #4
        sta np_rows+52*5
        jsr room8_native_gates
        jmp room8_project
room8_active
        ldx #native_actors
        tst <active
        beq room8_actor_selected
        leax 10,x
room8_actor_selected
        rts
room8_native_frame
        lda #NATIVE_BANK
        sta MMU3
        ; $0905 decrements the global animation counter and reloads four.
        dec room8_clock
        bpl room8_clock_ready
        lda #4
        sta room8_clock
room8_clock_ready
        jsr native_inputs
        ldx #native_actors
        jsr native_physics
        jsr native_animate
        ldx #native_actors+10
        jsr native_physics
        jsr native_animate
        bra room8_enemy_step
native_inputs
        ldx #native_actors
        lda #31
        sta 8,x
        sta 18,x
        jsr room8_active
        lda <keys
        anda #15
        ldb <keys
        bitb #64
        beq room8_input_ready
        ora #16
room8_input_ready
        eora #31
        sta 8,x
        rts
room8_enemy_step
        tst <enemy_on
        beq room8_after_enemy
        tst room8_dying
        bne room8_death_frame
        tst room8_clock
        bne room8_enemy_physics
        inc room8_phase
room8_enemy_physics
        ldx #native_actors+20
        jsr native_physics
        jsr native_animate
        jsr room8_native_ai
        bra room8_after_enemy
room8_death_frame
        dec room8_dying
        beq room8_remove_enemy
        lda #29
        ldb room8_dying
        cmpb #5
        blo room8_store_death
        lda #28
room8_store_death
        sta native_actors+24
        bra room8_after_enemy
room8_remove_enemy
        clr <enemy_on
room8_after_enemy
        jsr room8_native_gates
        jsr update_room8
        jsr room8_native_pit
        jsr room8_project
        tst <death
        lbne room8_native_return
        lda #NATIVE_BANK
        sta MMU3
        ldu #native_exit_box
        jsr room8_both
        lbcc room8_native_return
        jsr score_room4_exit
        jmp exit_win
room8_native_return
        rts
room8_native_ai
        tst room8_forced
        bne room8_command_right
        ldx #native_actors
        ldu #native_engagement_box
        jsr native_overlap
        bcs room8_chase
        ldb room8_phase
        andb #3
        ldu #room8_idle_poses
        lda b,u
        sta native_actors+24
        bra room8_command_left
room8_chase
        lda ,x
        anda #254
        sta <hazard_box
        lda native_actors+20
        anda #254
        cmpa <hazard_box
        blo room8_command_right
        bne room8_command_left
        lda room8_phase
        anda #1
        adda #24
        sta native_actors+24
        lda #31
        bra room8_command
room8_command_left
        lda #27
        bra room8_command
room8_command_right
        lda #23
room8_command
        sta native_actors+28
        lda native_actors+20
        adda #2
        sta <hazard_box
        adda #3
        sta <hazard_box+2
        lda native_actors+21
        adda #4
        sta <hazard_box+1
        adda #12
        sta <hazard_box+3
        ldx #native_actors
        ldu #hazard_box
        jsr native_overlap
        lbcc room8_native_return
room8_mark_player
        ldx #px
room8_mark_selected
        jmp mark_death
room8_idle_poses fcb 26,20,57,20
native_control_box fcb 81,126,81,126
native_exit_box fcb 144,64,144,64
native_engagement_box fcb 92,117,132,132
native_pit_box fcb 137,178,159,178
room8_native_pit
        ldu #native_pit_box
        ldx #native_actors
        jsr native_overlap
        bcc room8_pit_second
        ldx #px
        jsr mark_death
room8_pit_second
        ldx #native_actors+10
        jsr native_overlap
        bcc room8_pit_enemy_native
        ldx #p2x
        jsr mark_death
room8_pit_enemy_native
        tst <enemy_on
        lbeq room8_native_return
        tst room8_dying
        lbne room8_native_return
        ldx #native_actors+20
        jsr native_overlap
        lbcc room8_native_return
        ; Nine includes the terminal removal tick after eight death poses.
        lda #9
        sta room8_dying
        rts
room8_either
        ldx #native_actors
        jsr native_overlap
        bcs room8_either_done
        leax 10,x
        jsr native_overlap
room8_either_done
        rts
room8_both
        ldx #native_actors
        jsr native_overlap
        bcc room8_either_done
        leax 10,x
        jmp native_overlap
room8_native_gates
        clr <gate_mask
        ldu #native_switches
room8_native_switch
        jsr room8_either
        rol <gate_mask
        leau 4,u
        cmpu #native_clearance
        blo room8_native_switch
        ldu #layout8
        ldb <gate_mask
        lda b,u
        sta <gate_mask
        ldu #native_clearance
        ldb #4
room8_native_clearance
        pshs b
        jsr room8_either
        puls b
        bcc room8_native_clear_next
        orb <gate_mask
        stb <gate_mask
        ; Mask iterator is recomputed from the point pointer below.
room8_native_clear_next
        leau 4,u
        cmpu #native_clearance+12
        bhs room8_native_commit
        ldb #2
        cmpu #native_clearance+4
        beq room8_native_clearance
        ldb #1
        bra room8_native_clearance
room8_native_commit
        lda <gate_mask
        ldu #native_gate_rows
        ldb #3
room8_native_commit_loop
        pshs a,b
        ldx ,u++
        ldy ,u++
        lsra
        bcs room8_native_open
        lda #3
        sta ,x
        lda #2
        bra room8_native_wall
room8_native_open
        lda #4
        sta ,x
        lda #128
room8_native_wall
        sta ,y
        puls a,b
        lsra
        decb
        bne room8_native_commit_loop
        rts
native_switches
        fcb 42,71,42,71,62,111,62,111,62,152,62,152,81,126,81,126
native_clearance
        fcb 32,61,32,61,53,101,53,101,48,141,48,141
native_gate_rows
        fdb np_rows+32*5,np_rows+51*5
        fdb np_rows+43*5,np_rows+50*5
        fdb np_rows+22*5,np_rows+49*5
room8_project
        lda #ROOM6_ART
        sta MMU3
        ldx #native_actors
        ldy #px
room8_project_one
        ldb ,x
        clra
        ldu #room5_xmap
        lda d,u
        inca                   ; inverse projection restores the exact byte column
        ldb 1,x
        std ,y++
        leax 10,x
        cmpx #native_actors+30
        blo room8_project_one
        rts
room8_native_draw
        lda #NATIVE_BANK
        sta MMU3
native_draw_players
        ldx #native_actors
room8_native_draw_one
        pshs x
        jsr native_draw_player
        puls x
        leax 10,x
        cmpx #native_actors+20
        blo room8_native_draw_one
        bne room8_native_draw_done
        tst <enemy_on
        bne room8_native_draw_one
room8_native_draw_done
        rts
native_draw_player
        ldb 4,x
        tst <death
        beq room8_draw_pose
        cmpx #native_actors+20
        beq room8_draw_pose
        lda #px
        cmpx #native_actors
        beq room8_draw_death_target
        lda #p2x
room8_draw_death_target
        cmpa <dead_player
        bne room8_draw_pose
        ldb #28
        lda <death
        cmpa #9
        blo room8_draw_pose
        incb
room8_draw_pose
native_draw_pose
        clra
        lslb
        rola
        ldu #$6000
        ldu d,u
        ; Native x is already a two-pixel byte column. Avoid rounding drift.
        lda ,x
        adda #2
        sta <row_x
        lda 1,x
        sta <row_y
        lda #22
        sta <rows
        lda <room_bank
        cmpa #ROOM7
        bne native_draw_rows
        ldb #8
        jsr room7_log_rectangle
native_draw_rows
        jmp draw_row

        include "room7.inc"
room8_code_end
        endc
