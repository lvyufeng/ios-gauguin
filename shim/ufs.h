#pragma once
void test_ufs(void);
/* userdata bounds found by test_ufs() (0, 0 if the GPT was not read). */
void ufs_userdata_range(uint32_t *first, uint32_t *last);
/* write "SHIMRST" + imem/pshold/seq into the last block of userdata. */
uint32_t ufs_write_reason(uint32_t imem, uint32_t pshold, uint32_t seq);
