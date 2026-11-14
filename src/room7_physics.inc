        ; This module runs in the same bank as the shared 6809 physics.
room7_logic
        jsr native_inputs
        ldx #native_actors
        jsr native_physics7
        jsr native_animate
        ldx #native_actors+10
        jsr native_physics7
        jsr native_animate
        jsr room7_box_step
        jsr room7_bats_step
        jsr room7_currents
        jsr room7_box_support
        jsr room7_lever_step
        jsr room7_water_step
        ldu #room7_pit_zone
        jsr room7_check_death
        jsr room7_wave_step
        jsr room7_spawn_step
        tst <death
        bne room7_no_exit
        ldu #room7_exit_zone
        jmp room8_both
room7_no_exit
        andcc #254
        rts
room7_pit_zone fcb 102,159,107,186
room7_exit_zone fcb 141,119,141,119
room7_box_step
        jsr room8_active
        lda native_actors+20
        sta <hazard_box
        sta <hazard_box+2
        lda native_actors+21
        sta <hazard_box+1
        adda #8
        sta <hazard_box+3
        ldu #hazard_box
        jsr native_overlap
        bcc room7_box_right
        lda 2,x
        ble room7_box_move
        bra room7_box_push
room7_box_right
        lda ,u
        adda #8
        sta ,u
        sta 2,u
        jsr native_overlap
        bcc room7_box_move
        lda 2,x
        bpl room7_box_move
room7_box_push
        sta native_actors+22
room7_box_move
        ldx #native_actors+20
        lda #31
        tst room7_box_open
        beq room7_box_input
        lda #29
room7_box_input
        sta 8,x
        jmp native_box_physics
room7_box_support
        tst room7_box_open
        beq room7_box_release
        lda native_actors+20
        adda #2
        sta room7_rows+1
        sta room7_rows+3
        lda native_actors+21
        sta room7_rows+2
        sta room7_rows+4
        lda #3
        sta room7_rows
        rts
room7_box_release
        ldu #room7_upper_bar
        jsr room8_either
        bcc room7_box_wait
        inc room7_box_open
        ldx #room4_score+4
        lda #5
        jsr room4_score_add
room7_box_wait
        lda #$83
        sta room7_rows
        rts
room7_upper_bar fcb 48,44,48,44
room7_lower_bar fcb 36,142,36,142
room7_left_lever fcb 20,104,40,104
room7_right_lever fcb 57,104,67,104
room7_lever_step
        clr room7_levers
        clr room7_unlock
        lda #$86
        sta room7_rows+33*5
        ldu #room7_lower_bar
        jsr room8_either
        bcc room7_lever_right
        inc room7_unlock
        lda #6
        sta room7_rows+33*5
        ldu #room7_left_lever
        jsr room8_either
        bcc room7_lever_right
        inc room7_levers
        tst room7_drain
        bne room7_lever_right
        inc room7_drain
        ldx #room4_score+3
        lda #5
        jsr room4_score_add
room7_lever_right
        ldu #room7_right_lever
        jsr room8_either
        bcc room7_lever_done
        lda #2
        ora room7_levers
        sta room7_levers
room7_lever_done
        rts
room7_water_step
        tst room7_drain
        beq room7_clock_step
        lda room7_octopus
        cmpa #150
        bhs room7_clock_step
        inc room7_octopus
room7_clock_step
        dec room7_clock
        bpl room7_phase_step
        lda #4
        sta room7_clock
room7_phase_step
        tst room7_clock
        bne room7_octopus_contact
        inc room7_phase
room7_octopus_contact
        ldb room7_phase
        andb #3
        ldx #room7_octopus_offsets
        lda b,x
        adda room7_octopus
        ldx #room7_head_offsets
        suba b,x
        inca
        sta <hazard_box+1
        lda #124
        sta <hazard_box
        lda #136
        sta <hazard_box+2
        lda #171
        sta <hazard_box+3
        ldu #hazard_box
room7_check_death
        tst <death
        bne room7_death_done
        jsr room8_either
        bcc room7_death_done
        cmpx #native_actors
        ldx #px
        beq room7_mark_death
        ldx #p2x
room7_mark_death
        jmp mark_death
room7_death_done
        rts
room7_rng
        inc room7_random
        ldb room7_random
        clra
        ldy #$4212
        lda d,y
        rts
room7_currents
        ldu #room7_current_zones
