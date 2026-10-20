/* Darwin's <libc.h> on Linux: the standard headers plus the BSD additions
 * the xnu SETUP host tools rely on (declared here, defined in compat.c). */
#pragma once
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/param.h>
#include <sys/mman.h>
#include <sys/file.h>
#include <sys/queue.h>
#include "mode.h"
#ifndef MAXPATHLEN
#define MAXPATHLEN 1024
#endif
const char *getprogname(void);
int proc_pidpath(int pid, void *buffer, unsigned int buffersize);
