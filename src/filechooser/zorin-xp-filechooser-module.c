/*
 * Zorin XP — XP's "Abrir"/"Guardar como" also in the applications that make
 * GTK 3's file chooser themselves (GtkFileChooserDialog: Electron apps such
 * as VS Code, ONLYOFFICE, ...), which never ask the desktop portal.
 *
 * A GTK 3 module (GTK3_MODULES: GTK 2 and 4 do not read it). When such a
 * dialog is about to show, it stays hidden: the same question goes to the
 * portal's FileChooser (the theme's XP dialog, zorin-xp-filechooser) with
 * the dialog's action, title, folder, name and filters, and the answer comes
 * back as the dialog's own: the files chosen are what the application reads
 * from it (gtk_file_chooser_get_files and the rest), the filter chosen is
 * set, and the dialog responds with the application's own accept (or
 * cancel) button. If the portal does not answer, GTK's dialog shows as
 * before.
 *
 * Built at install time with only the C library's headers (the GLib/GTK
 * declarations it needs are below), linked against the installed
 * libraries: no development packages needed.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef unsigned long GType;
typedef void *gpointer;
typedef const void *gconstpointer;
typedef int gboolean;
typedef char gchar;
typedef int gint;
typedef unsigned int guint;
typedef unsigned long gulong;
typedef unsigned long gsize;
typedef struct _GSList { gpointer data; struct _GSList *next; } GSList;
typedef struct _GError { guint domain; gint code; gchar *message; } GError;
typedef void (*GCallback)(void);
typedef void (*GDestroyNotify)(gpointer);
typedef gpointer (*GCopyFunc)(gconstpointer, gpointer);

/* GLib, GObject, GIO */
extern void g_signal_override_class_handler(const gchar *, GType, GCallback);
extern void g_signal_chain_from_overridden_handler(gpointer, ...);
extern guint g_signal_lookup(const gchar *, GType);
extern gulong g_signal_handler_find(gpointer, int, guint, guint, gpointer, gpointer, gpointer);
extern void g_signal_handler_block(gpointer, gulong);
extern void g_signal_handler_unblock(gpointer, gulong);
extern gulong g_signal_connect_data(gpointer, const gchar *, GCallback, gpointer, GDestroyNotify, int);
extern gpointer g_object_get_data(gpointer, const gchar *);
extern void g_object_set_data_full(gpointer, const gchar *, gpointer, GDestroyNotify);
extern gpointer g_object_ref(gpointer);
extern void g_object_unref(gpointer);
extern gpointer g_type_class_ref(GType);
extern gpointer g_type_interface_peek(gpointer, GType);
extern const gchar *g_type_name(GType);
extern const gchar *g_get_prgname(void);
extern gchar *g_strdup_printf(const gchar *, ...);
extern void g_free(gpointer);
extern void g_error_free(GError *);
extern GSList *g_slist_prepend(GSList *, gpointer);
extern GSList *g_slist_reverse(GSList *);
extern void g_slist_free(GSList *);
extern void g_slist_free_full(GSList *, GDestroyNotify);
extern GSList *g_slist_copy_deep(GSList *, GCopyFunc, gpointer);
extern gpointer g_bus_get_sync(int, gpointer, GError **);
extern const gchar *g_dbus_connection_get_unique_name(gpointer);
extern guint g_dbus_connection_signal_subscribe(gpointer, const gchar *, const gchar *, const gchar *,
                                                const gchar *, const gchar *, int,
                                                void (*)(gpointer, const gchar *, const gchar *, const gchar *,
                                                         const gchar *, gpointer, gpointer),
                                                gpointer, GDestroyNotify);
extern void g_dbus_connection_signal_unsubscribe(gpointer, guint);
extern void g_dbus_connection_call(gpointer, const gchar *, const gchar *, const gchar *, const gchar *,
                                   gpointer, gconstpointer, int, gint, gpointer,
                                   void (*)(gpointer, gpointer, gpointer), gpointer);
