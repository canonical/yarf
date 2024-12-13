import os
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import ANY, MagicMock, Mock, call, patch, sentinel

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from robot.api import TestSuite

from yarf.output import (
    OUTPUT_FORMATS,
    OutputConverterBase,
    OutputConverterMeta,
    get_outdir_path,
    import_supported_formats,
    output_converter,
)
from yarf.tests.fixtures import fs  # noqa: F401


class TestOutputConverterMeta:
    """
    Tests for class OutputConverterMeta.
    """

    def test_new(self):
        """
        Test a new item is added to SUPPORTED_PLATFORMS at class creation.
        """

        OUTPUT_FORMATS.clear()

        class TestModule(metaclass=OutputConverterMeta):
            pass

        assert OUTPUT_FORMATS.get(TestModule.__name__) == TestModule


class TestOutputConverterBase:
    """
    Tests for class OutputConverterBase.
    """

    def test_not_implemented(self) -> None:
        """
        Test whether the abstractmethods are required when inheriting from
        OutputConverterBase.
        """

        class TestModule(OutputConverterBase):
            pass

        with pytest.raises(TypeError):
            TestModule()

    @patch("yarf.output.subprocess.run")
    def test_get_yarf_snap_info(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """
        Test whether the "get_yarf_snap_info" method is callable and return
        results with expected fields.
        """
        mock_subprocess_run.return_value.stdout = dedent(
            """
            name:      yarf
            summary:   Yet Another Robot Framework
            publisher: Canonical Certification Team (ce-certification-qa)
            store-url: https://snapcraft.io/yarf
            license:   unset
            description: |
              Yet Another Robot Framework (YARF) is an interface that
              allows developers to build complex test scenarios and
              bootstrap them locally, then work towards automated runs.
            commands:
              - yarf
            snap-id:      zIV9E2VxqRgGhIuttHs8YkCyWGjIOiRm
            tracking:     latest/beta
            refresh-date: 3 days ago, at 16:40 GMT
            channels:
              latest/stable:    –
              latest/candidate: –
              latest/beta:      1.0.0 2024-12-03 (124) 206MB -
              latest/edge:      1.0.0 2024-12-03 (124) 206MB -
            installed:          1.0.0            (124) 206MB -
            """
        )

        expected_result = {
            "channel": "latest/beta",
            "version": "1.0.0",
            "revision": "124",
            "date": "2024-12-03",
            "name": "yarf",
        }
        with patch.dict(os.environ, {"SNAP": str(sentinel.snap_env)}):
            result = OutputConverterBase.get_yarf_snap_info()
        assert expected_result == result

    @patch("yarf.output.subprocess.run")
    def test_get_yarf_snap_info_runtime_error(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """
        Test whether the function get_yarf_snap_info raises runtime error when
        subprocess.run raises a CalledProcessError exception.
        """

        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["snap", "info", "yarf"],
            output="Error: Could not find snap 'yarf'.",
        )

        with (
            patch.dict(os.environ, {"SNAP": str(sentinel.snap_env)}),
            pytest.raises(RuntimeError),
        ):
            OutputConverterBase.get_yarf_snap_info()

    @patch("yarf.output.subprocess.run")
    def test_get_yarf_snap_info_value_error(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        """
        Test whether the function get_yarf_snap_info raises value error when
        there is a mismatch between the installed YARF and the snap info.
        """

        mock_subprocess_run.return_value.stdout = dedent(
            """
            name:      yarf
            summary:   Yet Another Robot Framework
            publisher: Canonical Certification Team (ce-certification-qa)
            store-url: https://snapcraft.io/yarf
            license:   unset
            description: |
              Yet Another Robot Framework (YARF) is an interface that
              allows developers to build complex test scenarios and
              bootstrap them locally, then work towards automated runs.
            commands:
              - yarf
            snap-id:      zIV9E2VxqRgGhIuttHs8YkCyWGjIOiRm
            tracking:     latest/beta
            refresh-date: 3 days ago, at 16:40 GMT
            channels:
              latest/stable:    –
              latest/candidate: –
              latest/beta:      1.0.0 2024-12-03 (124) 206MB -
              latest/edge:      1.0.0 2024-12-03 (124) 206MB -
            installed:          9.9.9            (999) 206MB -
            """
        )

        with (
            patch.dict(os.environ, {"SNAP": str(sentinel.snap_env)}),
            pytest.raises(ValueError),
        ):
            OutputConverterBase.get_yarf_snap_info()

    def test_get_yarf_snap_info_no_snap(self) -> None:
        """
        Test whether the function get_yarf_snap_info returns None when the
        environment variable SNAP is not set.
        """
        with patch.dict(os.environ, {}, clear=True):
            res = OutputConverterBase.get_yarf_snap_info()
        assert res is None

    @pytest.mark.parametrize(
        "func,input,expected_result",
        [
            ("check_test_plan", sentinel.suite, True),
            ("get_output", sentinel.path, sentinel.path),
        ],
    )
    def test_abstract_methods_callable(
        self, func: str, input: str, expected_result: Any
    ) -> None:
        """
        Test whether the abstract methods are callable.
        """

        class TestModule(OutputConverterBase):
            def check_test_plan(self, suite: TestSuite):
                return suite is not None

            def get_output(self, outdir: Path) -> Any:
                return outdir

        m = TestModule()
        result = getattr(m, func)(input)
        assert result == expected_result


class TestInit:
    """
    Test the commonly available, module-level functions.
    """

    @pytest.mark.parametrize(
        "mock_outdir,mock_envars,mock_clear",
        [
            # User defined outdir
            ("user_outdir", {}, False),
            # In snap
            (
                "test-outdir",
                {
                    "SNAP": str(sentinel.snap_env),
                    "SNAP_USER_COMMON": "test-outdir",
                },
                False,
            ),
            # In source
            ("test-outdir", {}, True),
        ],
    )
    def test_get_outdir_path_with_outdir(
        self,
        mock_outdir: str,
        mock_envars: dict[str, str],
        mock_clear: bool,
        fs: FakeFilesystem,  # noqa: F811
    ) -> None:
        """
        Test whether get_outdir_path correctly constructs a path object with
        given outdir and delete relevant files only.
        """
        outdir = mock_outdir
        fs.create_dir(outdir)
        targeted_files = [
            "output.xml",
            "report.html",
            "log.html",
            "rfdebug_history.log",
        ]
        for file in targeted_files:
            fs.create_file(f"{outdir}/{file}")
        fs.create_file(f"{outdir}/test.txt")

        with patch.dict(os.environ, mock_envars, clear=mock_clear):
            result = get_outdir_path(outdir)
        assert result == Path(outdir)
        for file in targeted_files:
            assert not fs.exists(Path(outdir) / file)
        assert fs.exists(Path(outdir) / "test.txt")

    @patch("yarf.output.json.dump")
    @patch("yarf.output.open")
    @patch("yarf.output.OutputConverterBase")
    def test_output_converter(
        self,
        mock_output_converter: MagicMock,
        mock_open: MagicMock,
        mock_json_dump: MagicMock,
    ) -> None:
        """
        Test whether output_converter correctly sandwiches the target function.
        """
        OUTPUT_FORMATS.clear()
        OUTPUT_FORMATS[sentinel.output_format] = mock_output_converter
        mock_process = Mock()
        mock_function = Mock()

        mock_process.attach_mock(mock_function, "mock_function")
        mock_process.attach_mock(mock_output_converter, "OutputConverterBase")
        mock_process.attach_mock(mock_open, "open")
        mock_process.attach_mock(mock_json_dump, "dump")

        outdir = Path(str(sentinel.outdir))
        decorated_mock_function = output_converter(mock_function)
        decorated_mock_function(
            suite=sentinel.suite,
            outdir=outdir,
            output_format=sentinel.output_format,
        )

        mock_process.assert_has_calls(
            [
                call.OutputConverterBase(),
                call.OutputConverterBase().check_test_plan(sentinel.suite),
                call.mock_function(
                    suite=sentinel.suite,
                    outdir=outdir,
                    output_format=sentinel.output_format,
                ),
                call.OutputConverterBase().get_output(outdir),
                call.open(
                    outdir / f"{sentinel.output_format}_output.json", "w"
                ),
                call.open().__enter__(),
                call.dump(ANY, ANY, indent=4),
                call.open().__exit__(None, None, None),
            ]
        )

    @patch("yarf.output.OutputConverterBase")
    def test_output_converter_format_not_supported(
        self,
        mock_output_converter: MagicMock,
    ) -> None:
        """
        Test whether the wrapper raises a ValueError when a format that is not
        supported is specified.
        """
        OUTPUT_FORMATS.clear()
        OUTPUT_FORMATS[sentinel.output_format] = mock_output_converter
        mock_process = Mock()
        mock_function = Mock()

        mock_process.attach_mock(mock_function, "mock_function")
        mock_process.attach_mock(mock_output_converter, "OutputConverterBase")

        decorated_mock_function = output_converter(mock_function)
        with pytest.raises(ValueError):
            decorated_mock_function(
                suite=sentinel.suite,
                outdir=Path(str(sentinel.outdir)),
                output_format=sentinel.unsupported_output_format,
            )

        mock_process.assert_not_called()

    @patch("yarf.output.OutputConverterBase")
    def test_output_converter_no_output_format(
        self,
        mock_output_converter: MagicMock,
    ) -> None:
        """
        Test whether the wrapper will bypass the output converter routine when
        no output format is specified.
        """
        mock_function = Mock()
        decorated_mock_function = output_converter(mock_function)
        decorated_mock_function(sentinel.arg1, sentinel.arg2)

        mock_output_converter.assert_not_called()
        mock_output_converter.check_test_plan.assert_not_called()
        mock_output_converter.get_output.assert_not_called()
        mock_function.assert_called_with(sentinel.arg1, sentinel.arg2)

    def test_import_supported_formats(self) -> None:
        """
        OutputConverterBase should not be included in OUTPUT_FORMATS, Test
        whether OutputConverterBase is deleted from OUTPUT_FORMATS.
        """

        class TestModule(OutputConverterBase):
            def check_test_plan(self, suite: TestSuite) -> bool:
                pass

            def get_output(self, outdir: Path) -> Any:
                pass

        OUTPUT_FORMATS[OutputConverterBase.__name__] = TestModule()
        import_supported_formats()
        assert OutputConverterBase.__name__ not in OUTPUT_FORMATS
