from pathlib import Path
from yarf.robot.libraries import PlatformBase


class Mir(PlatformBase):
    def __init__(self) -> None:
        pass

    def get_pkg_path() -> str:
        return str(Path(__file__).parent)
