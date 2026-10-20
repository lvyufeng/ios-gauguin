/* BSD <bsd/.../mode.h>: setmode()/getmode() as used by installfile. */
#pragma once
#include <sys/types.h>
void *setmode(const char *mode_str);
mode_t getmode(const void *set, mode_t mode);
