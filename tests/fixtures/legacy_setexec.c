/* SPDX-License-Identifier: MIT
 * Real Darwin SETEXEC lifetime check, confined to this test executable.
 * Host success does not qualify iOS jetsam enforcement; the old223 probe's
 * GET8/footprint checks must still pass on the phone before any GPU open.
 */
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern int posix_spawnattr_setjetsam_ext(posix_spawnattr_t *, short, int, int, int);
extern char **environ;

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--replacement")) {
        printf("replacement=%d\n", getpid());
        return 0;
    }
    if (argc != 1) return 2;
    printf("original=%d\n", getpid());
    fflush(stdout);
    posix_spawnattr_t attr;
    int rc = posix_spawnattr_init(&attr);
    if (!rc) rc = posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETEXEC);
    /* Host test uses band0; the iOS loader queries and retains its own band. */
    if (!rc) rc = posix_spawnattr_setjetsam_ext(&attr, 0x0c, 0, 128, 128);
    char *const replacement[] = {argv[0], "--replacement", NULL};
    if (!rc) rc = posix_spawn(NULL, argv[0], NULL, &attr, replacement, environ);
    fprintf(stderr, "SETEXEC unexpectedly returned rc=%d\n", rc);
    return 1;
}
