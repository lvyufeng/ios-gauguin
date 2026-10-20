/*
 * get_word() and get_rest() from xnu SETUP/config/main.c (the helpers
 * mkmakefile.c calls); the native xconfig.c provides main() itself.
 */
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include "config.h"
#ifndef PSEUDO_DEVICE
#define PSEUDO_DEVICE 4
#endif
extern struct file_list *ftab, *conf_list, **confp;
extern struct opt *opt, *mkopt, *opt_tail, *mkopt_tail;
extern struct device *dtab;
extern char errbuf[80];
extern int yyline;

extern char *build_directory;
extern const char *object_directory;

const char *
get_word(FILE *fp)
{
	static char line[80];
	int ch;
	char *cp;

	while ((ch = getc(fp)) != EOF) {
		if (ch != ' ' && ch != '\t') {
			break;
		}
	}
	if (ch == EOF) {
		return (char *)EOF;
	}
	if (ch == '\n') {
		return NULL;
	}
	if (ch == '|') {
		return "|";
	}
	cp = line;
	*cp++ = ch;
	while ((ch = getc(fp)) != EOF) {
		if (isspace(ch)) {
			break;
		}
		*cp++ = ch;
	}
	*cp = 0;
	if (ch == EOF) {
		return (char *)EOF;
	}
	(void) ungetc(ch, fp);
	return line;
}

/*
 * get_rest
 *	returns EOF on end of file
 *	NULL on end of line
 *	pointer to the word otherwise
 */
char *
get_rest(FILE *fp)
{
	static char line[80];
	int ch;
	char *cp;

	cp = line;
	while ((ch = getc(fp)) != EOF) {
		if (ch == '\n') {
			break;
		}
		*cp++ = ch;
	}
	*cp = 0;
	if (ch == EOF) {
		return (char *)EOF;
	}
	return line;
}

/*
 * prepend the path to a filename
 */
char *
path(const char *file)
{
	char *cp;

	cp = malloc((unsigned)(strlen(build_directory) +
	    strlen(file) +
	    strlen(object_directory) +
	    3));
	(void) sprintf(cp, "%s/%s/%s", object_directory, build_directory, file);
	return cp;
}

/* ns() from parser.y */
char *
ns(const char *str)
{
	register char *cp;

	cp = malloc((unsigned)(strlen(str)+1));
	(void) strcpy(cp, str);
	return (cp);
}

/* newdev()/init_dev() from parser.y */
static struct device *curp;
void
newdev(struct device *dp)
{
	register struct device *np;

	np = (struct device *) malloc(sizeof *np);
	*np = *dp;
	if (curp == 0)
		dtab = np;
	else
		curp->d_next = np;
	curp = np;
	curp->d_next = 0;
}
init_dev(struct device *dp)
{

	dp->d_name = "OHNO!!!";
	dp->d_type = PSEUDO_DEVICE;
	dp->d_flags = 0;
	dp->d_slave = UNKNOWN;
	dp->d_init = 0;
}
