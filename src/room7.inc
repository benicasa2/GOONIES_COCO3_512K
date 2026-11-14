; Apple overlay 7. Logic runs with the shared physics bank in MMU3 and
; the room's original terrain, random table and waypoints in MMU2.
ROOM7 equ ROOM+30
room7_box_open equ $135C
room7_drain equ $135D
room7_levers equ $135E
room7_octopus equ $135F
room7_phase equ $1360
room7_clock equ $1361
room7_wave_clock equ $1362
room7_random equ $1363
room7_spawn equ $1364
room7_waves equ $1365
room7_bats equ $1375
room7_bats_end equ room7_bats+30
room7_sprite_width equ $1393
room7_sprite_start equ $1394
room7_draw_x equ $1395
room7_draw_index equ $1396
room7_draw_y equ $1397
room7_unlock equ $1398
room7_history equ $0C00
room7_write equ $1399
room7_read equ $139B
room7_copy_left equ $139D
room7_wave_draw equ $13A0
room7_to7
        lda #ROOM7_ART
        sta MMU2
        lda #NATIVE_BANK
        sta MMU3
        rts
reset_room7
        lda <room_bank
        cmpa #ROOM7
        bne room7_reset_done
        jsr room7_to7
        ldx #room7_initial
        ldu #native_actors
room7_init_actor
        lda ,x+
        sta ,u+
        cmpu #native_actors+30
        blo room7_init_actor
        ldu #room7_box_open
room7_init_state
        clr ,u+
        cmpu #room7_bats_end
        blo room7_init_state
        ldd #$7B14
        std room7_octopus
        lda #1
        sta room7_random
        lda #69
        sta room7_spawn
        ldx #room7_wave_initial
        ldu #room7_waves
room7_init_wave
        lda ,x+
        sta ,u+
        sta room7_wave_draw-room7_waves-1,u
        cmpu #room7_bats
        blo room7_init_wave
        lda #$83
        sta room7_rows
        lda #$86
        sta room7_rows+33*5
        clr room7_unlock
        clr room7_history
        clr room7_history+128
        lda #2
        sta <redraw
        clr <enemy_on
room7_reset_done
        rts
room7_initial
        fcb 10,142,1,0,0,0,0,0,0,0
        fcb 10,142,1,0,0,0,0,0,0,8
        fcb 46,121,0,0,48,0,0,0,31,0
room7_wave_initial
        fcb 1,2,3,4,5,6,7,0,8,9,1,2,3,4,5,6
room7_frame
        jsr room7_to7
        jsr room7_logic
        bcc room7_reset_done
        jsr score_room4_exit
        lda #ROOM8
        jmp change_room

; Keep a list of dirty rectangles separately for each framebuffer.
room7_paint
        ldu #room7_history
        lda <back
        cmpa #FB0
        beq room7_page_ready
        leau 128,u
room7_page_ready
        stu room7_write
        stu room7_read
        tst <redraw
        beq room7_restore_next
        dec <redraw
        jsr copy_background
        bra room7_paint_levers
room7_restore_next
        ldu room7_read
        lda ,u+
        beq room7_paint_levers
        sta room7_sprite_width
        lda ,u+
        sta <row_x
        lda ,u+
        sta <row_y
        lda ,u+
        sta <rows
        stu room7_read
room7_restore_row
        jsr row_address
        lda room7_sprite_width
        sta room7_copy_left
room7_restore_source
        lda <bank
        adda #ROOM7
        sta MMU3
        leay $2000,x
room7_restore_byte
        lda ,y+
        sta ,x+
        dec room7_copy_left
        beq room7_restore_row_end
        cmpx #BG
        bne room7_restore_byte
        jsr next_video_bank
        bra room7_restore_source
room7_restore_row_end
        inc <row_y
        dec <rows
        bne room7_restore_row
        bra room7_restore_next
room7_paint_levers
        lda #ROOM7_ART
        sta MMU3
        ldu $6210
        jsr video_patch_run
        tst room7_unlock
        bne room7_draw_left
        ldu $6206
        jsr video_patch_run
