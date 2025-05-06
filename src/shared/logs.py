import inspect
import logging
import os
import sys

# ANSI escape codes for colors
LOG_COLORS = {
    "DEBUG": "\033[92m",  # Green
    "INFO": "\033[94m",  # Blue
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",  # Red
    "CRITICAL": "\033[91m",  # Red
}
RESET_COLOR = "\033[0m"
RUNNER_LOG_LEVELS = {
    '0': logging.INFO,
    '1': logging.DEBUG,
}

class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        if levelname in LOG_COLORS:
            colored_levelname = f"{LOG_COLORS[levelname]}[{levelname}]{RESET_COLOR}"
        else:
            colored_levelname = f"[{levelname}]"
        original = self._style._fmt
        self._style._fmt = original.replace("[%(levelname)s]", colored_levelname)
        result = super().format(record)
        self._style._fmt = original  # restore for future calls
        return result


def get_logger(
        name: str,
        log_file: str | None = None,
        level: int | str = None,
        fmt: str = "[%(asctime)s] [%(name)s.%(module)s.%(funcName)s] [%(levelname)s] %(message)s",
        stream: str | object | None = "stdout",
) -> logging.Logger:

    if name in logging.root.manager.loggerDict:
        return logging.getLogger(name)

    logger = logging.getLogger(name)

    if not level:
        level = RUNNER_LOG_LEVELS[os.environ.get("RUNNER_DEBUG", "0")]

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(level)

    if stream:
        color_formatter = ColorFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        stream_obj = {"stdout": sys.stdout, "stderr": sys.stderr}.get(
            stream, stream
        )
        sh = logging.StreamHandler(stream_obj)
        sh.setFormatter(color_formatter)
        logger.addHandler(sh)

    if log_file:
        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
