/* Zorin XP — gravação do arranque: o ffmpeg (kmsgrab) abre /dev/dri/cardN, e
 * quem abre o dispositivo quando ninguém o controla fica "master" — o que
 * impediria o Plymouth ou o Xorg de o controlar. Este LD_PRELOAD larga o
 * controlo logo a seguir a abrir; para ler o ecrã não é preciso. */
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
