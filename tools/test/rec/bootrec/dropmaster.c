/* Zorin XP — boot recording: ffmpeg (kmsgrab) opens /dev/dri/cardN, and
 * whoever opens the device when nobody controls it becomes "master" — which
 * would stop Plymouth or Xorg from controlling it. This LD_PRELOAD drops the
 * control right after opening; reading the screen does not need it. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/types.h>

#define DRM_IOCTL_DROP_MASTER _IO('d', 0x1f)

static void drop(const char *path, int fd)
{
    if (fd >= 0 && path && strncmp(path, "/dev/dri/card", 13) == 0)
        ioctl(fd, DRM_IOCTL_DROP_MASTER, 0);
}

#define WRAP(name, ...)                                                   \
    {                                                                     \
        static int (*real)() = 0;                                         \
        mode_t mode = 0;                                                  \
        if (flags & (O_CREAT | __O_TMPFILE)) {                            \
            va_list ap; va_start(ap, flags); mode = va_arg(ap, int); va_end(ap); \
        }                                                                 \
        if (!real) real = dlsym(RTLD_NEXT, name);                         \
        int fd = real(__VA_ARGS__, mode);                                 \
        drop(path, fd);                                                   \
        return fd;                                                        \
    }

int open(const char *path, int flags, ...) WRAP("open", path, flags)
int open64(const char *path, int flags, ...) WRAP("open64", path, flags)
int openat(int dir, const char *path, int flags, ...) WRAP("openat", dir, path, flags)
int openat64(int dir, const char *path, int flags, ...) WRAP("openat64", dir, path, flags)
