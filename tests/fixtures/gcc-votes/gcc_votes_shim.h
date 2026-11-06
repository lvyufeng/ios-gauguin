#ifndef GCC_VOTES_SHIM_H
#define GCC_VOTES_SHIM_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef uint32_t vm_prot_t;
typedef uint32_t ppnum_t;
typedef int boolean_t;
#define PAGE_SHIFT 14
#define VM_PROT_READ 1u
#define VM_PROT_WRITE 2u
int ml_get_interrupts_enabled(void);
int ml_at_interrupt_context(void);
int get_preemption_level(void);
boolean_t pmap_valid_page(ppnum_t);
unsigned int pmap_cache_attributes(ppnum_t);
vm_offset_t ml_io_map_with_prot(vm_offset_t,vm_size_t,vm_prot_t);
vm_offset_t ml_vtophys(vm_offset_t);
uint32_t ggv_test_read(vm_offset_t,uint32_t);
void ggv_test_write(vm_offset_t,uint32_t,uint32_t);
#endif
