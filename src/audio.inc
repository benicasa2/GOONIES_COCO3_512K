; AUDIO_DRIVER_TYPE=0 DAC or =1 original Tandy Speech/Sound Cartridge.
; Audio events run on the main thread and SSC bytes are serialized by FIRQ.
        ifeq AUDIO_DRIVER_TYPE
KEY_PORT_MODE equ $34

audio_init
        lda     #$34            ; analog mux select 00: internal DAC
        sta     $FF01
        sta     $FF03
        lda     #$3C            ; enable analog audio via PIA1 CB2
        sta     $FF23
        clr     $FF21
        lda     $FF20
        ora     #$FC            ; bits 2..7 output, preserve bits 0..1 DDR
        sta     $FF20
        lda     #4
        sta     $FF21
        lda     $FF20
        anda    #3
        sta     <length         ; low bits preserved for DAC writes
        ora     #$80
        sta     $FF20
        lda     #$60
        sta     INIT1
        lda     #$7C
        sta     INIT0
        ldd     #446            ; ~8 kHz, timer overhead depends on GIME rev
        stb     TIMER_L
        sta     TIMER_H
        lda     #$20
        sta     FIRQEN
        rts

audio_frame
        jsr     music_tick
        ldd     <music_note+2
        std     <pitch2
        tst     <ssc_ptr
        beq     dac_music
        dec     <ssc_ptr
        bne     dac_frame_done
dac_music
        ldd     <music_note
        std     <pitch
dac_frame_done
        rts

audio_event
        pshs    cc
        orcc    #$50
        ldd     #3604           ; 440 Hz at nominal 8 kHz
        cmpx    #speech_jump
        bne     dac_note
        ldd     #5407           ; 660 Hz
dac_note
        std     <pitch
        lda     #8
        sta     <ssc_ptr
        puls    cc,pc

sample_firq
        pshs    a,b
        lda     FIRQEN
        lda     #$80
        sta     <sample_mix
        ldd     <pitch
        beq     dac_second
        addd    <phase
        std     <phase
        lda     #$EC
        tst     <phase
        bpl     dac_mix_first
        lda     #$14
dac_mix_first
        adda    <sample_mix
        sta     <sample_mix
dac_second
        ldd     <pitch2
        beq     dac_out
        addd    <phase2
        std     <phase2
        lda     #$E4
        tst     <phase2
        bpl     dac_mix_second
        lda     #$1C
dac_mix_second
        adda    <sample_mix
        sta     <sample_mix
dac_out
        lda     <sample_mix
        ora     <length
        sta     $FF20
        puls    a,b
        rti

speech_actor
        fcb 0
speech_jump
        fcb 0

        else
KEY_PORT_MODE equ $3C

SSC_RST equ     $FF7D
SSC_IO  equ     $FF7E

audio_init
        lda     #1
        sta     SSC_RST
        clr     SSC_RST
        lda     #$34
        sta     $FF01
        lda     #$3C            ; analog mux 10: sound from cartridge
        sta     $FF03
        sta     $FF23
        lda     #$7C
        sta     INIT0
        lda     #$40            ; slow clock (~15.7 kHz), task 0
        sta     INIT1
        lda     #10             ; ~1.4 kHz service, no busy loop
        sta     TIMER_L
        clr     TIMER_H
        lda     #$20
        sta     FIRQEN
        ldx     #startup_ay
        stx     <ssc_ptr
        lda     #12
        sta     <length
        rts

audio_frame
        jsr     ssc_music_tick
        ldd     <ssc_ptr
        bne     ssc_frame_done
        tst     <length
        beq     ssc_music
        dec     <length
        bne     ssc_frame_done
        inc     <music_dirty
ssc_music
        tst     <music_dirty
        beq     ssc_frame_done
        clr     <music_dirty
        ldx     #ssc_packet
        lda     #$AF
        sta     ,x+
        ldu     #music_note
        ldy     #ssc_periods
        clrb
ssc_channel
        pshs    b
        lda     ,u+
        lsla
        ldd     a,y
        pshs    a
        lda     1,s
        std     ,x++
        inca
        ldb     ,s+
        std     ,x++
        lda     ,s
        lsra
        adda    #8
        clrb
        tst     -1,u
        beq     ssc_level
        ldb     #6
ssc_level
        std     ,x++
        puls    b
        addb    #2
        cmpb    #6
        blo     ssc_channel
        lda     #$FF
        sta     ,x
        ldx     #ssc_packet
        stx     <ssc_ptr
ssc_frame_done
        rts