extern gpointer g_dbus_connection_call_finish(gpointer, gpointer, GError **);
extern gpointer g_variant_new(const gchar *, ...);
extern gpointer g_variant_new_string(const gchar *);
extern gpointer g_variant_new_boolean(gboolean);
extern gpointer g_variant_new_bytestring(const gchar *);
extern gpointer g_variant_builder_new(gconstpointer);
extern void g_variant_builder_add(gpointer, const gchar *, ...);
extern void g_variant_builder_add_value(gpointer, gpointer);
extern gpointer g_variant_builder_end(gpointer);
extern void g_variant_builder_unref(gpointer);
extern void g_variant_get(gpointer, const gchar *, ...);
extern gpointer g_variant_lookup_value(gpointer, const gchar *, gconstpointer);
extern gpointer g_variant_get_child_value(gpointer, gsize);
extern gsize g_variant_n_children(gpointer);
extern const gchar *g_variant_get_string(gpointer, gsize *);
extern void g_variant_unref(gpointer);
extern gpointer g_file_new_for_uri(const gchar *);
extern gpointer g_file_get_parent(gpointer);
extern gchar *g_file_get_path(gpointer);

/* GTK 3 */
extern GType gtk_dialog_get_type(void);
extern GType gtk_file_chooser_dialog_get_type(void);
extern GType gtk_file_chooser_get_type(void);
extern int gtk_file_chooser_get_action(gpointer);
extern gchar *gtk_file_chooser_get_current_folder(gpointer);
extern gchar *gtk_file_chooser_get_current_name(gpointer);
extern gboolean gtk_file_chooser_get_select_multiple(gpointer);
extern GSList *gtk_file_chooser_list_filters(gpointer);
extern gpointer gtk_file_chooser_get_filter(gpointer);
extern void gtk_file_chooser_set_filter(gpointer, gpointer);
extern gpointer gtk_file_filter_to_gvariant(gpointer);
extern const gchar *gtk_file_filter_get_name(gpointer);
extern const gchar *gtk_window_get_title(gpointer);
extern gpointer gtk_window_get_transient_for(gpointer);
extern gpointer gtk_widget_get_window(gpointer);
extern void gtk_widget_show(gpointer);
extern void gtk_dialog_response(gpointer, gint);
extern gpointer gtk_dialog_get_widget_for_response(gpointer, gint);

enum { ACTION_OPEN, ACTION_SAVE, ACTION_SELECT_FOLDER, ACTION_CREATE_FOLDER };
enum { RESPONSE_REJECT = -2, RESPONSE_ACCEPT = -3, RESPONSE_OK = -5, RESPONSE_CANCEL = -6,
       RESPONSE_CLOSE = -7, RESPONSE_YES = -8, RESPONSE_NO = -9, RESPONSE_APPLY = -10 };
#define BUS_SESSION 2
#define PORTAL "org.freedesktop.portal.Desktop"
#define PORTAL_PATH "/org/freedesktop/portal/desktop"

/* GtkFileChooserIface (GTK 3, unchanged since 2.x): GTypeInterface (two
   GTypes) then the methods; set_current_folder is the 1st, get_current_folder
   the 2nd, get_files the 9th */
#define IFACE_SET_CURRENT_FOLDER (2 * sizeof(GType) + 0 * sizeof(gpointer))
#define IFACE_GET_CURRENT_FOLDER (2 * sizeof(GType) + 1 * sizeof(gpointer))
#define IFACE_GET_FILES (2 * sizeof(GType) + 8 * sizeof(gpointer))
typedef gboolean (*SetFolderFn)(gpointer, gpointer, GError **);
typedef GSList *(*GetFilesFn)(gpointer);
typedef gpointer (*GetFolderFn)(gpointer);
static SetFolderFn orig_set_current_folder;
static GetFilesFn orig_get_files;
static GetFolderFn orig_get_current_folder;

static int debug;
#define DBG(...) do { if (debug) fprintf(stderr, "zorin-xp-filechooser-module: " __VA_ARGS__); } while (0)

static gpointer bus;
static guint serial;

typedef struct {
    gpointer dialog;
    guint subscription;
    int action;
} Pending;

/* ------------------------------------------------- what the app reads */
static GSList *zxp_get_files(gpointer chooser)
{
    GSList *ours = g_object_get_data(chooser, "zxp-files");
    if (ours)
        return g_slist_copy_deep(ours, (GCopyFunc)g_object_ref, NULL);
    return orig_get_files(chooser);
}

/* the folder the app asks for (GTK sets its own only after looking it up,
   later: the portal needs it now) */
