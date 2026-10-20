/*
 * xnu's SETUP/installfile, reimplemented for a Linux build host.
 * Same command line (-c, -S, -m MODE, SRCs DST) and semantics: files are
 * compared and only rewritten when the content differs, the mode is applied
 * to new files (-c: only when created). Uses plain POSIX + compat.c.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <err.h>
#include <sysexits.h>
#include <fcntl.h>
#include <sys/stat.h>
#include "mode.h"

int
main(int argc, char *argv[])
{
	int ch, only_changed = 0;
	void *mset = NULL;
	mode_t mode = 0;
	int rc = 0;
	char *src = NULL, *dst = NULL;
	char tmp[1024];

	while ((ch = getopt(argc, argv, "cSm:")) != -1) {
		switch (ch) {
		case 'c': only_changed = 1; break;
		case 'S': break;
		case 'm': mset = setmode(optarg); break;
		default: return EX_USAGE;
		}
	}
	argc -= optind; argv += optind;
	if (argc < 2) {
		return EX_USAGE;
	}
	dst = argv[argc - 1];
	for (int i = 0; i < argc - 1; i++) {
		src = argv[i];
		if (mset) {
			mode = getmode(mset, 0);
		}
		/* compare */
		struct stat ss, ds;
		if (stat(src, &ss) != 0) {
			err(EX_NOINPUT, "%s", src);
			rc = EX_NOINPUT;
			continue;
		}
		if (stat(dst, &ds) == 0 && S_ISREG(ds.st_mode) &&
		    ds.st_size == ss.st_size) {
			FILE *a = fopen(src, "rb"), *b = fopen(dst, "rb");
			int same = a && b;
			while (same) {
				int ca = fgetc(a), cb = fgetc(b);
				if (ca != cb) {
					same = 0;
				}
				if (ca == EOF) {
					break;
				}
			}
			if (a) {
				fclose(a);
			}
			if (b) {
				fclose(b);
			}
			if (same) {
				if (!only_changed && mset) {
					chmod(dst, mode & 07777);
				}
				continue;
			}
		}
		snprintf(tmp, sizeof(tmp), "%s.__installfile__", dst);
		unlink(tmp);
		FILE *in = fopen(src, "rb"), *out = fopen(tmp, "wb");
		if (!in || !out) {
			err(EX_OSERR, "%s", tmp);
			rc = EX_OSERR;
			continue;
		}
		char buf[65536];
		size_t n;
		while ((n = fread(buf, 1, sizeof(buf), in)) > 0) {
			if (fwrite(buf, 1, n, out) != n) {
				err(EX_OSERR, "write");
				rc = EX_OSERR;
			}
		}
		fclose(in);
		fclose(out);
		if (mset) {
			/* -c: the mode is for new files; the umask must not decide */
			chmod(tmp, mode & 07777);
		}
		if (rename(tmp, dst) != 0) {
			err(EX_OSERR, "rename %s", dst);
			rc = EX_OSERR;
		}
	}
	return rc;
}
