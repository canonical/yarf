import argparse
import logging

_logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""

    top_level_parser = argparse.ArgumentParser()
    top_level_parser.add_argument(
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="verbosity",
        help="be very verbose",
        default="INFO",
    )

    top_level_parser.add_argument(
        "--quiet",
        action="store_const",
        const="WARNING",
        dest="verbosity",
        help="be less verbose",
    )

    args = top_level_parser.parse_args()
    print("Hello yarf!")

if __name__ == "__main__":
    main()
