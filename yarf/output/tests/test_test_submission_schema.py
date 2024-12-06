from datetime import date
from importlib import metadata
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, sentinel

from yarf.output.test_submission_schema import TestSubmissionSchema


class TestTestSubmissionSchema:
    """
    Tests for class TestSubmissionSchema.
    """

    @patch("yarf.output.test_submission_schema.ET")
    def test_get_output(self, mock_ET: MagicMock) -> None:
        """
        Test whether the function get the test plan from output.xml in the
        output directory and return the expected output in Test Submission
        Schema format.
        """
        converter = TestSubmissionSchema()
        converter.get_origin = Mock(return_value="origin")
        converter.get_session_data = Mock(return_value="session_data")
        converter.get_results = Mock(return_value="results")
        expected_output = {
            "version": 1,
            "origin": "origin",
            "session_data": "session_data",
            "results": "results",
        }

        output = converter.get_output(Path(str(sentinel.outdir)))

        mock_ET.parse.assert_called_once_with(
            Path(str(sentinel.outdir)) / "output.xml"
        )
        mock_ET.parse.return_value.getroot.assert_called_once()
        converter.get_origin.assert_called_once()
        converter.get_session_data.assert_called_once()
        converter.get_results.assert_called_once()
        assert output == expected_output

    def test_get_origin_has_snap(self) -> None:
        """
        Test whether the function get_origin returns the expected output when a
        snap is present.
        """
        converter = TestSubmissionSchema()
        converter.get_yarf_snap_info = Mock(
            return_value={
                "channel": "latest/beta",
                "version": "1.0.0",
                "revision": "124",
                "date": "2024-12-03",
                "name": "yarf",
            }
        )
        expected_output = {
            "name": "YARF",
            "version": "1.0.0",
            "packaging": {
                "type": "snap",
                "name": "yarf",
                "version": "1.0.0",
                "revision": "124",
                "date": "2024-12-03",
            },
        }

        output = converter.get_origin()
        converter.get_yarf_snap_info.assert_called_once()
        assert output == expected_output

    def test_get_origin_has_no_snap(self) -> None:
        """
        Test whether the function get_origin returns the expected output when a
        snap is not present.
        """
        converter = TestSubmissionSchema()
        converter.get_yarf_snap_info = Mock(return_value=None)
        expected_output = {
            "name": "YARF",
            "version": metadata.version("yarf"),
            "packaging": {
                "type": "source",
                "name": "yarf",
                "version": metadata.version("yarf"),
                "revision": None,
                "date": str(date.today()),
            },
        }

        output = converter.get_origin()
        converter.get_yarf_snap_info.assert_called_once()
        assert output == expected_output