static gboolean zxp_set_current_folder(gpointer chooser, gpointer file, GError **error)
{
    g_object_set_data_full(chooser, "zxp-asked-folder", file ? g_object_ref(file) : NULL,
                           file ? g_object_unref : NULL);
    return orig_set_current_folder(chooser, file, error);
}

static gpointer zxp_get_current_folder(gpointer chooser)
{
    gpointer folder = g_object_get_data(chooser, "zxp-folder");
    if (folder)
        return g_object_ref(folder);
    return orig_get_current_folder(chooser);
}

static void free_files(gpointer list)
{
    g_slist_free_full(list, g_object_unref);
}

/* ------------------------------------------------------ the answer */
static gint first_response(gpointer dialog, const gint *ids, gint fallback)
{
    for (; *ids; ids++)
        if (gtk_dialog_get_widget_for_response(dialog, *ids))
            return *ids;
    return fallback;
}

static void finish(Pending *p, guint response, gpointer results)
{
    static const gint accept[] = {RESPONSE_ACCEPT, RESPONSE_OK, RESPONSE_YES, RESPONSE_APPLY, 0};
    static const gint cancel[] = {RESPONSE_CANCEL, RESPONSE_CLOSE, RESPONSE_NO, RESPONSE_REJECT, 0};
    gpointer dialog = p->dialog;
    gboolean ok = 0;

    if (p->subscription)
        g_dbus_connection_signal_unsubscribe(bus, p->subscription);
    g_object_set_data_full(dialog, "zxp-pending", NULL, NULL);

    if (response == 0 && results) {
        gpointer uris = g_variant_lookup_value(results, "uris", "as");
        GSList *files = NULL;
        gsize i, n = uris ? g_variant_n_children(uris) : 0;
        for (i = 0; i < n; i++) {
            gpointer v = g_variant_get_child_value(uris, i);
            files = g_slist_prepend(files, g_file_new_for_uri(g_variant_get_string(v, NULL)));
            g_variant_unref(v);
        }
        if (uris)
            g_variant_unref(uris);
        files = g_slist_reverse(files);
        DBG("%lu file(s)\n", (unsigned long)n);
        if (files) {
            ok = 1;
            g_object_set_data_full(dialog, "zxp-files", files, free_files);
            /* (the folder: the one chosen, or the one the chosen file is in) */
            gpointer folder = p->action == ACTION_SELECT_FOLDER || p->action == ACTION_CREATE_FOLDER
                ? g_object_ref(files->data) : g_file_get_parent(files->data);
            g_object_set_data_full(dialog, "zxp-folder", folder, folder ? g_object_unref : NULL);
            /* the filter chosen, by its name */
            gpointer cur = g_variant_lookup_value(results, "current_filter", "(sa(us))");
            if (cur) {
                const gchar *name = NULL;
                gpointer rules = NULL;
                g_variant_get(cur, "(&s@a(us))", &name, &rules);
                GSList *l, *filters = gtk_file_chooser_list_filters(dialog);
                for (l = filters; l; l = l->next) {
                    const gchar *fname = gtk_file_filter_get_name(l->data);
                    if (fname && name && strcmp(fname, name) == 0) {
                        gtk_file_chooser_set_filter(dialog, l->data);
                        break;
                    }
                }
                g_slist_free(filters);
                if (rules)
                    g_variant_unref(rules);
                g_variant_unref(cur);
            }
        }
    }
    /* GtkFileChooserDialog's own "response" handler (the first one connected,
       when the dialog is made) stops an accept when its hidden chooser has
       nothing chosen: it stays blocked while the answer goes out */
    gulong check = g_signal_handler_find(dialog, 1 /* G_SIGNAL_MATCH_ID */,
                                         g_signal_lookup("response", gtk_dialog_get_type()),
                                         0, NULL, NULL, NULL);
    DBG("answer %s, blocking handler %lu\n", ok ? "accept" : "cancel", check);
    if (check)
        g_signal_handler_block(dialog, check);
    gtk_dialog_response(dialog, ok ? first_response(dialog, accept, RESPONSE_ACCEPT)
                                   : first_response(dialog, cancel, RESPONSE_CANCEL));
    if (check)
        g_signal_handler_unblock(dialog, check);
    g_object_unref(dialog);
    free(p);
}

