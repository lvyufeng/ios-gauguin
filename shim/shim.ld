ENTRY(_head)
SECTIONS
{
	. = 0;
	.text : { *(.text.head) *(.text*) }
	.rodata : { *(.rodata*) }
	.data : { *(.data*) }
	. = ALIGN(16);
	_bss_start = .;
	.bss : { *(.bss*) *(COMMON) }
	. = ALIGN(16);
	_bss_end = .;
	/*
	 * MMU page tables (shim/mmu.c). The addresses must stay < 1 MB so
	 * ADRP+ADD (imm12 x 4K, image < 1 MB) reaches them from start.S.
	 */
	. = ALIGN(0x4000);
	.pt (NOLOAD) : {
		/* Actual array sizes (mmu.c): 512 + 2048 + 2048 + 2*2048 entries
		 * of 8 bytes. Reserving 2048 tables each made the Image 136 MB
		 * (ABL copies image_size bytes and stopped booting it). */
		pt_l1 = .; . += 0x1000;
		pt_l2lo = .; . += 0x4000;
		pt_l2hi = .; . += 0x4000;
		pt_l3 = .; . += 0x4000 * 2;
	}
	. = ALIGN(16);
	_stack_top = .;
	. += 0x8000;
	. = ALIGN(4096);
	_sec_stacks = .;
	. += 8 * 0x1000;
	_end = .;
	/DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
