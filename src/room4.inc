        ifne PRELOAD_ALL
; Disk BASIC reserves this area before LOADM. It stays mapped during play.
        org     $1700
        include "room4_data.inc"
ROOM4 equ ROOM+15
ROOM4_GRAPH equ ROOM+39
room4_branches equ $6F0D

room4_state fdb $6100
room4_mask fcb 0
room4_steps fcb 3
room4_count fcb 6
room4_flash fcb 0
room4_old fdb 0,0

reset_room4
        ldd     #$6100
        std     room4_state
        clr     room4_mask
        ldd     #$0306
        std     room4_steps
        clr     room4_flash
        jmp     reset_room4_particles

update_room4
        lda     <room_bank
        cmpa    #ROOM4
        lbne    room4_done
        jsr     update_room4_particles
        lbsr    room4_map_state
        ldb     4,x
        beq     room4_default
        lda     #3
        mul
        ldu     #room4_branches
        leau    d,u
        lda     ,u+
        bita    room4_mask
        bne     room4_edge
room4_default
        leau    2,x
room4_edge
        ldd     ,u
        pshs    a
        anda    #$9F
        ora     #$60
        std     room4_state
        tst     room4_flash
        beq     room4_event
        dec     room4_flash
room4_event
        puls    a
        bita    #$40
        beq     room4_right_end
        tst     room4_steps
        beq     room4_contacts
        dec     room4_steps
        jsr     score_room4_step
        bra     room4_contacts
room4_right_end
        bita    #$20
        beq     room4_contacts
        inc     room4_count
        lda     room4_count
        cmpa    #7
        blo     room4_contacts
        clr     room4_count
        lda     #6
        sta     room4_flash
        lda     #5
        sta     particle_spawn
room4_contacts
        clr     room4_mask
        ldu     #room4_switches+4
room4_switch
        jsr     point_either
        rol     room4_mask
        leau    -2,u
        cmpu    #room4_switches
        bhs     room4_switch
        ldu     #room4_bumper
        jsr     either_box
        bcc     room4_floor
        lda     #8
        ora     room4_mask
        sta     room4_mask
room4_floor
        jsr     map_terrain
        lda     #3
        tst     room4_steps
        bne     room4_store_floor
        lda     #$7F
room4_store_floor
        sta     TERRAIN+16*5
room4_done
        rts

room4_switches
        fcb 162,31,162,71,162,111
room4_bumper
        fcb 146,174,146,188

room4_page
        ldx     #room4_old
        lda     <back
        cmpa    #FB0
        beq     room4_page_done
        leax    2,x
room4_page_done
        rts

restore_room4
        lda     <room_bank
        cmpa    #ROOM4
        lbne    room4_done
        bsr     room4_page
        ldd     ,x
        bsr     room4_rect
        jsr     restore_row
        jmp     restore_room4_particles

draw_room4
        lda     <room_bank
        cmpa    #ROOM4
        lbne    room4_done
        lda     #ROOM4_GRAPH
        sta     MMU3
        lda     #27
        bsr     room4_patch
        lda     room4_mask
        lsra
        lsra
        lsra
        adda    #8
        bsr     room4_patch
        lda     room4_steps
        adda    #10
        bsr     room4_patch
        lda     room4_count
        ldb     room4_flash
        beq     room4_draw_counter
        tfr     b,a
        adda    #6
room4_draw_counter
        adda    #14
        bsr     room4_patch
        lda     room4_mask
        anda    #7
        bsr     room4_patch
        bsr     room4_map_state
        ldy     ,x
        bsr     room4_page
        sty     ,x
        tfr     y,d
        bsr     room4_rect
        lda     #ROOM4_GRAPH
        sta     MMU3
        ldu     #room4_sprite
        jsr     draw_row
        jmp     draw_room4_particles

room4_patch
        lsla
        ldx     #$64A0
        ldu     a,x
        jmp     video_patch_run

room4_map_state
        ldd     room4_state
        anda    #$7F
        tfr     d,x
        lda     #ROOM+29
        tst     room4_state
        bpl     room4_state_bank
        adda    #5
room4_state_bank
        sta     MMU3
        rts

room4_rect
        jsr     rect_start
        lda     #6
        sta     <rows
        rts
        include "room4_rewards.inc"

; Install the Room 5 code after the final Disk BASIC LOADM has returned.
install_room5
        lda     #ROOM5_ART
        sta     MMU3
        ldu     #room5_code
        ldd     ,u++
        ldx     #$0D00
install_room5_byte
        pshs    a
        lda     ,u+
        sta     ,x+
        puls    a
        subd    #1
        bne     install_room5_byte
        rts
        org $1D00
install_room6
        ; FB1 is invisible during BASIC/title. Reclaim $3C/$3E after EXEC.
        lda #$0E
        ldb #ROOM7_ART
        ldy #$5E00
        bsr install_native_partial
        lda #$0D
        ldb #ROOM6_ART
        bsr install_native_bank
        lda #$0C
        ldb #NATIVE_BANK
        bsr install_native_bank
        lda #ROOM6_ART
        sta MMU3
        ldu #room6_code
        ldd ,u++
        ldx #$1400
        jsr install_room5_byte
        ldu #$7000
        ldd ,u++
        ldx #$0400
        jsr install_room5_byte
        lda #ROOM+8
        sta MMU2
        ldx #$5800
        lda #ROOM8_ART
        sta MMU3
        jsr decode_bank
        lda #ROOM+13
        sta MMU2
        ldx #$5800
        ldy #$7000
        jsr title_token
        lda #FB0
        sta <back
        jmp restore_title
install_native_bank
        ldy #$6000
install_native_partial
        sta MMU2
        stb MMU3
        ldx #$4000
        ldu #$6000
install_native_word
        ldd ,x++
        std ,u++
        pshs y
        cmpx ,s++
        blo install_native_word
        rts
        endc

