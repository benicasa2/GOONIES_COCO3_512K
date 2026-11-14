; Apple II $0951, table $001D, 11 entries
; X = 6809 table base. B = first free index, or 11 if full.
; Carry clear means free. A holds the entry last read.
find_free_slot
        clrb
scan_free_slot
        lda     b,x
        beq     slot_free
        incb
        cmpb    #11
        blo     scan_free_slot
        orcc    #1
        rts
slot_free
        andcc   #$FE
        rts
