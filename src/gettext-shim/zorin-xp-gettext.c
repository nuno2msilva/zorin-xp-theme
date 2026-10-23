/*
 * Zorin XP — XP's names ("O meu computador", "Reciclagem") in Files and on
 * the desktop, without touching the system's translation catalogues.
 *
 * Loaded with LD_PRELOAD only in those programs. For the translation domains
 * in ZXP_GETTEXT_DOMAINS (separated by ":") it binds the catalogue to the
 * ZXP_LOCALEDIR folder (copies made by tools/setup/molocale.py), even if the
 * program asks for another folder. Then it removes these variables from the
 * environment, so the programs these ones open do not inherit it.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>

static char *(*real_bindtextdomain)(const char *, const char *);
static char localedir[4096];
static char domains[1024];

static int listed(const char *domain)
{
    size_t n;
    const char *p;

    if (!domain || !localedir[0])
        return 0;
    n = strlen(domain);
    for (p = domains; *p;) {
        const char *end = strchr(p, ':');
        size_t len = end ? (size_t)(end - p) : strlen(p);
        if (len == n && strncmp(p, domain, n) == 0)
            return 1;
        if (!end)
            break;
        p = end + 1;
    }
    return 0;
}

char *bindtextdomain(const char *domain, const char *dirname)
{
    if (!real_bindtextdomain)
        real_bindtextdomain = dlsym(RTLD_NEXT, "bindtextdomain");
    if (dirname && listed(domain))
        dirname = localedir;
    return real_bindtextdomain(domain, dirname);
}

__attribute__((constructor)) static void zxp_init(void)
{
    const char *dir = getenv("ZXP_LOCALEDIR");
    const char *list = getenv("ZXP_GETTEXT_DOMAINS");
    char copy[1024], *tok, *save = NULL;

    real_bindtextdomain = dlsym(RTLD_NEXT, "bindtextdomain");
    if (dir && list && strlen(dir) < sizeof(localedir) && strlen(list) < sizeof(domains)) {
        strcpy(localedir, dir);
        strcpy(domains, list);
        /* (domains the program never binds: they get bound here already) */
        strcpy(copy, list);
        for (tok = strtok_r(copy, ":", &save); tok; tok = strtok_r(NULL, ":", &save))
            real_bindtextdomain(tok, localedir);
    }
    unsetenv("LD_PRELOAD");
    unsetenv("ZXP_LOCALEDIR");
    unsetenv("ZXP_GETTEXT_DOMAINS");
}
