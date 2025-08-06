from collections.abc import Iterator
from pathlib import Path
from unittest.mock import ANY, MagicMock, Mock, call, patch, sentinel

import pytest
from PIL import Image

from yarf.rf_libraries.interactive_console.tools.roi_selector import (
    ROISelector,
)


class TestROISelector:
    @pytest.fixture
    def roi_selector(self) -> Iterator[ROISelector]:
        """
        Fixture to create an instance of the ROISelector class.
        """
        sentinel.image = Image.new("RGB", (100, 100), "white")
        with (
            patch(
                "yarf.rf_libraries.interactive_console.tools.roi_selector.ImageTk"
            ),
            patch(
                "yarf.rf_libraries.interactive_console.tools.roi_selector.logger"
            ),
            patch(
                "yarf.rf_libraries.interactive_console.tools.roi_selector.tk"
            ),
            patch.object(Path, "mkdir", return_value=None),
            patch.object(Path, "cwd", return_value=Path("cwd")),
        ):
            yield ROISelector(sentinel.image)

    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.tk")
    @patch(
        "yarf.rf_libraries.interactive_console.tools.roi_selector.ImageTk.PhotoImage"
    )
    def test_init(
        self,
        mock_photo_image: MagicMock,
        mock_tk: MagicMock,
    ) -> None:
        mock_process = Mock()
        mock_process.attach_mock(mock_tk, "tk")
        mock_process.attach_mock(mock_photo_image, "PhotoImage")

        sentinel.screenshot = Image.new("RGB", (100, 100), "white")
        sentinel.template_names = ("template1", "template2.png")

        roi_selector = ROISelector(
            sentinel.screenshot, *sentinel.template_names
        )
        mock_process.assert_has_calls(
            [
                call.tk.Tk(),
                call.tk.Tk().title("ROI Selector"),
                call.tk.Tk().bind("<Escape>", ANY),
                call.tk.Tk().bind("<Left>", ANY),
                call.tk.Tk().bind("<Right>", ANY),
                call.tk.Canvas(roi_selector.root, highlightthickness=0),
                call.tk.Canvas().pack(),
                call.tk.Label(roi_selector.root, text=ANY, fg="gray"),
                call.tk.Label().pack(pady=5),
                call.tk.Canvas().bind("<ButtonPress-1>", ANY),
                call.tk.Canvas().bind("<B1-Motion>", ANY),
                call.tk.Canvas().bind("<ButtonRelease-1>", ANY),
                call.PhotoImage(roi_selector.original),
                call.tk.Canvas().config(width=100, height=100),
                call.tk.Canvas().delete("all"),
                call.tk.Canvas().create_image(
                    0, 0, anchor="nw", image=roi_selector.tk_image
                ),
            ]
        )
        assert roi_selector.template_names == ["template1", "template2"]

    @pytest.mark.parametrize(
        "outdir_content,expected_idx",
        [
            ([], 0),
            (
                [Path("roi_0.png"), Path("roi_1.png")],
                2,
            ),
            (
                [Path("dir"), Path("roi_0.png"), Path("roi_1.png")],
                2,
            ),
            (
                [Path("dir"), Path("roi_0.png"), Path("roi_a.png")],
                1,
            ),
            (
                [Path("README.md"), Path("roi_0.png")],
                1,
            ),
        ],
    )
    def test_check_target_outdir_with_templates(
        self,
        outdir_content: list[Path],
        expected_idx: int,
        roi_selector: ROISelector,
    ) -> None:
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "glob", return_value=outdir_content),
        ):
            roi_selector.check_target_outdir()
        roi_selector.template_names_idx = expected_idx

    def test_check_target_outdir_not_exist(
        self, roi_selector: ROISelector
    ) -> None:
        with (
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "mkdir", return_value=None) as mock_mkdir,
        ):
            roi_selector.check_target_outdir()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.parametrize(
        "template_names,template_names_idx,template_idx,expected_template_names_idx,expected_template_idx",
        [
            (["a", "b"], 0, 0, 0, 0),
            (["a", "b"], 1, 0, 0, 0),
            (["a", "b"], 2, 0, 1, 0),
            (["a", "b"], 2, 1, 2, 0),
            (None, 0, 0, 0, 0),
            (None, 0, 1, 0, 0),
        ],
    )
    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.tk.Label")
    def test_previous_template(
        self,
        mock_tk_label: MagicMock,
        template_names: list[str] | None,
        template_names_idx: int,
        template_idx: int,
        expected_template_names_idx: int,
        expected_template_idx: int,
        roi_selector: ROISelector,
    ) -> None:
        roi_selector.template_names = template_names
        roi_selector.template_names_idx = template_names_idx
        roi_selector.template_idx = template_idx
        roi_selector.root_msg = mock_tk_label
        roi_selector.previous_template()

        assert roi_selector.template_names_idx == expected_template_names_idx
        assert roi_selector.template_idx == expected_template_idx
        mock_tk_label.assert_has_calls(
            [
                call.destroy(),
                call(roi_selector.root, text=ANY, fg=ANY),
            ]
        )

    @pytest.mark.parametrize(
        "template_names,template_names_idx,template_idx,expected_template_names_idx,expected_template_idx",
        [
            (["a", "b"], 0, 0, 1, 0),
            (["a", "b"], 1, 0, 2, 0),
            (["a", "b"], 2, 0, 2, 1),
            (None, 0, 0, 0, 1),
        ],
    )
    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.tk.Label")
    def test_next_template(
        self,
        mock_tk_label: MagicMock,
        template_names: list[str],
        template_names_idx: int,
        template_idx: int,
        expected_template_names_idx: int,
        expected_template_idx: int,
        roi_selector: ROISelector,
    ) -> None:
        roi_selector.template_names = template_names
        roi_selector.template_names_idx = template_names_idx
        roi_selector.template_idx = template_idx
        roi_selector.root_msg = mock_tk_label
        roi_selector.next_template()

        assert roi_selector.template_names_idx == expected_template_names_idx
        assert roi_selector.template_idx == expected_template_idx
        mock_tk_label.assert_has_calls(
            [
                call.destroy(),
                call(roi_selector.root, text=ANY, fg=ANY),
            ]
        )

    def test_on_press(self, roi_selector: ROISelector) -> None:
        event = Mock()
        event.x = 10
        event.y = 20
        roi_selector.on_press(event)
        assert roi_selector.start_x == 10
        assert roi_selector.start_y == 20
        roi_selector.canvas.create_rectangle.assert_called_once_with(
            10, 20, 10, 20, outline="green", width=2
        )

    def test_on_drag(self, roi_selector: ROISelector) -> None:
        event = Mock()
        event.x = 30
        event.y = 40
        roi_selector.start_x = 10
        roi_selector.start_y = 20
        roi_selector.rect = Mock()
        roi_selector.canvas.coords = Mock()
        roi_selector.on_drag(event)
        roi_selector.canvas.coords.assert_called_once_with(
            roi_selector.rect, 10, 20, 30, 40
        )

    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.tk")
    @patch(
        "yarf.rf_libraries.interactive_console.tools.roi_selector.ImageTk.PhotoImage"
    )
    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.abs")
    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.sorted")
    def test_on_release(
        self,
        mock_sorted: MagicMock,
        mock_abs: MagicMock,
        mock_photo_image: MagicMock,
        mock_tk: MagicMock,
        roi_selector: ROISelector,
    ) -> None:
        mock_preview_window = mock_tk.Toplevel.return_value
        mock_sorted.side_effect = [
            (10, 30),
            (20, 40),
        ]
        mock_abs.side_effect = [
            20,
            20,
        ]
        event = Mock()
        event.x = 30
        event.y = 40
        roi_selector.start_x = 10
        roi_selector.start_y = 20
        roi_selector.original.crop = Mock(
            return_value=Image.new("RGB", (10, 10), "white")
        )
        roi_selector.save_and_close = Mock()
        roi_selector.close_preview = Mock()

        mock_process = Mock()
        mock_process.attach_mock(roi_selector.original.crop, "crop")
        mock_process.attach_mock(mock_sorted, "sorted")
        mock_process.attach_mock(mock_abs, "abs")
        mock_process.attach_mock(mock_photo_image, "PhotoImage")
        mock_process.attach_mock(mock_preview_window, "preview_window")
        mock_process.attach_mock(mock_tk.Toplevel, "Toplevel")
        mock_process.attach_mock(mock_tk.Label, "Label")

        roi_selector.on_release(event)

        mock_process.assert_has_calls(
            [
                call.sorted([10, 30]),
                call.sorted([20, 40]),
                call.abs(30 - 10),
                call.abs(40 - 20),
                call.crop((10, 20, 30, 40)),
                call.Toplevel(roi_selector.root),
                call.preview_window.title("ROI Preview"),
                call.preview_window.focus_set(),
                call.PhotoImage(roi_selector.crop),
                call.Label(
                    mock_preview_window, image=mock_photo_image.return_value
                ),
                call.Label().pack(),
                call.Label(mock_preview_window, text=ANY, fg=ANY),
                call.Label().pack(pady=5),
                call.preview_window.bind("<Return>", ANY),
                call.preview_window.bind("<KP_Enter>", ANY),
                call.preview_window.bind("<Escape>", ANY),
                call.preview_window.protocol("WM_DELETE_WINDOW", ANY),
            ]
        )

    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.logger")
    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.abs")
    @patch("yarf.rf_libraries.interactive_console.tools.roi_selector.sorted")
    def test_on_release_roi_too_small(
        self,
        mock_sorted: MagicMock,
        mock_abs: MagicMock,
        mock_logger: MagicMock,
        roi_selector: ROISelector,
    ) -> None:
        mock_sorted.side_effect = [
            (10, 11),
            (20, 21),
        ]
        mock_abs.side_effect = [
            1,
            1,
        ]
        event = Mock()
        event.x = 11
        event.y = 21

        roi_selector.rect = roi_selector.canvas.create_rectangle(
            0,
            0,
            1,
            1,
            outline="green",
            width=2,
        )
        rect = roi_selector.rect
        roi_selector.start_x = 10
        roi_selector.start_y = 20
        roi_selector.canvas.delete = Mock()
        roi_selector.original.crop = Mock()
        roi_selector._show_crop = Mock()

        roi_selector.on_release(event)
        roi_selector.canvas.delete.assert_called_once_with(rect)
        assert roi_selector.rect is None
        mock_logger.info.assert_called_once()
        roi_selector.original.crop.assert_not_called()
        roi_selector._show_crop.assert_not_called()

    def test_save_and_close(self, roi_selector: ROISelector) -> None:
        roi_selector.crop = Mock()
        roi_selector.close_preview = Mock()

        mock_process = Mock()
        mock_process.attach_mock(roi_selector.crop, "crop")
        mock_process.attach_mock(roi_selector.close_preview, "close_preview")
        roi_selector.save_and_close(sentinel.window)

        mock_process.assert_has_calls(
            [
                call.crop.save(ANY),
                call.close_preview(sentinel.window),
            ]
        )

    def test_save_and_close_allow_overwrites(
        self, roi_selector: ROISelector
    ) -> None:
        roi_selector.crop = Mock()
        roi_selector.close_preview = Mock()
        roi_selector.allowed_overwrites = ["roi_0.png"]

        mock_process = Mock()
        mock_process.attach_mock(roi_selector.crop, "crop")
        mock_process.attach_mock(roi_selector.close_preview, "close_preview")
        with patch.object(Path, "exists", return_value=True):
            roi_selector.save_and_close(sentinel.window)

        mock_process.assert_has_calls(
            [
                call.crop.save(ANY),
                call.close_preview(sentinel.window),
            ]
        )
        args, _ = mock_process.crop.save.call_args
        filepath: Path = args[0]
        assert filepath.name == "roi_0.png"

    def test_save_and_close_no_crop(self, roi_selector: ROISelector) -> None:
        roi_selector.crop = None
        roi_selector.close_preview = Mock()

        mock_process = Mock()
        mock_process.attach_mock(roi_selector.close_preview, "close_preview")
        roi_selector.save_and_close(sentinel.window)
        mock_process.assert_not_called()

    def test_save_and_close_images_exist(
        self, roi_selector: ROISelector
    ) -> None:
        roi_selector.crop = Mock()
        roi_selector.close_preview = Mock()

        mock_process = Mock()
        mock_process.attach_mock(roi_selector.crop, "crop")
        mock_process.attach_mock(roi_selector.close_preview, "close_preview")
        roi_selector.save_and_close(sentinel.window)

        mock_process.assert_has_calls(
            [
                call.crop.save(ANY),
                call.close_preview(sentinel.window),
            ]
        )

    def test_save_and_close_with_template_names(
        self, roi_selector: ROISelector
    ) -> None:
        roi_selector.template_names = ["template1", "extra/template2"]
        roi_selector.crop = Mock()
        roi_selector.close_preview = Mock()

        mock_process = Mock()
        mock_process.attach_mock(roi_selector.crop, "crop")
        mock_process.attach_mock(roi_selector.close_preview, "close_preview")
        for _ in range(5):
            roi_selector.save_and_close(sentinel.window)

        calls = []
        for p in [
            "template1",
            "extra/template2",
            "extra/template2_0",
            "extra/template2_1",
            "extra/template2_2",
        ]:
            calls.extend(
                [
                    call.crop.save(Path(f"{roi_selector.outdir}/{p}.png")),
                    call.close_preview(sentinel.window),
                ]
            )

        mock_process.assert_has_calls(calls)
        assert roi_selector.template_names_idx == 2
        assert roi_selector.template_idx == 3

    def test_close_preview(self, roi_selector: ROISelector) -> None:
        roi_selector.rect = roi_selector.canvas.create_rectangle(
            0,
            0,
            1,
            1,
            outline="green",
            width=2,
        )
        rect = roi_selector.rect
        roi_selector.canvas.delete = Mock()
        sentinel.window.destroy = Mock()
        roi_selector.close_preview(sentinel.window)
        sentinel.window.destroy.assert_called_once()
        roi_selector.canvas.delete.assert_called_once_with(rect)
        assert roi_selector.rect is None

    def test_close_preview_no_rect(self, roi_selector: ROISelector) -> None:
        roi_selector.canvas.delete = Mock()
        sentinel.window.destroy = Mock()
        roi_selector.close_preview(sentinel.window)
        sentinel.window.destroy.assert_called_once()
        roi_selector.canvas.delete.assert_not_called()

    def test_start(self, roi_selector: ROISelector) -> None:
        roi_selector.root.mainloop = Mock()
        roi_selector.start()
        roi_selector.root.mainloop.assert_called_once()
