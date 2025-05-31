"""All functions and features for logging the app"""

import sys
from functools import partialmethod
import loguru
from loguru import logger
from pydantic import BaseModel, ConfigDict


class WatcherConfiguration(BaseModel):
    """
    Configuration settings for generic_requests
    """

    log_level: str = ""
    log_file_path: str = ""
    logger: loguru._logger.Logger = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


def init_logging(config) -> None:
    """Initialization of logging to create log file and set level at beginning of the app.

    Args:
        log_level (str): Configured log level
    """
    logger.remove()
    logger.level("EXTDEBUG", no=9, color="<bold><yellow>")
    logger.__class__.extdebug = partialmethod(logger.__class__.log, "EXTDEBUG")
    logger.add(
        config.watcher.log_file_path, rotation="500 MB", level=config.watcher.log_level
    )
    logger.add(sys.stdout, colorize=True, level=config.watcher.log_level)
    config.watcher.logger = logger
