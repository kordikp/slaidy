#!/usr/bin/env python3
"""A window for SlAIdy, so it is an application rather than a browser.

    scripts/window.py http://localhost:8080/

GTK4 and WebKitGTK, both of which Ubuntu already has. No address bar, no tabs,
no browser: a window with the application's own icon that the dock files under
the application's own name, because its app id is the desktop entry's.

What it has to carry over from a browser window, and does:
  · full screen, which is the whole point of a presenter (F, or the page asking)
  · printing, which is how a PDF is made — the GTK dialog has Print to File
  · downloads, which is how markdown and bundles leave, into ~/Downloads
  · a real file dialog, because "save to a file" has to mean the file you point
    at. The File System Access API is Chrome's; this is the same thing done
    natively and handed to the page through a message channel.
  · the page's title, so the window and the dock say which deck this is

It falls back to the browser if any of this is missing; see studio.sh.
"""
import os, sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit, GLib, Gio  # noqa: E402

APP_ID = "io.github.kordikp.slaidy"


class Slaidy(Gtk.Application):
    def __init__(self, url):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.url = url

    def do_activate(self):
        win = Gtk.ApplicationWindow(application=self)
        win.set_default_size(1440, 900)
        win.set_title("SlAIdy")
        win.set_icon_name("slaidy")

        # ── the file dialog the page cannot open for itself ──────────────
        # The page asks through a message channel; the answer goes back as a
        # path, and the server writes it. That is the whole of Save As here:
        # the deck is a file the server owns, so the page never needs a handle.
        ucm = WebKit.UserContentManager()
        view = WebKit.WebView(user_content_manager=ucm)

        def reply(token, path):
            js = "window.__nativeFile && window.__nativeFile(%s, %s)" % (
                GLib.Variant("s", token).print_(False),
                GLib.Variant("s", path or "").print_(False))
            view.evaluate_javascript(js, -1, None, None, None, None, None)

        def on_message(_m, value):
            try:
                req = value.to_json(0)
            except Exception:
                return
            import json as _j
            try:
                req = _j.loads(req)
            except Exception:
                return
            token = req.get("token") or ""
            dlg = Gtk.FileDialog()
            dlg.set_title(req.get("title") or "Choose a file")
            if req.get("name"):
                dlg.set_initial_name(req["name"])
            filt = Gtk.FileFilter()
            filt.set_name("Deck (*.json)")
            filt.add_pattern("*.json")
            store = Gio.ListStore.new(Gtk.FileFilter)
            store.append(filt)
            dlg.set_filters(store)

            def done(d, res):
                try:
                    f = (d.save_finish(res) if req.get("mode") == "save"
                         else d.open_finish(res))
                    reply(token, f.get_path() if f else "")
                except Exception:
                    reply(token, "")
            if req.get("mode") == "save":
                dlg.save(win, None, done)
            else:
                dlg.open(win, None, done)

        ucm.register_script_message_handler("slaidy", None)
        ucm.connect("script-message-received::slaidy", on_message)
        st = view.get_settings()
        st.set_enable_developer_extras(True)
        st.set_enable_fullscreen(True)
        st.set_javascript_can_access_clipboard(True)
        st.set_enable_write_console_messages_to_stdout(False)
        # a cache that answers for the application is how you end up looking at
        # last week's; there is nothing here worth keeping anyway
        view.get_network_session().get_website_data_manager()
        view.load_uri(self.url)
        win.set_child(view)

        # the deck's name, in the window and in the dock
        view.connect("notify::title", lambda v, _:
                     win.set_title(v.get_title() or "SlAIdy"))

        # full screen: the page asks for it when you present
        view.connect("enter-fullscreen", lambda v: (win.fullscreen(), False)[1])
        view.connect("leave-fullscreen", lambda v: (win.unfullscreen(), False)[1])

        # printing is how a PDF is made
        def on_print(v, op):
            op.set_property("page-setup", op.get_page_setup())
            op.run_dialog(win)
            return True
        view.connect("print", on_print)

        # downloads go where downloads go
        def on_download(session, dl):
            def decide(d, suggested):
                out = os.path.join(GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_DOWNLOAD) or GLib.get_home_dir(), suggested)
                d.set_destination("file://" + out)
                return True
            dl.connect("decide-destination", decide)
        view.get_network_session().connect("download-started", on_download)

        # the keys a window is expected to have
        keys = Gtk.EventControllerKey()

        def on_key(_c, keyval, _code, state):
            ctrl = state & 4                      # Gdk.ModifierType.CONTROL_MASK
            if keyval == 0xFFC8:                  # F11
                (win.unfullscreen if win.is_fullscreen() else win.fullscreen)()
                return True
            if ctrl and keyval in (ord("q"), ord("Q")):
                win.close(); return True
            if ctrl and keyval in (ord("r"), ord("R")):
                view.reload_bypass_cache(); return True
            return False
        keys.connect("key-pressed", on_key)
        win.add_controller(keys)

        win.present()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/"
    GLib.set_prgname("slaidy")
    GLib.set_application_name("SlAIdy")
    sys.exit(Slaidy(url).run([]))


if __name__ == "__main__":
    main()
