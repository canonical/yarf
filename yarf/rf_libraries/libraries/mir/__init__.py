from pathlib import Path

from yarf.rf_libraries.libraries import PlatformBase


class Mir(PlatformBase):
    def __init__(self) -> None:
        pass

    def get_pkg_path() -> str:
        return str(Path(__file__).parent)
