; Room-local rules recovered from the Apple II overlays.
ROOM5   equ     ROOM+20
ROOM6   equ     ROOM+25
ROOM8   equ     ROOM+35

reset_mechanics
        clr     <portal_cd
        clr     <portal_cd+1
        clr     <plate_timer
        clr     <plate_timer+1
        clr     <plate_timer+2
        ldd     #layout6
        std     <layout_ptr
        rts

; Called once before both players move. Four-frame plate timers match $610B.
room_puzzles
        tst     <portal_cd
        beq     cooldown_second
        dec     <portal_cd
cooldown_second
        tst     <portal_cd+1
        beq     update_layout
        dec     <portal_cd+1
update_layout
        lda     <room_bank
        cmpa    #ROOM8
        lbeq    final_room_gates
        cmpa    #ROOM8
        lbeq    final_room_gates
        cmpa    #ROOM6
        bne     puzzles_done
        ldu     #plates6
        ldy     #plate_timer
        clr     <plate_mask
plate_loop
        lsl     <plate_mask
        tst     ,y
        beq     plate_contact
        dec     ,y
plate_contact
        tst     ,y
        beq     plate_check_player
        inc     <plate_mask
plate_check_player
        jsr     point_either
        bcc     plate_next
        lda     #4
        sta     ,y
plate_next
        leay    1,y
        leau    2,u
        cmpu    #plates6+6
        blo     plate_loop
        lda     <plate_mask
        ldb     #13
        mul
        addd    #layout6
        std     <layout_ptr
puzzles_done
        rts

; U points to an X/Y point. AABB uses the same bounds as the exits.
point_either
        ldx     #px
        bsr     point_player
        bcs     point_done
        ldx     #p2x
point_player
        lda     ,x
        cmpa    ,u
        bhi     point_miss
        adda    #BODY_X
        cmpa    ,u
        blo     point_miss
        lda     1,x
        cmpa    1,u
        bhi     point_miss
        adda    #BODY_Y
        cmpa    1,u
        blo     point_miss
        orcc    #1
point_done
        rts
point_miss
        andcc   #$FE
        rts

; Uses active X and <keys. A set carry returns a completed passage.
room_passage
        lda     <room_bank
        cmpa    #ROOM5
        beq     passage_room5
        cmpa    #ROOM6
        bne     point_miss
        pshs    x
        ldu     #portal_switches6
        bsr     point_either
        bcs     passage_enabled
        leau    2,u
        bsr     point_either
passage_enabled
        puls    x
        bcc     point_miss
        ldu     #portals6
        bra     passage_scan
passage_room5
        ldu     #portals5
passage_scan
        lda     ,u
        cmpa    #$FF
        beq     point_miss
        lda     <keys
        anda    #12
        cmpa    2,u
        bne     passage_next
        bsr     point_player
        bcs     passage_move
passage_next
        leau    5,u
        bra     passage_scan
passage_move
        lda     ,x
        ldb     3,u
        bmi     passage_left
        adda    3,u
        bcs     passage_right_limit
        cmpa    #SPRITE_MAX_X
        bls     passage_x
passage_right_limit
        lda     #SPRITE_MAX_X
        bra     passage_x
passage_left
        adda    3,u
        bcs     passage_x
        clra
passage_x
        sta     ,x
        lda     1,x
        ldb     4,u
        bmi     passage_up
        adda    4,u
        bcs     passage_bottom
        cmpa    #SPRITE_MAX_Y
        bls     passage_y
passage_bottom
        lda     #SPRITE_MAX_Y
        bra     passage_y
passage_up
        adda    4,u
        bcs     passage_y
        clra
passage_y
        sta     1,x
        clr     <grounded
        clr     <vy
        ldy     #portal_cd
        ldb     <active
        lda     #4
        sta     b,y
        orcc    #1
        rts

; Type-7 bars in the room-6 terrain are the same points as its portal
; switches. Like Apple $0DB5, an overlap sets the player's top to the bar.
room_grip
        ifne PRELOAD_ALL
        lda     <room_bank
        cmpa    #ROOM8
        lbeq    room8_grip
        endc
        lda     <room_bank
        cmpa    #ROOM6
        lbne    point_miss
        ldu     #portal_switches6
