/* SPDX-License-Identifier: MIT */
#import <Foundation/Foundation.h>
#import <mach/mach_time.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

enum { max_plist_bytes = 256 * 1024, max_records = 4096, deadline_seconds = 8 };
static const char icon_state[] = "/private/var/mobile/Library/SpringBoard/IconState.plist";
static const char system_version[] = "/System/Library/CoreServices/SystemVersion.plist";
static const char core_services[] = "/System/Library/Frameworks/CoreServices.framework/CoreServices";

static void timeout(int signal_number)
{
    (void)signal_number;
    _exit(124);
}

static NSDictionary *read_plist(const char *path)
{
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
    if (fd < 0)
        return nil;

    struct stat before, after;
    NSDictionary *result = nil;
    if (fstat(fd, &before) == 0 && S_ISREG(before.st_mode) &&
        before.st_size > 0 && before.st_size <= max_plist_bytes) {
        NSMutableData *bytes = [NSMutableData dataWithLength:(NSUInteger)before.st_size];
        ssize_t size = pread(fd, bytes.mutableBytes, bytes.length, 0);
        if (size == before.st_size && fstat(fd, &after) == 0 &&
            after.st_size == before.st_size &&
            after.st_mtimespec.tv_sec == before.st_mtimespec.tv_sec &&
            after.st_mtimespec.tv_nsec == before.st_mtimespec.tv_nsec) {
            id value = [NSPropertyListSerialization propertyListWithData:bytes
                options:NSPropertyListImmutable format:NULL error:NULL];
            if ([value isKindOfClass:NSDictionary.class])
                result = value;
        }
    }
    close(fd);
    return result;
}

struct layout {
    NSUInteger pages;
    NSUInteger dock;
    NSUInteger strings;
    NSUInteger records;
};

static BOOL count_slots(id entries, struct layout *layout)
{
    if (![entries isKindOfClass:NSArray.class] ||
        [entries count] > max_records - layout->strings - layout->records)
        return NO;
    for (id entry in entries) {
        if ([entry isKindOfClass:NSString.class] && [entry length] > 0)
            ++layout->strings;
        else if ([entry isKindOfClass:NSDictionary.class])
            ++layout->records;
        else
            return NO;
    }
    return YES;
}

static BOOL layout_counts(NSDictionary *plist, struct layout *result)
{
    id pages = plist[@"iconLists"];
    id dock = plist[@"buttonBar"];
    struct layout layout = {0};
    if (![pages isKindOfClass:NSArray.class] || [pages count] > max_records ||
        !count_slots(dock, &layout))
        return NO;
    layout.pages = [pages count];
    layout.dock = [dock count];
    for (id page in pages) {
        if (!count_slots(page, &layout))
            return NO;
    }
    *result = layout;
    return YES;
}

static BOOL matches_object_getter(Class cls, SEL selector)
{
    Method method = cls ? class_getInstanceMethod(cls, selector) : NULL;
    return method && strcmp(method_getTypeEncoding(method), "@16@0:8") == 0;
}

@interface NSObject (GauguinRegistrationGetters)
+ (id)defaultWorkspace;
- (id)allApplications;
- (id)applicationIdentifier;
@end

static int filesystem_snapshot(void)
{
    struct statfs filesystem;
    if (statfs("/private/var", &filesystem) != 0) {
        puts("GAUGUIN DESKTOP_STATE v1 state=var-unavailable");
        return 1;
    }
    const char *type = strcmp(filesystem.f_fstypename, "hfs") == 0 ? "hfs" :
        strcmp(filesystem.f_fstypename, "apfs") == 0 ? "apfs" :
        strcmp(filesystem.f_fstypename, "tmpfs") == 0 ? "tmpfs" : "other";
    struct statfs root;
    int root_mount = statfs("/", &root) == 0 ?
        memcmp(&filesystem.f_fsid, &root.f_fsid, sizeof(root.f_fsid)) == 0 : -1;
    printf("GAUGUIN DESKTOP_STATE v1 state=var fs=%s readonly=%d root_mount=%d tick=%llu\n",
        type, !!(filesystem.f_flags & MNT_RDONLY), root_mount, mach_absolute_time());

    NSDictionary *plist = read_plist(icon_state);
    struct layout layout;
    if (!layout_counts(plist, &layout)) {
        puts("GAUGUIN DESKTOP_STATE v1 state=layout-unavailable");
        return 1;
    }
    printf("GAUGUIN DESKTOP_STATE v1 state=layout pages=%lu dock=%lu string_slots=%lu opaque_slots=%lu tick=%llu\n",
        (unsigned long)layout.pages, (unsigned long)layout.dock,
        (unsigned long)layout.strings, (unsigned long)layout.records, mach_absolute_time());
    return 0;
}

