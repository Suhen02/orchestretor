import sys

from loguru import logger


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stdout, serialize=True, backtrace=False, diagnose=False)
    logger.add("logs/app.log", rotation="50 MB", retention="7 days", serialize=True)
    logger.add("logs/error.log", level="ERROR", rotation="50 MB", retention="7 days", serialize=True)