room7_draw_left
        ldu $620C
        lda room7_levers
        bita #1
        beq room7_left_stamp
        ldu $6208
room7_left_stamp
        jsr video_patch_run
        ldu $620E
        lda room7_levers
        bita #2
        beq room7_right_stamp
        ldu $620A
room7_right_stamp
        jsr video_patch_run
room7_draw_water
        lda room7_phase
        anda #3
        leax room7_octopus_offsets,pcr
        lda a,x
        adda room7_octopus
        sta room7_draw_y
        ldb room7_phase
        andb #3
        lslb
        ldx #$61E0
        ldu b,x
        jsr room7_stamp
        ldb room7_phase
        andb #3
        leax room7_head_offsets,pcr
        lda room7_draw_y
        suba b,x
        inca
        incb
        andb #3
        lslb
        ldx #$61E8
        ldu b,x
        jsr room7_stamp
        clr room7_draw_index
room7_draw_wave
        ldb room7_draw_index
        andb #3
        lslb
        ldx #$61F0
        ldu b,x
        ldx #room7_wave_draw
        ldb room7_draw_index
        ldb b,x
        lslb
        leau b,u
        ldd ,u
        tsta
        beq room7_next_wave
        suba #8
        clr room7_draw_x
room7_wave_column
        cmpa #7
        blo room7_wave_stamp
        suba #7
        pshs a
        lda room7_draw_x
        adda #7
        sta room7_draw_x
        puls a
        bra room7_wave_column
room7_wave_stamp
        ldx #$61F8
        lsla
        ldu a,x
        tfr b,a
        jsr room7_moving_stamp
room7_next_wave
        inc room7_draw_index
        lda room7_draw_index
        cmpa #16
        blo room7_draw_wave
        ldx #native_actors+20
        ldb #48
        jsr native_draw_pose
        ldx #room7_bats
room7_draw_bat
        tst 4,x
        beq room7_next_bat
        ldb 4,x
        pshs x
        jsr native_draw_pose
        puls x
room7_next_bat
        leax 10,x
        cmpx #room7_bats_end
        blo room7_draw_bat
        lda #NATIVE_BANK
        sta MMU3
        ldx #native_actors
        jsr native_draw_player
        lda #ROOM7_ART
        sta MMU3
        ldx #native_actors+10
        ldb 4,x
        tst <death
        beq room7_second_pose
        lda <dead_player
        cmpa #p2x
        bne room7_second_pose
        lda #NATIVE_BANK
        sta MMU3
        ldb #28
        lda <death
        cmpa #9
        blo room7_second_pose
        incb
room7_second_pose
        jsr native_draw_pose
        ldu room7_write
        clr ,u
        jsr draw_lives
        jmp draw_room4_score
room7_octopus_offsets fcb 1,0,0,0
room7_head_offsets fcb 10,12,15,12
room7_stamp
        clr room7_draw_x
room7_moving_stamp
        sta <row_y
        lda ,u+
        adda room7_draw_x
        sta <row_x
        lda ,u+
        sta room7_sprite_width
        lda ,u+
        sta <rows
        ldb room7_sprite_width
        jsr room7_log_rectangle
room7_stamp_row
        jsr row_address
        ldb room7_sprite_width
        pshs b
room7_stamp_byte
        ldb ,u+
        beq room7_stamp_skip
        lda #255
        bitb #$F0
        beq room7_stamp_high
        anda #$0F
room7_stamp_high
        bitb #$0F
        beq room7_stamp_merge
        anda #$F0
room7_stamp_merge
        anda ,x
        stb room7_sprite_start
        ora room7_sprite_start
        sta ,x
room7_stamp_skip
        leax 1,x
        cmpx #BG
        bne room7_stamp_count
        jsr next_video_bank
room7_stamp_count
        dec ,s
        bne room7_stamp_byte
        leas 1,s
        inc <row_y
        dec <rows
        bne room7_stamp_row
        rts

room7_log_rectangle
        pshs u
        ldu room7_write
        stb ,u+
        lda <row_x
        sta ,u+
        lda <row_y
        sta ,u+
        lda <rows
        sta ,u+
        stu room7_write
        puls u,pc
