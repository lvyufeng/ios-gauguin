/* Linux stand-in for <uuid/uuid.h> (the host tools only need the type). */
#pragma once
#include <stdint.h>
typedef struct { uint8_t b[16]; } uuid_t;
