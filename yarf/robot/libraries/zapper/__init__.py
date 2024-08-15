import logging
import os
from contextlib import contextmanager
from pathlib import Path

import rpyc
from yarf.robot.libraries import PlatformBase


logger = logging.getLogger()


class Zapper(PlatformBase):
    """
    This platform relies on the Zapper unit connected
    to the DUT as a support machine.

    Requests are handled by RPyC and the server IP
    is retrieved from the ZAPPER_IP environment variable.
    """

    RPYC_PORT = 60000
    RPYC_TIMEOUT = 60

    def __init__(self) -> None:
        pass

    @staticmethod
    def get_pkg_path() -> str:
        return str(Path(__file__).parent)


@contextmanager
def zapper_api(timeout: int = Zapper.RPYC_TIMEOUT):
    """Connect to the Zapper RPyC service and yields the Service object."""

    ip_addr = os.getenv("ZAPPER_IP", "localhost")
    connection = rpyc.connect(
        ip_addr,
        Zapper.RPYC_PORT,
        config={
            "allow_all_attrs": True,
            "sync_request_timeout": timeout,
        },
    )
    logger.debug("Connected to Zapper service at %s", ip_addr)
    try:
        yield connection.root
    finally:
        connection.close()


class ZapperException(Exception):
    """Generic Zapper Exception"""


# Required by RPyC when the server might raise custom exceptions.
# Ref. https://rpyc.readthedocs.io/en/latest/tutorial/tut2.html
rpyc.core.vinegar._generic_exceptions_cache[
    "zapper.exceptions.ZapperServiceError"
] = ZapperException
