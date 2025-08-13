import argparse
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


class CounterApp(Adw.Application):
    def __init__(self, dark_mode):
        super().__init__(application_id="example.CounterApp")
        self.dark_mode = dark_mode
        self.count = 0
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK
            if self.dark_mode
            else Adw.ColorScheme.FORCE_LIGHT
        )

        win = Gtk.ApplicationWindow(application=app)
        win.set_default_size(300, 220)

        headerbar = Adw.HeaderBar()
        headerbar.set_title_widget(Gtk.Label(label="Simple Counter"))
        headerbar.set_show_end_title_buttons(True)

        win.set_titlebar(headerbar)

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=20,
            margin_bottom=20,
            margin_start=20,
            margin_end=20,
        )
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_halign(Gtk.Align.CENTER)
        win.set_child(vbox)

        self.label = Gtk.Label(label=f"Count: {self.count}")
        self.label.set_css_classes(["title-1"])
        vbox.append(self.label)

        hbox = Gtk.Box(spacing=12)
        hbox.set_halign(Gtk.Align.CENTER)
        vbox.append(hbox)

        dec_btn = Gtk.Button(label="-")
        dec_btn.connect("clicked", self.on_decrement)
        hbox.append(dec_btn)

        inc_btn = Gtk.Button(label="+")
        inc_btn.connect("clicked", self.on_increment)
        hbox.append(inc_btn)

        toggle_btn = Gtk.Button(label="Toggle Theme")
        toggle_btn.connect("clicked", self.on_toggle_theme)
        vbox.append(toggle_btn)

        win.present()

    def on_increment(self, btn):
        self.count += 1
        self.label.set_label(f"Count: {self.count}")

    def on_decrement(self, btn):
        self.count -= 1
        self.label.set_label(f"Count: {self.count}")

    def on_toggle_theme(self, btn):
        self.dark_mode = not self.dark_mode
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK
            if self.dark_mode
            else Adw.ColorScheme.FORCE_LIGHT
        )


def main(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=["dark", "light"], default="dark")
    args, _ = parser.parse_known_args(argv)

    app = CounterApp(dark_mode=(args.theme == "dark"))
    sys.exit(app.run([sys.argv[0]]))


if __name__ == "__main__":
    main()
