/*
 * Helpers from xnu SETUP/config/main.c and parser.y that the generators
 * call; the native xconfig.c provides main().
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "config.h"
#ifndef PSEUDO_DEVICE
#define PSEUDO_DEVICE 4
#endif

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
char *
ns(const char *str)
{
	register char *cp;

	cp = malloc((unsigned)(strlen(str)+1));
	(void) strcpy(cp, str);
	return (cp);
}

/* init_dev() from parser.y */
void
init_dev(struct device *dp)
{
	dp->d_name = "OHNO!!!";
	dp->d_type = PSEUDO_DEVICE;
	dp->d_flags = 0;
	dp->d_slave = UNKNOWN;
	dp->d_init = 0;
}
