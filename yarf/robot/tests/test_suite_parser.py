import unittest
from unittest.mock import Mock
from pyfakefs.fake_filesystem_unittest import patchfs, FakeFilesystem
from pathlib import Path
from yarf.robot.suite_parser import SuiteParser


class TestSuiteParser(unittest.TestCase):
    def test_suite_parser_init(self) -> None:
        """
        Test whether the SuiteParser class is initialized correctly.
        """
        path_to_suite = "/path/to/suite"
        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, path_to_suite)
        self.assertEqual(
            mock_suite_parser_instance.suite_path, Path(path_to_suite)
        )
        mock_suite_parser_instance.read_suite.assert_called_once()

    @patchfs
    def test_read_suite(self, mock_fs: FakeFilesystem) -> None:
        """
        Test whether read_suite read the correct assets' and variants'
        relative and full path from provided suite path.
        """
        mock_suite_path = "suite"
        mock_files = [
            "test.robot",
            "asset1.png",
            "asset2.jpg",
            "asset3.jpeg",
            "variants/var1/asset1.png",
            "variants/var1/var2/asset2.jpg",
            "variants/var2/asset3.jpeg",
        ]
        for m_file in mock_files:
            mock_fs.create_file(f"{mock_suite_path}/{m_file}")

        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, mock_suite_path)
        SuiteParser.read_suite(mock_suite_parser_instance)
        self.assertEqual(
            mock_suite_parser_instance.assets,
            {
                Path("test.robot"): Path(f"{mock_suite_path}/test.robot"),
                Path("asset1.png"): Path(f"{mock_suite_path}/asset1.png"),
                Path("asset2.jpg"): Path(f"{mock_suite_path}/asset2.jpg"),
                Path("asset3.jpeg"): Path(f"{mock_suite_path}/asset3.jpeg"),
            },
        )
        self.assertEqual(
            mock_suite_parser_instance.variants,
            {
                Path("var1/asset1.png"): Path(
                    f"{mock_suite_path}/variants/var1/asset1.png"
                ),
                Path("var1/var2/asset2.jpg"): Path(
                    f"{mock_suite_path}/variants/var1/var2/asset2.jpg"
                ),
                Path("var2/asset3.jpeg"): Path(
                    f"{mock_suite_path}/variants/var2/asset3.jpeg"
                ),
            },
        )

    @patchfs
    def test_read_suite_sub_dir(self, mock_fs: FakeFilesystem) -> None:
        """
        Test whether read_suite read the correct assets' and variants'
        relative and full path from provided suite path if there is/are
        subdirectories.
        """
        mock_suite_path = "suite"
        mock_files = [
            "test.robot",
            "asset1.png",
            "asset2.jpg",
            "subdir/asset3.jpeg",
            "subdir/variants/asset4.png",
            "variants/var1/asset1.png",
            "variants/var1/var2/asset2.jpg",
            "variants/var2/subdir/asset3.jpeg",
        ]
        for m_file in mock_files:
            mock_fs.create_file(f"{mock_suite_path}/{m_file}")

        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, mock_suite_path)
        SuiteParser.read_suite(mock_suite_parser_instance)
        self.assertEqual(
            mock_suite_parser_instance.assets,
            {
                Path("test.robot"): Path(f"{mock_suite_path}/test.robot"),
                Path("asset1.png"): Path(f"{mock_suite_path}/asset1.png"),
                Path("asset2.jpg"): Path(f"{mock_suite_path}/asset2.jpg"),
                Path("subdir/asset3.jpeg"): Path(
                    f"{mock_suite_path}/subdir/asset3.jpeg"
                ),
                Path("subdir/variants/asset4.png"): Path(
                    f"{mock_suite_path}/subdir/variants/asset4.png"
                ),
            },
        )
        self.assertEqual(
            mock_suite_parser_instance.variants,
            {
                Path("var1/asset1.png"): Path(
                    f"{mock_suite_path}/variants/var1/asset1.png"
                ),
                Path("var1/var2/asset2.jpg"): Path(
                    f"{mock_suite_path}/variants/var1/var2/asset2.jpg"
                ),
                Path("var2/subdir/asset3.jpeg"): Path(
                    f"{mock_suite_path}/variants/var2/subdir/asset3.jpeg"
                ),
            },
        )

    @patchfs
    def test_read_suite_no_robot_file(self, mock_fs: FakeFilesystem) -> None:
        """
        Test whether read_suite raises a ValueError when no robot file is found.
        """
        mock_suite_path = "suite"
        mock_files = [
            "asset1.png",
            "asset2.jpg",
            "asset3.jpeg",
            "variants/var1/asset1.png",
            "variants/var1/var2/asset2.jpg",
            "variants/var2/asset3.jpeg",
        ]
        for m_file in mock_files:
            mock_fs.create_file(f"{mock_suite_path}/{m_file}")

        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, mock_suite_path)
        with self.assertRaises(ValueError):
            SuiteParser.read_suite(mock_suite_parser_instance)

    @patchfs
    def test_suite_in_temp_folder(self, mock_fs: FakeFilesystem) -> None:
        """
        Test whether the function suite_in_temp_folder correctly
        move the suite assets to a temporary folder after the correct
        assets are selected.
        """
        mock_suite_path = "suite"
        mock_variant = "var1/var2/var3"
        mock_files = [
            "test.robot",
            "asset1.png",
            "var2/asset2.jpg",
            "var2/var3/asset3.jpeg",
            "variants/var1/asset1.png",
            "variants/var1/var2/asset2.jpg",
            "variants/var2/var3/asset3.jpeg",
        ]
        for m_file in mock_files:
            mock_fs.create_file(f"{mock_suite_path}/{m_file}")

        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, mock_suite_path)
        mock_suite_parser_instance.select_assets.return_value = {
            Path("test.robot"): Path(f"{mock_suite_path}/test.robot"),
            Path("asset1.png"): Path(
                f"{mock_suite_path}/variants/var1/asset1.png"
            ),
            Path("var2/asset2.jpg"): Path(
                f"{mock_suite_path}/variants/var1/var2/asset2.jpg"
            ),
            Path("var2/var3/asset3.jpeg"): Path(
                f"{mock_suite_path}/variants/var2/var3/asset3.jpeg"
            ),
        }
        with SuiteParser.suite_in_temp_folder(
            mock_suite_parser_instance, mock_variant
        ) as temp_directory_path:
            expected_file_system = {
                temp_directory_path / "test.robot",
                temp_directory_path / "asset1.png",
                temp_directory_path / "var2",
                temp_directory_path / "var2/var3",
                temp_directory_path / "var2/asset2.jpg",
                temp_directory_path / "var2/var3/asset3.jpeg",
            }
            self.assertTrue(temp_directory_path.exists())
            self.assertEqual(
                set(temp_directory_path.rglob("*")), expected_file_system
            )

    @patchfs
    def test_select_assets(self, mock_fs: FakeFilesystem) -> None:
        """
        Test whether the select_assets method correctly get
        assets according to variant string.
        """
        mock_suite_path = "suite"
        mock_variant = "var1/var2"
        mock_files = [
            "test.robot",
            "asset1.png",
            "asset2.jpg",
            "subdir/asset3.jpeg",
            "variants/var1/asset1.png",
            "variants/var1/var2/asset2.jpg",
            "variants/var2/subdir/asset3.jpeg",
        ]
        for m_file in mock_files:
            mock_fs.create_file(f"{mock_suite_path}/{m_file}")

        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, mock_suite_path)
        mock_suite_parser_instance.assets = {
            Path("test.robot"): Path(f"{mock_suite_path}/test.robot"),
            Path("asset1.png"): Path(f"{mock_suite_path}/asset1.png"),
            Path("asset2.jpg"): Path(f"{mock_suite_path}/asset2.jpg"),
            Path("subdir/asset3.jpeg"): Path(
                f"{mock_suite_path}/subdir/asset3.jpeg"
            ),
        }
        mock_suite_parser_instance.variants = {
            Path("var1/asset1.png"): Path(
                f"{mock_suite_path}/variants/var1/asset1.png"
            ),
            Path("var1/var2/asset2.jpg"): Path(
                f"{mock_suite_path}/variants/var1/var2/asset2.jpg"
            ),
            Path("var2/subdir/asset3.jpeg"): Path(
                f"{mock_suite_path}/variants/var2/subdir/asset3.jpeg"
            ),
        }
        mock_precedence_list = [Path("var1/var2"), Path("var1"), Path("var2")]
        mock_suite_parser_instance.get_variants_precedence_list.return_value = (
            mock_precedence_list
        )
        actual_assets = SuiteParser.select_assets(
            mock_suite_parser_instance, mock_variant
        )
        mock_suite_parser_instance.get_variants_precedence_list.assert_called_once()
        self.assertEqual(
            actual_assets,
            {
                Path("test.robot"): Path(f"{mock_suite_path}/test.robot"),
                Path("asset2.jpg"): Path(
                    f"{mock_suite_path}/variants/var1/var2/asset2.jpg"
                ),
                Path("asset1.png"): Path(
                    f"{mock_suite_path}/variants/var1/asset1.png"
                ),
                Path("subdir/asset3.jpeg"): Path(
                    f"{mock_suite_path}/variants/var2/subdir/asset3.jpeg"
                ),
            },
        )

    def test_get_variants_precedence_list(self) -> None:
        """
        Test whether the get_variants_precedence_list method returns
        the reversed ascending sort by specificity degree.
        """
        mock_suite_path = "/path/to/suite"
        mock_suite_parser_instance = Mock()
        SuiteParser.__init__(mock_suite_parser_instance, mock_suite_path)

        precedence_list = SuiteParser.get_variants_precedence_list(
            mock_suite_parser_instance, "var1/var2/var3"
        )
        self.assertEqual(
            precedence_list,
            [
                Path("var1/var2/var3"),
                Path("var2/var3"),
                Path("var1/var2"),
                Path("var3"),
                Path("var2"),
                Path("var1"),
            ],
        )

        precedence_list = SuiteParser.get_variants_precedence_list(
            mock_suite_parser_instance, ""
        )
        self.assertEqual(precedence_list, [])

        precedence_list = SuiteParser.get_variants_precedence_list(
            mock_suite_parser_instance, None
        )
        self.assertEqual(precedence_list, [])
