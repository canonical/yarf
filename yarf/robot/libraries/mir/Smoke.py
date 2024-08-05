from yarf.robot.libraries.smoke_base import SmokeBase
from robot.api import logger
from robot.api.deco import library, keyword


@library
class Smoke(SmokeBase):
    def __init__(self) -> None:
        pass

    @keyword
    def print_smoke(self) -> None:
        logger.info("Smoke test for Mir platform")