grip_loop
        lda     ,x
        cmpa    ,u
        bhi     grip_next
        adda    #BODY_X
        cmpa    ,u
        blo     grip_next
        lda     <next_y
        cmpa    1,u
        bhi     grip_next
        adda    #BODY_Y
        cmpa    1,u
        blo     grip_next
        lda     1,u
        sta     1,x
        clr     <vy
        clr     <grounded
        orcc    #1
        rts
grip_next
        leau    2,u
        cmpu    #portal_switches6+4
        blo     grip_loop
        lbra    point_miss

; The 13 lines occupy empty cells in the original background. Write on or
; off after restoring the dirty actor rectangles, before drawing the actors.
draw_platforms
        lda     <room_bank
        cmpa    #ROOM6
        bne     platforms_done
        ldu     #platform_rows6
        ldy     <layout_ptr
platform_line
        lda     ,u+
        sta     <row_x
        lda     ,u+
        sta     <row_y
        jsr     row_address
        clra
        tst     ,y+
        beq     platform_width
        lda     #$CC
platform_width
        ldb     ,u+
platform_pixel_pair
        sta     ,x+
        decb
        beq     platform_next_line
        cmpx    #BG
        bne     platform_pixel_pair
        pshs    a
        jsr     next_video_bank
        puls    a
        bra     platform_pixel_pair
platform_next_line
        cmpu    #platform_rows6_end
        blo     platform_line
        ldu     #plates6
        ldy     #plate_timer
draw_plate
        lda     ,u+
        jsr     logical_to_row_x
        lda     ,u+
        sta     <row_y
        jsr     row_address
        lda     #$88
        tst     ,y+
        beq     plate_ink
        lda     #$DD
plate_ink
        sta     ,x
        cmpu    #plates6+6
        blo     draw_plate
platforms_done
        rts


; Overlay 8: $6367 selects three gates from four switches and the
; clearance points next to each gate ($63E5). Row indices match Apple.
final_room_gates
        jsr     map_terrain
        ldu     #switches8
        clr     <gate_mask
gates8_switch
        jsr     point_either
        rol     <gate_mask
        leau    2,u
        cmpu    #switches8+8
        blo     gates8_switch
        ldx     #layout8
        ldb     <gate_mask
        lda     b,x
        sta     <gate_mask
        ldb     #4
gates8_clearance
        pshs    b
        jsr     point_either
        puls    b
        bcc     gates8_next
        tfr     b,a
        ora     <gate_mask
        sta     <gate_mask
gates8_next
        lsrb
        leau    2,u
        cmpu    #switches8+14
        blo     gates8_clearance
        ldu     #gates8_rows
        lda     <gate_mask
        pshs    a
        ldb     #3
gates8_commit
        ldx     ,u++
        ldy     ,u++
        lsr     ,s
        bcs     gates8_open
        lda     #3
        sta     ,x
        lda     #2
        bra     gates8_wall
gates8_open
        lda     #4
        sta     ,x
        lda     #$7F
gates8_wall
        sta     ,y
        decb
        bne     gates8_commit
        leas    1,s
        rts
gates8_rows
        fdb TERRAIN+32*5,TERRAIN+51*5
        fdb TERRAIN+43*5,TERRAIN+50*5
        fdb TERRAIN+22*5,TERRAIN+49*5

; $6125 targets the active Goonie inside its engagement rectangle.
; Use the shared collision integrator for vertical movement.
final_room_enemy
        ifne PRELOAD_ALL
        jmp room8_enemy
        else
        ifne PRELOAD_ALL
        tst room8_dying
        lbne actor_done
        endc
        pshs    x
        lda     <vy
        ldb     <grounded
        pshs    a,b
        lda     <enemy_vy
        sta     <vy
        ldx     #ex
        inc     <idle_step
        jsr     actor_fall
        clr     <idle_step
        lda     <vy
        sta     <enemy_vy
        puls    a,b
        sta     <vy
        stb     <grounded
        puls    x
        ifne PRELOAD_ALL
        tst room8_forced
        bne enemy8_right
        endc
        ldu     #fratelli_zone8
        jsr     box_overlap
        bcc     enemy8_left
        lda     ,x
        anda    #$FE
        cmpa    <ex
        beq     enemy8_contact
        blo     enemy8_left
enemy8_right
        inc     <ex
        inc     <ex
        bra     enemy8_contact
