/*
 * Native (Linux) driver for xnu's SETUP/config generators, used by the
 * CMake port. Same generators (mkmakefile.c, mkheaders.c, mkioconf.c,
 * searchp.c, openp.c); only the input path differs: doconf.py has already
 * resolved MASTER into the final `config` file, so this reads that file
 * instead of running the lex/yacc front end (which needs Darwin headers).
 *
 *   xconfig CONFIG_FILE     (-c SRCDIR / -o OBJDIR optional)
 *     reads CONFIG_FILE (from doconf), sets build_directory to its parent
 *     directory (path() then yields "%s/%s/%s" = OBJDIR/config.<name>/...),
 *     then runs mkioconf(), makefile() and headers() in that directory.
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libgen.h>
#include "config.h"

extern void mkioconf(void);
extern void makefile(void);
extern void headers(void);
extern char *path(const char *file);

#ifndef PSEUDO_DEVICE
#define PSEUDO_DEVICE 4
#endif

/* normally in externs.c, but the generators are linked without it */
int profiling;
char *build_directory;
const char *source_directory = "..";
const char *object_directory = "..";
const char *machinename = "arm64";
struct opt *opt, *mkopt, *opt_tail, *mkopt_tail;
struct device *dtab;
struct file_list *ftab, *conf_list, **confp;
char errbuf[80];
int yyline;

static struct device *curdev;

void
newdev(struct device *dp)
{
	struct device *np = calloc(1, sizeof(*np));
	*np = *dp;
	if (curdev == NULL) {
		dtab = np;
	} else {
		curdev->d_next = np;
	}
	curdev = np;
}

static struct opt *
add_opt(const char *name, const char *value, int mk)
{
	struct opt *op = calloc(1, sizeof(*op));
	op->op_name = (char *)name;
	op->op_value = value ? (char *)value : NULL;
	if (mk) {
		if (!mkopt) {
			mkopt = op;
		} else {
			mkopt_tail->op_next = op;
		}
		mkopt_tail = op;
	} else {
		if (!opt) {
			opt = op;
		} else {
			opt_tail->op_next = op;
		}
		opt_tail = op;
	}
	return op;
}

int
main(int argc, char *argv[])
{
	char *cfg = NULL, *dir = NULL;
	const char *conf_dir = NULL;
	char line[8192];

	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "-c") && i + 1 < argc) {
			conf_dir = argv[++i];
		} else if (!strcmp(argv[i], "-d") && i + 1 < argc) {
			source_directory = argv[++i];
		} else if (0) {
			source_directory = argv[++i];
		} else if (!strcmp(argv[i], "-o") && i + 1 < argc) {
			object_directory = argv[++i];
		} else if (!strcmp(argv[i], "-p")) {
			profiling++;
		} else {
			cfg = argv[i];
		}
	}
	if (!cfg) {
		fprintf(stderr, "usage: xconfig -c SRCDIR CONFIG_FILE\n");
		return 1;
	}
	/* run in the component object dir, one level below the config file's
	 * directory: the file name carries the kernel name (config.DEVELOPMENT_ARM64)
	 * and the component is named by the -c / conf template directory. */
	{
		static char dirbuf[8192];
		char *copy = strdup(cfg);
		char *parent = strdup(dirname(copy));
		char *conf = strdup(conf_dir ? conf_dir : ".");
		/* <tree>/<component>/conf -> component */
		char *slash = strrchr(conf, '/');
		if (slash) {
			*slash = 0;
		}
		char *comp = strdup(basename(conf));
		free(copy);
		snprintf(dirbuf, sizeof(dirbuf), "%s/%s", parent, comp);
		dir = dirbuf;
	}
	/* -c SRCDIR names the source tree; its <component>/conf holds the
	 * templates (<SRCDIR>/conf when the call site already points at conf). */
	config_directory = (char *)(conf_dir ? conf_dir : "..");
	if (chdir(dir) != 0) {
		perror(dir);
		return 2;
	}
	build_directory = ".";
	object_directory = dir;
	machinename = "arm64";

	FILE *in = fopen(cfg, "r");
	if (!in) {
		perror(cfg);
		return 2;
	}
	int nopt = 0, ndev = 0;
	while (fgets(line, sizeof(line), in)) {
		char *p = line, *tok;
		while (*p == ' ' || *p == '\t') {
			p++;
		}
		p[strcspn(p, "\r\n")] = 0;
		if (!strncmp(p, "options", 7) || !strncmp(p, "makeoptions", 11)) {
			int mk = p[0] == 'm';
			char *v = p + (mk ? 11 : 7), *eq;
			while (*v == ' ' || *v == '\t') {
				v++;
			}
			eq = strchr(v, '=');
			if (eq) {
				*eq = 0;
				add_opt(strdup(v), strdup(eq + 1), mk);
			} else if ((tok = strtok(v, " \t")) != NULL) {
				add_opt(strdup(tok), NULL, mk);
			}
			nopt++;
		} else if (!strncmp(p, "pseudo-device", 13)) {
			char *v = p + 13;
			struct device dp;
			memset(&dp, 0, sizeof(dp));
			while (*v == ' ' || *v == '\t') {
				v++;
			}
			if ((tok = strtok(v, " \t")) == NULL) {
				continue;
			}
			dp.d_type = PSEUDO_DEVICE;
			dp.d_name = strdup(tok);
			while ((tok = strtok(NULL, " \t")) != NULL) {
				if (!strcmp(tok, "init")) {
					char *init = strtok(NULL, " \t");
					if (init) {
						dp.d_init = strdup(init);
					}
				}
			}
			newdev(&dp);
			ndev++;
		}
	}
	fclose(in);
	fprintf(stderr, "xconfig: %d options, %d pseudo-devices (%s)\n", nopt, ndev, dir);
	confp = &conf_list;
	mkioconf();
	makefile();
	headers();
	return 0;
}
