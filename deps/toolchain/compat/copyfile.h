/* Linux stand-in for <copyfile.h>: the xnu SETUP host tools only need
 * fcopyfile() with COPYFILE_ALL | COPYFILE_UNLINK semantics for new files. */
#pragma once
#include <stdint.h>
#include <sys/types.h>
/* Darwin copyfile.h pulls in the BSD mode API (setmode/getmode). */
#include "mode.h"
typedef void *copyfile_state_t;
typedef uint32_t copyfile_flags_t;
#define COPYFILE_ACL        (1 << 0)
#define COPYFILE_STAT       (1 << 1)
#define COPYFILE_XATTR      (1 << 2)
#define COPYFILE_DATA       (1 << 3)
#define COPYFILE_SECURITY   (COPYFILE_STAT | COPYFILE_ACL)
#define COPYFILE_METADATA   (COPYFILE_SECURITY | COPYFILE_XATTR)
#define COPYFILE_ALL        (COPYFILE_METADATA | COPYFILE_DATA)
#define COPYFILE_UNLINK     (1 << 15)
int fcopyfile(int from_fd, int to_fd, copyfile_state_t state, copyfile_flags_t flags);
copyfile_state_t copyfile_state_alloc(void);
void copyfile_state_free(copyfile_state_t);
