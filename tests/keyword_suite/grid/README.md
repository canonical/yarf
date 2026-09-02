# Word Grid test app

A small GTK4 / libadwaita application that displays a **7x7 grid of words**
navigated entirely with the keyboard. It is used by
[`grid_test.robot`](../grid_test.robot) to exercise YARF's highlight-detection
keywords (`Get Highlighted Text` / `Is Highlighted Text`) and the
`Press ... Until ... Is Highlighted` keywords from `kvm.resource`.

The app is a small [uv](https://docs.astral.sh/uv/)-managed project, like the
`yarf-example-simple-counter` example.

## Behaviour

- When the app starts, the word in the **top-left** corner is highlighted.
- The **arrow keys** move the highlight, wrapping around at the edges. Pressing
  `Right` advances through every cell in reading order, so a single direction
  can reach any word.
- Pressing **Enter** turns the currently highlighted word **green** (selected).
- Pressing **Esc** clears all green selections.

## Contrast

The contrast between the highlight color and the background is adjustable, so
the difficulty of the highlight detection can be tuned:

```bash
uv --project tests/keyword_suite/grid run grid-app --contrast 0.85   # high (default)
uv --project tests/keyword_suite/grid run grid-app --contrast 0.2    # low
```

`--contrast` takes a value between `0` (highlight almost identical to the
background) and `1` (maximum contrast).

## Running

The GObject bindings come from the system, so the venv is created with
`--system-site-packages`:

```bash
sudo apt-get install python3-gi gir1.2-gtk-4.0 libadwaita-1-dev gir1.2-adw-1
uv venv --python=/usr/bin/python3 --system-site-packages \
  --project tests/keyword_suite/grid
uv --project tests/keyword_suite/grid run grid-app --contrast 0.85
```

## Notes

The GTK imports are deferred into `grid_app.main._run()` so the module can be
imported (for example by pytest's `--doctest-modules`) in environments without
the GObject bindings installed.