static void on_response(gpointer conn, const gchar *sender, const gchar *path, const gchar *iface,
                        const gchar *signal, gpointer params, gpointer data)
{
    Pending *p = data;
    guint response = 2;
    gpointer results = NULL;
    (void)conn; (void)sender; (void)path; (void)iface; (void)signal;
    g_variant_get(params, "(u@a{sv})", &response, &results);
    DBG("Response %u\n", response);
    finish(p, response, results);
    if (results)
        g_variant_unref(results);
}

/* the portal did not take the question: GTK's own dialog, as before */
static void fall_back(Pending *p)
{
    gpointer dialog = p->dialog;
    if (p->subscription)
        g_dbus_connection_signal_unsubscribe(bus, p->subscription);
    g_object_set_data_full(dialog, "zxp-pending", NULL, NULL);
    g_object_set_data_full(dialog, "zxp-gtk", (gpointer)1, NULL);
    gtk_widget_show(dialog);
    g_object_unref(dialog);
    free(p);
}

static void on_called(gpointer conn, gpointer res, gpointer data)
{
    GError *err = NULL;
    gpointer reply = g_dbus_connection_call_finish(conn, res, &err);
    if (!reply) {
        fprintf(stderr, "zorin-xp-filechooser-module: %s; GTK's dialog\n", err ? err->message : "?");
        if (err)
            g_error_free(err);
        fall_back(data);
        return;
    }
    g_variant_unref(reply);
}

/* ------------------------------------------------------ the question */
static const gchar *parent_window(gpointer dialog)
{
    static gchar buf[64];
    static unsigned long (*xid)(gpointer);
    gpointer parent = gtk_window_get_transient_for(dialog);
    gpointer win = parent ? gtk_widget_get_window(parent) : NULL;
    buf[0] = 0;
    if (!win)
        return buf;
    if (!xid)
        xid = (unsigned long (*)(gpointer))dlsym(RTLD_DEFAULT, "gdk_x11_window_get_xid");
    /* (only on X11: the instance's class gives its type) */
    if (xid && strcmp(g_type_name(**(GType **)win), "GdkX11Window") == 0)
        snprintf(buf, sizeof buf, "x11:%lx", xid(win));
    return buf;
}

static gboolean ask_portal(gpointer dialog)
{
    gint action = gtk_file_chooser_get_action(dialog);
    const gchar *title = gtk_window_get_title(dialog);
    gchar *token, *path, *sender;
    const gchar *unique;
    Pending *p;
    gpointer opts, filters;
    GSList *l, *list;

    if (!bus) {
        bus = g_bus_get_sync(BUS_SESSION, NULL, NULL);
        if (!bus)
            return 0;
    }
    unique = g_dbus_connection_get_unique_name(bus);
    if (!unique)
        return 0;

    token = g_strdup_printf("zxp%d_%u", (int)getpid(), ++serial);
    sender = g_strdup_printf("%s", unique + 1);         /* ":1.42" -> "1_42" */
    for (gchar *c = sender; *c; c++)
        if (*c == '.')
            *c = '_';
    path = g_strdup_printf(PORTAL_PATH "/request/%s/%s", sender, token);

    p = calloc(1, sizeof *p);
    p->dialog = g_object_ref(dialog);
    p->action = action;
    p->subscription = g_dbus_connection_signal_subscribe(bus, PORTAL, "org.freedesktop.portal.Request",
                                                         "Response", path, NULL, 0, on_response, p, NULL);
    g_object_set_data_full(dialog, "zxp-pending", (gpointer)1, NULL);

    opts = g_variant_builder_new("a{sv}");
    g_variant_builder_add(opts, "{sv}", "handle_token", g_variant_new_string(token));
    g_variant_builder_add(opts, "{sv}", "modal", g_variant_new_boolean(1));
    if (action == ACTION_SELECT_FOLDER || action == ACTION_CREATE_FOLDER)
        g_variant_builder_add(opts, "{sv}", "directory", g_variant_new_boolean(1));
    if (action == ACTION_OPEN)
        g_variant_builder_add(opts, "{sv}", "multiple",
                              g_variant_new_boolean(gtk_file_chooser_get_select_multiple(dialog)));
    list = gtk_file_chooser_list_filters(dialog);
    if (list) {
        filters = g_variant_builder_new("a(sa(us))");
        for (l = list; l; l = l->next)
            g_variant_builder_add_value(filters, gtk_file_filter_to_gvariant(l->data));
        g_variant_builder_add(opts, "{sv}", "filters", g_variant_builder_end(filters));
        g_variant_builder_unref(filters);
        g_slist_free(list);
        gpointer cur = gtk_file_chooser_get_filter(dialog);
        if (cur)
            g_variant_builder_add(opts, "{sv}", "current_filter", gtk_file_filter_to_gvariant(cur));
    }
    gchar *folder = gtk_file_chooser_get_current_folder(dialog);
    if (!folder && g_object_get_data(dialog, "zxp-asked-folder"))
        folder = g_file_get_path(g_object_get_data(dialog, "zxp-asked-folder"));
    if (folder) {
        g_variant_builder_add(opts, "{sv}", "current_folder", g_variant_new_bytestring(folder));
        g_free(folder);
    }
    if (action == ACTION_SAVE) {
        gchar *name = gtk_file_chooser_get_current_name(dialog);
        if (name && *name)
            g_variant_builder_add(opts, "{sv}", "current_name", g_variant_new_string(name));
        g_free(name);
    }

    DBG("asking the portal (action %d), waiting on %s\n", action, path);
    g_dbus_connection_call(bus, PORTAL, PORTAL_PATH, "org.freedesktop.portal.FileChooser",
                           action == ACTION_SAVE ? "SaveFile" : "OpenFile",
                           g_variant_new("(ssa{sv})", parent_window(dialog), title ? title : "", opts),
                           "(o)", 0, 10000, NULL, on_called, p);   /* (no answer in 10 s: GTK's) */
    g_variant_builder_unref(opts);
    g_free(token);
    g_free(sender);
    g_free(path);
    return 1;
}

