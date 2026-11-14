ROOM2   equ     ROOM+5
GATE2   equ     TERRAIN+31*5

room2_hazards
        lda     <room_bank
        cmpa    #ROOM2
        bne     room2_done
        ifne    PRELOAD_ALL
        jsr     update_motion2
        tst     <death
        bne     room2_done
        endc
        clr     <room2_mask
        ldu     #switches2+4
room2_switches
        jsr     point_either
        rol     <room2_mask
        leau    -2,u
        cmpu    #switches2
        bhs     room2_switches
        lda     <room2_open
        beq     room2_unlock
        cmpa    #4
        bhs     room2_gate
        inc     <room2_open
        bra     room2_gate
room2_unlock
        lda     <room2_mask
        cmpa    #3
        bne     room2_gate
        lda     #1
        sta     <room2_open
room2_gate
        lda     <room2_open
        bne     room2_gate_open
        lda     #1
        bra     room2_gate_write
room2_gate_open
        lda     #$7F
room2_gate_write
        sta     GATE2
        ldx     #trap_flags2
        ldb     <room2_mask
        leay    b,x
        ldu     #trap_zones2
room2_traps
        tst     ,y
        bmi     room2_trap_next
        jsr     either_box
        bcs     room2_lethal
room2_trap_next
        leay    8,y
        leau    4,u
        cmpu    #trap_zones2+12
        blo     room2_traps
        ifne    PRELOAD_ALL
        jmp     update_launcher
        endc
room2_done
        rts
room2_lethal
        jmp     mark_death

room2_exit
        lda     <room_bank
        cmpa    #ROOM2
        bne     room2_exit_allow
        tst     <room2_open
        beq     room2_exit_block
room2_exit_allow
        orcc    #1
        rts
room2_exit_block
        andcc   #$FE
        rts

draw_room2
        lda     <room_bank
        cmpa    #ROOM2
        bne     room2_done
        ifne    PRELOAD_ALL
        jsr     draw_motion2
        endc
        jsr     map_terrain
        ldx     #TERRAIN+33*5+1
        lda     <room2_mask
        lsla
        ldu     a,x
        jsr     video_patch_run
        ldx     #TERRAIN+33*5+1+16
        lda     <room2_open
        beq     room2_draw_closed
        inca
        lsla
        bra     room2_draw_door
room2_draw_closed
        lda     <room2_mask
        anda    #2
room2_draw_door
        ldu     a,x
        jmp     video_patch_run