; The IRQ reads a compressed note event from the invisible bitmap padding.
ssc_music_tick
        tst     <music_ticks
        beq     ssc_music_read
        dec     <music_ticks
        bne     ssc_tick_done
ssc_music_read
        lda     MMU3
        pshs    a
        ldx     <music_ptr
        bne     ssc_music_map
ssc_music_restart
        ldx     #$7800
        lda     #19
        sta     <music_note+3
        clr     <music_note
        clr     <music_note+1
        clr     <music_note+2
ssc_music_map
        lda     <music_note+3
        sta     MMU3
        lda     ,x+
        beq     ssc_music_restart
        cmpa    #1
        bne     ssc_music_event
        ldx     #$7800
        lda     <music_note+3
        cmpa    #19
        bne     ssc_music_last
        lda     #34
        bra     ssc_music_next
ssc_music_last
        lda     #3
ssc_music_next
        sta     <music_note+3
        bra     ssc_music_map
ssc_music_event
        tfr     a,b
        lsra
        lsra
        lsra
        sta     <music_ticks
        lsla
        adda    <music_ticks
        sta     <music_ticks
        andb    #7
        beq     ssc_music_saved
        ldu     #music_note
ssc_note_loop
        lsrb
        bcc     ssc_note_skip
        lda     ,x+
        sta     ,u
ssc_note_skip
        leau    1,u
        cmpu    #music_note+3
        blo     ssc_note_loop
        inc     <music_dirty
ssc_music_saved
        stx     <music_ptr
        puls    a
        sta     MMU3
ssc_tick_done
        rts

ssc_install_music
        pshs    cc,a,b,x,y,u
        orcc    #$50
        lda     MMU2
        pshs    a
        ldx     #$6000
        ldu     #ssc_music_banks
ssc_copy_bank
        lda     ,u+
        sta     MMU2
        ldy     #$5800
ssc_copy_byte
        lda     ,x+
        sta     ,y+
        cmpy    #$6000
        blo     ssc_copy_byte
        cmpu    #ssc_music_banks+3
        blo     ssc_copy_bank
        puls    a
        sta     MMU2
        puls    cc,a,b,x,y,u,pc
ssc_music_banks
        fcb     19,34,3

ssc_packet equ $13C0
ssc_packet_end equ ssc_packet+20

audio_event
        pshs    cc
        orcc    #$50
        ldd     <ssc_ptr
        bne     ssc_event_done  ; discard events while transmitting a command
        stx     <ssc_ptr
        lda     #12
        sta     <length
ssc_event_done
        puls    cc,pc

sample_firq
        pshs    a,x
        lda     FIRQEN
        ldx     <ssc_ptr
        beq     ssc_done
        tst     SSC_IO          ; bit 7 active-low BUSY*, high = ready
        bpl     ssc_done
        cmpx    #ssc_packet_end
        beq     ssc_end
        lda     ,x+
        cmpx    #ssc_packet+1
        blo     ssc_check_marker
        cmpx    #ssc_packet_end
        bls     ssc_send
ssc_check_marker
        cmpa    #$FE            ; local end marker (never sent)
        beq     ssc_end
ssc_send
        sta     SSC_IO
        stx     <ssc_ptr
        bra     ssc_done
ssc_end
        clr     <ssc_ptr
        clr     <ssc_ptr+1
ssc_done
        puls    a,x
        rti

; AF followed by AY register/value pairs and FF to leave direct mode.
startup_ay
        fcb $AF,7,$38,8,0,9,0,10,0,$FF,$FE
speech_actor
        fcb $AF,0,155,1,0,8,5,$FF,$B0,21,20,17,15,4,$FF,$F0,$FE ; Data
speech_jump
        fcb $AF,0,106,1,0,8,5,$FF,$B0,10,15,16,9,4,$FF,$F0,$FE  ; jump

        endc





; DAC 60 Hz sequencer. Only IRQ writes this state.
        ifeq AUDIO_DRIVER_TYPE
music_tick
        tst     <music_ticks
        beq     music_read
        dec     <music_ticks
        bne     music_done
music_read
        ldx     <music_ptr
        bne     music_fetch
music_restart
        ldx     #music_notes
music_fetch
        lda     ,x+
        beq     music_restart
        sta     <music_ticks
        ldy     #music_periods
        lda     ,x+
        ldd     a,y
        std     <music_note
        lda     ,x+
        ldd     a,y
        std     <music_note+2
        inc     <music_dirty
        stx     <music_ptr
music_done
        rts
        endc