static int registration_snapshot(void)
{
    if (!dlopen(core_services, RTLD_LAZY | RTLD_LOCAL)) {
        puts("GAUGUIN DESKTOP_STATE v1 state=coreservices-unavailable");
        return 1;
    }
    Class workspace_class = objc_lookUpClass("LSApplicationWorkspace");
    Class proxy_class = objc_lookUpClass("LSApplicationProxy");
    if (!matches_object_getter(object_getClass(workspace_class), @selector(defaultWorkspace)) ||
        !matches_object_getter(workspace_class, @selector(allApplications)) ||
        !matches_object_getter(proxy_class, @selector(applicationIdentifier))) {
        puts("GAUGUIN DESKTOP_STATE v1 state=unexpected-abi");
        return 1;
    }
    id workspace = [workspace_class defaultWorkspace];
    id apps = [workspace isKindOfClass:workspace_class] &&
        matches_object_getter(object_getClass(workspace), @selector(allApplications)) ?
        [workspace allApplications] : nil;
    if (![apps isKindOfClass:NSArray.class] || [apps count] > max_records) {
        puts("GAUGUIN DESKTOP_STATE v1 state=registration-unavailable");
        return 1;
    }
    BOOL settings = NO, safari = NO;
    NSUInteger unreadable = 0;
    for (id app in apps) {
        if (![app isKindOfClass:proxy_class] ||
            !matches_object_getter(object_getClass(app), @selector(applicationIdentifier))) {
            ++unreadable;
            continue;
        }
        id identifier = [app applicationIdentifier];
        if (![identifier isKindOfClass:NSString.class]) {
            ++unreadable;
            continue;
        }
        settings |= [identifier isEqualToString:@"com.apple.Preferences"];
        safari |= [identifier isEqualToString:@"com.apple.mobilesafari"];
    }
    printf("GAUGUIN DESKTOP_STATE v1 state=registration applications=%lu unreadable=%lu settings=%d safari=%d tick=%llu\n",
        (unsigned long)[apps count], (unsigned long)unreadable, settings, safari, mach_absolute_time());
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 2 || getuid() != 501 || geteuid() != 501)
        return 64;
    BOOL filesystem = strcmp(argv[1], "--filesystem") == 0;
    if (!filesystem && strcmp(argv[1], "--registration") != 0)
        return 64;
    setvbuf(stdout, NULL, _IONBF, 0);
    struct sigaction action = {.sa_handler = timeout};
    if (sigemptyset(&action.sa_mask) != 0 || sigaction(SIGALRM, &action, NULL) != 0)
        return 70;
    alarm(deadline_seconds);
    @autoreleasepool {
        NSDictionary *version = read_plist(system_version);
        if (![@"20H392" isEqual:version[@"ProductBuildVersion"]])
            return 65;
        mach_timebase_info_data_t timebase;
        if (mach_timebase_info(&timebase) != KERN_SUCCESS || !timebase.denom)
            return 70;
        printf("GAUGUIN DESKTOP_STATE v1 state=begin mode=%s tick=%llu numer=%u denom=%u\n",
            filesystem ? "filesystem" : "registration", mach_absolute_time(), timebase.numer, timebase.denom);
        return filesystem ? filesystem_snapshot() : registration_snapshot();
    }
}