room7_current_zone
        ldx #native_actors+20
room7_current_actor
        jsr native_overlap
        bcc room7_current_next
        jsr room7_rng
        cmpa #$70
        bhs room7_current_next
        lda 2,x
        inca
        cmpa #3
        bge room7_current_next
        sta 2,x
room7_current_next
        leax -10,x
        cmpx #native_actors
        bhs room7_current_actor
        leau 4,u
        cmpu #room7_current_zones+12
        blo room7_current_zone
        rts
room7_current_zones fcb 94,118,117,126,86,94,95,119,6,173,107,186
room7_wave_step
        dec room7_wave_clock
        bpl room7_wave_update
        lda #2
        sta room7_wave_clock
room7_wave_update
        ldx #room7_waves+15
        ldb #15
room7_wave_one
        pshs b
        ldu #room7_wave_draw
        lda ,x
        sta b,u
        andb #3
        lslb
        ldu #$41F0
        ldu b,u
        leau -$2000,u
        ldb ,x
        lslb
        tst b,u
        bne room7_wave_advance
        clr ,x
        bra room7_wave_next
room7_wave_advance
        tst room7_wave_clock
        bne room7_wave_next
        inc ,x
room7_wave_next
        puls b
        leax -1,x
        decb
        bpl room7_wave_one
        rts
room7_spawn_step
        tst room7_spawn
        bne room7_spawn_delay
        jsr room7_rng
        anda #63
        adda #85
        sta room7_spawn
        ldx #room7_bats
room7_find_bat
        tst 4,x
        beq room7_spawn_bat
        leax 10,x
        cmpx #room7_bats_end
        blo room7_find_bat
        bra room7_spawn_delay
room7_spawn_bat
        lda #16
        sta 4,x
        sta 7,x
        clr 9,x
        jsr room7_rng
        ldb #7
        cmpa #$70
        bhs room7_spawn_path
        ldb #9
room7_spawn_path
        stb 5,x
        jsr room7_waypoint
        ldd ,u
        std ,x
        std 2,x
room7_spawn_delay
        dec room7_spawn
        rts
room7_waypoint
        ldb 5,x
        lslb
        ldu #$41C2
        ldu b,u
        leau -$2000,u
        ldb 9,x
        lslb
        leau b,u
        rts
room7_bats_step
        ldx #room7_bats
room7_bat_one
        tst 4,x
        lbeq room7_bat_next
        lda ,x
        anda #254
        ldb 2,x
        andb #254
        pshs b
        cmpa ,s+
        beq room7_bat_x_equal
        blo room7_bat_move_right
        suba #2
        bra room7_bat_x_store
room7_bat_move_right
        adda #2
room7_bat_x_store
        sta ,x
        clrb
        bra room7_bat_y
room7_bat_x_equal
        ldb #1
room7_bat_y
        pshs b
        lda 1,x
        anda #254
        ldb 3,x
        andb #254
        pshs b
        cmpa ,s+
        beq room7_bat_arrival
        blo room7_bat_move_down
        suba #2
        bra room7_bat_y_store
room7_bat_move_down
        adda #2
room7_bat_y_store
        sta 1,x
        leas 1,s
        bra room7_bat_contact
room7_bat_arrival
        puls b
        tstb
        beq room7_bat_same_y
        bra room7_bat_waypoint
room7_bat_same_y
        sta 1,x
        bra room7_bat_contact
room7_bat_waypoint
        inc 9,x
        jsr room7_waypoint
        ldd ,u
        std 2,x
        cmpb #255
        beq room7_bat_remove
        tstb
        bne room7_bat_contact
        jsr room7_rng
        bmi room7_bat_waypoint
        ldu #$41D6
        ldb 5,x
        lda b,u
        sta 5,x
        lda #255
        sta 9,x
        bra room7_bat_waypoint
room7_bat_remove
        clr 4,x
        bra room7_bat_next
room7_bat_contact
        lda ,x
        sta <hazard_box
        adda #4
        sta <hazard_box+2
        lda 1,x
        sta <hazard_box+1
        adda #4
        sta <hazard_box+3
        pshs x
        ldu #hazard_box
        jsr room7_check_death
        puls x
        inc 7,x
        lda 7,x
        anda #3
        adda #16
        sta 4,x
room7_bat_next
        leax 10,x
        cmpx #room7_bats_end
        lblo room7_bat_one
        rts
