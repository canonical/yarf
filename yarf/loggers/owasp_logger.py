"""
OWASP-compliant logger configuration for YARF.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path


class PrettyJSONFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()

        try:
            parsed = json.loads(message)
            pretty = json.dumps(parsed, indent=2, sort_keys=True)
            record.msg = pretty
            record.args = ()
        except Exception:
            # If it's not valid JSON, leave it untouched
            pass

        return super().format(record)


def get_owasp_logger() -> logging.Logger:
    """
    Creates a dedicated OWASP base logger that writes to a single file per
    program execution.

    Returns:
        logging.Logger: Configured OWASP logger instance.
    """
    log_dir = (
        f"{os.getenv('SNAP_USER_COMMON')}/yarf-outdir/security_logs"
        if "SNAP" in os.environ
        else f"{tempfile.gettempdir()}/yarf-outdir/security_logs"
    )

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"owasp_{timestamp}.log"

    logger = logging.getLogger("owasp")
    logger.propagate = False

    # Prevent duplicate handlers if imported multiple times
    if not logger.handlers:
        handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")

        formatter = PrettyJSONFormatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
