"""
Region-of-interest selector tool for the YARF interactive console.
"""

import contextlib
import tkinter as tk
from pathlib import Path
from tkinter import Event

from PIL import Image, ImageTk
from robot.api import logger

IMAGE_EXTS = set(Image.registered_extensions().keys())
DEFAULT_TEMPLATE_PREFIX = "roi_"
EXTENSION = ".png"


class ROISelector:
    """
    A simple GUI for selecting a region of interest (ROI) in an image. This
    class provides a zoomable canvas where the user can click and drag to
    select a rectangular area. The selected area can be saved as a new image as
    png.

    Args:
        pil_image: The image to be displayed and selected from.
        *template_names: Names of the templates to be cropped
    """

    def __init__(
        self,
        pil_image: Image.Image,
        *template_names: str,
    ) -> None:
        self.template_names = list(template_names)
        if self.template_names:
            for idx, name in enumerate(self.template_names):
                if (ext_idx := name.rfind(".")) == -1:
                    continue

                if name[ext_idx:] in IMAGE_EXTS:
                    self.template_names[idx] = name[:ext_idx]

        self.template_names_idx = 0
        self.template_idx = 0
        self.outdir = Path.cwd()
        self.original = pil_image
        self.crop: Image.Image | None = None

        # Root window
        self.root = tk.Tk()
        self.root.title("ROI Selector")
        self.root_msg: tk.Label | None = None
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Left>", lambda e: self.previous_template())
        self.root.bind("<Right>", lambda e: self.next_template())

        # Canvas
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack()

        # Check output directory
        self.check_target_outdir()

        self.root_msg = None
        self._update_instructions()

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # State for ROI selection
        self.start_x: float = 0.0
        self.start_y: float = 0.0
        self.rect: int | None = None

        # Draw image
        self._display_image()

    def check_target_outdir(self) -> None:
        """
        Check if the output directory exists, if not create it.

        If the output directory already exists and is not empty, scan
        for existing template files and determine the next template
        index to use for saving new templates. If template names are
        provided, the existing templates will be overwritten.
        """

        if not self.outdir.exists():
            self.outdir.mkdir(parents=True, exist_ok=True)
            return

        if not self.template_names and (
            templates := sorted(
                self.outdir.glob(f"{DEFAULT_TEMPLATE_PREFIX}*{EXTENSION}"),
                reverse=True,
            )
        ):
            # Find biggest valid index
            for template in templates:
                with contextlib.suppress(ValueError):
                    index = (
                        int(template.stem.split(DEFAULT_TEMPLATE_PREFIX)[-1])
                        + 1
                    )
                    self.template_idx = int(index)
                    break

    def previous_template(self) -> None:
        """
        Select the previous template.
        """
        if self.template_idx > 0:
            self.template_idx = max(0, self.template_idx - 1)
        else:
            self.template_names_idx = max(0, self.template_names_idx - 1)

        self._update_instructions()

    def next_template(self) -> None:
        """
        Select the next template.
        """
        if self.template_names and self.template_names_idx < len(
            self.template_names
        ):
            self.template_names_idx = min(
                len(self.template_names), self.template_names_idx + 1
            )
        else:
            self.template_idx = self.template_idx + 1

        self._update_instructions()

    def _update_instructions(self) -> None:
        """
        Update the instructions shown on the root window.
        """
        if self.root_msg is not None:
            self.root_msg.destroy()

        if self.template_names:
            display_text = f"Select template {self.template_names[min(self.template_names_idx, len(self.template_names) - 1)]}"
            if self.template_names_idx >= len(self.template_names):
                display_text += f"_{self.template_idx}. "
            else:
                display_text += "."

        else:
            display_text = f"Select template roi_{self.template_idx} and press Enter to save."

        display_text += " Press Left to overwrite the previous selected template or press Right to skip the current template."
        self.root_msg = tk.Label(
            self.root,
            text=display_text,
            fg="gray",
        )
        self.root_msg.pack(pady=5)

    def _display_image(self) -> None:
        """
        Display the image on the canvas.
        """
        w, h = self.original.size
        self.tk_image = ImageTk.PhotoImage(self.original)

        self.canvas.config(width=w, height=h)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def on_press(self, event: Event) -> None:
        """
        Handle mouse button press event to start selecting a ROI.

        Args:
            event: The event object containing the mouse press
                coordinates.
        """
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="green",
            width=2,
        )

    def on_drag(self, event: Event) -> None:
        """
        Handle mouse drag event to update the rectangle coordinates.

        Args:
            event: The event object containing the mouse drag
                coordinates.
        """
        self.canvas.coords(
            self.rect,  # type: ignore
            self.start_x,
            self.start_y,
            event.x,
            event.y,
        )

    def on_release(self, event: Event) -> None:
        """
        Handle mouse button release event to finalize the ROI selection.

        Args:
            event: The event object containing the mouse release
                coordinates.
        """
        x1, x2 = sorted([self.start_x, event.x])
        y1, y2 = sorted([self.start_y, event.y])

        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            self._clear_overlay()
            logger.info("ROI too small.", also_console=True)
            return

        self.crop = self.original.crop((int(x1), int(y1), int(x2), int(y2)))
        self._show_crop()

    def _show_crop(self) -> None:
        """
        Show the cropped image in a new window for preview and saving.
        """
        preview_window = tk.Toplevel(self.root)
        preview_window.title("ROI Preview")
        preview_window.focus_set()

        crop_tk = ImageTk.PhotoImage(self.crop)
        label = tk.Label(preview_window, image=crop_tk)
        label.image = crop_tk  # type: ignore
        label.pack()

        msg = tk.Label(
            preview_window, text="Press Enter to save, Esc to close", fg="gray"
        )
        msg.pack(pady=5)

        preview_window.bind(
            "<Return>", lambda e: self.save_and_close(preview_window)
        )
        preview_window.bind(
            "<KP_Enter>", lambda e: self.save_and_close(preview_window)
        )
        preview_window.bind(
            "<Escape>", lambda e: self.close_preview(preview_window)
        )
        preview_window.protocol(
            "WM_DELETE_WINDOW", lambda: self.close_preview(preview_window)
        )

    def save_and_close(self, window: tk.Toplevel) -> None:
        """
        Save the cropped image and close the preview window.

        Args:
            window: The preview window to be closed.
        """
        if not self.crop:
            return

        if self.template_names:
            if self.template_names_idx < len(self.template_names):
                filepath = (
                    self.outdir
                    / f"{self.template_names[self.template_names_idx]}{EXTENSION}"
                )
                self.template_names_idx += 1

            else:
                filepath = (
                    self.outdir
                    / f"{self.template_names[-1]}_{self.template_idx}{EXTENSION}"
                )
                self.template_idx += 1
        else:
            filepath = (
                self.outdir
                / f"{DEFAULT_TEMPLATE_PREFIX}{self.template_idx}{EXTENSION}"
            )
            self.template_idx += 1

        self.crop.save(filepath)
        logger.info(f"ROI saved as {filepath}", also_console=True)
        self._update_instructions()
        self.close_preview(window)

    def close_preview(self, window: tk.Toplevel) -> None:
        """
        Close the preview window and clear the overlay.

        Args:
            window: The preview window to be closed.
        """
        window.destroy()
        self._clear_overlay()

    def _clear_overlay(self) -> None:
        """
        Clear the rectangle overlay on the canvas.
        """
        if not self.rect:
            return

        self.canvas.delete(self.rect)
        self.rect = None

    def start(self) -> None:
        """
        Start the ROI selector GUI.
        """
        logger.info(
            "Click and drag to select and save an ROI, press Esc to exit the ROI selector.",
            also_console=True,
        )
        self.root.mainloop()
