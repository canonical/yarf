import pytest

from yarf.robot.libraries import (
    SUPPORTED_PLATFORMS,
    PlatformBase,
    PlatformMeta,
    import_libraries,
)


class TestPlatformMeta:
    """
    Test the Platform metaclass.
    """

    def test_new(self):
        """
        Test a new item is added to SUPPORTED_PLATFORMS at class creation.
        """

        SUPPORTED_PLATFORMS.clear()

        class TestModule(metaclass=PlatformMeta):
            pass

        assert SUPPORTED_PLATFORMS.get(TestModule.__name__) == TestModule


class TestPlatformBase:
    """
    Test the Platform base class.
    """

    def test_not_implemented(self):
        """
        Test whether the abstractmethods are required when inheriting from
        PlatformBase.
        """

        class TestModule(PlatformBase):
            pass

        with pytest.raises(TypeError):
            TestModule()

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
