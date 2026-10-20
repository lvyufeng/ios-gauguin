/* Darwin libc pieces the xnu SETUP host tools use but glibc lacks. */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/stat.h>
#include "copyfile.h"
#include "mode.h"
#include <stdint.h>

/* ---- setmode/getmode (BSD tzsetwall-style mode strings) ---- */
static const int rwx_bits[3][3] = {
	/* u */ { 0400, 0200, 0100 },
	/* g */ { 0040, 0020, 0010 },
	/* o */ { 0004, 0002, 0001 },
};

void *
setmode(const char *p)
{
	mode_t *m;
	int who[3] = { 0, 0, 0 };   /* u, g, o selected by this clause */
	int nwho = 0;
	int i;

	if (!p) {
		return NULL;
	}
	m = calloc(1, sizeof(*m));
	if (!m) {
		return NULL;
	}
	while (*p) {
		mode_t add = 0, clr = 0;
		int op = '=';
		nwho = 0;
		if (*p >= '0' && *p <= '7') {
			/* octal mode: like BSD setmode, return the value as the handle */
			while (*p >= '0' && *p <= '7') {
				*m = (mode_t)((*m << 3) | (mode_t)(*p - '0'));
				p++;
			}
		}
		for (; *p == 'u' || *p == 'g' || *p == 'o' || *p == 'a'; p++) {
			if (*p == 'a') {
				who[nwho++] = 0; who[nwho++] = 1; who[nwho++] = 2;
				break;
			}
			who[nwho++] = (*p == 'u') ? 0 : (*p == 'g') ? 1 : 2;
		}
		if (nwho == 0) {
			who[nwho++] = 0; who[nwho++] = 1; who[nwho++] = 2;
		}
		for (;;) {
			mode_t bits = 0, special = 0;
			if (*p == '+' || *p == '-' || *p == '=') {
				op = *p++;
			}
			for (; *p && *p != ','; p++) {
				int c = *p;
				int kind = (c == 'r') ? 0 : (c == 'w') ? 1 : (c == 'x' || c == 'X') ? 2 : -1;
				if (kind == 2 && c == 'X') {
					continue;
				}
				if (kind >= 0) {
					for (i = 0; i < nwho; i++) {
						bits |= rwx_bits[who[i]][kind];
					}
				} else if (c == 's') {
					for (i = 0; i < nwho; i++) {
						special |= (who[i] == 0) ? 04000 : (who[i] == 1) ? 02000 : 0;
					}
				} else if (c == 't') {
					special |= 01000;
				}
			}
			bits |= special;
			if (op == '+') {
				add |= bits;
			} else if (op == '-') {
				clr |= bits;
			} else {
				*m = (mode_t)(*m & ~(bits & 0777));
				add |= bits;
			}
			if (*p == ',') {
				p++;
				break;
			}
			if (!*p) {
				break;
			}
		}
		*m = (mode_t)((*m | add) & ~clr);
	}
	return m;
}

mode_t
getmode(const void *set, mode_t mode)
{
	if (!set) {
		return 0;
	}
	return *(const mode_t *)set | (mode & 07777);
}


static char progname_buf[256];

const char *
getprogname(void)
{
	if (!progname_buf[0]) {
		FILE *f = fopen("/proc/self/comm", "r");
		if (f && fgets(progname_buf, sizeof(progname_buf), f)) {
			const char *slash = strrchr(progname_buf, '/');
			if (slash) {
				memmove(progname_buf, slash + 1, strlen(slash));
			}
			progname_buf[strcspn(progname_buf, "\n")] = 0;
		} else {
			snprintf(progname_buf, sizeof(progname_buf), "xnu-tool");
		}
		if (f) {
			fclose(f);
		}
	}
	return progname_buf;
}

unsigned long
mach_vm_round_page(unsigned long x)
{
	return (x + 4095UL) & ~4095UL;
}

int
uuid_generate(void *out)
{
	FILE *f = fopen("/dev/urandom", "rb");
	size_t n = 0;
	if (f) {
		n = fread(out, 1, 16, f);
		fclose(f);
	}
	return n == 16 ? 0 : -1;
}

const char *
proc_pidpath(int pid, void *buffer, unsigned int buffersize)
{
	(void)pid;
	(void)buffer;
	(void)buffersize;
	return NULL;
}

void *
copyfile_state_alloc(void)
{
	return calloc(1, 8);
}

void
copyfile_state_free(void *state)
{
	free(state);
}

int
fcopyfile(int from_fd, int to_fd, copyfile_state_t state, copyfile_flags_t flags)
{
	char buf[65536];
	ssize_t n;
	(void)state;
	while ((n = read(from_fd, buf, sizeof(buf))) > 0) {
		ssize_t off = 0;
		while (off < n) {
			ssize_t w = write(to_fd, buf + off, (size_t)(n - off));
			if (w < 0) {
				return -1;
			}
			off += w;
		}
	}
	if (n < 0) {
		return -1;
	}
	if (flags & COPYFILE_DATA) {
		/* mode is copied by the caller for new files; nothing else to do */
	}
	return 0;
}
