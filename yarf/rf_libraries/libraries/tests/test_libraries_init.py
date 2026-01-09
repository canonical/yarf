import tempfile
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest
from pytest import LogCaptureFixture

from yarf.rf_libraries.libraries import (
    PLATFORM_PLUGIN_PREFIX,
    SUPPORTED_PLATFORMS,
    PlatformBase,
    PlatformMeta,
    import_libraries,
    import_platform_plugin,
)


class TestPlatformMeta:
    """
    Test the Platform metaclass.
    """

    @patch("yarf.rf_libraries.libraries.IMPORT_PROCESS_COMPLETED", False)
    def test_new(self):
        """
        Test a new item is added to SUPPORTED_PLATFORMS at class creation.
        """

        SUPPORTED_PLATFORMS.clear()

        class TestModule(metaclass=PlatformMeta):
            pass

        assert SUPPORTED_PLATFORMS.get(TestModule.__name__) == TestModule

    @patch("yarf.rf_libraries.libraries.IMPORT_PROCESS_COMPLETED", False)
    def test_platform_meta_logs_warning(self, caplog: LogCaptureFixture):
        """
        Test whether a warning is logged when a platform is overridden by
        another module with the same name.
        """
        SUPPORTED_PLATFORMS.clear()

        class FirstPlatform(metaclass=PlatformMeta):
            pass

        assert "FirstPlatform" in SUPPORTED_PLATFORMS
        assert not caplog.records

        with caplog.at_level("WARNING"):

            class FirstPlatform(metaclass=PlatformMeta):
                __module__ = PLATFORM_PLUGIN_PREFIX + "second"

        assert any(
            FirstPlatform.__module__ in record.message
            for record in caplog.records
        )

        assert (
            SUPPORTED_PLATFORMS["FirstPlatform"].__module__
            == FirstPlatform.__module__
        )


class TestPlatformBase:
    """
    Test the Platform base class.
    """

    @patch("yarf.rf_libraries.libraries.IMPORT_PROCESS_COMPLETED", False)
    def test_not_implemented(self):
        """
        Test whether the abstractmethods are required when inheriting from
        PlatformBase.
        """

        class TestModule(PlatformBase):
            pass

        with pytest.raises(TypeError):
            TestModule()

    @patch("yarf.rf_libraries.libraries.IMPORT_PROCESS_COMPLETED", False)
    def test_get_pkg_path(self):
        """
        Test whether the "get_pkg_path" method is callable when a class
        inherits from PlatformBase.
        """
        test_lib_path = "lib-path"

        class TestModule(PlatformBase):
            def get_pkg_path(self) -> str:
                return test_lib_path

        platform = TestModule()
        assert platform.get_pkg_path() == test_lib_path


class TestInit:
    """
    Test the commonly available, module-level functions.
    """

    @patch("yarf.rf_libraries.libraries.IMPORT_PROCESS_COMPLETED", False)
    def test_import_libraries(self) -> None:
        """
        PlatformBase should not be included in SUPPORTED_PLATFORMS, Test
        whether PlatformBase is deleted from SUPPORTED_PLATFORMS.
        """

        class TestModule(PlatformBase):
            def get_pkg_path(self) -> str:
                pass

        SUPPORTED_PLATFORMS[PlatformBase.__name__] = TestModule()
        import_libraries()
        assert PlatformBase.__name__ not in SUPPORTED_PLATFORMS

    @patch("yarf.rf_libraries.libraries.IMPORT_PROCESS_COMPLETED", False)
    def test_import_platform_plugin(self) -> None:  # noqa: F811
        """
        Test whether the import_platform_plugin function is callable.

        This function is not implemented yet, so we just check if it can
        be called without raising an error.
        """
        SUPPORTED_PLATFORMS.clear()
        mock_path = MagicMock()
        with (
            tempfile.TemporaryDirectory() as tempdir,
            patch("sys.path", new=mock_path),
        ):
            platform_plugin_dir = Path(tempdir) / "platform_plugins"
            test_plugin_dir = platform_plugin_dir / "yarf_plugin_test"
            test_plugin_dir.mkdir(parents=True, exist_ok=True)

            test_plugin_init = test_plugin_dir / "__init__.py"
            test_plugin_init.write_text(
                dedent(
                    """
                from yarf.rf_libraries.libraries import PlatformBase

                class TestPlugin(PlatformBase):
                    @staticmethod
                    def get_pkg_path() -> str:
                        return "test_plugin_path"
                """
                )
            )

            plugin_to_ignore_dir = (
                platform_plugin_dir / "test_plugin_to_ignore"
            )
            plugin_to_ignore_dir.mkdir(parents=True, exist_ok=True)
            plugin_to_ignore_sample_class = (
                plugin_to_ignore_dir / "sample_class.py"
            )
            plugin_to_ignore_sample_class.write_text(
                dedent(
                    """
                class SampleClass:
                    pass
                """
                )
            )

            import_platform_plugin(platform_plugin_dir)

        assert mock_path.insert.call_count == 1
        assert "TestPlugin" in SUPPORTED_PLATFORMS
        assert (
            SUPPORTED_PLATFORMS["TestPlugin"].get_pkg_path()
            == "test_plugin_path"
        )
        assert "SampleClass" not in SUPPORTED_PLATFORMS

    def test_import_platform_plugin_spec_exception(self) -> None:  # noqa: F811
        """
        Test whether the import_platform_plugin function is callable.

        This function is not implemented yet, so we just check if it can
        be called without raising an error.
        """
        SUPPORTED_PLATFORMS.clear()
        with tempfile.TemporaryDirectory() as tempdir:
            platform_plugin_dir = Path(tempdir) / "site_packages"
            test_plugin_dir = platform_plugin_dir / "yarf_plugin_test"
            test_plugin_dir.mkdir(parents=True, exist_ok=True)

            # This file will raise a NameError
            test_plugin_init = test_plugin_dir / "__init__.py"
            test_plugin_init.write_text(
                dedent(
                    """
                from .cramjam import *

                __doc__ = cramjam.__doc__
                if hasattr(cramjam, "__all__"):
                    __all__ = cramjam.__all__
                """
                )
            )

            import_platform_plugin(platform_plugin_dir)
        assert len(SUPPORTED_PLATFORMS) == 0

    @patch("yarf.rf_libraries.libraries.pkgutil.iter_modules")
    def test_import_platform_plugin_empty_dir(
        self, mock_iter_modules: MagicMock
    ) -> None:
        """
        Test whether the import_platform_plugin function handles an empty
        directory without raising an error.
        """
        SUPPORTED_PLATFORMS.clear()

        with tempfile.TemporaryDirectory() as tempdir:
            empty_dir = Path(tempdir) / "empty_dir"
            empty_dir.mkdir(parents=True, exist_ok=True)

            import_platform_plugin(empty_dir)

        mock_iter_modules.assert_not_called()
        assert not SUPPORTED_PLATFORMS

    @pytest.mark.parametrize(
        "dir_path",
        [
            None,
            "non_existent_directory",
        ],
    )
    @patch("yarf.rf_libraries.libraries.pkgutil.iter_modules")
    def test_import_platform_plugin_no_dir(
        self, mock_iter_modules: MagicMock, dir_path: str
    ) -> None:
        """
        Test whether the import_platform_plugin function handles a non-
        existent directory without raising an error.
        """
        SUPPORTED_PLATFORMS.clear()
        import_platform_plugin(dir_path)

        mock_iter_modules.assert_not_called()
        assert not SUPPORTED_PLATFORMS
