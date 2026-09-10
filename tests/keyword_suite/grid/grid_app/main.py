"""
A navigable 7x7 word grid used by the grid keyword suite.

The grid is driven entirely from the keyboard: the arrow keys move the
highlight (with wraparound) and Enter turns the highlighted word green. The
contrast between the highlight and the background is adjustable so the
difficulty of the highlight detection can be tuned.

The GTK/libadwaita imports are deferred into ``_run`` so this module can be
imported (for example by pytest's ``--doctest-modules``) in environments
without the GObject bindings installed.
"""

import argparse
import sys

ROWS = 7
COLS = 7

# 49 short, OCR-friendly words laid out row by row.
WORDS = [
    "apple",
    "bread",
    "cloud",
    "dance",
    "eagle",
    "flame",
    "grape",
    "honey",
    "ivory",
    "jelly",
    "koala",
    "lemon",
    "mango",
    "night",
    "ocean",
    "pearl",
    "queen",
    "river",
    "stone",
    "tiger",
    "umbra",
    "vivid",
    "whale",
    "xenon",
    "yacht",
    "zebra",
    "amber",
    "brick",
    "crane",
    "dwarf",
    "ember",
    "forge",
    "glide",
    "hazel",
    "inlet",
    "joker",
    "kayak",
    "lunar",
    "medal",
    "noble",
    "olive",
    "prism",
    "quilt",
    "raven",
    "spark",
    "torch",
    "unity",
    "vapor",
    "wheat",
]

# The highlight is a lighter shade of the same cool hue as the background, so
# a low --contrast value keeps the two colors genuinely similar.
BACKGROUND = (40, 46, 58)
HIGHLIGHT_TARGET = (165, 180, 205)
SELECTED = (70, 190, 110)


def _lerp(start, end, amount):
    return tuple(round(a + (b - a) * amount) for a, b in zip(start, end))


def _luminance(color):
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]


def _hex(color):
    return "#{:02x}{:02x}{:02x}".format(*color)


def _text_color(background):
    return (20, 20, 20) if _luminance(background) > 140 else (235, 235, 235)


def _run(contrast):
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gtk

    highlight = _lerp(BACKGROUND, HIGHLIGHT_TARGET, contrast)

    css = """
    window {{ background-color: {bg}; }}
    .cell {{
        background-color: {bg};
        color: {text};
        padding: 16px 28px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 20px;
    }}
    .cell.highlight {{ background-color: {hl}; color: {hl_text}; }}
    .cell.selected {{ background-color: {sel}; color: {sel_text}; }}
    """.format(
        bg=_hex(BACKGROUND),
        text=_hex(_text_color(BACKGROUND)),
        hl=_hex(highlight),
        hl_text=_hex(_text_color(highlight)),
        sel=_hex(SELECTED),
        sel_text=_hex(_text_color(SELECTED)),
    )

    class GridApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id="example.GridApp")
            self.current = 0
            self.selected = set()
            self.cells = []
            self.connect("activate", self.on_activate)

        def on_activate(self, app):
            Adw.StyleManager.get_default().set_color_scheme(
                Adw.ColorScheme.FORCE_DARK
            )
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

            win = Gtk.ApplicationWindow(application=app)
            win.set_default_size(1040, 720)

            headerbar = Adw.HeaderBar()
            headerbar.set_title_widget(Gtk.Label(label="Word Grid"))
            win.set_titlebar(headerbar)

            grid = Gtk.Grid(
                row_spacing=16,
                column_spacing=32,
                margin_top=16,
                margin_bottom=16,
                margin_start=16,
                margin_end=16,
            )
            grid.set_hexpand(True)
            grid.set_vexpand(True)
            win.set_child(grid)

            for index, word in enumerate(WORDS):
                label = Gtk.Label(label=word)
                label.set_hexpand(True)
                label.set_vexpand(True)
                self.cells.append(label)
                grid.attach(label, index % COLS, index // COLS, 1, 1)

            controller = Gtk.EventControllerKey()
            controller.connect("key-pressed", self.on_key_pressed)
            win.add_controller(controller)

            self._refresh()
            win.fullscreen()
            win.present()

        def _refresh(self):
            for index, label in enumerate(self.cells):
                classes = ["cell"]
                if index in self.selected:
                    classes.append("selected")
                elif index == self.current:
                    classes.append("highlight")
                label.set_css_classes(classes)

        def on_key_pressed(self, controller, keyval, keycode, state):
            total = len(WORDS)
            if keyval == Gdk.KEY_Right:
                self.current = (self.current + 1) % total
            elif keyval == Gdk.KEY_Left:
                self.current = (self.current - 1) % total
            elif keyval == Gdk.KEY_Down:
                self.current = (self.current + COLS) % total
            elif keyval == Gdk.KEY_Up:
                self.current = (self.current - COLS) % total
            elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                self.selected.add(self.current)
            elif keyval == Gdk.KEY_Escape:
                self.selected.clear()
            else:
                return False

            self._refresh()
            return True

    return GridApp().run([sys.argv[0]])


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="A navigable 7x7 word grid.")
    parser.add_argument(
        "--contrast",
        type=float,
        default=0.85,
        help="Contrast (0-1) between the highlight and the background.",
    )
    args, _ = parser.parse_known_args(argv)

    sys.exit(_run(max(0.0, min(1.0, args.contrast))))


if __name__ == "__main__":
    main()
