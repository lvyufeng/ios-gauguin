/*
 * Native (Linux) driver for xnu's SETUP/config generators, used by the
 * CMake port (xnu-port). Same sources (mkmakefile.c, mkheaders.c,
 * mkioconf.c, searchp.c); only the input path differs: the doconf port has
 * already resolved MASTER into the final `config` file, so instead of the
 * lex/yacc front end this reads that file and builds the opt/device lists
 * the generators consume.
 *
 * usage: xconfig -c SRCDIR -o OBJDIR CONFIG_FILE
 *   SRCDIR       xnu source root (contains osfmk/conf, bsd/conf, ...)
 *   OBJDIR       per-component object dir (%<dir> terminations are appended)
 *   CONFIG_FILE  config.<KERNEL>_<ARCH>_<MACHINE> written by doconf
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
#ifndef PSEUDO_DEVICE
#define PSEUDO_DEVICE 4
#endif

extern void mkioconf(void);
extern void makefile(void);
extern void headers(void);

int profiling;
char *build_directory;
const char *source_directory = "..";
const char *object_directory = "..";
const char *machinename = "arm64";

/* state the generators share (normally defined by externs.c) */
struct opt *opt, *mkopt, *opt_tail, *mkopt_tail;
struct device *dtab;
struct file_list *ftab, *conf_list, **confp;
char errbuf[80];

static struct opt *
add_opt(const char *name, const char *value, int mk)
{
	struct opt *op = calloc(1, sizeof(*op));
	op->op_name = strdup(name);
	op->op_value = value ? strdup(value) : NULL;
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
	const char *cfg = NULL;
	char line[8192];

	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "-c") && i + 1 < argc) {
			config_directory = argv[++i];
			source_directory = argv[i];
		} else if (!strcmp(argv[i], "-d") && i + 1 < argc) {
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
		fprintf(stderr, "usage: xconfig -c SRCDIR -o OBJDIR CONFIG_FILE\n");
		return 1;
	}
	if (!config_directory) {
		static char cd[4096];
		snprintf(cd, sizeof(cd), "%s/osfmk/conf", source_directory);
		config_directory = cd;
	}
	FILE *in = fopen(cfg, "r");
	if (!in) {
		perror(cfg);
		return 2;
	}
	int nopt = 0, ndev = 0;
	while (fgets(line, sizeof(line), in)) {
		char *p = line;
		while (*p == ' ' || *p == '\t') {
			p++;
		}
		p[strcspn(p, "\n")] = 0;
		if (!strncmp(p, "options", 7) || !strncmp(p, "makeoptions", 11)) {
			int mk = p[0] == 'm';
			char *v = p + (mk ? 11 : 7);
			while (*v == ' ' || *v == '\t') {
				v++;
			}
			char *name = strtok(v, " \t=");
			char *val = NULL;
			if (name) {
				char *eq = strchr(v, '=');
				val = eq ? eq + 1 : NULL;
				add_opt(name, val, mk);
				nopt++;
			}
		} else if (!strncmp(p, "pseudo-device", 13)) {
			char *v = p + 13;
			while (*v == ' ' || *v == '\t') {
				v++;
			}
			char *name = strtok(v, " \t");
			if (!name) {
				continue;
			}
			struct device *dp = calloc(1, sizeof(*dp));
			dp->d_type = PSEUDO_DEVICE;
			dp->d_name = strdup(name);
			char *tok = strtok(NULL, " \t");
			while (tok) {
				if (!strncmp(tok, "init", 4)) {
					char *init = strtok(NULL, " \t");
					if (init) {
						dp->d_init = strdup(init);
					}
				}
				tok = strtok(NULL, " \t");
			}
			dp->d_next = dtab;
			dtab = dp;
			ndev++;
		}
	}
	fclose(in);
	fprintf(stderr, "xconfig: %d options, %d pseudo-devices from %s\n", nopt, ndev, cfg);
	mkioconf();
	makefile();
	headers();
	return 0;
}
