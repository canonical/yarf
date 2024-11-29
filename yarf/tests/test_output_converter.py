from pathlib import Path
from unittest.mock import Mock

import pytest
from pyfakefs.fake_filesystem_unittest import FakeFilesystem

from yarf.output_converter import OutputConverter
from yarf.tests.fixtures import fs  # noqa: F401


class TestOutputConverter:
    def test_init(self, fs: FakeFilesystem) -> None:  # noqa: F811
        outdir = Path("/testoutdir")
        fs.create_dir(outdir)

        output_converter = OutputConverter(outdir)
        assert output_converter.outdir == outdir

    def test_init_outdir_not_exist(self) -> None:
        with pytest.raises(ValueError):
            OutputConverter(Path("/nonexistent"))

    def test_convert_to_format(self, fs: FakeFilesystem) -> None:  # noqa: F811
        outdir = Path("/testoutdir")
        fs.create_dir(outdir)
        output_converter = OutputConverter(outdir)
        output_converter.convert_to_hexr = Mock()

        output_converter.convert_to_format("hexr")
        output_converter.convert_to_hexr.assert_called_once()

    def test_convert_to_format_unsupported(self, fs: FakeFilesystem) -> None:  # noqa: F811
        outdir = Path("/testoutdir")
        fs.create_dir(outdir)
        output_converter = OutputConverter(outdir)

        with pytest.raises(ValueError):
            output_converter.convert_to_format("unsupported_format")