enemy8_left
        dec     <ex
        dec     <ex
enemy8_contact
        jmp     enemy_contact

        endc

; $60B8 marks a player or enemy that enters the pit. The CoCo uses
; the shared death sequence and removes the Fratelli until room reset.
final_room_pit
        ifne PRELOAD_ALL
        lda     <room_bank
        cmpa    #ROOM6
        lbeq    room6_pit
        endc
        lda     <room_bank
        cmpa    #ROOM8
        bne     pit8_done
        ldu     #pit_zone8
        ldx     #px
        jsr     box_overlap
        bcc     pit8_second
        jsr     mark_death
pit8_second
        ldx     #p2x
        jsr     box_overlap
        bcc     pit8_enemy
        jsr     mark_death
pit8_enemy
        tst     <enemy_on
        beq     pit8_done
        ldx     #ex
        jsr     box_overlap
        bcc     pit8_done
        ifne PRELOAD_ALL
        jsr room8_enemy_hit
        else
        clr     <enemy_on
        endc
pit8_done
        rts


; Patches are the original Apple HGR gate stamps in GIME pixel order.
draw_final_gates
        lda     <room_bank
        cmpa    #ROOM8
        bne     final_gates_done
        jsr     map_terrain
        ldy     #TERRAIN+53*5+1
        lda     <gate_mask
        pshs    a
draw_gate8
        lsr     ,s
        bcs     draw_gate8_open
        ldu     ,y
        bra     draw_gate8_stamp
draw_gate8_open
        ldu     2,y
draw_gate8_stamp
        jsr     video_patch_run
        leay    4,y
        cmpy    #TERRAIN+53*5+13
        blo     draw_gate8
        leas    1,s
final_gates_done
        rts


; Overlay 1, actor type 5 at $60BD. Pick a Goonie on the same vertical
; band before following the home/away patrol. Use the room wall geometry.
first_room_enemy
        jsr     cash_tick
        clr     cash_grab
        lda     <ex
        cmpa    #230            ; Apple X=$86
        blo     first_enemy_watch
        tst     cash_low
        beq     first_enemy_watch
        inc     cash_grab
        tst     cash_phase
        bne     first_enemy_collect
        lda     cash_pose_phase
        eora    #1
        sta     cash_pose_phase
        lda     #$8C
        sta     cash_limit
first_enemy_collect
        lbra    first_enemy_contact
first_enemy_watch
        tst     cash_visible
        bne     first_enemy_distracted
        lda     <ey
        sta     <hazard_box+1
        adda    #16
        sta     <hazard_box+3
        clr     <hazard_box
        lda     #$FF
        sta     <hazard_box+2
        ldu     #hazard_box
        jsr     either_box
        bcc     first_enemy_patrol
        lda     ,x
        anda    #$FE
        bra     first_enemy_move
first_enemy_patrol
        dec     <enemy_wait
        bne     first_enemy_target
        lda     <enemy_patrol
        eora    #1
        sta     <enemy_patrol
        beq     first_enemy_home
        lda     #87             ; Apple X=$38
        sta     <enemy_target
        lda     #64
        bra     first_enemy_timer
first_enemy_home
        lda     #193
        sta     <enemy_target
        lda     #160
first_enemy_timer
        sta     <enemy_wait
first_enemy_target
        lda     <enemy_target
        bra     first_enemy_move
first_enemy_distracted
        lda     #237            ; Apple X=$8A
first_enemy_move
        anda    #$FE
        ldx     #ex
        cmpa    ,x
        beq     first_enemy_contact
        blo     first_enemy_left
        lda     ,x
        cmpa    #SPRITE_MAX_X
        bhs     first_enemy_contact
        adda    #2
        jsr     wall_right
        bra     first_enemy_contact
first_enemy_left
        lda     ,x
        beq     first_enemy_contact
        suba    #2
        jsr     wall_left
first_enemy_contact
        lda     <ex
        sta     <hazard_box
        adda    #14
        sta     <hazard_box+2
        lda     <ey
        adda    #2
        sta     <hazard_box+1
        adda    #6
        sta     <hazard_box+3
        ldu     #hazard_box
        jsr     either_box
        bcc     first_enemy_done
        jsr     mark_death
first_enemy_done
        rts


