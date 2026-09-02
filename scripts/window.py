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
from gi.repository import Gtk, WebKit, GLib, Gio, Gdk, GObject  # noqa: E402

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

        # ── and the clipboard the page cannot always read for itself ─────
        # WebKit answers navigator.clipboard.readText() with nothing in this
        # window, and does not raise a paste event outside a text field, so
        # Ctrl-V on a slide list had no clipboard to read. The window reads
        # and writes it through GDK and hands the text across the same channel.
        def clip_reply(token, text):
            js = "window.__nativeClip && window.__nativeClip(%s, %s)" % (
                GLib.Variant("s", token).print_(False),
                GLib.Variant("s", text or "").print_(False))
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
            mode = req.get("mode") or ""
            if mode == "clip-read":
                try:
                    cb = Gdk.Display.get_default().get_clipboard()
                    def got(c, res):
                        try:
                            clip_reply(token, c.read_text_finish(res) or "")
                        except Exception:
                            clip_reply(token, "")
                    cb.read_text_async(None, got)
                except Exception:
                    clip_reply(token, "")
                return
            if mode == "clip-write":
                try:
                    cb = Gdk.Display.get_default().get_clipboard()
                    try:
                        cb.set_text(req.get("text") or "")
                    except Exception:
                        cb.set_content(Gdk.ContentProvider.new_for_value(
                            GObject.Value(str, req.get("text") or "")))
                    clip_reply(token, "ok")
                except Exception:
                    clip_reply(token, "")
                return
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
        # Console and errors go to the log studio.sh keeps. A window that
        # swallows what the page says about itself is a window in which a fault
        # is invisible, and the first anyone hears of it is "it is broken".
        st.set_enable_write_console_messages_to_stdout(True)
        # a cache that answers for the application is how you end up looking at
        # last week's; there is nothing here worth keeping anyway
        view.get_network_session().get_website_data_manager()
        # The server may not be listening for another moment. A browser would
        # show its own "could not connect" page; an application waits, because
        # the thing it is connecting to is itself.
        tries = {"n": 0}

        def on_load_failed(_v, _event, _uri, _err):
            if tries["n"] < 40:
                tries["n"] += 1
                GLib.timeout_add(250, lambda: (view.load_uri(self.url), False)[1])
                return True                      # and nothing is shown meanwhile
            return False
        view.connect("load-failed", on_load_failed)
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
