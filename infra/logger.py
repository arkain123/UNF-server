import logging
import sys

import config


def setup_logger() -> logging.Logger:
    root = logging.getLogger()
    if root.handlers:
        return logging.getLogger("unf.server")

    root.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
    root.addHandler(handler)

    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("websockets").propagate = True

    return logging.getLogger("unf.server")