/* GtkFileChooserDialog::show — instead of showing, ask the portal */
static void on_show(gpointer dialog, gpointer data)
{
    (void)data;
    if (g_object_get_data(dialog, "zxp-gtk")) {
        g_signal_chain_from_overridden_handler(dialog);
        return;
    }
    if (g_object_get_data(dialog, "zxp-pending"))
        return;
    /* (a dialog shown again: its earlier answer does not count) */
    g_object_set_data_full(dialog, "zxp-files", NULL, NULL);
    g_object_set_data_full(dialog, "zxp-folder", NULL, NULL);
    if (!ask_portal(dialog))
        g_signal_chain_from_overridden_handler(dialog);
}

/* ------------------------------------------------------------ start */
static gboolean excluded(void)
{
    /* the portal's own dialogs (it would ask itself) and anything that says so */
    static const char *names[] = {"xdg-desktop-portal-gtk", "xdg-desktop-portal-gnome",
                                  "zorin-xp-filechooser", NULL};
    const gchar *prg = g_get_prgname();
    if (getenv("ZXP_FILECHOOSER_MODULE_OFF"))
        return 1;
    for (int i = 0; prg && names[i]; i++)
        if (strcmp(prg, names[i]) == 0)
            return 1;
    return 0;
}

__attribute__((visibility("default"))) void gtk_module_init(gint *argc, gchar ***argv)
{
    (void)argc; (void)argv;
    if (excluded())
        return;
    GType type = gtk_file_chooser_dialog_get_type();
    gpointer klass = g_type_class_ref(type);
    char *iface = g_type_interface_peek(klass, gtk_file_chooser_get_type());
    if (!iface)
        return;
    SetFolderFn *set_folder = (SetFolderFn *)(iface + IFACE_SET_CURRENT_FOLDER);
    GetFilesFn *files = (GetFilesFn *)(iface + IFACE_GET_FILES);
    GetFolderFn *folder = (GetFolderFn *)(iface + IFACE_GET_CURRENT_FOLDER);
    if (!*set_folder || !*files || !*folder)
        return;
    debug = getenv("ZXP_FILECHOOSER_MODULE_DEBUG") != NULL;
    orig_set_current_folder = *set_folder;
    orig_get_files = *files;
    orig_get_current_folder = *folder;
    *set_folder = zxp_set_current_folder;
    *files = zxp_get_files;
    *folder = zxp_get_current_folder;
    g_signal_override_class_handler("show", type, (GCallback)on_show);
}
