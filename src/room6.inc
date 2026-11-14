        ifne PRELOAD_ALL
; Room 6 owns room5's nine actor slots while active. Original slot order
; is indices 8..0, as created by Apple $6196. Poses 43..47 map to 31..35
; solely to reuse the two-strip renderer and its double-buffer history.
        org $1400
ROOM6_ART equ $3C
room6_initial equ $6400
room6_pit_box equ $6480
room6_code equ $6C00
reset_room6
        lda <room_bank
        cmpa #ROOM6
        bne room6_return
        lda #ROOM6_ART
        sta MMU3
        ldu #room6_initial
        ldx #room5_eggs
room6_init_actor
        ldd ,u++
        std 3,x
        stb 5,x
        lda ,u+
        sta 6,x
        lda ,u+
        sta 2,x
        lda ,u+
        sta 9,x
        lda #35
        sta 7,x
        leax R5_SIZE,x
        cmpx #room5_end
        blo room6_init_actor
        lda #1
        sta room5_dropped
room6_return
        rts

; Run before room_puzzles: Apple dispatches actors before $636B decreases
; the plate timers. A middle impact sets 16, then the layout sees 15.
update_room6
        lda <room_bank
        cmpa #ROOM6
        bne room6_return
        lda #ROOM6_ART
        sta MMU3
        ldx #room5_eggs
room6_actor_loop
        jsr room6_actor
        leax R5_SIZE,x
        cmpx #room5_end
        blo room6_actor_loop
        rts
room6_actor
        lda 2,x
        beq room6_fall
        tst 8,x
        bne room6_wait
        inc 8,x
        lda #35
        sta 7,x
        rts
room6_wait
        ldb 5,x
        stb 4,x
        dec 2,x
        cmpa #7
        lda #31
        bhs room6_pose
        lda #32
room6_pose
        sta 7,x
        rts
room6_fall
        lda 8,x
        inca
        cmpa #5
        bhs room6_velocity
        sta 8,x
room6_velocity
        adda 4,x
        sta 4,x
        cmpa 6,x
        bhs room6_impact
        ; The original attack rectangle is a vertical line at native X+2.
        pshs x
        ldb 3,x
        addb #2
        clra
        ldu #room5_xmap
        lda d,u
        sta <hazard_box
        sta <hazard_box+2
        lda 4,x
        sta <hazard_box+1
        adda #3
        sta <hazard_box+3
        ldu #hazard_box
        jsr either_box
        bcc room6_no_hit
        jsr mark_death
room6_no_hit
        puls x
        lda 4,x
        bita #4
        beq room6_pose_low
        lda #33
        bra room6_pose
room6_pose_low
        lda #34
        bra room6_pose
room6_impact
        lda 9,x
        cmpa #3
        blo room6_outer
        cmpa #6
        bhs room6_outer
        suba #3
        tfr a,b
        ldu #plate_timer
        lda #16
        sta b,u
        lda 4,x
        suba #7
        sta 4,x
        jsr room6_random
        ; Apple ADC retains carry from SBC #7.
        adda #33
        bra room6_restart
room6_outer
        jsr room6_random
        adda #48
        ldb 9,x
        cmpb #6
        blo room6_restart
        inca                    ; carry retained by Apple CMP #6
room6_restart
        sta 2,x
        clr 8,x
        lda #35
        sta 7,x
        rts
room6_random
        inc particle_rng
        lda #ROOM4_GRAPH
        sta MMU3
        clra
        ldb particle_rng
        ldu #particle_random
        lda d,u
        anda #63
        pshs a
        lda #ROOM6_ART
        sta MMU3
        puls a,pc

room6_pit
        lda #ROOM6_ART
        sta MMU3
        ldu #room6_pit_box
        jsr either_box
        bcc room6_pit_done
        jsr mark_death
room6_pit_done
        jmp map_terrain
room6_return2
        rts
restore_room6
        lda <room_bank
        cmpa #ROOM6
        bne room6_return2
        jsr room5_page
        jmp room5_restore_next
draw_room6
        lda <room_bank
        cmpa #ROOM6
        bne room6_return2
        lda #ROOM6_ART
        sta MMU3
        jsr room5_page
        ldx #room5_eggs
        jmp room5_draw_actor
room6_code_end
        endc
